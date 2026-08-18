"""mini_games: game_prompts content bank

Revision ID: 0006_game_prompts
Revises: 0005_chat_safety
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_game_prompts"
down_revision: str | None = "0005_chat_safety"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_type", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("options", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("correct_option", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_game_prompts_game_type", "game_prompts", ["game_type"])


def downgrade() -> None:
    op.drop_index("ix_game_prompts_game_type", table_name="game_prompts")
    op.drop_table("game_prompts")
