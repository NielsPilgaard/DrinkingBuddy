import uuid
from typing import Literal

from pydantic import BaseModel

# "csam" = sexual content involving a minor. Routes to app/csam (separate
# legal duty, docs/csam-runbook.md) in addition to the generic breaker.
ReportReason = Literal["nudity", "harassment", "underage", "csam", "spam", "other"]


class ReportBody(BaseModel):
    reported_id: uuid.UUID
    call_session_id: str
    reason: ReportReason


class BlockBody(BaseModel):
    blocked_id: uuid.UUID
