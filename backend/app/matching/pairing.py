import time
import uuid
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.matching.queue import dequeue, enqueue, match_channel
from app.matching.schemas import Filters

DEFAULT_COLD_START_TIMEOUT_SECONDS = 25


async def _wait_for_partner(pubsub: PubSub, *, timeout_seconds: float) -> uuid.UUID:
    """Block until a match is published, or `timeout_seconds` genuinely elapses.

    `get_message` returns `None` both on a real timeout and whenever it
    filters out a subscribe-confirmation event (which arrives near-instantly
    after `subscribe()`), so a bare `None` can't be treated as "give up" -
    only the wall-clock deadline can.
    """
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=remaining)
        if message is None:
            continue
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
    is_blocked_pair: Callable[[uuid.UUID, uuid.UUID], Awaitable[bool]] | None = None,
) -> uuid.UUID | None:
    """Try to pair `user_id` with a compatible waiting user; else join the
    queue and wait up to `timeout_seconds`. Returns the matched partner's id,
    or None on cold-start timeout (caller is left dequeued in that case).

    `on_waiting`, if given, is awaited once this user is enqueued and about to
    block, but not if a partner was found instantly - letting the caller notify
    a client only when it's actually about to wait.

    `is_blocked_pair`, if given, is used to skip candidates blocked (in
    either direction) with `user_id` - see `queue.enqueue`.
    """
    pubsub = redis.pubsub()
    async with pubsub:
        # Subscribe before enqueueing: enqueue() can make this user matchable
        # (and immediately popped + published to) by a concurrent partner, so
        # the subscription must already be live or that publish is dropped.
        await pubsub.subscribe(match_channel(user_id))

        partner_id = await enqueue(
            redis, user_id, filters, widened=widened, is_blocked_pair=is_blocked_pair
        )
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
