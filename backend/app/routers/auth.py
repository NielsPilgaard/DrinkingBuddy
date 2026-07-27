from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RequestLinkBody, RequestLinkResponse, VerifyResponse
from app.auth.service import InvalidOrExpiredTokenError, request_link, verify_token
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
_db_dependency = Depends(get_db)


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
