import logging

from anyio.to_thread import run_sync
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.email import send_verification_waitlist_welcome_back_email
from app.models.user import User
from app.models.verification import VerificationWaitlistEntry
from app.verification.service import promote_waitlist_if_room

logger = logging.getLogger(__name__)


async def sweep_verification_waitlist(db: AsyncSession, redis: Redis) -> int:
    """Promotes as many waitlisted users as this month's quota allows,
    emailing each one promoted. Intended to run on a monthly schedule
    (e.g. cron hitting a maintenance endpoint, or a scheduled task runner) -
    no scheduler is wired up by this task; see tasks/10-age-verification.md
    scope (admin/ops tooling is out of scope). Returns the number promoted.

    A promoted user keeps their freed slot even if the notification email
    fails to send - there's no retryable outbox for this send today, so a
    failure here is logged and the sweep continues with the next user
    rather than losing every remaining promotion in this run.
    """
    result = await db.execute(
        select(User).join(VerificationWaitlistEntry, VerificationWaitlistEntry.user_id == User.id)
    )
    waitlisted_users = result.scalars().all()

    promoted = 0
    for user in waitlisted_users:
        if not await promote_waitlist_if_room(db, redis, user):
            continue
        promoted += 1
        try:
            await run_sync(send_verification_waitlist_welcome_back_email, user.email)
        except Exception:
            logger.exception("Failed to send waitlist welcome-back email to %s", user.email)

    return promoted
