from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RequestLinkBody, RequestLinkResponse, VerifyResponse
from app.auth.service import (
    InvalidOrExpiredTokenError,
    request_link,
    revoke_session,
    verify_token,
)
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
_db_dependency = Depends(get_db)
_bearer_scheme = HTTPBearer(auto_error=False)
_bearer_dependency = Depends(_bearer_scheme)


@router.post("/request-link", response_model=RequestLinkResponse)
async def request_link_endpoint(
    body: RequestLinkBody, db: AsyncSession = _db_dependency
) -> RequestLinkResponse:
    await request_link(db, body.email, body.birthdate)
    return RequestLinkResponse()


@router.get("/verify", response_model=VerifyResponse)
async def verify_endpoint(token: str, db: AsyncSession = _db_dependency) -> VerifyResponse:
    try:
        session_token, user = await verify_token(db, token)
    except InvalidOrExpiredTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired link.",
        ) from exc

    return VerifyResponse(session_token=session_token, user_id=user.id, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    credentials: HTTPAuthorizationCredentials | None = _bearer_dependency,
    db: AsyncSession = _db_dependency,
) -> None:
    if credentials is not None:
        await revoke_session(db, credentials.credentials)
