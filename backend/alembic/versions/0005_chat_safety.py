"""chat_safety: flagged messages, pattern rules, audit log

Revision ID: 0005_chat_safety
Revises: 0004_report_block
Create Date: 2026-08-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_chat_safety"
down_revision: str | None = "0004_report_block"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_safety_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_chat_safety_patterns_slug", "chat_safety_patterns", ["slug"])

    op.create_table(
        "flagged_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_session_id", sa.String(), nullable=False),
        sa.Column(
            "sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "recipient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("matched_pattern_slug", sa.String(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_flagged_messages_call_session_id", "flagged_messages", ["call_session_id"])
    op.create_index("ix_flagged_messages_sender_id", "flagged_messages", ["sender_id"])
    op.create_index("ix_flagged_messages_recipient_id", "flagged_messages", ["recipient_id"])
    op.create_index("ix_flagged_messages_created_at", "flagged_messages", ["created_at"])

    op.create_table(
        "chat_safety_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("chat_safety_audit_log")
    op.drop_index("ix_flagged_messages_created_at", table_name="flagged_messages")
    op.drop_index("ix_flagged_messages_recipient_id", table_name="flagged_messages")
    op.drop_index("ix_flagged_messages_sender_id", table_name="flagged_messages")
    op.drop_index("ix_flagged_messages_call_session_id", table_name="flagged_messages")
    op.drop_table("flagged_messages")
    op.drop_index("ix_chat_safety_patterns_slug", table_name="chat_safety_patterns")
    op.drop_table("chat_safety_patterns")
