import logging
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import cast

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

_ALERT_THRESHOLDS = (0.5, 0.8, 1.0)


def _month_key() -> str:
    now = datetime.now(UTC)
    return f"verification:cap:{now.year:04d}{now.month:02d}"


def _alerted_key(month_key: str, threshold: float) -> str:
    return f"{month_key}:alerted:{int(threshold * 100)}"


async def _maybe_fire_alert(redis: Redis, month_key: str, count: int) -> None:
    cap = settings.verification_monthly_cap
    for threshold in _ALERT_THRESHOLDS:
        if count < cap * threshold:
            continue
        # SET NX so each threshold fires exactly once per month, even under
        # concurrent increments crossing the line at the same time.
        fired = await redis.set(
            _alerted_key(month_key, threshold), "1", nx=True, ex=60 * 60 * 24 * 40
        )
        if fired:
            logger.warning(
                "Didit verification spend at %d%% of monthly cap (%d/%d)",
                int(threshold * 100),
                count,
                cap,
            )


async def try_consume_verification_slot(redis: Redis) -> bool:
    """Atomically claims one of this month's Didit verification slots.
    Returns False once the monthly cap is hit — caller should waitlist
    instead of blocking the user. Fires budget alerts at 50/80/100%."""
    month_key = _month_key()
    count = await cast(Awaitable[int], redis.incr(month_key))
    if count == 1:
        await redis.expire(month_key, 60 * 60 * 24 * 40)

    await _maybe_fire_alert(redis, month_key, count)

    if count > settings.verification_monthly_cap:
        await cast(Awaitable[int], redis.decr(month_key))
        return False
    return True


async def release_verification_slot(redis: Redis) -> None:
    """Returns a slot consumed by `try_consume_verification_slot` to this
    month's pool - only safe to call when the attempt is confirmed to have
    never reached Didit (a genuine rejection), not on an ambiguous transport
    failure where the request may have gone through."""
    await cast(Awaitable[int], redis.decr(_month_key()))
