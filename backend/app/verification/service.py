import uuid
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.verification import Verification, VerificationWaitlistEntry
from app.verification.cost_cap import release_verification_slot, try_consume_verification_slot
from app.verification.didit import (
    DiditRequestError,
    DiditRequestRejectedError,
    create_verification_session,
)
from app.verification.schemas import VerificationMethod, VerificationStatus


class VerificationProviderError(Exception):
    pass


async def start_verification(
    db: AsyncSession, redis: Redis, user_id: uuid.UUID, method: VerificationMethod
) -> tuple[VerificationStatus, str | None]:
    """Kicks off (or waitlists) a verification attempt for `user_id`.

    Returns (status, session_token). status is "pending" with a session_token
    to hand the Didit SDK's startVerification(), or "waitlisted" with no
    token when the monthly cap is hit — never raises for a full cap, only
    for a genuine Didit-side error.
    """
    if await is_video_eligible(db, user_id):
        return "verified", None

    existing_verification = (
        await db.execute(
            select(Verification)
            .where(Verification.user_id == user_id)
            .order_by(Verification.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if existing_verification is not None and existing_verification.status in (
        "verified",
        "pending",
    ):
        if existing_verification.status == "verified":
            return "verified", None
        # Already has a pending attempt in flight - don't consume another
        # monthly slot or create a duplicate row for a retried call. No
        # session_token: the client already has the one from the original
        # start call, or should poll /verify/status.
        return "pending", None

    if not await try_consume_verification_slot(redis):
        existing = await db.execute(
            select(VerificationWaitlistEntry).where(VerificationWaitlistEntry.user_id == user_id)
        )
        if existing.scalar_one_or_none() is None:
            db.add(VerificationWaitlistEntry(user_id=user_id))
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
        return "waitlisted", None

    try:
        session = await create_verification_session(user_id, method)
    except DiditRequestRejectedError as exc:
        # Confirmed rejection: Didit definitely never started an attempt,
        # so the slot is safe to give back to the pool.
        await release_verification_slot(redis)
        raise VerificationProviderError(str(exc)) from exc
    except DiditRequestError as exc:
        # Ambiguous failure (e.g. timeout) - the attempt may have reached
        # Didit, so keep the slot consumed rather than risk double-issuing.
        raise VerificationProviderError(str(exc)) from exc

    verification = Verification(
        user_id=user_id,
        status="pending",
        method=method,
        provider_session_id=session.session_id,
    )
    db.add(verification)

    stale_waitlist_entry = (
        await db.execute(
            select(VerificationWaitlistEntry).where(VerificationWaitlistEntry.user_id == user_id)
        )
    ).scalar_one_or_none()
    if stale_waitlist_entry is not None:
        await db.delete(stale_waitlist_entry)

    await db.commit()

    return "pending", session.session_token


async def get_verification_status(db: AsyncSession, user_id: uuid.UUID) -> Verification | None:
    result = await db.execute(
        select(Verification)
        .where(Verification.user_id == user_id)
        .order_by(Verification.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def is_video_eligible(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Fresh, full-predicate re-evaluation: verified, not expired, not
    revoked. Called at every match-formed / video-toggle gate check per
    tasks/10-age-verification.md - never cached across calls."""
    verification = await get_verification_status(db, user_id)
    if verification is None:
        return False
    if verification.revoked_at is not None:
        return False
    if verification.status != "verified":
        return False
    if verification.expiry is not None and datetime.now(UTC) >= verification.expiry:
        return False
    return True


async def apply_webhook_result(
    db: AsyncSession, provider_session_id: str, provider_status: str
) -> bool:
    """Idempotently applies a Didit webhook result. Returns False (no-op) if
    the session is unknown or already in a terminal state - replays of an
    already-processed callback can't double-apply or corrupt state."""
    result = await db.execute(
        select(Verification)
        .where(Verification.provider_session_id == provider_session_id)
        .with_for_update()
    )
    verification = result.scalar_one_or_none()
    if verification is None:
        return False

    if verification.status in ("verified", "failed", "revoked"):
        return False

    if provider_status == "Approved":
        verification.status = "verified"
        verification.verified_at = datetime.now(UTC)
        verification.expiry = datetime.now(UTC) + timedelta(days=settings.verification_expiry_days)
    else:
        verification.status = "failed"

    await db.commit()
    return True


async def promote_waitlist_if_room(db: AsyncSession, redis: Redis, user: User) -> bool:
    """Best-effort: called when a waitlisted user's slot might have opened up
    (e.g. next month's quota). Removes them from the waitlist if a slot was
    claimed; caller is responsible for sending the welcome-back email and for
    actually starting a fresh verification attempt afterward."""
    result = await db.execute(
        select(VerificationWaitlistEntry).where(VerificationWaitlistEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return False

    if not await try_consume_verification_slot(redis):
        return False

    await db.delete(entry)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    return True
