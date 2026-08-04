import asyncio
import contextlib
import uuid

import anyio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_user_for_session_token
from app.db import get_db
from app.matching.pairing import DEFAULT_COLD_START_TIMEOUT_SECONDS, find_or_wait
from app.matching.queue import dequeue
from app.matching.schemas import (
    ErrorEvent,
    Filters,
    JoinMessage,
    LeaveMessage,
    MatchedEvent,
    SkipMessage,
    WaitingEvent,
    WidenSearchPromptEvent,
)
from app.redis import get_redis

router = APIRouter(tags=["matching"])

COLD_START_TIMEOUT_SECONDS = DEFAULT_COLD_START_TIMEOUT_SECONDS
_redis_dependency = Depends(get_redis)
_db_dependency = Depends(get_db)


async def _authenticate(websocket: WebSocket, db: AsyncSession) -> uuid.UUID | None:
    token = websocket.query_params.get("token")
    if not token:
        return None

    user = await get_user_for_session_token(db, token)
    return user.id if user else None


async def _join_and_wait(
    websocket: WebSocket, redis: Redis, user_id: uuid.UUID, filters: Filters, *, widened: bool
) -> uuid.UUID | None:
    """Enqueue user and wait for a match. Returns partner_id, or None on cold-start timeout."""

    async def _send_waiting() -> None:
        await websocket.send_json(WaitingEvent().model_dump())

    return await find_or_wait(
        redis,
        user_id,
        filters,
        widened=widened,
        timeout_seconds=COLD_START_TIMEOUT_SECONDS,
        on_waiting=_send_waiting,
    )


@router.websocket("/matching/ws")
async def matching_ws(
    websocket: WebSocket,
    redis: Redis = _redis_dependency,
    db: AsyncSession = _db_dependency,
) -> None:
    user_id = await _authenticate(websocket, db)
    if user_id is None:
        await websocket.close(code=4401, reason="Not authenticated")
        return

    await websocket.accept()
    current_filters: Filters | None = None
    wait_task: asyncio.Task[uuid.UUID | None] | None = None

    async def cancel_wait() -> None:
        nonlocal wait_task
        if wait_task is not None:
            wait_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await wait_task
            wait_task = None
        await dequeue(redis, user_id)

    try:
        while True:
            receive_task = asyncio.ensure_future(websocket.receive_json())
            pending = {receive_task}
            if wait_task is not None:
                pending.add(wait_task)

            done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            if wait_task is not None and wait_task in done:
                partner_id = wait_task.result()
                wait_task = None
                if partner_id is not None:
                    await websocket.send_json(MatchedEvent(partner_id=partner_id).model_dump())
                else:
                    await websocket.send_json(WidenSearchPromptEvent().model_dump())

            if receive_task not in done:
                continue

            raw = receive_task.result()
            if not isinstance(raw, dict):
                await websocket.send_json(
                    ErrorEvent(detail="Message must be a JSON object").model_dump()
                )
                continue
            msg_type = raw.get("type")

            if msg_type == "join":
                try:
                    join = JoinMessage.model_validate(raw)
                except ValidationError as exc:
                    await websocket.send_json(ErrorEvent(detail=str(exc)).model_dump())
                    continue

                if wait_task is not None:
                    await cancel_wait()
                current_filters = join.filters
                wait_task = asyncio.ensure_future(
                    _join_and_wait(
                        websocket, redis, user_id, join.filters, widened=join.widen_search
                    )
                )

            elif msg_type == "skip":
                SkipMessage.model_validate(raw)
                if wait_task is not None:
                    await cancel_wait()
                if current_filters is not None:
                    await dequeue(redis, user_id)
                    wait_task = asyncio.ensure_future(
                        _join_and_wait(websocket, redis, user_id, current_filters, widened=False)
                    )

            elif msg_type == "leave":
                LeaveMessage.model_validate(raw)
                if wait_task is not None:
                    await cancel_wait()
                else:
                    await dequeue(redis, user_id)
                current_filters = None

            else:
                await websocket.send_json(
                    ErrorEvent(detail=f"Unknown message type: {msg_type}").model_dump()
                )

    except WebSocketDisconnect:
        pass
    finally:
        if wait_task is not None:
            wait_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await wait_task
        if not receive_task.done():
            receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receive_task
        with contextlib.suppress(anyio.BrokenResourceError):
            await dequeue(redis, user_id)
