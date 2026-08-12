import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_safety.schemas import (
    FlaggedMessageDetail,
    FlaggedMessageSummary,
    PatternRuleBody,
    PatternRuleOut,
)
from app.chat_safety.service import (
    InvalidPatternError,
    decrypt_flag,
    list_active_patterns,
    log_audit,
    rollback_pattern,
    upsert_pattern,
)
from app.config import settings
from app.db import get_db
from app.models.chat_safety import FlaggedMessage

router = APIRouter(prefix="/moderation/chat-safety", tags=["moderation"])

_db_dependency = Depends(get_db)


async def _require_moderator(
    x_moderation_secret: str = Header(default=""),
) -> str:
    """Minimal privileged-access gate, matching task 06's precedent of
    "no full admin UI required at MVP" - a shared secret rather than a
    role/permission system. Returns the actor label used for audit rows."""
    if not secrets.compare_digest(x_moderation_secret, settings.chat_safety_moderation_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")
    return "moderator"


_moderator_dependency = Depends(_require_moderator)


@router.get("/flags", response_model=list[FlaggedMessageSummary])
async def list_flags_endpoint(
    actor: str = _moderator_dependency,
    db: AsyncSession = _db_dependency,
) -> list[FlaggedMessage]:
    result = await db.execute(select(FlaggedMessage).order_by(FlaggedMessage.created_at.desc()))
    flags = list(result.scalars().all())
    await log_audit(db, action="list_flags", actor=actor, detail=f"{len(flags)} row(s)")
    return flags


@router.get("/flags/{flag_id}", response_model=FlaggedMessageDetail)
async def get_flag_endpoint(
    flag_id: uuid.UUID,
    actor: str = _moderator_dependency,
    db: AsyncSession = _db_dependency,
) -> FlaggedMessageDetail:
    flag = await db.get(FlaggedMessage, flag_id)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    text = await decrypt_flag(flag)
    await log_audit(db, action="view_flag", actor=actor, detail=str(flag_id))
    return FlaggedMessageDetail(
        id=flag.id,
        call_session_id=flag.call_session_id,
        sender_id=flag.sender_id,
        recipient_id=flag.recipient_id,
        category=flag.category,
        matched_pattern_slug=flag.matched_pattern_slug,
        created_at=flag.created_at,
        text=text,
    )


@router.get("/patterns", response_model=list[PatternRuleOut])
async def list_patterns_endpoint(
    actor: str = _moderator_dependency,
    db: AsyncSession = _db_dependency,
) -> list[PatternRuleOut]:
    patterns = await list_active_patterns(db)
    return [PatternRuleOut.model_validate(p, from_attributes=True) for p in patterns]


@router.put("/patterns", response_model=PatternRuleOut)
async def upsert_pattern_endpoint(
    body: PatternRuleBody,
    actor: str = _moderator_dependency,
    db: AsyncSession = _db_dependency,
) -> PatternRuleOut:
    try:
        row = await upsert_pattern(
            db, slug=body.slug, category=body.category, pattern=body.pattern, actor=actor
        )
    except InvalidPatternError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PatternRuleOut.model_validate(row, from_attributes=True)


@router.post("/patterns/{slug}/rollback/{version}", response_model=PatternRuleOut)
async def rollback_pattern_endpoint(
    slug: str,
    version: int,
    actor: str = _moderator_dependency,
    db: AsyncSession = _db_dependency,
) -> PatternRuleOut:
    try:
        row = await rollback_pattern(db, slug=slug, version=version, actor=actor)
    except InvalidPatternError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PatternRuleOut.model_validate(row, from_attributes=True)
