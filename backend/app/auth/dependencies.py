from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_user_for_session_token
from app.db import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
_bearer_dependency = Depends(bearer_scheme)
_db_dependency = Depends(get_db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = _bearer_dependency,
    db: AsyncSession = _db_dependency,
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = await get_user_for_session_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session"
        )

    return user
