import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

from anyio.to_thread import run_sync
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_safety.matcher import (
    AGE_UNDER_18_CATEGORY,
    DEFAULT_PATTERNS,
    CompiledPattern,
    compile_patterns,
    match_message,
    parse_age_under_18,
)
from app.config import settings
from app.email import send_chat_safety_retention_escalation_email
from app.models.chat_safety import ChatSafetyAuditLog, ChatSafetyPattern, FlaggedMessage

_CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD = 2

logger = logging.getLogger(__name__)

# call_id -> user_id who most recently asked an age question, awaiting a
# reply. In-process/in-memory like signaling.registry.CallRegistry - single
# VPS, single worker, ephemeral per call, no cross-process sharing needed.
_pending_age_questions: dict[str, uuid.UUID] = {}


def _fernet() -> Fernet:
    if not settings.chat_safety_flag_encryption_key:
        raise RuntimeError("chat_safety_flag_encryption_key is not configured")
    return Fernet(settings.chat_safety_flag_encryption_key.encode())


async def _load_active_patterns(db: AsyncSession) -> list[CompiledPattern]:
    result = await db.execute(
        select(ChatSafetyPattern.slug, ChatSafetyPattern.category, ChatSafetyPattern.pattern).where(
            ChatSafetyPattern.is_active
        )
    )
    rows = result.all()
    if not rows:
        return compile_patterns(DEFAULT_PATTERNS)
    return compile_patterns([(slug, category, pattern) for slug, category, pattern in rows])


async def _flag(
    db: AsyncSession,
    *,
    call_session_id: str,
    sender_id: uuid.UUID,
    recipient_id: uuid.UUID,
    category: str,
    matched_pattern_slug: str,
    text: str,
) -> None:
    ciphertext = _fernet().encrypt(text.encode())
    db.add(
        FlaggedMessage(
            call_session_id=call_session_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            category=category,
            matched_pattern_slug=matched_pattern_slug,
            ciphertext=ciphertext,
        )
    )
    await db.commit()


async def scan_chat_message(
    db: AsyncSession,
    *,
    call_session_id: str,
    sender_id: uuid.UUID,
    recipient_id: uuid.UUID,
    text: str,
) -> None:
    """Runs the three-category matcher against a relayed chat message and
    silently writes a flag on a hit - no in-chat indication to either user,
    no auto-suspend from a filter hit alone (tasks/13-chat-safety-filters.md).
    Never raises: a filter bug must not break the chat relay."""
    try:
        pending_asker = _pending_age_questions.get(call_session_id)
        if pending_asker is not None and pending_asker != sender_id:
            age = parse_age_under_18(text)
            if age is not None:
                await _flag(
                    db,
                    call_session_id=call_session_id,
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    category=AGE_UNDER_18_CATEGORY,
                    matched_pattern_slug="age-answer-under-18",
                    text=text,
                )
            _pending_age_questions.pop(call_session_id, None)

        patterns = await _load_active_patterns(db)
        hit = match_message(text, patterns)
        if hit is None:
            return

        if hit.category == AGE_UNDER_18_CATEGORY:
            # This is the *question* pattern ("how old are you") - remember
            # who asked so the next message from the other party can resolve
            # the exchange. Not flagged on its own (a question alone isn't a
            # disclosure).
            _pending_age_questions[call_session_id] = sender_id
            return

        await _flag(
            db,
            call_session_id=call_session_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            category=hit.category,
            matched_pattern_slug=hit.slug,
            text=text,
        )
    except Exception:
        await db.rollback()
        logger.exception(
            "chat safety filter failed for call_session_id=%s - message relayed unfiltered",
            call_session_id,
        )


class InvalidPatternError(Exception):
    pass


async def list_active_patterns(db: AsyncSession) -> list[ChatSafetyPattern]:
    result = await db.execute(
        select(ChatSafetyPattern)
        .where(ChatSafetyPattern.is_active)
        .order_by(ChatSafetyPattern.slug)
    )
    return list(result.scalars().all())


async def upsert_pattern(
    db: AsyncSession, *, slug: str, category: str, pattern: str, actor: str
) -> ChatSafetyPattern:
    """Creates a new version of `slug`, deactivating any prior version -
    edits are validated before taking effect and superseded versions are
    kept (not deleted) so they can be rolled back to, per
    tasks/13-chat-safety-filters.md config scope."""
    try:
        re.compile(pattern)
    except re.error as exc:
        raise InvalidPatternError(f"Invalid regex pattern: {exc}") from exc

    result = await db.execute(
        select(ChatSafetyPattern)
        .where(ChatSafetyPattern.slug == slug)
        .order_by(ChatSafetyPattern.version.desc())
        .limit(1)
    )
    previous = result.scalar_one_or_none()
    next_version = 1 if previous is None else previous.version + 1

    if previous is not None:
        previous.is_active = False

    row = ChatSafetyPattern(
        slug=slug,
        version=next_version,
        category=category,
        pattern=pattern,
        is_active=True,
        created_by=actor,
    )
    db.add(row)
    await db.commit()
    await log_audit(
        db,
        action="pattern_upsert",
        actor=actor,
        detail=f"{slug} -> v{next_version}",
    )
    return row


async def rollback_pattern(
    db: AsyncSession, *, slug: str, version: int, actor: str
) -> ChatSafetyPattern:
    """Reactivates a prior version of `slug`, deactivating whatever is
    currently active for it."""
    result = await db.execute(
        select(ChatSafetyPattern).where(
            ChatSafetyPattern.slug == slug, ChatSafetyPattern.version == version
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise InvalidPatternError(f"No version {version} for pattern {slug!r}")

    current_result = await db.execute(
        select(ChatSafetyPattern).where(ChatSafetyPattern.slug == slug, ChatSafetyPattern.is_active)
    )
    for current in current_result.scalars().all():
        current.is_active = False

    target.is_active = True
    await db.commit()
    await log_audit(
        db,
        action="pattern_rollback",
        actor=actor,
        detail=f"{slug} -> v{version}",
    )
    return target


def clear_call_state(call_session_id: str) -> None:
    """Drops any pending age-question state for a call - call on call teardown
    so state doesn't leak across a call_id being reused."""
    _pending_age_questions.pop(call_session_id, None)


async def decrypt_flag(flag: FlaggedMessage) -> str:
    return _fernet().decrypt(flag.ciphertext).decode()


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    actor: str,
    detail: str = "",
    success: bool = True,
) -> None:
    db.add(ChatSafetyAuditLog(action=action, actor=actor, detail=detail, success=success))
    await db.commit()


async def purge_expired_flags(db: AsyncSession) -> int:
    """Deletes flagged rows past the 30-day + 24h grace cutoff. Logs the run
    (rows purged, success/failure) to the same audit trail as access logging
    per tasks/13-chat-safety-filters.md retention scope. Intended to run on a
    daily schedule (e.g. cron hitting a maintenance endpoint, or a scheduled
    task runner) - no scheduler is wired up by this task, matching the
    existing precedent in app/verification/waitlist_sweep.py."""
    cutoff = datetime.now(UTC) - timedelta(
        days=settings.chat_safety_retention_days,
        hours=settings.chat_safety_retention_grace_hours,
    )
    try:
        result = await db.execute(select(FlaggedMessage).where(FlaggedMessage.created_at < cutoff))
        expired = result.scalars().all()
        count = len(expired)
        for row in expired:
            await db.delete(row)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        await log_audit(
            db,
            action="retention_sweep",
            actor="system",
            detail=str(exc),
            success=False,
        )
        await _escalate_if_consecutive_failures(db)
        raise

    await log_audit(
        db,
        action="retention_sweep",
        actor="system",
        detail=f"purged {count} row(s) older than {cutoff.isoformat()}",
        success=True,
    )
    return count


async def _escalate_if_consecutive_failures(db: AsyncSession) -> None:
    """Alerts moderation-on-call once retention_sweep has failed
    N times in a row (escalation, not a silent skip) - see
    tasks/13-chat-safety-filters.md retention scope."""
    result = await db.execute(
        select(ChatSafetyAuditLog.success)
        .where(ChatSafetyAuditLog.action == "retention_sweep")
        .order_by(ChatSafetyAuditLog.created_at.desc())
        .limit(_CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD)
    )
    recent = result.scalars().all()
    if len(recent) < _CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD or any(recent):
        return

    await run_sync(
        send_chat_safety_retention_escalation_email,
        settings.chat_safety_oncall_email,
        _CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD,
    )
    await log_audit(
        db,
        action="retention_sweep_escalation",
        actor="system",
        detail=f"emailed {settings.chat_safety_oncall_email} after "
        f"{_CONSECUTIVE_FAILURE_ESCALATION_THRESHOLD} consecutive failures",
        success=True,
    )
