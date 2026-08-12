import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChatSafetyPattern(Base):
    """A single keyword/pattern rule, versioned so edits have an auditable
    history and can be rolled back to a prior known-good version. The active
    row for a given `slug` is the one with the highest `version`; superseded
    versions are kept (not deleted) as the rollback trail."""

    __tablename__ = "chat_safety_patterns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    category: Mapped[str] = mapped_column(String, nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FlaggedMessage(Base):
    """A chat message that matched a safety pattern, held for moderator
    review. `ciphertext` is the Fernet-encrypted message body (encrypted at
    rest per tasks/13-chat-safety-filters.md); nothing here stores plaintext.
    Purged by the retention sweep once `created_at` is older than the
    30-day + 24h grace window."""

    __tablename__ = "flagged_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    call_session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    matched_pattern_slug: Mapped[str] = mapped_column(String, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ChatSafetyAuditLog(Base):
    """Append-only audit trail for everything this task requires proof of:
    moderator access to flagged content, keyword/pattern rule edits, and
    retention-sweep runs. `action` distinguishes the event kind; `detail` is
    a short free-text description (e.g. "purged 42 rows")."""

    __tablename__ = "chat_safety_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    success: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
