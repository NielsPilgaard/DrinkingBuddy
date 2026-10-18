import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

import app.auth.service as auth_service
from app.models.verification import Verification
from app.signaling.session import call_id_for_pair

pytestmark = pytest.mark.integration

FILTERS = {"language": "en", "drink_type": "alcoholic", "location": "dk"}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _signup_and_get_token(client, monkeypatch, email: str) -> tuple[str, str]:
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service, "send_magic_link_email", lambda email, link: sent.append(link)
    )

    await client.post("/auth/request-link", json={"email": email, "birthdate": "2000-01-01"})
    token = parse_qs(urlparse(sent[-1]).query)["token"][0]

    verify_response = await client.post("/auth/verify", json={"token": token})
    body = verify_response.json()
    return body["session_token"], body["user_id"]


async def _mark_verified(db_session, user_id: str) -> None:
    db_session.add(
        Verification(
            user_id=user_id,
            status="verified",
            method="age_estimation",
            provider_session_id=f"sess-{user_id}",
            verified_at=datetime.now(UTC),
            expiry=datetime.now(UTC) + timedelta(days=365),
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_matched_event_video_ineligible_when_both_unverified(ws_client, monkeypatch):
    token_a, _ = await _signup_and_get_token(ws_client, monkeypatch, "alice@example.com")
    token_b, _ = await _signup_and_get_token(ws_client, monkeypatch, "bob@example.com")

    async with ws_client.websocket("/matching/ws", headers=_bearer(token_a)) as ws_a:
        await ws_a.send_json({"type": "join", "filters": FILTERS})
        await ws_a.receive_json()  # waiting

        async with ws_client.websocket("/matching/ws", headers=_bearer(token_b)) as ws_b:
            await ws_b.send_json({"type": "join", "filters": FILTERS})
            matched_b = await ws_b.receive_json()
            matched_a = await ws_a.receive_json()

    assert matched_a["video_eligible"] is False
    assert matched_b["video_eligible"] is False


@pytest.mark.asyncio
async def test_matched_event_video_ineligible_when_only_one_verified(
    ws_client, monkeypatch, db_session
):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "carol@example.com")
    token_b, _user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "dave@example.com")
    await _mark_verified(db_session, user_a_id)

    async with ws_client.websocket("/matching/ws", headers=_bearer(token_a)) as ws_a:
        await ws_a.send_json({"type": "join", "filters": FILTERS})
        await ws_a.receive_json()  # waiting

        async with ws_client.websocket("/matching/ws", headers=_bearer(token_b)) as ws_b:
            await ws_b.send_json({"type": "join", "filters": FILTERS})
            matched_b = await ws_b.receive_json()
            matched_a = await ws_a.receive_json()

    assert matched_a["video_eligible"] is False
    assert matched_b["video_eligible"] is False


@pytest.mark.asyncio
async def test_matched_event_video_eligible_when_both_verified(ws_client, monkeypatch, db_session):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "erin@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "frank@example.com")
    await _mark_verified(db_session, user_a_id)
    await _mark_verified(db_session, user_b_id)

    async with ws_client.websocket("/matching/ws", headers=_bearer(token_a)) as ws_a:
        await ws_a.send_json({"type": "join", "filters": FILTERS})
        await ws_a.receive_json()  # waiting

        async with ws_client.websocket("/matching/ws", headers=_bearer(token_b)) as ws_b:
            await ws_b.send_json({"type": "join", "filters": FILTERS})
            matched_b = await ws_b.receive_json()
            matched_a = await ws_a.receive_json()

    assert matched_a["video_eligible"] is True
    assert matched_b["video_eligible"] is True


@pytest.mark.asyncio
async def test_video_status_request_reflects_fresh_revocation(ws_client, monkeypatch, db_session):
    """Verified at match time, then revoked mid-call: a video_status_request
    sent afterward must reflect the revocation, proving status isn't cached
    from the initial match-formed check."""
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "grace@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "heidi@example.com")
    await _mark_verified(db_session, user_a_id)
    await _mark_verified(db_session, user_b_id)
    call_id = call_id_for_pair(uuid.UUID(user_a_id), uuid.UUID(user_b_id))

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

            await ws_a.send_json({"type": "video_status_request"})
            status_before = await ws_a.receive_json()
            assert status_before["video_eligible"] is True

            result = await db_session.execute(
                select(Verification).where(Verification.user_id == user_a_id)
            )
            verification = result.scalar_one()
            verification.revoked_at = datetime.now(UTC)
            await db_session.commit()

            await ws_a.send_json({"type": "video_status_request"})
            status_after = await ws_a.receive_json()
            assert status_after["video_eligible"] is False
