import uuid
from datetime import datetime

from pydantic import BaseModel


class FlaggedMessageSummary(BaseModel):
    id: uuid.UUID
    call_session_id: str
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    category: str
    matched_pattern_slug: str
    created_at: datetime


class FlaggedMessageDetail(FlaggedMessageSummary):
    text: str


class PatternRuleBody(BaseModel):
    slug: str
    category: str
    pattern: str


class PatternRuleOut(BaseModel):
    id: uuid.UUID
    slug: str
    version: int
    category: str
    pattern: str
    is_active: bool
    created_by: str
    created_at: datetime
