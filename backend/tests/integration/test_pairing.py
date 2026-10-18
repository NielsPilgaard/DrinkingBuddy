import asyncio
import uuid

import pytest

from app.matching.pairing import find_or_wait
from app.matching.schemas import Filters

pytestmark = pytest.mark.integration

FILTERS_DK_EN_ALC = Filters(language="en", drink_type="alcoholic", location="dk")
FILTERS_NO_EN_ALC = Filters(language="en", drink_type="alcoholic", location="no")


@pytest.mark.asyncio
async def test_find_or_wait_pairs_two_compatible_waiters(redis_conn):
    user_a, user_b = uuid.uuid4(), uuid.uuid4()

    task_a = asyncio.ensure_future(
        find_or_wait(redis_conn, user_a, FILTERS_DK_EN_ALC, timeout_seconds=5)
    )
    await asyncio.sleep(0.05)  # let A subscribe + enqueue before B joins
    partner_of_b = await find_or_wait(redis_conn, user_b, FILTERS_DK_EN_ALC, timeout_seconds=5)
    partner_of_a = await task_a

    assert partner_of_b == user_a
    assert partner_of_a == user_b


@pytest.mark.asyncio
async def test_find_or_wait_times_out_with_no_partner(redis_conn):
    user = uuid.uuid4()

    result = await find_or_wait(redis_conn, user, FILTERS_DK_EN_ALC, timeout_seconds=0.2)

    assert result is None


@pytest.mark.asyncio
async def test_find_or_wait_times_out_when_only_incompatible_waiter_present(redis_conn):
    waiter = uuid.uuid4()
    seeker = uuid.uuid4()

    task = asyncio.ensure_future(
        find_or_wait(redis_conn, waiter, FILTERS_DK_EN_ALC, timeout_seconds=1)
    )
    await asyncio.sleep(0.05)

    result = await find_or_wait(
        redis_conn,
        seeker,
        Filters(language="en", drink_type="non_alcoholic", location="dk"),
        timeout_seconds=0.2,
    )
    assert result is None

    await task  # drain waiter's own timeout so it doesn't leak a task warning


@pytest.mark.asyncio
async def test_find_or_wait_widened_pairs_across_locations(redis_conn):
    user_a, user_b = uuid.uuid4(), uuid.uuid4()

    task_a = asyncio.ensure_future(
        find_or_wait(redis_conn, user_a, FILTERS_DK_EN_ALC, widened=True, timeout_seconds=5)
    )
    await asyncio.sleep(0.05)
    partner_of_b = await find_or_wait(
        redis_conn, user_b, FILTERS_NO_EN_ALC, widened=True, timeout_seconds=5
    )
    partner_of_a = await task_a

    assert partner_of_b == user_a
    assert partner_of_a == user_b


async def _pair(redis_conn, waiter_filters, waiter_widened, seeker_filters, seeker_widened):
    """Waiter joins first, seeker second; returns (partner_of_waiter, partner_of_seeker, ids)."""
    waiter, seeker = uuid.uuid4(), uuid.uuid4()
    task = asyncio.ensure_future(
        find_or_wait(redis_conn, waiter, waiter_filters, widened=waiter_widened, timeout_seconds=1)
    )
    await asyncio.sleep(0.05)
    partner_of_seeker = await find_or_wait(
        redis_conn, seeker, seeker_filters, widened=seeker_widened, timeout_seconds=0.2
    )
    return await task, partner_of_seeker, waiter, seeker


@pytest.mark.asyncio
async def test_widened_seeker_pairs_with_strict_waiter_in_same_location(redis_conn):
    partner_of_waiter, partner_of_seeker, waiter, seeker = await _pair(
        redis_conn, FILTERS_DK_EN_ALC, False, FILTERS_DK_EN_ALC, True
    )
    assert partner_of_seeker == waiter
    assert partner_of_waiter == seeker


@pytest.mark.asyncio
async def test_widened_seeker_pairs_with_strict_waiter_in_other_location(redis_conn):
    partner_of_waiter, partner_of_seeker, waiter, seeker = await _pair(
        redis_conn, FILTERS_NO_EN_ALC, False, FILTERS_DK_EN_ALC, True
    )
    assert partner_of_seeker == waiter
    assert partner_of_waiter == seeker


@pytest.mark.asyncio
async def test_strict_seeker_pairs_with_widened_waiter_in_other_location(redis_conn):
    partner_of_waiter, partner_of_seeker, waiter, seeker = await _pair(
        redis_conn, FILTERS_NO_EN_ALC, True, FILTERS_DK_EN_ALC, False
    )
    assert partner_of_seeker == waiter
    assert partner_of_waiter == seeker


@pytest.mark.asyncio
async def test_strict_seekers_in_different_locations_do_not_pair(redis_conn):
    partner_of_waiter, partner_of_seeker, _, _ = await _pair(
        redis_conn, FILTERS_NO_EN_ALC, False, FILTERS_DK_EN_ALC, False
    )
    assert partner_of_seeker is None
    assert partner_of_waiter is None


@pytest.mark.asyncio
async def test_widened_seeker_skips_other_drink_type(redis_conn):
    partner_of_waiter, partner_of_seeker, _, _ = await _pair(
        redis_conn,
        Filters(language="en", drink_type="non_alcoholic", location="no"),
        False,
        FILTERS_DK_EN_ALC,
        True,
    )
    assert partner_of_seeker is None
    assert partner_of_waiter is None


@pytest.mark.asyncio
async def test_find_or_wait_calls_on_waiting_only_when_not_matched_instantly(redis_conn):
    seeker = uuid.uuid4()
    matcher = uuid.uuid4()

    waiting_calls: list[None] = []

    async def on_waiting() -> None:
        waiting_calls.append(None)

    task = asyncio.ensure_future(
        find_or_wait(
            redis_conn, seeker, FILTERS_DK_EN_ALC, timeout_seconds=5, on_waiting=on_waiting
        )
    )
    await asyncio.sleep(0.05)
    assert waiting_calls == [None]

    matched_calls: list[None] = []

    async def matcher_on_waiting() -> None:
        matched_calls.append(None)

    partner_of_matcher = await find_or_wait(
        redis_conn,
        matcher,
        FILTERS_DK_EN_ALC,
        timeout_seconds=5,
        on_waiting=matcher_on_waiting,
    )
    partner_of_seeker = await task

    assert partner_of_matcher == seeker
    assert partner_of_seeker == matcher
    assert matched_calls == []
