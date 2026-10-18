import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import bearer_token
from app.auth.service import get_user_for_session_token
from app.chat_safety.service import clear_call_state as clear_chat_safety_state
from app.chat_safety.service import scan_chat_message
from app.db import get_db
from app.mini_games import service as mini_games_service
from app.mini_games.schemas import (
    GameAcceptMessage,
    GameClosedEvent,
    GameCloseMessage,
    GameDeclinedEvent,
    GameDeclineMessage,
    GameInviteEvent,
    GameNextMessage,
    GamePromptEvent,
    GameRevealedEvent,
    GameRevealMessage,
    GameStartedEvent,
    GameStartMessage,
    InboundGameMessage,
    PublicGamePrompt,
)
from app.signaling.registry import CallFullError, call_registry
from app.signaling.schemas import (
    AnswerMessage,
    ChatMessage,
    ErrorEvent,
    IceBreakerMessage,
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
from app.ws import reject_websocket

router = APIRouter(tags=["signaling"])

_db_dependency = Depends(get_db)

_MESSAGE_TYPES: dict[str, type[InboundMessage | InboundGameMessage]] = {
    "offer": OfferMessage,
    "answer": AnswerMessage,
    "ice_candidate": IceCandidateMessage,
    "chat": ChatMessage,
    "ice_breaker": IceBreakerMessage,
    "video_status_request": VideoStatusRequestMessage,
    "game_start": GameStartMessage,
    "game_accept": GameAcceptMessage,
    "game_decline": GameDeclineMessage,
    "game_next": GameNextMessage,
    "game_reveal": GameRevealMessage,
    "game_close": GameCloseMessage,
}


async def _authenticate(websocket: WebSocket, db: AsyncSession) -> uuid.UUID | None:
    # Header, not a query param: URLs end up in access logs and trace spans.
    token = bearer_token(websocket.headers.get("authorization"))
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
        await reject_websocket(websocket, 4401, "Not authenticated")
        return

    call_id = websocket.query_params.get("call_id")
    if not call_id:
        await reject_websocket(websocket, 4400, "Missing call_id")
        return

    call_user_ids = _parse_call_user_ids(call_id)
    if call_user_ids is None or user_id not in call_user_ids:
        await reject_websocket(websocket, 4403, "Not a participant in this call")
        return
    partner_id = call_user_ids[0] if call_user_ids[1] == user_id else call_user_ids[1]

    try:
        previous_socket = call_registry.join(call_id, user_id, websocket)
    except CallFullError:
        await reject_websocket(websocket, 4409, "Call already has two participants")
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

            if isinstance(message, GameStartMessage):
                # Structured control data, not freeform text - deliberately
                # not run through scan_chat_message (tasks/mini-games.md).
                mini_games_service.start_game(call_id, message.game_type, user_id)
                peer_socket = call_registry.peer_socket(call_id, user_id)
                if peer_socket is not None:
                    await peer_socket.send_json(
                        GameInviteEvent(
                            game_type=message.game_type, from_user_id=user_id
                        ).model_dump(mode="json")
                    )
                continue

            if isinstance(message, GameAcceptMessage):
                pending = mini_games_service.get_session(call_id)
                if pending is None or pending.requested_by == user_id:
                    continue
                session = mini_games_service.accept_game(call_id)
                if session is None:
                    continue
                prompt = await mini_games_service.pick_next_prompt(db, session)
                if prompt is None:
                    continue
                event = GameStartedEvent(
                    game_type=session.game_type, prompt=PublicGamePrompt.from_prompt(prompt)
                ).model_dump(mode="json")
                await websocket.send_json(event)
                peer_socket = call_registry.peer_socket(call_id, user_id)
                if peer_socket is not None:
                    await peer_socket.send_json(event)
                continue

            if isinstance(message, GameDeclineMessage):
                pending = mini_games_service.get_session(call_id)
                if pending is None or pending.requested_by == user_id:
                    continue
                mini_games_service.close_game(call_id)
                peer_socket = call_registry.peer_socket(call_id, user_id)
                if peer_socket is not None:
                    await peer_socket.send_json(GameDeclinedEvent().model_dump())
                continue

            if isinstance(message, GameNextMessage):
                session = mini_games_service.get_session(call_id)
                if session is None or not session.accepted:
                    continue
                prompt = await mini_games_service.pick_next_prompt(db, session)
                if prompt is None:
                    continue
                event = GamePromptEvent(prompt=PublicGamePrompt.from_prompt(prompt)).model_dump(
                    mode="json"
                )
                await websocket.send_json(event)
                peer_socket = call_registry.peer_socket(call_id, user_id)
                if peer_socket is not None:
                    await peer_socket.send_json(event)
                continue

            if isinstance(message, GameRevealMessage):
                session = mini_games_service.get_session(call_id)
                if session is None or not session.accepted:
                    continue
                session.revealed = True
                correct_option = (
                    session.current_prompt.correct_option if session.current_prompt else None
                )
                event = GameRevealedEvent(correct_option=correct_option).model_dump()
                await websocket.send_json(event)
                peer_socket = call_registry.peer_socket(call_id, user_id)
                if peer_socket is not None:
                    await peer_socket.send_json(event)
                continue

            if isinstance(message, GameCloseMessage):
                mini_games_service.close_game(call_id)
                event = GameClosedEvent().model_dump()
                await websocket.send_json(event)
                peer_socket = call_registry.peer_socket(call_id, user_id)
                if peer_socket is not None:
                    await peer_socket.send_json(event)
                continue

            peer_socket = call_registry.peer_socket(call_id, user_id)
            if peer_socket is not None:
                envelope = RelayEnvelope(from_user_id=user_id, message=message)
                await peer_socket.send_json(envelope.model_dump(mode="json"))

    except WebSocketDisconnect:
        pass
    finally:
        left = call_registry.leave(call_id, user_id, websocket)
        if left:
            clear_chat_safety_state(call_id)
            mini_games_service.clear_call_state(call_id)
            peer_socket = call_registry.peer_socket(call_id, user_id)
            if peer_socket is not None:
                await peer_socket.send_json(PeerLeftEvent().model_dump())
