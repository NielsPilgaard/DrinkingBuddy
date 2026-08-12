import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from httpx2.websockets import WebSocketUpgradeError
from sqlalchemy import select

import app.auth.service as auth_service
from app.config import settings
from app.models.block import Block

pytestmark = pytest.mark.integration


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
async def test_report_endpoint_requires_auth(client):
    response = await client.post(
        "/report",
        json={
            "reported_id": str(uuid.uuid4()),
            "call_session_id": "call-1",
            "reason": "harassment",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_report_endpoint_succeeds_for_authenticated_user(client, monkeypatch):
    token, _ = await _signup_and_get_token(client, monkeypatch, "reporter@example.com")

    response = await client.post(
        "/report",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reported_id": str(uuid.uuid4()),
            "call_session_id": "call-1",
            "reason": "harassment",
        },
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_block_endpoint_creates_block_row(client, db_session, monkeypatch):
    token, blocker_id = await _signup_and_get_token(client, monkeypatch, "blocker-http@example.com")
    blocked_id = uuid.uuid4()

    response = await client.post(
        "/block",
        headers={"Authorization": f"Bearer {token}"},
        json={"blocked_id": str(blocked_id)},
    )
    assert response.status_code == 204

    result = await db_session.execute(
        select(Block).where(Block.blocker_id == blocker_id, Block.blocked_id == blocked_id)
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_block_endpoint_requires_auth(client):
    response = await client.post("/block", json={"blocked_id": str(uuid.uuid4())})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_report_endpoint_rejects_self_report(client, monkeypatch):
    token, user_id = await _signup_and_get_token(client, monkeypatch, "self-reporter@example.com")

    response = await client.post(
        "/report",
        headers={"Authorization": f"Bearer {token}"},
        json={"reported_id": str(user_id), "call_session_id": "call-1", "reason": "harassment"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_block_endpoint_rejects_self_block(client, monkeypatch):
    token, user_id = await _signup_and_get_token(client, monkeypatch, "self-blocker@example.com")

    response = await client.post(
        "/block",
        headers={"Authorization": f"Bearer {token}"},
        json={"blocked_id": str(user_id)},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_block_endpoint_is_idempotent(client, db_session, monkeypatch):
    token, blocker_id = await _signup_and_get_token(client, monkeypatch, "dupe-blocker@example.com")
    blocked_id = uuid.uuid4()

    for _ in range(2):
        response = await client.post(
            "/block",
            headers={"Authorization": f"Bearer {token}"},
            json={"blocked_id": str(blocked_id)},
        )
        assert response.status_code == 204

    result = await db_session.execute(
        select(Block).where(Block.blocker_id == blocker_id, Block.blocked_id == blocked_id)
    )
    assert len(result.all()) == 1


@pytest.mark.asyncio
async def test_nth_report_suspends_login(client, monkeypatch):
    token, reported_id = await _signup_and_get_token(
        client, monkeypatch, "will-be-suspended@example.com"
    )

    for i in range(settings.report_auto_suspend_threshold):
        reporter_token, _ = await _signup_and_get_token(
            client, monkeypatch, f"threshold-reporter-{i}@example.com"
        )
        response = await client.post(
            "/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={
                "reported_id": str(reported_id),
                "call_session_id": f"call-{i}",
                "reason": "harassment",
            },
        )
        assert response.status_code == 204

    # Suspended user requests a fresh magic link and tries to verify - should be blocked.
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service, "send_magic_link_email", lambda email, link: sent.append(link)
    )
    await client.post(
        "/auth/request-link",
        json={"email": "will-be-suspended@example.com", "birthdate": "2000-01-01"},
    )
    new_token = parse_qs(urlparse(sent[-1]).query)["token"][0]

    verify_response = await client.get("/auth/verify", params={"token": new_token})
    assert verify_response.status_code == 403


@pytest.mark.asyncio
async def test_suspended_user_cannot_join_matching_queue(ws_client, monkeypatch):
    token, reported_id = await _signup_and_get_token(
        ws_client, monkeypatch, "suspended-matching@example.com"
    )

    for i in range(settings.report_auto_suspend_threshold):
        reporter_token, _ = await _signup_and_get_token(
            ws_client, monkeypatch, f"matching-reporter-{i}@example.com"
        )
        await ws_client.post(
            "/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={
                "reported_id": str(reported_id),
                "call_session_id": f"call-{i}",
                "reason": "harassment",
            },
        )

    with pytest.raises(WebSocketUpgradeError) as exc_info:
        async with ws_client.websocket(f"/matching/ws?token={token}") as ws:
            await ws.send_json(
                {
                    "type": "join",
                    "filters": {"language": "en", "drink_type": "alcoholic", "location": "dk"},
                }
            )
            await ws.receive_json()
    assert exc_info.value.response.status_code == 403
