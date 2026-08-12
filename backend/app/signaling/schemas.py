import uuid
from typing import Any, Literal

from pydantic import BaseModel


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


RelayedFromPeer = OfferMessage | AnswerMessage | IceCandidateMessage | ChatMessage
InboundMessage = RelayedFromPeer | VideoStatusRequestMessage


class RelayEnvelope(BaseModel):
    """Wraps a relayed message with the sender's user id, so the receiver
    can't be spoofed by trusting a client-supplied sender field."""

    from_user_id: uuid.UUID
    message: RelayedFromPeer
