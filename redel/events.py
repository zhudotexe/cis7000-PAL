import abc
import time
from typing import Literal

from kani import ChatMessage, ChatRole
from pydantic import BaseModel, Field

from .state import KaniState, RunState


class BaseEvent(BaseModel, abc.ABC):
    """The base event that all other events should inherit from."""

    __log_event__ = True  # whether or not the event should be logged
    type: str
    timestamp: float = Field(default_factory=time.time)


# server events
class Error(BaseEvent):
    type: Literal["error"] = "error"
    scope: str | None = None
    msg: str


class KaniSpawn(KaniState, BaseEvent):
    """
    A new kani was spawned. Includes the state of the kani. See :class:`.BaseKani`.

    The ID can be the same as an existing ID, in which case this event should overwrite the previous state.
    """

    type: Literal["kani_spawn"] = "kani_spawn"


class KaniStateChange(BaseEvent):
    """
    A kani's run state changed.

    This is primarily used for rendering the color of a node in the web interface.
    """

    type: Literal["kani_state_change"] = "kani_state_change"
    id: str
    state: RunState


class TokensUsed(BaseEvent):
    """A kani just finished a request to the engine, which used this many tokens."""

    type: Literal["tokens_used"] = "tokens_used"
    id: str
    prompt_tokens: int
    completion_tokens: int


class KaniMessage(BaseEvent):
    """A kani added a message to its chat history."""

    type: Literal["kani_message"] = "kani_message"
    id: str
    msg: ChatMessage


class RootMessage(BaseEvent):
    """
    The root kani has a new result.

    This will be fired *in addition* to a ``kani_message`` event.
    """

    type: Literal["root_message"] = "root_message"
    msg: ChatMessage


class StreamDelta(BaseEvent):
    """A kani is streaming and emitted a new token."""

    __log_event__ = False

    type: Literal["kani_message"] = "stream_delta"
    id: str
    delta: str
    role: ChatRole


class AudioDelta(BaseEvent):
    """A kani is streaming and is playing this audio."""

    __log_event__ = False

    type: Literal["audio_delta"] = "audio_delta"
    id: str
    delta: str


class RoundComplete(BaseEvent):
    """The root kani has finished a full round and control should be handed off to the user."""

    type: Literal["round_complete"] = "round_complete"
    session_id: str


class EndSession(BaseEvent):
    """The session has ended and the server should push an evaluation message."""

    type: Literal["end_session"] = "end_session"
    trancript: str

# user events
class SendMessage(BaseEvent):
    """Send a user message to the root kani and request a completion."""

    type: Literal["send_message"] = "send_message"
    content: str


class SendAudio(BaseEvent):
    """Send an audio message to the root kani, transcribe it, and request a completion."""

    type: Literal["send_audio"] = "send_audio"
    audio: str


# todo if we want to do realtime streaming
# class SendAudioStream(BaseEvent):
#     type: Literal["kani_message"] = "send_audio_chunk"
#     delta: str
