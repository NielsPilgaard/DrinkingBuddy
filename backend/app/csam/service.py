import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from anyio.to_thread import run_sync
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_safety.service import decrypt_flag
from app.config import settings
from app.email import send_csam_case_opened_email
from app.models.chat_safety import FlaggedMessage
from app.models.csam import CsamAuditLog, CsamCase
from app.models.report import Report
from app.models.suspension import Suspension
from app.models.user import User
from app.models.verification import Verification

# Report reason that routes to this module instead of only the generic
# auto-suspend breaker (docs/csam-runbook.md).
CSAM_REPORT_REASON = "csam"

logger = logging.getLogger(__name__)


class CaseStateError(Exception):
    pass


def _fernet() -> Fernet:
    if not settings.csam_evidence_encryption_key:
        raise RuntimeError("csam_evidence_encryption_key is not configured")
    return Fernet(settings.csam_evidence_encryption_key.encode())


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    actor: str,
    case_id: uuid.UUID | None = None,
    detail: str = "",
    success: bool = True,
) -> None:
    db.add(
        CsamAuditLog(case_id=case_id, action=action, actor=actor, detail=detail, success=success)
    )
    await db.commit()


async def _snapshot_evidence(
    db: AsyncSession, *, source: str, reported_id: uuid.UUID, call_session_id: str
) -> dict[str, Any]:
    """Minimum necessary: who, when, what the server already held. The
    server never holds call audio/video, so there is no imagery to copy.
    Flagged chat text is copied so it outlives the 30-day chat-safety purge
    while the case is retained."""
    user = await db.get(User, reported_id)
    verifications = (
        (await db.execute(select(Verification).where(Verification.user_id == reported_id)))
        .scalars()
        .all()
    )
    reports = (
        (
            await db.execute(
                select(Report).where(
                    Report.reported_id == reported_id,
                    Report.call_session_id == call_session_id,
                )
            )
        )
        .scalars()
        .all()
    )
    flags = (
        (
            await db.execute(
                select(FlaggedMessage).where(FlaggedMessage.call_session_id == call_session_id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "source": source,
        "call_session_id": call_session_id,
        "reported_user": {
            "id": str(reported_id),
            "email": user.email if user else None,
            "self_declared_birthdate": user.birthdate.isoformat() if user else None,
            "account_created_at": user.created_at.isoformat() if user else None,
        },
        "verifications": [
            {
                "status": v.status,
                "method": v.method,
                "verified_at": v.verified_at.isoformat() if v.verified_at else None,
            }
            for v in verifications
        ],
        "reports": [
            {
                "reporter_id": str(r.reporter_id),
                "reason": r.reason,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ],
        "flagged_messages": [
            {
                "sender_id": str(f.sender_id),
                "recipient_id": str(f.recipient_id),
                "category": f.category,
                "created_at": f.created_at.isoformat(),
                "text": await decrypt_flag(f),
            }
            for f in flags
        ],
    }


async def open_case(
    db: AsyncSession,
    *,
    source: str,
    reported_id: uuid.UUID,
    call_session_id: str,
    actor: str,
) -> CsamCase:
    """Opens a CSAM-suspected case: encrypted evidence snapshot, precautionary
    suspension until reviewed, on-call email. A second trigger for the same
    user + call while a case is open is logged against that case instead of
    opening a duplicate. Commits."""
    existing = (
        await db.execute(
            select(CsamCase).where(
                CsamCase.reported_id == reported_id,
                CsamCase.call_session_id == call_session_id,
                CsamCase.status == "open",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        await log_audit(
            db, action="additional_trigger", actor=actor, case_id=existing.id, detail=source
        )
        return existing

    evidence = await _snapshot_evidence(
        db, source=source, reported_id=reported_id, call_session_id=call_session_id
    )
    now = datetime.now(UTC)
    suspension = Suspension(
        user_id=reported_id, expires_at=now + timedelta(hours=settings.csam_suspension_hours)
    )
    db.add(suspension)
    await db.flush()

    case = CsamCase(
        source=source,
        reported_id=reported_id,
        call_session_id=call_session_id,
        suspension_id=suspension.id,
        status="open",
        evidence_ciphertext=_fernet().encrypt(json.dumps(evidence).encode()),
        legal_hold=False,
        retain_until=now + timedelta(days=settings.csam_evidence_retention_days),
    )
    db.add(case)
    await db.flush()
    await log_audit(db, action="open_case", actor=actor, case_id=case.id, detail=source)

    try:
        await run_sync(
            send_csam_case_opened_email, settings.csam_oncall_email, str(case.id), source
        )
    except Exception as exc:
        # Never fail the report over SMTP; the audit row is the alert trail
        # and the runbook's daily check catches unnotified cases.
        logger.exception("CSAM on-call email failed for case %s", case.id)
        await log_audit(
            db,
            action="notify_oncall",
            actor="system",
            case_id=case.id,
            detail=str(exc),
            success=False,
        )
    else:
        await log_audit(db, action="notify_oncall", actor="system", case_id=case.id)
    return case


async def list_cases(db: AsyncSession) -> list[CsamCase]:
    result = await db.execute(select(CsamCase).order_by(CsamCase.created_at.desc()))
    return list(result.scalars().all())


def read_evidence(case: CsamCase) -> dict[str, Any]:
    return json.loads(_fernet().decrypt(case.evidence_ciphertext))


async def mark_reported(
    db: AsyncSession, case: CsamCase, *, external_reference: str, actor: str
) -> CsamCase:
    """Records that the case went to the authorities named in the runbook.
    Sets a legal hold: the receiving authority may still ask for the
    evidence, and only counsel/authority decides when it can be lifted."""
    if case.status != "open":
        raise CaseStateError(f"Case is {case.status}, not open")
    case.status = "reported"
    case.external_reference = external_reference
    case.legal_hold = True
    case.closed_at = datetime.now(UTC)
    await log_audit(
        db, action="mark_reported", actor=actor, case_id=case.id, detail=external_reference
    )
    return case


async def dismiss(db: AsyncSession, case: CsamCase, *, reason: str, actor: str) -> CsamCase:
    """Closes a case judged not CSAM and lifts its precautionary suspension.
    Evidence still follows the normal retention window."""
    if case.status != "open":
        raise CaseStateError(f"Case is {case.status}, not open")
    now = datetime.now(UTC)
    case.status = "dismissed"
    case.closed_at = now
    if case.suspension_id is not None:
        suspension = await db.get(Suspension, case.suspension_id)
        if suspension is not None and suspension.expires_at > now:
            suspension.expires_at = now
    await log_audit(db, action="dismiss", actor=actor, case_id=case.id, detail=reason)
    return case


async def set_legal_hold(
    db: AsyncSession, case: CsamCase, *, active: bool, reason: str, actor: str
) -> CsamCase:
    case.legal_hold = active
    await log_audit(
        db,
        action="legal_hold_on" if active else "legal_hold_off",
        actor=actor,
        case_id=case.id,
        detail=reason,
    )
    return case


async def purge_expired_cases(db: AsyncSession) -> int:
    """Deletes cases past `retain_until` that are not under legal hold. A
    lifted hold resumes normal deletion on the next run. No scheduler is
    wired up (same precedent as chat_safety.service.purge_expired_flags);
    run daily once deployed."""
    now = datetime.now(UTC)
    try:
        result = await db.execute(
            select(CsamCase).where(CsamCase.retain_until < now, CsamCase.legal_hold.is_(False))
        )
        expired = result.scalars().all()
        purged_ids = [str(case.id) for case in expired]
        for case in expired:
            await db.delete(case)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        await log_audit(
            db, action="retention_sweep", actor="system", detail=str(exc), success=False
        )
        raise

    await log_audit(
        db,
        action="retention_sweep",
        actor="system",
        detail=f"purged {len(purged_ids)} case(s): {', '.join(purged_ids)}",
    )
    return len(purged_ids)
