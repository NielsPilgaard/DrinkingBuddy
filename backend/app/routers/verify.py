from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_user_for_session_token
from app.db import get_db
from app.models.user import User
from app.redis import get_redis
from app.verification.didit import verify_webhook_signature
from app.verification.rate_limit import RateLimitedError, enforce_verification_rate_limit
from app.verification.schemas import (
    DiditWebhookPayload,
    StartVerificationBody,
    StartVerificationResponse,
    VerificationMethod,
    VerificationStatus,
    VerificationStatusResponse,
)
from app.verification.service import (
    VerificationProviderError,
    apply_webhook_result,
    get_verification_status,
    start_verification,
)

router = APIRouter(prefix="/verify", tags=["verify"])

_db_dependency = Depends(get_db)
_redis_dependency = Depends(get_redis)
_bearer_scheme = HTTPBearer()
_bearer_dependency = Depends(_bearer_scheme)


async def _current_user(
    credentials: HTTPAuthorizationCredentials = _bearer_dependency,
    db: AsyncSession = _db_dependency,
) -> User:
    user = await get_user_for_session_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


_current_user_dependency = Depends(_current_user)


@router.post("/start", response_model=StartVerificationResponse)
async def start_verification_endpoint(
    body: StartVerificationBody,
    request: Request,
    user: User = _current_user_dependency,
    db: AsyncSession = _db_dependency,
    redis: Redis = _redis_dependency,
) -> StartVerificationResponse:
    client_ip = request.client.host if request.client else "unknown"
    try:
        await enforce_verification_rate_limit(redis, user_id=str(user.id), client_ip=client_ip)
    except RateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Try again later.",
        ) from exc

    try:
        result_status, session_token = await start_verification(db, redis, user.id, body.method)
    except VerificationProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Verification provider is currently unavailable.",
        ) from exc

    detail = "You're on the list, we'll email you." if result_status == "waitlisted" else None
    return StartVerificationResponse(
        status=result_status, session_token=session_token, detail=detail
    )


@router.get("/status", response_model=VerificationStatusResponse)
async def verification_status_endpoint(
    user: User = _current_user_dependency,
    db: AsyncSession = _db_dependency,
) -> VerificationStatusResponse:
    verification = await get_verification_status(db, user.id)
    if verification is None:
        return VerificationStatusResponse(status="pending", method=None)

    effective_status = verification.status
    if verification.revoked_at is not None:
        effective_status = "revoked"

    return VerificationStatusResponse(
        status=cast(VerificationStatus, effective_status),
        method=cast(VerificationMethod, verification.method),
        verified_at=verification.verified_at,
        expiry=verification.expiry,
    )


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def didit_webhook_endpoint(
    request: Request,
    db: AsyncSession = _db_dependency,
) -> None:
    raw_body = await request.body()
    signature = request.headers.get("X-Didit-Signature", "")
    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    payload = DiditWebhookPayload.model_validate_json(raw_body)
    await apply_webhook_result(db, payload.session_id, payload.status)
