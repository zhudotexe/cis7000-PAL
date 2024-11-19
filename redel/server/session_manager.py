import asyncio
import base64
from collections import defaultdict
from typing import TYPE_CHECKING

from fastapi import WebSocket
from kani import ChatRole

from redel import ReDel
from redel.events import AudioDelta, BaseEvent, Error, KaniMessage, RoundComplete, StreamDelta, EndSession
from .models import SaveMeta, SessionMeta, SessionState

if TYPE_CHECKING:
    from .server import VizServer

_break_sentinel = object()


class SessionManager:
    """Responsible for a single session and all connections to it."""

    def __init__(self, server: "VizServer", redel: ReDel, uid: str):
        self.server = server
        self.redel = redel
        self.redel.add_listener(self.on_event)
        self.task = None
        self.msg_queue = asyncio.Queue()
        self.active_connections: list[WebSocket] = []
        self.uid = uid

        # tts
        self._tts_queues = defaultdict(asyncio.Queue)
        self._tts_tasks = {}
        self.disable_tts = False

    # ==== lifecycle ====
    async def start(self):
        if self.task is not None:
            raise RuntimeError("This session has already been started.")
        self.task = asyncio.create_task(self.redel.chat_from_queue(self.msg_queue))

    async def close(self):
        if self.task is not None:
            self.task.cancel()
        await self.redel.close()

    # ==== state ====
    def get_state(self) -> SessionState:
        kanis = [self.redel.kani.get_save_state()] if self.redel.kani else []
        return SessionState(
            id=self.redel.session_id,
            title=self.redel.title,
            last_modified=self.redel.logger.last_modified,
            n_events=self.redel.logger.event_count.total(),
            extra=self.redel.extra,
            state=kanis,
        )

    def get_session_meta(self) -> SessionMeta:
        return SessionMeta(
            id=self.redel.session_id,
            title=self.redel.title,
            last_modified=self.redel.logger.last_modified,
            n_events=self.redel.logger.event_count.total(),
            extra=self.redel.extra,
        )

    def get_save_meta(self) -> SaveMeta:
        return SaveMeta(
            id=self.redel.session_id,
            title=self.redel.title,
            last_modified=self.redel.logger.last_modified,
            n_events=self.redel.logger.event_count.total(),
            extra=self.redel.extra,
            grouping_prefix=self.redel.logger.log_dir.parent.parts,
            state_fp=self.redel.logger.state_path,
            event_fp=self.redel.logger.aof_path,
        )

    # ==== ws ====
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: str):
        await asyncio.gather(
            *(connection.send_text(data) for connection in self.active_connections), return_exceptions=True
        )

    async def on_event(self, event: BaseEvent):
        await self.broadcast(event.model_dump_json())
        # update the server save info on each RoundComplete
        if isinstance(event, RoundComplete):
            self.server.saves[self.redel.session_id] = self.get_save_meta()

    # ==== PAL ====
    async def register_tts_listener(self):
        async def on_event(event):
            if self.disable_tts:
                return
            
            if isinstance(event, StreamDelta):
                # for each text stream token, TTS task it if it does not exist
                if event.id not in self._tts_tasks:
                    task = asyncio.create_task(self._tts_impl(event.id))
                    self._tts_tasks[event.id] = task
                    task.add_done_callback(lambda _: self._tts_tasks.pop(event.id, None))
                # otherwise append the text to the processing stream
                await self._tts_queues[event.id].put(event.delta)
            if isinstance(event, KaniMessage) and event.id in self._tts_queues and event.msg.role == ChatRole.ASSISTANT:
                await self._tts_queues[event.id].put(_break_sentinel)

        self.redel.add_listener(on_event)

    async def _tts_impl(self, kani_id: str):
        # 11labs' main library does not currently support async input streaming yet, so we use a community fork
        # (which I forked to fix pip metadata)
        # pip install "git+https://github.com/zhudotexe/elevenlabs-python-async-temp.git"

        async def _stream():
            q = self._tts_queues[kani_id]
            while True:
                item = await q.get()
                if item is _break_sentinel:
                    return
                yield item

        try:
            # noinspection PyTypeChecker
            audio_stream = await self.server.eleven.generate(
                text=_stream(),
                voice=self.redel.extra.get("patient_voice", "Brian"),  # default voice if none specified
                model="eleven_turbo_v2_5",
                stream=True,
                output_format="pcm_24000",
            )
            async for audio_bytes in audio_stream:
                audio_string = base64.b64encode(audio_bytes).decode("utf-8")
                self.redel.dispatch(AudioDelta(id=kani_id, delta=audio_string))
        except Exception as e:
            self.redel.dispatch(Error(msg=str(e), scope="voice"))
            raise
