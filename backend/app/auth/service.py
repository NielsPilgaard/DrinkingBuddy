from datetime import UTC, date, datetime, timedelta

from anyio.to_thread import run_sync
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import generate_token, hash_token
from app.config import settings
from app.email import send_magic_link_email
from app.models.magic_link_token import MagicLinkToken
from app.models.session import Session
from app.models.user import User

MIN_SIGNUP_AGE_YEARS = 18


class InvalidOrExpiredTokenError(Exception):
    pass


def _is_underage(birthdate: date) -> bool:
    today = datetime.now(UTC).date()
    age = (
        today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )
    return age < MIN_SIGNUP_AGE_YEARS


async def request_link(db: AsyncSession, email: str, birthdate: date | None) -> None:
    normalized_email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if user is None:
        if birthdate is None or _is_underage(birthdate):
            # Deliberately silent: creating no account and sending no email here
            # (instead of raising) keeps this response indistinguishable from the
            # existing-user success path, so a caller can't use status code to
            # probe whether an email is already registered.
            return
        user = User(email=normalized_email, birthdate=birthdate)
        db.add(user)
        await db.flush()

    raw_token = generate_token()
    magic_link = MagicLinkToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.magic_link_ttl_minutes),
    )
    db.add(magic_link)
    await db.flush()

    deep_link = f"{settings.app_universal_link_base}/verify?token={raw_token}"
    try:
        await run_sync(send_magic_link_email, user.email, deep_link)
    except OSError:
        await db.rollback()
        raise

    await db.commit()


async def verify_token(db: AsyncSession, raw_token: str) -> tuple[str, User]:
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(MagicLinkToken)
        .where(MagicLinkToken.token_hash == token_hash)
        .with_for_update()
    )
    magic_link = result.scalar_one_or_none()

    now = datetime.now(UTC)
    if magic_link is None or magic_link.used_at is not None or magic_link.expires_at < now:
        raise InvalidOrExpiredTokenError

    magic_link.used_at = now

    user = await db.get(User, magic_link.user_id)
    if user is None:
        raise InvalidOrExpiredTokenError

    raw_session_token = generate_token()
    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_session_token),
        expires_at=now + timedelta(days=settings.session_ttl_days),
    )
    db.add(session)
    await db.commit()

    return raw_session_token, user


async def get_user_for_session_token(db: AsyncSession, raw_token: str) -> User | None:
    token_hash = hash_token(raw_token)
    now = datetime.now(UTC)
    result = await db.execute(select(Session).where(Session.token_hash == token_hash))
    session = result.scalar_one_or_none()

    if session is None or session.revoked_at is not None or session.expires_at < now:
        return None

    return await db.get(User, session.user_id)
