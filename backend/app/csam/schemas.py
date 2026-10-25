import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CsamCaseSummary(BaseModel):
    id: uuid.UUID
    source: str
    reported_id: uuid.UUID
    call_session_id: str
    status: str
    external_reference: str | None
    legal_hold: bool
    retain_until: datetime
    created_at: datetime
    closed_at: datetime | None


class CsamEvidence(BaseModel):
    case_id: uuid.UUID
    evidence: dict[str, Any]


class MarkReportedBody(BaseModel):
    # The authority's case/receipt number (e.g. police journal number).
    external_reference: str = Field(min_length=1)


class DismissBody(BaseModel):
    reason: str = Field(min_length=1)


class LegalHoldBody(BaseModel):
    active: bool
    reason: str = Field(min_length=1)
