from redis.asyncio import Redis

from app.config import settings


class RateLimitedError(Exception):
    pass


# Atomic incr-and-set-TTL-on-first-hit: doing this in one script closes the
# window a plain INCR followed by a separate EXPIRE would leave open (e.g. a
# crash between the two calls leaving the key without a TTL, growing forever).
_INCR_WITH_TTL_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def _check_and_increment(redis: Redis, key: str, *, limit: int, window_seconds: int) -> None:
    count = await redis.eval(_INCR_WITH_TTL_SCRIPT, 1, key, window_seconds)
    if count > limit:
        raise RateLimitedError


async def enforce_verification_rate_limit(redis: Redis, *, user_id: str, client_ip: str) -> None:
    """Raises RateLimitedError if `user_id` or `client_ip` has exceeded its
    verification-attempt budget. Both are checked (and both incremented)
    so a single call counts against each independently — catches both a
    single abusive account and a bot farm spreading attempts across many
    freshly-created accounts from one IP/device."""
    await _check_and_increment(
        redis,
        f"verification:ratelimit:user:{user_id}",
        limit=settings.verification_rate_limit_per_user,
        window_seconds=settings.verification_rate_limit_user_window_minutes * 60,
    )
    await _check_and_increment(
        redis,
        f"verification:ratelimit:ip:{client_ip}",
        limit=settings.verification_rate_limit_per_ip,
        window_seconds=settings.verification_rate_limit_ip_window_minutes * 60,
    )
