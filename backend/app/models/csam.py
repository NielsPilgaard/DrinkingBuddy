import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CsamCase(Base):
    """A CSAM-suspected incident, routed to docs/csam-runbook.md instead of
    the generic report queue. `evidence_ciphertext` is a Fernet-encrypted
    JSON snapshot of what the server held at open time (account metadata,
    report, flagged chat text) - the server never holds call media. Deleted
    by the retention sweep once `retain_until` passes, unless `legal_hold`
    is set."""

    __tablename__ = "csam_cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String, nullable=False)
    reported_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    call_session_id: Mapped[str] = mapped_column(String, nullable=False)
    suspension_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suspensions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    external_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_ciphertext: Mapped[bytes] = mapped_column(nullable=False)
    legal_hold: Mapped[bool] = mapped_column(nullable=False, default=False)
    retain_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CsamAuditLog(Base):
    """Append-only trail of every touch on a CSAM case: open, list, evidence
    view, status change, legal hold, retention purge. Kept apart from
    chat_safety_audit_log so it can be scoped to the CSAM-authorized set.
    `case_id` is a plain column, not a FK, so rows outlive purged cases."""

    __tablename__ = "csam_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    success: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
