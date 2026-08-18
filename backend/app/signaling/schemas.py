import uuid
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from app.signaling.ice_breakers import ICE_BREAKERS


class OfferMessage(BaseModel):
    type: Literal["offer"] = "offer"
    sdp: str


class AnswerMessage(BaseModel):
    type: Literal["answer"] = "answer"
    sdp: str


class IceCandidateMessage(BaseModel):
    type: Literal["ice_candidate"] = "ice_candidate"
    candidate: dict[str, Any]


class ChatMessage(BaseModel):
    type: Literal["chat"] = "chat"
    text: str


class IceBreakerMessage(BaseModel):
    """Relayed like chat but never scanned by chat_safety - content must be
    one of the pre-vetted static prompts in ice_breakers.ICE_BREAKERS, not
    freeform input (tasks/ice-breaker.md). Validated against that allowlist
    below so a client can't smuggle arbitrary text through the channel
    that's deliberately exempt from the chat-safety filter."""

    type: Literal["ice_breaker"] = "ice_breaker"
    text: str

    @field_validator("text")
    @classmethod
    def _text_must_be_allowlisted(cls, value: str) -> str:
        if value not in ICE_BREAKERS:
            raise ValueError("ice_breaker text is not a recognized prompt")
        return value


class VideoStatusRequestMessage(BaseModel):
    type: Literal["video_status_request"] = "video_status_request"


class VideoStatusEvent(BaseModel):
    type: Literal["video_status"] = "video_status"
    video_eligible: bool


class PeerJoinedEvent(BaseModel):
    type: Literal["peer_joined"] = "peer_joined"


class PeerLeftEvent(BaseModel):
    type: Literal["peer_left"] = "peer_left"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    detail: str


RelayedFromPeer = (
    OfferMessage | AnswerMessage | IceCandidateMessage | ChatMessage | IceBreakerMessage
)
InboundMessage = RelayedFromPeer | VideoStatusRequestMessage


class RelayEnvelope(BaseModel):
    """Wraps a relayed message with the sender's user id, so the receiver
    can't be spoofed by trusting a client-supplied sender field."""

    from_user_id: uuid.UUID
    message: RelayedFromPeer
