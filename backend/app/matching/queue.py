import uuid
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis

from app.matching.schemas import Filters

QUEUE_KEY_PREFIX = "queue:bucket"
MATCH_CHANNEL_PREFIX = "queue:match"
FILTERS_KEY_PREFIX = "queue:filters"

WIDE_LOCATION = "*"

# Bound on how many blocked candidates get skipped before falling back to
# waiting - guards against pathological all-blocked buckets spinning forever.
MAX_BLOCK_SKIPS = 20

RESERVED_PREFIX = "RESERVED"


def _bucket_key(filters: Filters, *, widened: bool) -> str:
    location = WIDE_LOCATION if widened else filters.location
    return f"{QUEUE_KEY_PREFIX}:{filters.language}:{filters.drink_type}:{location}"


def match_channel(user_id: uuid.UUID) -> str:
    return f"{MATCH_CHANNEL_PREFIX}:{user_id}"


def _filters_key(user_id: uuid.UUID) -> str:
    return f"{FILTERS_KEY_PREFIX}:{user_id}"


# Atomic pop-one-candidate: pops the next waiter that isn't the caller itself
# (skipping any stale self-entry from a prior connection) and, if found, marks
# their filters key as reserved-by-this-bucket (rather than deleting it) so a
# later requeue can tell whether the candidate re-joined elsewhere in the
# meantime. Returns false if the bucket has no other waiter.
# Block-compatibility can't be checked here (Lua has no DB access), so the
# Python caller re-pushes a popped-but-blocked candidate and retries.
_POP_CANDIDATE_SCRIPT = """
local bucket = KEYS[1]
local user_id = ARGV[1]
local reserved_prefix = ARGV[2]

while true do
    local partner_id = redis.call('RPOP', bucket)
    if not partner_id then
        return false
    end
    if partner_id ~= user_id then
        redis.call('SET', KEYS[2] .. ':' .. partner_id, reserved_prefix .. ':' .. bucket)
        return partner_id
    end
end
"""

# Requeues a candidate popped-but-blocked only if their filters key still
# shows them reserved by this bucket - if they rejoined a queue in the
# meantime (their filters key changed), leave that newer state alone.
_REQUEUE_RESERVED_SCRIPT = """
local bucket = KEYS[1]
local filters_key = KEYS[2]
local reserved_marker = ARGV[1]
local candidate_id = ARGV[2]

if redis.call('GET', filters_key) == reserved_marker then
    redis.call('SET', filters_key, bucket)
    redis.call('RPUSH', bucket, candidate_id)
end
"""

_JOIN_SCRIPT = """
local bucket = KEYS[1]
local filters_key = KEYS[2]
local user_id = ARGV[1]

local old_bucket = redis.call('GET', filters_key)
if old_bucket then
    redis.call('LREM', old_bucket, 0, user_id)
end
redis.call('SET', filters_key, bucket)
redis.call('LPUSH', bucket, user_id)
"""


async def enqueue(
    redis: Redis,
    user_id: uuid.UUID,
    filters: Filters,
    *,
    widened: bool = False,
    is_blocked_pair: Callable[[uuid.UUID, uuid.UUID], Awaitable[bool]] | None = None,
) -> uuid.UUID | None:
    """Try to pair with a waiting compatible user; else join the queue and wait.

    If `is_blocked_pair` is given, a popped candidate that's blocked (in
    either direction) with `user_id` is put back in the bucket and the next
    candidate is tried instead, up to `MAX_BLOCK_SKIPS` times.

    Returns the matched partner's id, or None if this user is now waiting.
    """
    bucket = _bucket_key(filters, widened=widened)

    skipped: list[uuid.UUID] = []
    try:
        for _ in range(MAX_BLOCK_SKIPS + 1):
            result = await redis.eval(
                _POP_CANDIDATE_SCRIPT, 2, bucket, FILTERS_KEY_PREFIX, str(user_id), RESERVED_PREFIX
            )
            if not result:
                break

            partner_id = uuid.UUID(result)
            if is_blocked_pair is not None and await is_blocked_pair(user_id, partner_id):
                skipped.append(partner_id)
                continue
            return partner_id
    finally:
        # Requeue candidates skipped for being blocked with this caller, so
        # they aren't lost from the pool for anyone else - unless they've
        # since re-joined a queue themselves, in which case leave that alone.
        for candidate_id in skipped:
            reserved_marker = f"{RESERVED_PREFIX}:{bucket}"
            await redis.eval(
                _REQUEUE_RESERVED_SCRIPT,
                2,
                bucket,
                _filters_key(candidate_id),
                reserved_marker,
                str(candidate_id),
            )

    await redis.eval(_JOIN_SCRIPT, 2, bucket, _filters_key(user_id), str(user_id))
    return None


async def dequeue(redis: Redis, user_id: uuid.UUID) -> None:
    """Remove a user from whatever bucket they're waiting in, if any."""
    bucket = await redis.get(_filters_key(user_id))
    if bucket is None:
        return
    await redis.lrem(bucket, 0, str(user_id))
    await redis.delete(_filters_key(user_id))
