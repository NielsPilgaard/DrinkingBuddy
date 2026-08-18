import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GamePrompt(Base):
    """Backend-served content bank for all three mini-game types
    (tasks/mini-games.md). Trivia rows are a server-side cache of opentdb.com
    responses (`source="opentdb"`); would-you-rather/never-have-I-ever rows
    are a one-time, manually-reviewed scrape (`source="scrape"`). DB-served
    rather than bundled so content can be tuned/expanded post-launch without
    an app store release, matching the chat-safety pattern-list precedent."""

    __tablename__ = "game_prompts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    game_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    correct_option: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
