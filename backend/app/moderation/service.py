import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.csam.service import CSAM_REPORT_REASON, open_case
from app.models.block import Block
from app.models.report import Report
from app.models.suspension import Suspension

# Postgres advisory lock keyed on reported_id, held for the duration of the
# transaction (xact-scoped, auto-released on commit/rollback). Serializes the
# threshold check + suspend so two concurrent reports for the same user can't
# both read a count below threshold and both skip suspending.
_REPORT_THRESHOLD_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtext(:reported_id))"


async def submit_report(
    db: AsyncSession,
    reporter_id: uuid.UUID,
    reported_id: uuid.UUID,
    call_session_id: str,
    reason: str,
) -> None:
    await db.execute(text(_REPORT_THRESHOLD_LOCK_SQL), {"reported_id": str(reported_id)})

    insert_stmt = (
        pg_insert(Report)
        .values(
            reporter_id=reporter_id,
            reported_id=reported_id,
            call_session_id=call_session_id,
            reason=reason,
        )
        .on_conflict_do_nothing(index_elements=["reporter_id", "call_session_id"])
        .returning(Report.id)
    )
    inserted = await db.execute(insert_stmt)
    if inserted.first() is None:
        # Already reported this call - don't re-run the threshold check.
        await db.commit()
        return

    window_start = datetime.now(UTC) - timedelta(hours=settings.report_window_hours)
    result = await db.execute(
        select(Report.id).where(
            Report.reported_id == reported_id,
            Report.created_at >= window_start,
        )
    )
    recent_report_count = len(result.all())

    if recent_report_count >= settings.report_auto_suspend_threshold:
        if not await is_suspended(db, reported_id):
            await _suspend(db, reported_id)

    if reason == CSAM_REPORT_REASON:
        await open_case(
            db,
            source="user_report",
            reported_id=reported_id,
            call_session_id=call_session_id,
            actor=f"user:{reporter_id}",
        )

    await db.commit()


async def _suspend(db: AsyncSession, user_id: uuid.UUID) -> None:
    expires_at = datetime.now(UTC) + timedelta(hours=settings.suspension_duration_hours)
    db.add(Suspension(user_id=user_id, expires_at=expires_at))
    await db.flush()


async def is_suspended(db: AsyncSession, user_id: uuid.UUID) -> bool:
    now = datetime.now(UTC)
    result = await db.execute(
        select(Suspension.id)
        .where(Suspension.user_id == user_id, Suspension.expires_at > now)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def create_block(db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> None:
    stmt = (
        pg_insert(Block)
        .values(blocker_id=blocker_id, blocked_id=blocked_id)
        .on_conflict_do_nothing(index_elements=["blocker_id", "blocked_id"])
    )
    await db.execute(stmt)
    await db.commit()


async def are_blocked(db: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
    """True if either user has blocked the other, in either direction."""
    result = await db.execute(
        select(Block.id)
        .where(
            ((Block.blocker_id == user_a) & (Block.blocked_id == user_b))
            | ((Block.blocker_id == user_b) & (Block.blocked_id == user_a))
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
