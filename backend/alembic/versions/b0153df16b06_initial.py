"""initial

Revision ID: b0153df16b06
Revises:
Create Date: 2026-07-13 23:06:02.818363

"""

from collections.abc import Sequence

revision: str = "b0153df16b06"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
