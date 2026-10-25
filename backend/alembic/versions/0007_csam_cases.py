"""csam: csam_cases, csam_audit_log

Revision ID: 0007_csam_cases
Revises: 0006_game_prompts
Create Date: 2026-10-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_csam_cases"
down_revision: str | None = "0006_game_prompts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "csam_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "reported_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("call_session_id", sa.String(), nullable=False),
        sa.Column(
            "suspension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suspensions.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("external_reference", sa.String(), nullable=True),
        sa.Column("evidence_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("legal_hold", sa.Boolean(), nullable=False),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_csam_cases_reported_id", "csam_cases", ["reported_id"])
    op.create_index("ix_csam_cases_retain_until", "csam_cases", ["retain_until"])

    op.create_table(
        "csam_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_csam_audit_log_case_id", "csam_audit_log", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_csam_audit_log_case_id", table_name="csam_audit_log")
    op.drop_table("csam_audit_log")
    op.drop_index("ix_csam_cases_retain_until", table_name="csam_cases")
    op.drop_index("ix_csam_cases_reported_id", table_name="csam_cases")
    op.drop_table("csam_cases")
