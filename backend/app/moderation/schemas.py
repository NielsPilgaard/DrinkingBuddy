import uuid
from typing import Literal

from pydantic import BaseModel

ReportReason = Literal["nudity", "harassment", "underage", "spam", "other"]


class ReportBody(BaseModel):
    reported_id: uuid.UUID
    call_session_id: str
    reason: ReportReason


class BlockBody(BaseModel):
    blocked_id: uuid.UUID
