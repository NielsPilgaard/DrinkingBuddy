import uuid
from typing import Literal

from pydantic import BaseModel


class Filters(BaseModel):
    language: str
    drink_type: Literal["alcoholic", "non_alcoholic"]
    location: str


class JoinMessage(BaseModel):
    type: Literal["join"] = "join"
    filters: Filters
    widen_search: bool = False


class SkipMessage(BaseModel):
    type: Literal["skip"] = "skip"


class LeaveMessage(BaseModel):
    type: Literal["leave"] = "leave"


class MatchedEvent(BaseModel):
    type: Literal["matched"] = "matched"
    partner_id: uuid.UUID


class WaitingEvent(BaseModel):
    type: Literal["waiting"] = "waiting"


class WidenSearchPromptEvent(BaseModel):
    type: Literal["widen_search_prompt"] = "widen_search_prompt"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    detail: str
