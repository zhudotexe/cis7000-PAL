import asyncio
import base64
import io
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Awaitable, Callable, Collection

from elevenlabs.client import AsyncElevenLabs
from kani.engines import BaseEngine
from kani import ChatMessage, ChatRole
from openai import AsyncOpenAI
from pydub import AudioSegment

try:
    from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, WebSocketException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
except ImportError:
    raise ImportError(
        "You are missing required dependencies to use the bundled web viewer. Please install ReDel using `pip install"
        ' "redel[web]"`.'
    ) from None

from redel import ReDel, pal_sessions
from redel.config import DEFAULT_LOG_DIR
from redel.events import Error, SendAudio, SendMessage
from redel.utils import read_jsonl
from .indexer import find_saves
from .models import SaveMeta, SessionMeta, SessionState
from .session_manager import SessionManager

VIZ_DIST = Path(__file__).parent / "viz_dist"
log = logging.getLogger("server")


class VizServer:
    def __init__(
        self,
        *,
        # config for kanis
        engine: BaseEngine = None,
        system_prompt: str | None = None,
        kani_kwargs: dict = None,
        # replay
        save_dirs: Collection[Path] = (DEFAULT_LOG_DIR,),
        # helpers
        startup_fn: Callable[["VizServer"], Awaitable] = None,
    ):
        """
        :param engine: The engine to use for each kani managed by this server. (default: gpt-4o)
            See :external+kani:doc:`engines` for a list of available engines and their capabilities.
        :param system_prompt: The system prompt for each new kani managed by this server.
        :param kani_kwargs: Additional keyword args to pass to :class:`kani.Kani`.
        :param save_dirs: A list of paths to scan for ReDel saves to make available to load. Defaults to
            ``~/.redel/instances/``.
        :param startup_fn: An async function to call before server startup.
        """
        self.engine = engine
        self.system_prompt = system_prompt
        self.kani_kwargs = kani_kwargs
        self.startup_fn = startup_fn

        # saves
        self.save_dirs = save_dirs
        self.saves: dict[str, SaveMeta] = {}

        # interactive session states
        self.interactive_sessions: dict[str, SessionManager] = {}

        # webserver
        self.fastapi = FastAPI(lifespan=self._lifespan)
        self.setup_app()

        # pal
        self.openai = AsyncOpenAI()
        self.eleven = AsyncElevenLabs()

    # ==== utils ====
    async def reindex_saves(self):
        """Asynchronously walk the save_dirs and update self.saves."""

        def _index():
            new_saves = {}
            for root in self.save_dirs:
                for save in find_saves(root):
                    new_saves[save.id] = save
            self.saves = new_saves
            log.info(f"Finished indexing saves - {len(self.saves)} files loaded.")

        # most of the time is spent in IO with the filesystem so we can thread this
        await asyncio.get_event_loop().run_in_executor(None, _index)

    async def create_new_redel(self, **kwargs) -> ReDel:
        """Return a new ReDel instance given the server config."""
        return ReDel(engine=self.engine, system_prompt=self.system_prompt, kani_kwargs=self.kani_kwargs, **kwargs)

    async def append_new_redel(self, redel: ReDel, uid: str = None):
        """Start tracking the given redel in this server."""
        manager = SessionManager(self, redel, uid=uid)
        self.interactive_sessions[redel.session_id] = manager
        self.saves[redel.session_id] = manager.get_save_meta()
        await manager.start()
        return manager

    def serve(self, host="127.0.0.1", port=8000, **kwargs):
        """Serve this server at the given IP and port. Blocks until interrupted."""
        import uvicorn

        uvicorn.run(self.fastapi, host=host, port=port, **kwargs)

    # ==== fastapi ====
    @asynccontextmanager
    async def _lifespan(self, _: FastAPI):
        _ = asyncio.create_task(self.reindex_saves())
        if self.startup_fn is not None:
            await self.startup_fn(self)
        yield
        await asyncio.gather(*(session.close() for session in self.interactive_sessions.values()))

    def setup_app(self):
        """Set up the FastAPI routes, middleware, etc."""
        # cors middleware
        # noinspection PyTypeChecker
        self.fastapi.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
        )

        # ===== routes =====
        # ---- saves ----
        @self.fastapi.get("/api/saves")
        async def list_saves() -> list[SaveMeta]:
            """List all the saves the server is configured to see."""
            return list(self.saves.values())

        @self.fastapi.get("/api/saves/{save_id}")
        async def get_save_state(save_id: str) -> SessionState:
            """Get the state saves in a given save (not interactive - this just loads from file)."""
            if save_id not in self.saves:
                raise HTTPException(404, "save not found")
            save = self.saves[save_id]
            return SessionState.model_validate_json(save.state_fp.read_text())

        @self.fastapi.get("/api/saves/{save_id}/events")
        async def get_save_events(save_id: str):
            """Get all events in a given save (not interactive - this just loads from file)."""
            if save_id not in self.saves:
                raise HTTPException(404, "save not found")
            save = self.saves[save_id]
            return list(read_jsonl(save.event_fp))

        @self.fastapi.delete("/api/saves/{save_id}")
        async def delete_save(save_id: str) -> SaveMeta:
            """Delete the state and event files of the given save, and the directory they're contained in if empty."""
            if save_id not in self.saves:
                raise HTTPException(404, "save not found")
            save = self.saves[save_id]
            try:
                save.state_fp.unlink(missing_ok=True)
                save.event_fp.unlink(missing_ok=True)
                del self.saves[save_id]
                save.state_fp.parent.rmdir()
            except FileNotFoundError:
                raise HTTPException(404, "save not found")
            except OSError as e:
                # probably additional files - let's just log it
                log.warning(f"Could not fully delete save: {e}")
            return save

        # ---- interactive ----
        @self.fastapi.get("/api/states")
        async def list_states_interactive(uid: str = None) -> list[SessionMeta]:
            """List the interactive sessions currently loaded by the server."""
            if uid:
                return [
                    manager.get_session_meta() for manager in self.interactive_sessions.values() if manager.uid == uid
                ]
            return [manager.get_session_meta() for manager in self.interactive_sessions.values()]

        @self.fastapi.post("/api/states")
        async def create_state_interactive(
            start_content: Annotated[str, Body(embed=True)] = None, uid: str = None
        ) -> SessionState:
            """Create a fresh new interactive session, optionally with a first user message.
            This will also create a new save.
            """
            session_id = f"{int(time.time())}-{uuid.uuid4()}"
            log_dir = (DEFAULT_LOG_DIR / uid / session_id) if uid else (DEFAULT_LOG_DIR / session_id)
            # create a new redel instance given the settings
            redel = await self.create_new_redel(log_dir=log_dir, session_id=session_id)
            # assign it to a sessionmanager and start
            manager = await self.append_new_redel(redel, uid=uid)
            if start_content:
                await manager.msg_queue.put(SendMessage(content=start_content))
            return manager.get_state()

        @self.fastapi.get("/api/states/{session_id}")
        async def get_state_interactive(session_id: str) -> SessionState:
            """Get the state of a specific interactive session loaded in the server."""
            if session_id not in self.interactive_sessions:
                raise HTTPException(404, "session is not initialized - load from archive or create new first")
            manager = self.interactive_sessions[session_id]
            return manager.get_state()

        @self.fastapi.websocket("/api/ws/{session_id}")
        async def ws_interactive(websocket: WebSocket, session_id: str):
            """Stream events from a given session loaded in the server."""
            if session_id not in self.interactive_sessions:
                raise WebSocketException(
                    1008,  # policy violation
                    "session is not initialized - load from archive or create new first",
                )
            manager = self.interactive_sessions[session_id]
            await manager.connect(websocket)
            await manager.register_tts_listener()  # todo disable switch
            while True:
                try:
                    data = await websocket.receive_json()
                    log.debug(f"got data from ws for session {session_id}: {data}")

                    # if it's an audio message, transcribe it
                    if data["type"] == "send_audio":
                        manager.disable_tts = False
                        audio_event = SendAudio.model_validate(data)
                        audio_bytes = base64.b64decode(audio_event.audio)
                        transcript = await self.whisper_transcribe(audio_bytes)
                        event = SendMessage(content=transcript)
                    elif data["type"] == "end_session":
                        manager.disable_tts = True
                        eval_message = self.generate_evaluation(data["transcript"])
                        event = SendMessage(content=eval_message)
                    # otherwise push the message onto the queue
                    else:
                        manager.disable_tts = True
                        event = SendMessage.model_validate(data)

                    await manager.msg_queue.put(event)
                except WebSocketDisconnect:
                    manager.disconnect(websocket)
                    break
                except Exception as e:
                    log.exception(f"Exception on ws event in session {session_id}:")
                    await websocket.send_text(Error(msg=str(e)).model_dump_json())

        # ---- PAL session helper ----
        @self.fastapi.post("/api/init-pal-states")
        async def init_pal_states(uid: str) -> list[SessionState]:
            """
            Create the three default PAL states for the given user ID and return them.
            """
            if sum(1 for manager in self.interactive_sessions.values() if manager.uid == uid) >= 3:
                return []
            states = []
            for pal_redel in await pal_sessions.get_default_sessions(self.engine, uid=uid):
                manager = await self.append_new_redel(pal_redel, uid=uid)
                states.append(manager.get_state())
            return states

        # viz static files
        if not VIZ_DIST.exists():
            raise RuntimeError(
                f"The {VIZ_DIST} directory does not exist. If you have cloned ReDel from source, this is likely because"
                " you need to build the web frontend.\nSee"
                " https://redel.readthedocs.io/en/latest/install.html#building-web-interface for more information."
            )
        self.fastapi.mount("/", StaticFiles(directory=VIZ_DIST, html=True), name="viz")

    # ===== PAL utils =====
    def generate_evaluation(self, transcript: str):
        message = f"Analyze a transcript from a doctor-patient encounter and provide actionable communication improvement advice for the doctor.\n\nConsider effective communication tools such as NURSE statements, avoiding jargon, and preventing common learner hiccups. Your advice should be clear, specific, and include practical steps for improvement. Address emotional cues and provide suggestions to optimize patient understanding and support. You should speak directly to the doctor and use second person pronouns. Do not enumerate your response.\n\n# Steps\n\n- **Analyze Transcript:**\n  - Identify moments where the doctor's communication can be improved.\n  - Assess instances where the doctor faced emotionally driven reactions from the patient/family, and determine whether appropriate NURSE statements were used.\n\n- **Identify Gaps and Give Actionable Feedback:**\n  - Focus on common learner hiccups like skipping initial steps, unclear headlines, or neglecting to offer NURSE statements.\n  - Offer suggestions that go beyond simple feedback, outlining specific ways the doctor can alter their phrasing or behavior.\n\n- **Provide Emotional Support Guidance:**\n  - When providing alternate suggestions, use examples that appropriately name emotions, offer understanding or respect, explore emotions, or provide emotional support.\n\n- **Link Feedback to Techniques:**\n  - Clearly link feedback to provided communication methods such as NURSE statements, offering enhanced implementation or corrections.\n\n# Output Format\n\nProvide feedback in a list format where:\n- Each item contains **a specific scenario/moment** that could be improved.\n- Each item includes **detailed suggestions** for what the doctor could say differently, and why this change is beneficial.\n- Use **NURSE-related language** where applicable and avoid broad, unspecific comments.\n\nExample Feedback Segment:\n1. **Scenario**: Doctor introduces prognosis without assessing the emotion.\n   - **Current Approach**: \"The prognosis is not very good.\"\n   - **Improvement Suggestion**: Add an understanding statement first. For instance, \"I know this must be really hard to hear.\" This would help in validating the patient's feelings, allowing them space to process the news and feel understood.\n\n2. **Scenario**: Doctor uses medical jargon.\n   - **Current Approach**: \"There's evidence of multisystem organ failure.\"\n   - **Improvement Suggestion**: Replace jargon with simpler language. Try, \"We're noticing that several of their important organs are starting to not work as they should.\" This ensures that the patient and their family can follow and understand the diagnosis clearly.\n\n3. **Scenario**: Doctor doesn't explore the family member's concerns after giving troubling news.\n   - **Current Approach**: \"This must be really hard. But let's talk about next steps.\"\n   - **Improvement Suggestion**: Instead, pause after acknowledging their concerns with an explore statement: \"Can you tell me more about what's on your mind right now?\" This gives an opportunity for the family member to voice their concerns and ensures they feel heard.\n\n# Notes\n\n- **Avoid Fake NURSE Statements**: Ensure the given NURSE statement is sincere, and allow adequate space for the patient to react.\n- **Avoid Jargon or Vague Headline Information**: Deliver information directly with clear, patient-friendly language.\n- **Adjust Emotional Attunement**: Pay attention to phrases like \"I understand,\" which can come across as overconfident about a family's experience. Use phrases like \"I can't imagine what you're feeling\" to show empathy without overstepping.\n# Transcript:\n{transcript}"

        return message

    async def whisper_transcribe(self, audio_bytes: bytes) -> str:
        # We assume the audio bytes are PCM16LE single channel 24kHz
        audio = AudioSegment(data=audio_bytes, sample_width=2, channels=1, frame_rate=24000)
        audio_io = io.BytesIO()
        audio_io.name = "audio.mp3"
        audio.export(audio_io, "mp3")
        resp = await self.openai.audio.transcriptions.create(
            file=audio_io,
            model="whisper-1",
            language="en",
            response_format="json",
        )
        return resp.text
