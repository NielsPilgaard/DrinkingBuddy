import uuid
from typing import Literal

from pydantic import BaseModel

GameType = Literal["trivia", "would_you_rather", "never_have_i_ever"]


class GamePrompt(BaseModel):
    """Server-internal representation - carries `correct_option` so
    mini_games.service can track it across the session. Never sent to
    clients directly; see `PublicGamePrompt` for the wire-safe version sent
    before reveal."""

    id: uuid.UUID
    game_type: GameType
    text: str
    """Trivia's question text; WYR/NHIE's full prompt text."""
    options: list[str] | None = None
    """Trivia only: 4 shuffled answer options. None for WYR/NHIE."""
    correct_option: str | None = None
    """Trivia only. Kept server-side until reveal - must never be included
    in a payload sent to clients before GameRevealedEvent."""


class PublicGamePrompt(BaseModel):
    """Wire-safe prompt sent to clients ahead of reveal - deliberately omits
    `correct_option` so a client (or anyone inspecting network traffic)
    can't read the trivia answer before tapping reveal."""

    id: uuid.UUID
    game_type: GameType
    text: str
    options: list[str] | None = None

    @classmethod
    def from_prompt(cls, prompt: "GamePrompt") -> "PublicGamePrompt":
        return cls(
            id=prompt.id, game_type=prompt.game_type, text=prompt.text, options=prompt.options
        )


# --- Inbound (client -> server) ---


class GameStartMessage(BaseModel):
    type: Literal["game_start"] = "game_start"
    game_type: GameType


class GameAcceptMessage(BaseModel):
    type: Literal["game_accept"] = "game_accept"


class GameDeclineMessage(BaseModel):
    type: Literal["game_decline"] = "game_decline"


class GameNextMessage(BaseModel):
    type: Literal["game_next"] = "game_next"


class GameRevealMessage(BaseModel):
    type: Literal["game_reveal"] = "game_reveal"


class GameCloseMessage(BaseModel):
    type: Literal["game_close"] = "game_close"


InboundGameMessage = (
    GameStartMessage
    | GameAcceptMessage
    | GameDeclineMessage
    | GameNextMessage
    | GameRevealMessage
    | GameCloseMessage
)


# --- Outbound (server -> both clients) ---


class GameInviteEvent(BaseModel):
    """Pushed only to the receiving party - the requester already knows it
    asked. Distinct from GameStartedEvent so the requester's own client
    doesn't show itself an accept/decline prompt."""

    type: Literal["game_invite"] = "game_invite"
    game_type: GameType
    from_user_id: uuid.UUID


class GameDeclinedEvent(BaseModel):
    type: Literal["game_declined"] = "game_declined"


class GameStartedEvent(BaseModel):
    type: Literal["game_started"] = "game_started"
    game_type: GameType
    prompt: PublicGamePrompt


class GamePromptEvent(BaseModel):
    """Pushed on `next` - always pre-reveal, so `prompt` never carries
    trivia's correct_option (see PublicGamePrompt). `revealed` tells the
    client whether to expect a correct_option immediately (in practice
    always False here; reveal-time correct_option arrives via
    GameRevealedEvent instead)."""

    type: Literal["game_prompt"] = "game_prompt"
    prompt: PublicGamePrompt
    revealed: bool = False


class GameRevealedEvent(BaseModel):
    """Trivia's correct_option is only ever sent here, once the round is
    revealed. None for WYR/NHIE, which have no answer to reveal."""

    type: Literal["game_revealed"] = "game_revealed"
    correct_option: str | None = None


class GameClosedEvent(BaseModel):
    type: Literal["game_closed"] = "game_closed"


OutboundGameEvent = (
    GameInviteEvent
    | GameDeclinedEvent
    | GameStartedEvent
    | GamePromptEvent
    | GameRevealedEvent
    | GameClosedEvent
)
