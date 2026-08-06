from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_user_for_session_token
from app.db import get_db
from app.models.user import User
from app.moderation.schemas import BlockBody, ReportBody
from app.moderation.service import create_block, submit_report

router = APIRouter(tags=["moderation"])
_db_dependency = Depends(get_db)
_bearer_scheme = HTTPBearer(auto_error=False)
_bearer_dependency = Depends(_bearer_scheme)


async def _current_user(credentials: HTTPAuthorizationCredentials | None, db: AsyncSession) -> User:
    user = (
        await get_user_for_session_token(db, credentials.credentials)
        if credentials is not None
        else None
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return user


@router.post("/report", status_code=status.HTTP_204_NO_CONTENT)
async def report_endpoint(
    body: ReportBody,
    credentials: HTTPAuthorizationCredentials | None = _bearer_dependency,
    db: AsyncSession = _db_dependency,
) -> None:
    user = await _current_user(credentials, db)
    if body.reported_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot report yourself."
        )
    await submit_report(db, user.id, body.reported_id, body.call_session_id, body.reason)


@router.post("/block", status_code=status.HTTP_204_NO_CONTENT)
async def block_endpoint(
    body: BlockBody,
    credentials: HTTPAuthorizationCredentials | None = _bearer_dependency,
    db: AsyncSession = _db_dependency,
) -> None:
    user = await _current_user(credentials, db)
    if body.blocked_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot block yourself."
        )
    await create_block(db, user.id, body.blocked_id)
