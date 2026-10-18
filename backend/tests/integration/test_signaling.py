import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

import app.auth.service as auth_service
from app.models.chat_safety import FlaggedMessage
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
async def test_peers_receive_turn_credentials_and_peer_joined(ws_client, monkeypatch):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "alice@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "bob@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a:
        turn_a = await ws_a.receive_json()
        assert turn_a["ice_servers"]

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            turn_b = await ws_b.receive_json()
            assert turn_b["ice_servers"]

            joined_b = await ws_b.receive_json()
            joined_a = await ws_a.receive_json()
            assert joined_a["type"] == "peer_joined"
            assert joined_b["type"] == "peer_joined"


@pytest.mark.asyncio
async def test_offer_answer_and_ice_candidates_are_relayed(ws_client, monkeypatch):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "carol@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "dave@example.com")
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

            await ws_a.send_json({"type": "offer", "sdp": "v=0 fake-offer"})
            offer = await ws_b.receive_json()
            assert offer["message"]["type"] == "offer"
            assert offer["message"]["sdp"] == "v=0 fake-offer"
            assert offer["from_user_id"] == str(user_a_id)

            await ws_b.send_json({"type": "answer", "sdp": "v=0 fake-answer"})
            answer = await ws_a.receive_json()
            assert answer["message"]["type"] == "answer"
            assert answer["message"]["sdp"] == "v=0 fake-answer"
            assert answer["from_user_id"] == str(user_b_id)

            await ws_a.send_json(
                {"type": "ice_candidate", "candidate": {"candidate": "fake", "sdpMid": "0"}}
            )
            ice = await ws_b.receive_json()
            assert ice["message"]["type"] == "ice_candidate"
            assert ice["message"]["candidate"]["candidate"] == "fake"


@pytest.mark.asyncio
async def test_chat_messages_are_relayed_server_side(ws_client, monkeypatch):
    """Confirms the server actually sees plaintext chat content (needed for
    tasks/13-chat-safety-filters.md) rather than it being a P2P datachannel."""
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "erin@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "frank@example.com")
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

            await ws_a.send_json({"type": "chat", "text": "hello there"})
            chat = await ws_b.receive_json()
            assert chat["message"]["type"] == "chat"
            assert chat["message"]["text"] == "hello there"
            assert chat["from_user_id"] == str(user_a_id)


@pytest.mark.asyncio
async def test_ice_breaker_relays_and_bypasses_chat_safety_scan(ws_client, monkeypatch, db_session):
    """Confirms a valid allowlisted ice_breaker prompt is relayed like chat
    but never runs through scan_chat_message (tasks/ice-breaker.md)."""
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "quinn@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "ray@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    prompt = "Dogs, cats, or neither?"

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

            await ws_a.send_json({"type": "ice_breaker", "text": prompt})
            relayed = await ws_b.receive_json()
            assert relayed["message"]["type"] == "ice_breaker"
            assert relayed["message"]["text"] == prompt
            assert relayed["from_user_id"] == str(user_a_id)

    result = await db_session.execute(select(FlaggedMessage))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_ice_breaker_rejects_unallowlisted_text(ws_client, monkeypatch, db_session):
    """A client sending freeform text under the ice_breaker type (rather
    than one of the pre-vetted static prompts) must be rejected, not relayed
    - the ice_breaker channel is deliberately exempt from chat_safety
    scanning, so it must not become a way to smuggle arbitrary text past the
    filter (tasks/ice-breaker.md)."""
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "sybil@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "trent@example.com")
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

            await ws_a.send_json({"type": "ice_breaker", "text": "let's meet up this weekend"})
            error = await ws_a.receive_json()
            assert error["type"] == "error"

            # Nothing was relayed to B for the rejected message.
            await ws_a.send_json({"type": "chat", "text": "proof B's queue is otherwise empty"})
            chat = await ws_b.receive_json()
            assert chat["message"]["type"] == "chat"


@pytest.mark.asyncio
async def test_peer_leaving_notifies_remaining_participant(ws_client, monkeypatch):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "grace@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "heidi@example.com")
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

        left = await ws_a.receive_json()
        assert left["type"] == "peer_left"


@pytest.mark.asyncio
async def test_reconnect_does_not_spuriously_notify_peer_left(ws_client, monkeypatch):
    """When A reconnects (new socket replaces the old one for the same
    user_id), B must not see a peer_left for the still-present A - only the
    replaced (stale) socket's cleanup should be a no-op, not a departure."""
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "peggy@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "quentin@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(
        f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
    ) as ws_a1:
        await ws_a1.receive_json()  # turn creds

        async with ws_client.websocket(
            f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)
        ) as ws_b:
            await ws_b.receive_json()  # turn creds
            await ws_b.receive_json()  # peer_joined
            await ws_a1.receive_json()  # peer_joined

            # A reconnects: new socket replaces ws_a1 for the same user_id.
            async with ws_client.websocket(
                f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)
            ) as ws_a2:
                await ws_a2.receive_json()  # turn creds
                # B (still-active peer) and A (self) both get a fresh
                # peer_joined for the reconnect.
                await ws_b.receive_json()  # peer_joined
                await ws_a2.receive_json()  # peer_joined

                # ws_a1's server-side handler exits and its finally-block
                # cleanup runs; it must not emit peer_left for B since A
                # (via ws_a2) is still an active participant.
                await ws_a2.send_json({"type": "chat", "text": "still here"})
                chat = await ws_b.receive_json()
                assert chat["message"]["type"] == "chat"
                assert chat["message"]["text"] == "still here"


@pytest.mark.asyncio
async def test_third_participant_is_rejected_when_call_is_full(
    ws_client, ws_close_code, monkeypatch
):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "ivan@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "judy@example.com")
    token_c, _ = await _signup_and_get_token(ws_client, monkeypatch, "kevin@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with (
        ws_client.websocket(f"/signaling/ws?call_id={call_id}", headers=_bearer(token_a)) as ws_a,
        ws_client.websocket(f"/signaling/ws?call_id={call_id}", headers=_bearer(token_b)) as ws_b,
    ):
        await ws_a.receive_json()  # turn creds
        await ws_b.receive_json()  # turn creds
        await ws_b.receive_json()  # peer_joined
        await ws_a.receive_json()  # peer_joined

        code = await ws_close_code(f"/signaling/ws?call_id={call_id}", headers=_bearer(token_c))
        assert code == 4403


@pytest.mark.asyncio
async def test_nonparticipant_is_rejected_before_call_is_full(
    ws_client, ws_close_code, monkeypatch
):
    """A user_id that isn't one of the two ids encoded in call_id must be
    denied, even when a slot is free (i.e. before B has joined)."""
    _token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "mallory@example.com")
    _token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "nathan@example.com")
    token_c, _ = await _signup_and_get_token(ws_client, monkeypatch, "oscar@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    code = await ws_close_code(f"/signaling/ws?call_id={call_id}", headers=_bearer(token_c))
    assert code == 4403


@pytest.mark.asyncio
async def test_unauthenticated_connection_is_rejected(ws_close_code):
    assert await ws_close_code("/signaling/ws?call_id=whatever") == 4401


@pytest.mark.asyncio
async def test_token_in_query_string_is_rejected(ws_client, ws_close_code, monkeypatch):
    # Query strings end up in access logs and trace spans, so the session
    # token is only accepted from the Authorization header.
    token, _ = await _signup_and_get_token(ws_client, monkeypatch, "query@example.com")

    assert await ws_close_code(f"/signaling/ws?token={token}&call_id=whatever") == 4401


@pytest.mark.asyncio
async def test_missing_call_id_is_rejected(ws_client, ws_close_code, monkeypatch):
    token, _ = await _signup_and_get_token(ws_client, monkeypatch, "laura@example.com")

    assert await ws_close_code("/signaling/ws", headers=_bearer(token)) == 4400
