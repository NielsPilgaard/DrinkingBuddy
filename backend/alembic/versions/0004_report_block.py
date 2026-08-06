"""report_block: reports, blocks, suspensions

Revision ID: 0004_report_block
Revises: 0003_verification
Create Date: 2026-08-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_report_block"
down_revision: str | None = "0003_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "reported_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("call_session_id", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
    op.create_index("ix_reports_reported_id", "reports", ["reported_id"])
    op.create_unique_constraint(
        "uq_reports_reporter_id_call_session_id", "reports", ["reporter_id", "call_session_id"]
    )

    op.create_table(
        "blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "blocker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "blocked_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_blocks_blocker_id", "blocks", ["blocker_id"])
    op.create_index("ix_blocks_blocked_id", "blocks", ["blocked_id"])
    op.create_unique_constraint(
        "uq_blocks_blocker_id_blocked_id", "blocks", ["blocker_id", "blocked_id"]
    )

    op.create_table(
        "suspensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_suspensions_user_id", "suspensions", ["user_id"])


def downgrade() -> None:
    op.drop_table("suspensions")
    op.drop_constraint("uq_blocks_blocker_id_blocked_id", "blocks", type_="unique")
    op.drop_table("blocks")
    op.drop_constraint("uq_reports_reporter_id_call_session_id", "reports", type_="unique")
    op.drop_table("reports")
