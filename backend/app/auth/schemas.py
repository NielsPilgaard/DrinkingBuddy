import uuid
from datetime import date

from pydantic import BaseModel, EmailStr


class RequestLinkBody(BaseModel):
    email: EmailStr
    birthdate: date | None = None


class RequestLinkResponse(BaseModel):
    detail: str = "If this email is valid, a sign-in link has been sent."


class VerifyResponse(BaseModel):
    session_token: str
    user_id: uuid.UUID
    email: str
