import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.csam.schemas import (
    CsamCaseSummary,
    CsamEvidence,
    DismissBody,
    LegalHoldBody,
    MarkReportedBody,
)
from app.csam.service import (
    CaseStateError,
    dismiss,
    list_cases,
    log_audit,
    mark_reported,
    read_evidence,
    set_legal_hold,
)
from app.db import get_db
from app.models.csam import CsamCase

router = APIRouter(prefix="/moderation/csam", tags=["moderation"])

_db_dependency = Depends(get_db)


async def _require_csam_officer(
    x_csam_secret: str = Header(default=""),
    x_actor: str = Header(default=""),
) -> str:
    """Narrower gate than chat-safety moderation: its own secret, held only
    by the runbook's authorized set. X-Actor names the person so every audit
    row says who - honor-system at MVP, no per-user accounts."""
    if not secrets.compare_digest(x_csam_secret, settings.csam_moderation_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")
    if not x_actor.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="X-Actor header is required"
        )
    return f"csam:{x_actor.strip()}"


_officer_dependency = Depends(_require_csam_officer)


async def _get_case(db: AsyncSession, case_id: uuid.UUID) -> CsamCase:
    case = await db.get(CsamCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


@router.get("/cases", response_model=list[CsamCaseSummary])
async def list_cases_endpoint(
    actor: str = _officer_dependency,
    db: AsyncSession = _db_dependency,
) -> list[CsamCase]:
    cases = await list_cases(db)
    await log_audit(db, action="list_cases", actor=actor, detail=f"{len(cases)} case(s)")
    return cases


@router.get("/cases/{case_id}/evidence", response_model=CsamEvidence)
async def get_evidence_endpoint(
    case_id: uuid.UUID,
    actor: str = _officer_dependency,
    db: AsyncSession = _db_dependency,
) -> CsamEvidence:
    case = await _get_case(db, case_id)
    evidence = read_evidence(case)
    await log_audit(db, action="view_evidence", actor=actor, case_id=case.id)
    return CsamEvidence(case_id=case.id, evidence=evidence)


@router.post("/cases/{case_id}/reported", response_model=CsamCaseSummary)
async def mark_reported_endpoint(
    case_id: uuid.UUID,
    body: MarkReportedBody,
    actor: str = _officer_dependency,
    db: AsyncSession = _db_dependency,
) -> CsamCase:
    case = await _get_case(db, case_id)
    try:
        return await mark_reported(
            db, case, external_reference=body.external_reference, actor=actor
        )
    except CaseStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/cases/{case_id}/dismiss", response_model=CsamCaseSummary)
async def dismiss_endpoint(
    case_id: uuid.UUID,
    body: DismissBody,
    actor: str = _officer_dependency,
    db: AsyncSession = _db_dependency,
) -> CsamCase:
    case = await _get_case(db, case_id)
    try:
        return await dismiss(db, case, reason=body.reason, actor=actor)
    except CaseStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/cases/{case_id}/legal-hold", response_model=CsamCaseSummary)
async def legal_hold_endpoint(
    case_id: uuid.UUID,
    body: LegalHoldBody,
    actor: str = _officer_dependency,
    db: AsyncSession = _db_dependency,
) -> CsamCase:
    case = await _get_case(db, case_id)
    return await set_legal_hold(db, case, active=body.active, reason=body.reason, actor=actor)
