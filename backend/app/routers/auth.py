from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RequestLinkBody, RequestLinkResponse, VerifyBody, VerifyResponse
from app.auth.service import (
    AccountSuspendedError,
    InvalidOrExpiredTokenError,
    request_link,
    revoke_session,
    verify_token,
)
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
_db_dependency = Depends(get_db)
_bearer_scheme = HTTPBearer(auto_error=False)
_bearer_dependency = Depends(_bearer_scheme)


@router.post("/request-link", response_model=RequestLinkResponse)
async def request_link_endpoint(
    body: RequestLinkBody,
    db: AsyncSession = _db_dependency,
    x_test_mode: str | None = Header(default=None),
) -> RequestLinkResponse:
    raw_token = await request_link(db, body.email, body.birthdate)
    # Double-gated (environment + header) so a misconfigured deployment can't
    # leak sign-in tokens just by one of the two being wrong - see
    # tasks/NEEDS-HUMAN-REVIEW-maestro-e2e.md.
    if settings.environment == "development" and x_test_mode == "1" and raw_token is not None:
        return RequestLinkResponse(debug_token=raw_token)
    return RequestLinkResponse()


# POST with the token in the body, not GET with a query param: URLs end up in
# access logs and trace spans, and the token signs the user in.
@router.post("/verify", response_model=VerifyResponse)
async def verify_endpoint(body: VerifyBody, db: AsyncSession = _db_dependency) -> VerifyResponse:
    try:
        session_token, user = await verify_token(db, body.token)
    except InvalidOrExpiredTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired link.",
        ) from exc
    except AccountSuspendedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended pending review.",
        ) from exc

    return VerifyResponse(session_token=session_token, user_id=user.id, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    credentials: HTTPAuthorizationCredentials | None = _bearer_dependency,
    db: AsyncSession = _db_dependency,
) -> None:
    if credentials is not None:
        await revoke_session(db, credentials.credentials)
