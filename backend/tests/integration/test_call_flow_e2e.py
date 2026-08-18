"""Full user-journey E2E: signup -> match -> signal -> chat -> leave -> report -> block.

Chains the matching queue and signaling routers together (two real client
sessions over real websockets), which the per-router integration tests don't
cover - each of those starts from an already-known call_id rather than one
handed off from a live match.
"""

import uuid
from urllib.parse import parse_qs, urlparse

import pytest

import app.auth.service as auth_service
from app.models.block import Block

pytestmark = pytest.mark.integration

FILTERS = {"language": "en", "drink_type": "alcoholic", "location": "dk"}


async def _signup_and_get_token(client, monkeypatch, email: str) -> tuple[str, uuid.UUID]:
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service, "send_magic_link_email", lambda email, link: sent.append(link)
    )

    await client.post("/auth/request-link", json={"email": email, "birthdate": "2000-01-01"})
    token = parse_qs(urlparse(sent[-1]).query)["token"][0]

    verify_response = await client.get("/auth/verify", params={"token": token})
    body = verify_response.json()
    return body["session_token"], uuid.UUID(body["user_id"])


@pytest.mark.asyncio
async def test_full_call_flow_match_to_report(ws_client, monkeypatch):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "flow-a@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "flow-b@example.com")

    # 1. Both users join the matching queue and get paired.
    async with ws_client.websocket(f"/matching/ws?token={token_a}") as match_a:
        await match_a.send_json({"type": "join", "filters": FILTERS})
        waiting = await match_a.receive_json()
        assert waiting["type"] == "waiting"

        async with ws_client.websocket(f"/matching/ws?token={token_b}") as match_b:
            await match_b.send_json({"type": "join", "filters": FILTERS})

            matched_b = await match_b.receive_json()
            matched_a = await match_a.receive_json()

    assert matched_a["type"] == matched_b["type"] == "matched"
    assert matched_a["partner_id"] == str(user_b_id)
    assert matched_b["partner_id"] == str(user_a_id)
    call_id = matched_a["call_id"]
    assert call_id == matched_b["call_id"]

    # 2. Both users connect to signaling using the call_id handed off by matching.
    async with ws_client.websocket(f"/signaling/ws?token={token_a}&call_id={call_id}") as sig_a:
        await sig_a.receive_json()  # turn creds

        async with ws_client.websocket(f"/signaling/ws?token={token_b}&call_id={call_id}") as sig_b:
            await sig_b.receive_json()  # turn creds
            await sig_b.receive_json()  # peer_joined
            await sig_a.receive_json()  # peer_joined

            # 3. WebRTC handshake + chat exchange.
            await sig_a.send_json({"type": "offer", "sdp": "v=0 fake-offer"})
            offer = await sig_b.receive_json()
            assert offer["message"]["sdp"] == "v=0 fake-offer"

            await sig_b.send_json({"type": "answer", "sdp": "v=0 fake-answer"})
            answer = await sig_a.receive_json()
            assert answer["message"]["sdp"] == "v=0 fake-answer"

            await sig_a.send_json({"type": "chat", "text": "cheers"})
            chat = await sig_b.receive_json()
            assert chat["message"]["text"] == "cheers"

        # 4. B leaves the call; A is notified.
        left = await sig_a.receive_json()
        assert left["type"] == "peer_left"

    # 5. A reports and blocks B after the call ends.
    report_response = await ws_client.post(
        "/report",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"reported_id": str(user_b_id), "call_session_id": call_id, "reason": "harassment"},
    )
    assert report_response.status_code == 204

    block_response = await ws_client.post(
        "/block",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"blocked_id": str(user_b_id)},
    )
    assert block_response.status_code == 204


@pytest.mark.asyncio
async def test_blocked_user_is_not_rematched(ws_client, monkeypatch, db_session):
    """After A blocks B, a fresh match round between only A and B must not
    pair them again - proves the block actually feeds back into matching,
    not just into a DB row nobody reads."""
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "block-a@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "block-b@example.com")

    db_session.add(Block(blocker_id=user_a_id, blocked_id=user_b_id))
    await db_session.commit()

    async with (
        ws_client.websocket(f"/matching/ws?token={token_a}") as match_a,
        ws_client.websocket(f"/matching/ws?token={token_b}") as match_b,
    ):
        await match_a.send_json({"type": "join", "filters": FILTERS})
        waiting_a = await match_a.receive_json()
        assert waiting_a["type"] == "waiting"

        await match_b.send_json({"type": "join", "filters": FILTERS})
        waiting_b = await match_b.receive_json()
        assert waiting_b["type"] == "waiting"

        await match_a.send_json({"type": "leave"})
        await match_b.send_json({"type": "leave"})
