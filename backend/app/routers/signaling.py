import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_user_for_session_token
from app.chat_safety.service import clear_call_state, scan_chat_message
from app.db import get_db
from app.signaling.registry import CallFullError, call_registry
from app.signaling.schemas import (
    AnswerMessage,
    ChatMessage,
    ErrorEvent,
    IceCandidateMessage,
    InboundMessage,
    OfferMessage,
    PeerJoinedEvent,
    PeerLeftEvent,
    RelayEnvelope,
    VideoStatusEvent,
    VideoStatusRequestMessage,
)
from app.signaling.turn import generate_turn_credentials
from app.verification.service import is_video_eligible

router = APIRouter(tags=["signaling"])

_db_dependency = Depends(get_db)

_MESSAGE_TYPES: dict[str, type[InboundMessage]] = {
    "offer": OfferMessage,
    "answer": AnswerMessage,
    "ice_candidate": IceCandidateMessage,
    "chat": ChatMessage,
    "video_status_request": VideoStatusRequestMessage,
}


async def _authenticate(websocket: WebSocket, db: AsyncSession) -> uuid.UUID | None:
    token = websocket.query_params.get("token")
    if not token:
        return None

    user = await get_user_for_session_token(db, token)
    return user.id if user else None


def _parse_call_user_ids(call_id: str) -> tuple[uuid.UUID, uuid.UUID] | None:
    """call_id is `<sorted_user_a>:<sorted_user_b>` (see call_id_for_pair)."""
    parts = call_id.split(":")
    if len(parts) != 2:
        return None
    try:
        return (uuid.UUID(parts[0]), uuid.UUID(parts[1]))
    except ValueError:
        return None


@router.websocket("/signaling/ws")
async def signaling_ws(
    websocket: WebSocket,
    db: AsyncSession = _db_dependency,
) -> None:
    user_id = await _authenticate(websocket, db)
    if user_id is None:
        await websocket.close(code=4401, reason="Not authenticated")
        return

    call_id = websocket.query_params.get("call_id")
    if not call_id:
        await websocket.close(code=4400, reason="Missing call_id")
        return

    call_user_ids = _parse_call_user_ids(call_id)
    if call_user_ids is None or user_id not in call_user_ids:
        await websocket.close(code=4403, reason="Not a participant in this call")
        return
    partner_id = call_user_ids[0] if call_user_ids[1] == user_id else call_user_ids[1]

    try:
        previous_socket = call_registry.join(call_id, user_id, websocket)
    except CallFullError:
        await websocket.close(code=4409, reason="Call already has two participants")
        return

    try:
        if previous_socket is not None:
            await previous_socket.close(code=4409, reason="Replaced by a new connection")

        await websocket.accept()
        await websocket.send_json(generate_turn_credentials(user_id).model_dump())

        peer_socket = call_registry.peer_socket(call_id, user_id)
        if peer_socket is not None:
            await peer_socket.send_json(PeerJoinedEvent().model_dump())
            await websocket.send_json(PeerJoinedEvent().model_dump())

        while True:
            raw = await websocket.receive_json()
            if not isinstance(raw, dict):
                await websocket.send_json(
                    ErrorEvent(detail="Message must be a JSON object").model_dump()
                )
                continue

            msg_type = raw.get("type")
            schema = _MESSAGE_TYPES.get(msg_type) if isinstance(msg_type, str) else None
            if schema is None:
                await websocket.send_json(
                    ErrorEvent(detail=f"Unknown message type: {msg_type}").model_dump()
                )
                continue

            try:
                message = schema.model_validate(raw)
            except ValidationError as exc:
                await websocket.send_json(ErrorEvent(detail=str(exc)).model_dump())
                continue

            if isinstance(message, VideoStatusRequestMessage):
                # Re-evaluated fresh against both current participants on every
                # request, never cached - per tasks/10-age-verification.md.
                video_eligible = await is_video_eligible(db, user_id) and await is_video_eligible(
                    db, partner_id
                )
                await websocket.send_json(
                    VideoStatusEvent(video_eligible=video_eligible).model_dump()
                )
                continue

            if isinstance(message, ChatMessage):
                # Server-relayed (not P2P datachannel) specifically so the
                # server can see plaintext for the safety filter - see
                # tasks/04-webrtc-signaling.md and
                # tasks/13-chat-safety-filters.md. Silent: never surfaced to
                # either user, never blocks/delays the relay below.
                await scan_chat_message(
                    db,
                    call_session_id=call_id,
                    sender_id=user_id,
                    recipient_id=partner_id,
                    text=message.text,
                )

            peer_socket = call_registry.peer_socket(call_id, user_id)
            if peer_socket is not None:
                envelope = RelayEnvelope(from_user_id=user_id, message=message)
                await peer_socket.send_json(envelope.model_dump(mode="json"))

    except WebSocketDisconnect:
        pass
    finally:
        left = call_registry.leave(call_id, user_id, websocket)
        if left:
            clear_call_state(call_id)
            peer_socket = call_registry.peer_socket(call_id, user_id)
            if peer_socket is not None:
                await peer_socket.send_json(PeerLeftEvent().model_dump())
