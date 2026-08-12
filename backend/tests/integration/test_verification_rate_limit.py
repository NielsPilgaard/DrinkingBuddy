import pytest

from app.config import settings
from app.verification.rate_limit import RateLimitedError, enforce_verification_rate_limit

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_allows_attempts_within_per_user_limit(redis_conn, monkeypatch):
    monkeypatch.setattr(settings, "verification_rate_limit_per_user", 2)
    monkeypatch.setattr(settings, "verification_rate_limit_per_ip", 100)

    await enforce_verification_rate_limit(redis_conn, user_id="user-1", client_ip="1.1.1.1")
    await enforce_verification_rate_limit(redis_conn, user_id="user-1", client_ip="1.1.1.1")


@pytest.mark.asyncio
async def test_blocks_after_per_user_limit_exceeded(redis_conn, monkeypatch):
    monkeypatch.setattr(settings, "verification_rate_limit_per_user", 1)
    monkeypatch.setattr(settings, "verification_rate_limit_per_ip", 100)

    await enforce_verification_rate_limit(redis_conn, user_id="user-2", client_ip="1.1.1.1")
    with pytest.raises(RateLimitedError):
        await enforce_verification_rate_limit(redis_conn, user_id="user-2", client_ip="1.1.1.1")


@pytest.mark.asyncio
async def test_blocks_bot_farm_spreading_attempts_across_many_users_same_ip(
    redis_conn, monkeypatch
):
    """Simulates rapid repeated attempts from one IP across many freshly
    created accounts - per-user limiting alone wouldn't catch this."""
    monkeypatch.setattr(settings, "verification_rate_limit_per_user", 100)
    monkeypatch.setattr(settings, "verification_rate_limit_per_ip", 2)

    await enforce_verification_rate_limit(redis_conn, user_id="bot-1", client_ip="6.6.6.6")
    await enforce_verification_rate_limit(redis_conn, user_id="bot-2", client_ip="6.6.6.6")
    with pytest.raises(RateLimitedError):
        await enforce_verification_rate_limit(redis_conn, user_id="bot-3", client_ip="6.6.6.6")


@pytest.mark.asyncio
async def test_different_users_and_ips_do_not_share_limits(redis_conn, monkeypatch):
    monkeypatch.setattr(settings, "verification_rate_limit_per_user", 1)
    monkeypatch.setattr(settings, "verification_rate_limit_per_ip", 1)

    await enforce_verification_rate_limit(redis_conn, user_id="user-a", client_ip="2.2.2.2")
    await enforce_verification_rate_limit(redis_conn, user_id="user-b", client_ip="3.3.3.3")
