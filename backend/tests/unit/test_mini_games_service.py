import uuid

from app.mini_games.content_bank import NEVER_HAVE_I_EVER_PROMPTS, WOULD_YOU_RATHER_PROMPTS
from app.mini_games.service import (
    accept_game,
    clear_call_state,
    close_game,
    get_session,
    start_game,
)

_USER = uuid.uuid4()


def test_start_game_creates_pending_session():
    call_id = f"call-{uuid.uuid4()}"
    session = start_game(call_id, "trivia", _USER)

    assert session.game_type == "trivia"
    assert session.requested_by == _USER
    assert session.accepted is False
    assert get_session(call_id) is session

    clear_call_state(call_id)


def test_accept_game_marks_session_accepted():
    call_id = f"call-{uuid.uuid4()}"
    start_game(call_id, "would_you_rather", _USER)

    session = accept_game(call_id)

    assert session is not None
    assert session.accepted is True

    clear_call_state(call_id)


def test_accept_game_on_unknown_call_returns_none():
    assert accept_game(f"call-{uuid.uuid4()}") is None


def test_close_game_drops_session():
    call_id = f"call-{uuid.uuid4()}"
    start_game(call_id, "never_have_i_ever", _USER)

    close_game(call_id)

    assert get_session(call_id) is None


def test_clear_call_state_drops_session():
    call_id = f"call-{uuid.uuid4()}"
    start_game(call_id, "trivia", _USER)

    clear_call_state(call_id)

    assert get_session(call_id) is None


def test_content_bank_has_no_duplicate_prompts():
    assert len(WOULD_YOU_RATHER_PROMPTS) == len(set(WOULD_YOU_RATHER_PROMPTS))
    assert len(NEVER_HAVE_I_EVER_PROMPTS) == len(set(NEVER_HAVE_I_EVER_PROMPTS))
