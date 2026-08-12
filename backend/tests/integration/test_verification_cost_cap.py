import asyncio
import logging

import pytest

from app.config import settings
from app.verification.cost_cap import try_consume_verification_slot

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_consumes_slots_up_to_cap(redis_conn, monkeypatch):
    monkeypatch.setattr(settings, "verification_monthly_cap", 3)

    assert await try_consume_verification_slot(redis_conn) is True
    assert await try_consume_verification_slot(redis_conn) is True
    assert await try_consume_verification_slot(redis_conn) is True


@pytest.mark.asyncio
async def test_rejects_once_cap_is_hit(redis_conn, monkeypatch):
    monkeypatch.setattr(settings, "verification_monthly_cap", 1)

    assert await try_consume_verification_slot(redis_conn) is True
    assert await try_consume_verification_slot(redis_conn) is False
    # Counter must not keep climbing past the cap on repeated rejections.
    assert await try_consume_verification_slot(redis_conn) is False


@pytest.mark.asyncio
async def test_alerts_fire_once_per_threshold(redis_conn, monkeypatch, caplog):
    monkeypatch.setattr(settings, "verification_monthly_cap", 2)

    with caplog.at_level(logging.WARNING):
        await try_consume_verification_slot(redis_conn)  # count=1: 50% threshold crossed
        await try_consume_verification_slot(redis_conn)  # count=2: 80% and 100% crossed

    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert sum("50%" in w for w in warnings) == 1
    assert sum("80%" in w for w in warnings) == 1
    assert sum("100%" in w for w in warnings) == 1


@pytest.mark.asyncio
async def test_concurrent_attempts_never_overshoot_cap(redis_conn, monkeypatch):
    monkeypatch.setattr(settings, "verification_monthly_cap", 20)

    results = await asyncio.gather(*(try_consume_verification_slot(redis_conn) for _ in range(50)))

    # Redis INCR is atomic, so exactly `cap` callers should win the race
    # regardless of how many fire concurrently - no overshoot, no undershoot.
    assert sum(results) == 20
