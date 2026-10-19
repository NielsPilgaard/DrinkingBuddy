import uuid
from urllib.parse import parse_qs, urlparse

import pytest

import app.auth.service as auth_service
from app.mini_games.service import get_session, seed_content_bank_if_empty
from app.signaling.session import call_id_for_pair

pytestmark = pytest.mark.integration


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _signup_and_get_token(client, monkeypatch, email: str) -> tuple[str, uuid.UUID]:
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service, "send_magic_link_email", lambda email, link: sent.append(link)
    )
    await client.post("/auth/request-link", json={"email": email, "birthdate": "2000-01-01"})
    token = parse_qs(urlparse(sent[-1]).query)["token"][0]
    verify_response = await client.post("/auth/verify", json={"token": token})
    body = verify_response.json()
    return body["session_token"], uuid.UUID(body["user_id"])


@pytest.mark.asyncio
async def test_game_invite_accept_reveals_synced_prompt(ws_client, monkeypatch, db_session):
    await seed_content_bank_if_empty(db_session)

    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "wyr-a@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "wyr-b@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a:
        await ws_a.receive_json()  # turn creds

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            await ws_b.receive_json()  # turn creds
            await ws_b.receive_json()  # peer_joined
            await ws_a.receive_json()  # peer_joined

            await ws_a.send_json({"type": "game_start", "game_type": "would_you_rather"})
            invite = await ws_b.receive_json()
            assert invite["type"] == "game_invite"
            assert invite["game_type"] == "would_you_rather"
            assert invite["from_user_id"] == str(user_a_id)

            await ws_b.send_json({"type": "game_accept"})
            started_a = await ws_a.receive_json()
            started_b = await ws_b.receive_json()
            assert started_a["type"] == "game_started"
            assert started_b["type"] == "game_started"
            assert started_a["prompt"]["id"] == started_b["prompt"]["id"]
            assert started_a["prompt"]["text"]

            await ws_a.send_json({"type": "game_next"})
            next_a = await ws_a.receive_json()
            next_b = await ws_b.receive_json()
            assert next_a["type"] == "game_prompt"
            assert next_a["prompt"]["id"] == next_b["prompt"]["id"]

            await ws_b.send_json({"type": "game_close"})
            closed_a = await ws_a.receive_json()
            closed_b = await ws_b.receive_json()
            assert closed_a["type"] == "game_closed"
            assert closed_b["type"] == "game_closed"

    assert get_session(call_id) is None


@pytest.mark.asyncio
async def test_game_decline_notifies_requester(ws_client, monkeypatch, db_session):
    await seed_content_bank_if_empty(db_session)

    token_a, user_a_id = await _signup_and_get_token(
        ws_client, monkeypatch, "decline-a@example.com"
    )
    token_b, user_b_id = await _signup_and_get_token(
        ws_client, monkeypatch, "decline-b@example.com"
    )
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a:
        await ws_a.receive_json()

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            await ws_b.receive_json()
            await ws_b.receive_json()
            await ws_a.receive_json()

            await ws_a.send_json({"type": "game_start", "game_type": "never_have_i_ever"})
            await ws_b.receive_json()  # invite

            await ws_b.send_json({"type": "game_decline"})
            declined = await ws_a.receive_json()
            assert declined["type"] == "game_declined"

    assert get_session(call_id) is None


@pytest.mark.asyncio
async def test_requester_cannot_accept_own_game_invite(ws_client, monkeypatch, db_session):
    await seed_content_bank_if_empty(db_session)

    token_a, user_a_id = await _signup_and_get_token(
        ws_client, monkeypatch, "self-accept-a@example.com"
    )
    token_b, user_b_id = await _signup_and_get_token(
        ws_client, monkeypatch, "self-accept-b@example.com"
    )
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a:
        await ws_a.receive_json()

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            await ws_b.receive_json()
            await ws_b.receive_json()
            await ws_a.receive_json()

            await ws_a.send_json({"type": "game_start", "game_type": "would_you_rather"})
            await ws_b.receive_json()  # invite

            # The requester (A) tries to accept their own invite - must be a
            # silent no-op, not start the game.
            await ws_a.send_json({"type": "game_accept"})

            # The legitimate recipient (B) can still accept normally,
            # proving the session wasn't corrupted by the rejected attempt.
            await ws_b.send_json({"type": "game_accept"})
            started_a = await ws_a.receive_json()
            started_b = await ws_b.receive_json()
            assert started_a["type"] == "game_started"
            assert started_b["type"] == "game_started"

    assert get_session(call_id) is None


@pytest.mark.asyncio
async def test_requester_cannot_decline_own_game_invite(ws_client, monkeypatch, db_session):
    await seed_content_bank_if_empty(db_session)

    token_a, user_a_id = await _signup_and_get_token(
        ws_client, monkeypatch, "self-decline-a@example.com"
    )
    token_b, user_b_id = await _signup_and_get_token(
        ws_client, monkeypatch, "self-decline-b@example.com"
    )
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a:
        await ws_a.receive_json()

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            await ws_b.receive_json()
            await ws_b.receive_json()
            await ws_a.receive_json()

            await ws_a.send_json({"type": "game_start", "game_type": "never_have_i_ever"})
            await ws_b.receive_json()  # invite

            # The requester (A) tries to decline their own invite - must be a
            # silent no-op, session must survive for B to still accept it.
            await ws_a.send_json({"type": "game_decline"})

            await ws_b.send_json({"type": "game_accept"})
            started_a = await ws_a.receive_json()
            started_b = await ws_b.receive_json()
            assert started_a["type"] == "game_started"
            assert started_b["type"] == "game_started"

    assert get_session(call_id) is None


@pytest.mark.asyncio
async def test_trivia_correct_option_withheld_until_reveal(ws_client, monkeypatch, db_session):
    from app.models.game_prompt import GamePrompt as GamePromptRow

    db_session.add(
        GamePromptRow(
            game_type="trivia",
            text="What is 2+2?",
            options=["3", "4", "5", "6"],
            correct_option="4",
            source="opentdb",
            is_active=True,
        )
    )
    await db_session.commit()

    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "trivia-a@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "trivia-b@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a:
        await ws_a.receive_json()

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            await ws_b.receive_json()
            await ws_b.receive_json()
            await ws_a.receive_json()

            await ws_a.send_json({"type": "game_start", "game_type": "trivia"})
            await ws_b.receive_json()  # invite

            await ws_b.send_json({"type": "game_accept"})
            started_a = await ws_a.receive_json()
            await ws_b.receive_json()
            assert "correct_option" not in started_a["prompt"]
            assert len(started_a["prompt"]["options"]) == 4

            await ws_a.send_json({"type": "game_reveal"})
            revealed_a = await ws_a.receive_json()
            revealed_b = await ws_b.receive_json()
            assert revealed_a["type"] == "game_revealed"
            assert revealed_b["type"] == "game_revealed"
            assert revealed_a["correct_option"] == "4"
            assert revealed_b["correct_option"] == "4"


@pytest.mark.asyncio
async def test_accept_with_empty_bank_closes_game_for_both(ws_client, monkeypatch):
    # No trivia rows seeded: accepting must end the game, not leave the inviter waiting.
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "empty-a@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "empty-b@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a:
        await ws_a.receive_json()  # turn creds

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            await ws_b.receive_json()  # turn creds
            await ws_b.receive_json()  # peer_joined
            await ws_a.receive_json()  # peer_joined

            await ws_a.send_json({"type": "game_start", "game_type": "trivia"})
            assert (await ws_b.receive_json())["type"] == "game_invite"

            await ws_b.send_json({"type": "game_accept"})
            assert (await ws_b.receive_json())["type"] == "game_closed"
            assert (await ws_a.receive_json())["type"] == "game_closed"

    assert get_session(call_id) is None
