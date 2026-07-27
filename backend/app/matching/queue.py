import uuid

from redis.asyncio import Redis

from app.matching.schemas import Filters

QUEUE_KEY_PREFIX = "queue:bucket"
MATCH_CHANNEL_PREFIX = "queue:match"
FILTERS_KEY_PREFIX = "queue:filters"

WIDE_LOCATION = "*"


def _bucket_key(filters: Filters, *, widened: bool) -> str:
    location = WIDE_LOCATION if widened else filters.location
    return f"{QUEUE_KEY_PREFIX}:{filters.language}:{filters.drink_type}:{location}"


def match_channel(user_id: uuid.UUID) -> str:
    return f"{MATCH_CHANNEL_PREFIX}:{user_id}"


def _filters_key(user_id: uuid.UUID) -> str:
    return f"{FILTERS_KEY_PREFIX}:{user_id}"


# Atomic pair-or-join: pops the next compatible waiter (skipping any entry
# equal to the caller, a stale self-entry from a prior connection) and, if
# found, clears their filters key; otherwise removes any ghost entry the
# caller may already have in another bucket (e.g. from a second concurrent
# connection) before joining this bucket. Running this as a single script
# closes the race where two concurrent callers both see an empty bucket and
# both end up waiting instead of matching each other.
_ENQUEUE_SCRIPT = f"""
local bucket = KEYS[1]
local filters_key = KEYS[2]
local user_id = ARGV[1]

while true do
    local partner_id = redis.call('RPOP', bucket)
    if not partner_id then
        break
    end
    if partner_id ~= user_id then
        redis.call('DEL', '{FILTERS_KEY_PREFIX}:' .. partner_id)
        return partner_id
    end
end

local old_bucket = redis.call('GET', filters_key)
if old_bucket then
    redis.call('LREM', old_bucket, 0, user_id)
end
redis.call('SET', filters_key, bucket)
redis.call('LPUSH', bucket, user_id)
return false
"""


async def enqueue(
    redis: Redis, user_id: uuid.UUID, filters: Filters, *, widened: bool = False
) -> uuid.UUID | None:
    """Try to pair with a waiting compatible user; else join the queue and wait.

    Returns the matched partner's id, or None if this user is now waiting.
    """
    bucket = _bucket_key(filters, widened=widened)

    result = await redis.eval(
        _ENQUEUE_SCRIPT, 2, bucket, _filters_key(user_id), str(user_id)
    )
    if not result:
        return None
    return uuid.UUID(result)


async def dequeue(redis: Redis, user_id: uuid.UUID) -> None:
    """Remove a user from whatever bucket they're waiting in, if any."""
    bucket = await redis.get(_filters_key(user_id))
    if bucket is None:
        return
    await redis.lrem(bucket, 0, str(user_id))
    await redis.delete(_filters_key(user_id))
