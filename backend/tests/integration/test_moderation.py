import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.config import settings
from app.matching.pairing import find_or_wait
from app.matching.schemas import Filters
from app.models.report import Report
from app.models.suspension import Suspension
from app.models.user import User
from app.moderation.service import are_blocked, create_block, is_suspended, submit_report

pytestmark = pytest.mark.integration

FILTERS_DK_EN_ALC = Filters(language="en", drink_type="alcoholic", location="dk")


async def _make_user(db_session, email: str) -> uuid.UUID:
    user = User(email=email, birthdate=datetime(2000, 1, 1, tzinfo=UTC).date())
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


@pytest.mark.asyncio
async def test_report_below_threshold_does_not_suspend(db_session):
    reporter_id = await _make_user(db_session, "reporter1@example.com")
    reported_id = await _make_user(db_session, "reported1@example.com")

    await submit_report(db_session, reporter_id, reported_id, "call-1", "harassment")

    assert await is_suspended(db_session, reported_id) is False


@pytest.mark.asyncio
async def test_nth_report_within_window_auto_suspends(db_session):
    reported_id = await _make_user(db_session, "reported2@example.com")

    for i in range(settings.report_auto_suspend_threshold):
        reporter_id = await _make_user(db_session, f"reporter2-{i}@example.com")
        await submit_report(db_session, reporter_id, reported_id, f"call-{i}", "harassment")

    assert await is_suspended(db_session, reported_id) is True


@pytest.mark.asyncio
async def test_reports_outside_window_do_not_count_toward_suspension(db_session):
    reported_id = await _make_user(db_session, "reported3@example.com")

    stale_cutoff = datetime.now(UTC) - timedelta(hours=settings.report_window_hours + 1)
    for i in range(settings.report_auto_suspend_threshold - 1):
        reporter_id = await _make_user(db_session, f"reporter3-{i}@example.com")
        await submit_report(db_session, reporter_id, reported_id, f"call-{i}", "harassment")

    # Backdate all existing reports outside the window, then add one fresh
    # report — should NOT reach the threshold since the old ones don't count.
    await db_session.execute(
        update(Report).where(Report.reported_id == reported_id).values(created_at=stale_cutoff)
    )
    await db_session.commit()

    fresh_reporter_id = await _make_user(db_session, "reporter3-fresh@example.com")
    await submit_report(db_session, fresh_reporter_id, reported_id, "call-fresh", "harassment")

    assert await is_suspended(db_session, reported_id) is False


@pytest.mark.asyncio
async def test_expired_suspension_is_not_active(db_session):
    user_id = await _make_user(db_session, "expired-suspend@example.com")
    db_session.add(Suspension(user_id=user_id, expires_at=datetime.now(UTC) - timedelta(hours=1)))
    await db_session.commit()

    assert await is_suspended(db_session, user_id) is False


@pytest.mark.asyncio
async def test_are_blocked_true_regardless_of_direction(db_session):
    user_a = await _make_user(db_session, "blocker@example.com")
    user_b = await _make_user(db_session, "blocked@example.com")

    await create_block(db_session, user_a, user_b)

    assert await are_blocked(db_session, user_a, user_b) is True
    assert await are_blocked(db_session, user_b, user_a) is True


@pytest.mark.asyncio
async def test_are_blocked_false_when_no_block_exists(db_session):
    user_a = await _make_user(db_session, "unrelated1@example.com")
    user_b = await _make_user(db_session, "unrelated2@example.com")

    assert await are_blocked(db_session, user_a, user_b) is False


@pytest.mark.asyncio
async def test_blocked_pair_is_not_matched_and_falls_back_to_third_user(db_session, redis_conn):
    user_a = await _make_user(db_session, "block-match-a@example.com")
    user_b = await _make_user(db_session, "block-match-b@example.com")
    user_c = await _make_user(db_session, "block-match-c@example.com")

    await create_block(db_session, user_a, user_b)

    async def is_blocked_pair(x: uuid.UUID, y: uuid.UUID) -> bool:
        return await are_blocked(db_session, x, y)

    task_b = asyncio.ensure_future(
        find_or_wait(redis_conn, user_b, FILTERS_DK_EN_ALC, timeout_seconds=5)
    )
    await asyncio.sleep(0.05)

    # A joins - should skip blocked B and remain waiting (times out quickly).
    result_a = await find_or_wait(
        redis_conn,
        user_a,
        FILTERS_DK_EN_ALC,
        timeout_seconds=0.3,
        is_blocked_pair=is_blocked_pair,
    )
    assert result_a is None

    # C joins - B (still waiting, requeued after being skipped) should pair with C.
    result_c = await find_or_wait(redis_conn, user_c, FILTERS_DK_EN_ALC, timeout_seconds=5)
    result_b = await task_b

    assert result_c == user_b
    assert result_b == user_c
