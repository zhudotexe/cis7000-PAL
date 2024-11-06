import asyncio
import functools
import logging
import time
import uuid
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any, Awaitable, Callable

import kani.exceptions
from kani import ChatRole, chat_in_terminal_async
from kani.engines import BaseEngine

from . import events
from .base_kani import BaseKani
from .eventlogger import EventLogger
from .utils import AUTOGENERATE_TITLE, AutogenerateTitle, generate_conversation_title

log = logging.getLogger(__name__)


@functools.cache
def default_engine():
    try:
        from kani.engines.openai import OpenAIEngine
    except kani.exceptions.MissingModelDependencies:
        raise ImportError(
            'Default OpenAI engine is not installed. You can either install it using `pip install "kani[openai]"` or'
            " specify the engine to use in your ReDel system."
        )

    return OpenAIEngine(model="gpt-4o", temperature=0.8, top_p=0.95)


class ReDel:
    """This class represents a single session of a recursive multi-agent system.

    It's responsible for:

    * all delegation configuration options
    * all the spawned kani and their relations within the session
    * dispatching all events from the session
    * logging events

    All arguments to the constructor are keyword arguments.
    """

    def __init__(
        self,
        *,
        # engines
        engine: BaseEngine = None,
        # prompt/kani
        system_prompt: str | None = None,
        kani_kwargs: dict = None,
        # logging
        title: str | AutogenerateTitle | None = AUTOGENERATE_TITLE,
        log_dir: Path = None,
        clear_existing_log: bool = False,
        session_id: str = None,
    ):
        """
        :param engine: The engine to use for the kani. (default: gpt-4o)
            See :external+kani:doc:`engines` for a list of available engines and their capabilities.
        :param system_prompt: The system prompt for the kani. See ``redel.kanis`` for default.
        :param kani_kwargs: Additional keyword args to pass to :class:`kani.Kani`.
        :param title: The title of this session. Set to ``redel.AUTOGENERATE_TITLE`` to automatically generate one
            (default), or ``None`` to disable title generation.
        :param log_dir: A path to a directory to save logs for this session. Defaults to
            ``$REDEL_HOME/instances/{session_id}/`` (default ``~/.redel/instances/{session_id}``).
        :param clear_existing_log: If the log directory has existing events, clear them before writing new events.
            Otherwise, append to existing events.
        :param session_id: The ID of this session. Generally this should not be set manually; it is used for loading
            previous states.
        """
        if engine is None:
            engine = default_engine()
        if kani_kwargs is None:
            kani_kwargs = {}

        # engines
        self.engine = engine
        # prompt/kani
        self.system_prompt = system_prompt
        self.kani_kwargs = kani_kwargs

        # internals
        self._init_lock = asyncio.Lock()

        # events
        self.listeners = []
        self.event_queue = asyncio.Queue()
        self.dispatch_task = None
        # state
        self.session_id = session_id or f"{int(time.time())}-{uuid.uuid4()}"
        if title is AUTOGENERATE_TITLE:
            self.title = None
            self.add_listener(self.create_title_listener)
        else:
            self.title = title
        # logging
        self.logger = EventLogger(self, self.session_id, log_dir=log_dir, clear_existing_log=clear_existing_log)
        self.add_listener(self.logger.log_event)
        # kanis
        self.kani = None

    async def ensure_init(self):
        """Called at least once before any messaging happens. Used to do async init. Must be idempotent."""
        async with self._init_lock:  # lock in case of parallel calls - no double creation
            if self.kani is None:
                self.kani = BaseKani(
                    self.engine,
                    app=self,
                    name="root",
                    system_prompt=self.system_prompt,
                    **self.kani_kwargs,
                )
                self.dispatch(events.KaniSpawn.from_kani(self.kani))
            if self.dispatch_task is None:
                self.dispatch_task = asyncio.create_task(
                    self._dispatch_task(), name=f"redel-dispatch-{self.session_id}"
                )

    # === entrypoints ===
    async def chat_from_queue(self, q: asyncio.Queue):
        """Get chat messages from a provided queue. Used internally in the visualization server."""
        await self.ensure_init()
        while True:
            # main loop
            try:
                user_msg = await q.get()
                log.info(f"Message from queue: {user_msg.content!r}")
                async for stream in self.kani.full_round_stream(user_msg.content):
                    msg = await stream.message()
                    if msg.role == ChatRole.ASSISTANT:
                        log.info(f"AI: {msg}")
            except Exception:
                log.exception("Error in chat_from_queue:")
            finally:
                self.dispatch(events.RoundComplete(session_id=self.session_id))
                await self.logger.write_state()  # autosave

    async def chat_in_terminal(self):
        """Chat with the defined system in the terminal. Prints function calls and root messages to the terminal."""
        await self.ensure_init()
        while True:
            try:
                await chat_in_terminal_async(self.kani, show_function_args=True, rounds=1)
            except KeyboardInterrupt:
                await self.close()
            finally:
                self.dispatch(events.RoundComplete(session_id=self.session_id))
                await self.logger.write_state()  # autosave

    async def query(self, query: str) -> AsyncIterable[events.BaseEvent]:
        """Run one round with the given query.

        Yields all loggable events from the app (i.e. no stream deltas) during the query. To get only messages
        from the root, filter for `events.RootMessage`.
        """
        await self.ensure_init()

        # register a new listener which passes events into a local queue
        q = asyncio.Queue()
        self.add_listener(q.put)

        # submit query to the kani to run in bg
        async def _task():
            try:
                async for _ in self.kani.full_round(query):
                    pass
            finally:
                self.dispatch(events.RoundComplete(session_id=self.session_id))
                await self.logger.write_state()  # autosave

        task = asyncio.create_task(_task())

        # yield from the q until we get a RoundComplete
        while True:
            event = await q.get()
            if event.__log_event__:
                yield event
            if event.type == "round_complete":
                break

        # ensure task is completed and cleanup
        await task
        self.remove_listener(q.put)

    # === events ===
    def add_listener(self, callback: Callable[[events.BaseEvent], Awaitable[Any]]):
        """
        Add a listener which is called for every event dispatched by the system.
        The listener must be an asynchronous function that takes in an event in a single argument.
        """
        self.listeners.append(callback)

    def remove_listener(self, callback):
        """Remove a listener added by :meth:`add_listener`."""
        self.listeners.remove(callback)

    async def _dispatch_task(self):
        while True:
            # noinspection PyBroadException
            try:
                event = await self.event_queue.get()
                # get listeners, call them
                await asyncio.gather(*(callback(event) for callback in self.listeners), return_exceptions=True)
            except Exception:
                log.exception("Exception when dispatching event:")

    def dispatch(self, event: events.BaseEvent):
        """Dispatch an event to all listeners.
        Technically this just adds it to a queue and then an async background task dispatches it."""
        self.event_queue.put_nowait(event)

    # === resources + app lifecycle ===
    async def create_title_listener(self, event):
        """A listener that generates a conversation title after 4 root message events."""
        if (
            self.title is None
            and isinstance(event, events.RootMessage)
            and self.logger.event_count["root_message"] >= 4
            and event.msg.role == ChatRole.ASSISTANT
            and event.msg.content
        ):
            self.title = "..."  # prevent another message from generating a title
            try:
                self.title = await generate_conversation_title(self.kani)
            except Exception:
                log.exception("Could not generate conversation title:")
                self.title = None
            finally:
                self.remove_listener(self.create_title_listener)

    async def close(self):
        """Clean up all the app resources."""
        if self.dispatch_task is not None:
            self.dispatch_task.cancel()
        await asyncio.gather(self.logger.close(), self.kani.close())
