import uuid
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.matching.queue import dequeue, enqueue, match_channel
from app.matching.schemas import Filters

DEFAULT_COLD_START_TIMEOUT_SECONDS = 25


async def _wait_for_partner(pubsub: PubSub, *, timeout_seconds: float) -> uuid.UUID:
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout_seconds)
        if message is None:
            raise TimeoutError
        if message["type"] == "message":
            return uuid.UUID(message["data"])


async def find_or_wait(
    redis: Redis,
    user_id: uuid.UUID,
    filters: Filters,
    *,
    widened: bool = False,
    timeout_seconds: float = DEFAULT_COLD_START_TIMEOUT_SECONDS,
    on_waiting: Callable[[], Awaitable[None]] | None = None,
) -> uuid.UUID | None:
    """Try to pair `user_id` with a compatible waiting user; else join the
    queue and wait up to `timeout_seconds`. Returns the matched partner's id,
    or None on cold-start timeout (caller is left dequeued in that case).

    `on_waiting`, if given, is awaited once this user is enqueued and about to
    block, but not if a partner was found instantly - letting the caller notify
    a client only when it's actually about to wait.
    """
    pubsub = redis.pubsub()
    async with pubsub:
        # Subscribe before enqueueing: enqueue() can make this user matchable
        # (and immediately popped + published to) by a concurrent partner, so
        # the subscription must already be live or that publish is dropped.
        await pubsub.subscribe(match_channel(user_id))

        partner_id = await enqueue(redis, user_id, filters, widened=widened)
        if partner_id is not None:
            await redis.publish(match_channel(partner_id), str(user_id))
            return partner_id

        if on_waiting is not None:
            await on_waiting()

        try:
            return await _wait_for_partner(pubsub, timeout_seconds=timeout_seconds)
        except TimeoutError:
            await dequeue(redis, user_id)
            return None
