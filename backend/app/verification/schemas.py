import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

VerificationMethod = Literal["age_estimation", "cpr_passthrough"]
VerificationStatus = Literal["pending", "verified", "failed", "revoked", "waitlisted"]


class StartVerificationBody(BaseModel):
    method: VerificationMethod = "age_estimation"


class StartVerificationResponse(BaseModel):
    status: VerificationStatus
    session_token: str | None = None
    detail: str | None = None


class VerificationStatusResponse(BaseModel):
    status: VerificationStatus
    method: VerificationMethod | None = None
    verified_at: datetime | None = None
    expiry: datetime | None = None


class DiditWebhookPayload(BaseModel):
    session_id: str
    status: str
    user_id: uuid.UUID | None = None
