import logging
import random
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mini_games.content_bank import NEVER_HAVE_I_EVER_PROMPTS, WOULD_YOU_RATHER_PROMPTS
from app.mini_games.opentdb import OpenTdbRequestError, fetch_opentdb_questions
from app.mini_games.schemas import GamePrompt, GameType
from app.models.game_prompt import GamePrompt as GamePromptRow

logger = logging.getLogger(__name__)


@dataclass
class GameSession:
    game_type: GameType
    requested_by: uuid.UUID
    accepted: bool = False
    current_prompt: GamePrompt | None = None
    revealed: bool = False
    shown_prompt_ids: set[uuid.UUID] = field(default_factory=set)


# call_id -> active game session. In-process/in-memory like
# signaling.registry.CallRegistry and chat_safety's _pending_age_questions -
# single VPS, single worker, ephemeral per call, no cross-process sharing
# needed (tasks/mini-games.md session model).
_active_games: dict[str, GameSession] = {}


def start_game(call_id: str, game_type: GameType, requested_by: uuid.UUID) -> GameSession:
    session = GameSession(game_type=game_type, requested_by=requested_by)
    _active_games[call_id] = session
    return session


def get_session(call_id: str) -> GameSession | None:
    return _active_games.get(call_id)


def accept_game(call_id: str) -> GameSession | None:
    session = _active_games.get(call_id)
    if session is not None:
        session.accepted = True
    return session


def close_game(call_id: str) -> None:
    _active_games.pop(call_id, None)


def clear_call_state(call_id: str) -> None:
    """Drops any active game for a call - call on call teardown so state
    doesn't leak across a call_id being reused."""
    _active_games.pop(call_id, None)


async def _load_bank(db: AsyncSession, game_type: GameType) -> list[GamePromptRow]:
    result = await db.execute(
        select(GamePromptRow).where(GamePromptRow.game_type == game_type, GamePromptRow.is_active)
    )
    return list(result.scalars().all())


async def pick_next_prompt(db: AsyncSession, session: GameSession) -> GamePrompt | None:
    """Picks a random not-yet-shown prompt for the session's game type.
    Returns None once the bank is exhausted for this call (caller decides
    what to do - tasks/mini-games.md doesn't require wraparound, unlike
    ice-breaker's client-side list)."""
    rows = await _load_bank(db, session.game_type)
    candidates = [row for row in rows if row.id not in session.shown_prompt_ids]
    if not candidates:
        return None

    row = random.choice(candidates)
    session.shown_prompt_ids.add(row.id)
    prompt = GamePrompt(
        id=row.id,
        game_type=session.game_type,
        text=row.text,
        options=row.options,
        correct_option=row.correct_option,
    )
    session.current_prompt = prompt
    session.revealed = False
    return prompt


async def seed_content_bank_if_empty(db: AsyncSession) -> int:
    """Seeds WYR/NHIE rows from the static content_bank module if the table
    has none yet for those game types. Idempotent - safe to call on every
    startup. Does not touch trivia rows (those come from
    sync_trivia_from_opentdb). Returns the number of rows inserted."""
    inserted = 0
    for game_type, prompts in (
        ("would_you_rather", WOULD_YOU_RATHER_PROMPTS),
        ("never_have_i_ever", NEVER_HAVE_I_EVER_PROMPTS),
    ):
        existing = await _load_bank(db, game_type)  # type: ignore[arg-type]
        if existing:
            continue
        for text in prompts:
            db.add(GamePromptRow(game_type=game_type, text=text, source="scrape", is_active=True))
            inserted += 1
    if inserted:
        await db.commit()
    return inserted


async def sync_trivia_from_opentdb(db: AsyncSession, amount: int = 50) -> int:
    """Refills the trivia bank from opentdb.com. Intended to run on an
    unscheduled/manual maintenance cadence (no scheduler wired up here,
    matching app/verification/waitlist_sweep.py precedent) - never called
    per-round from live call traffic. Deactivates the previous batch so
    `_load_bank` only serves the freshest set, then inserts the new one.
    Never raises: an opentdb outage should leave the existing cache serving
    rather than break the sync caller."""
    try:
        questions = await fetch_opentdb_questions(amount)
    except OpenTdbRequestError:
        logger.exception("opentdb sync failed - trivia bank left unchanged")
        return 0

    existing = await _load_bank(db, "trivia")
    for row in existing:
        row.is_active = False

    for question, options, correct in questions:
        db.add(
            GamePromptRow(
                game_type="trivia",
                text=question,
                options=options,
                correct_option=correct,
                source="opentdb",
                is_active=True,
            )
        )
    await db.commit()
    return len(questions)
