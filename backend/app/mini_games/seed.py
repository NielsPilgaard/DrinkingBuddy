"""Fills the mini-game prompt banks. Run after migrations (the compose
`migrate` service does): `python -m app.mini_games.seed`.

Would-you-rather / never-have-I-ever come from the bundled content bank.
Trivia is fetched from opentdb.com only when its bank is empty; an opentdb
outage leaves it empty without failing the deploy.
"""

import asyncio
import logging

from app.db import async_session
from app.mini_games.service import (
    has_prompts,
    seed_content_bank_if_empty,
    sync_trivia_from_opentdb,
)

logger = logging.getLogger(__name__)


async def seed() -> None:
    async with async_session() as db:
        inserted = await seed_content_bank_if_empty(db)
        logger.info("seeded %d would-you-rather/never-have-I-ever prompts", inserted)
        if not await has_prompts(db, "trivia"):
            synced = await sync_trivia_from_opentdb(db)
            logger.info("synced %d trivia prompts from opentdb", synced)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
