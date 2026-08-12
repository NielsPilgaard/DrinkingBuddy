import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlparse

import pytest

import app.auth.service as auth_service
import app.routers.verify as verify_router
from app.config import settings

pytestmark = pytest.mark.integration


async def _signup_and_get_token(client, monkeypatch, email: str) -> tuple[str, str]:
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service, "send_magic_link_email", lambda email, link: sent.append(link)
    )

    await client.post("/auth/request-link", json={"email": email, "birthdate": "2000-01-01"})
    token = parse_qs(urlparse(sent[-1]).query)["token"][0]

    verify_response = await client.get("/auth/verify", params={"token": token})
    body = verify_response.json()
    return body["session_token"], body["user_id"]


def _sign(body: bytes) -> str:
    return hmac.new(settings.didit_webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_start_verification_returns_url_and_status_becomes_pending(client, monkeypatch):
    token, _ = await _signup_and_get_token(client, monkeypatch, "alice@example.com")
    monkeypatch.setattr(
        verify_router,
        "start_verification",
        lambda db, redis, user_id, method: _fake_start(db, redis, user_id, method),
    )

    response = await client.post(
        "/verify/start",
        json={"method": "age_estimation"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["session_token"] == "fake-session-token"


async def _fake_start(db, redis, user_id, method):
    return "pending", "fake-session-token"


@pytest.mark.asyncio
async def test_start_verification_requires_auth(client):
    response = await client.post("/verify/start", json={"method": "age_estimation"})
    assert response.status_code == 403 or response.status_code == 401


@pytest.mark.asyncio
async def test_status_defaults_to_pending_with_no_verification(client, monkeypatch):
    token, _ = await _signup_and_get_token(client, monkeypatch, "bob@example.com")

    response = await client.get("/verify/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_webhook_rejects_unsigned_payload(client):
    payload = json.dumps({"session_id": "abc", "status": "Approved"}).encode()
    response = await client.post(
        "/verify/webhook", content=payload, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_forged_signature(client):
    payload = json.dumps({"session_id": "abc", "status": "Approved"}).encode()
    response = await client.post(
        "/verify/webhook",
        content=payload,
        headers={"Content-Type": "application/json", "X-Didit-Signature": "0" * 64},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_marks_verification_verified_and_status_reflects_it(
    client, monkeypatch, db_session
):
    from app.models.verification import Verification

    token, user_id = await _signup_and_get_token(client, monkeypatch, "carol@example.com")
    db_session.add(
        Verification(
            user_id=user_id,
            status="pending",
            method="age_estimation",
            provider_session_id="sess-carol",
        )
    )
    await db_session.commit()

    payload = json.dumps({"session_id": "sess-carol", "status": "Approved"}).encode()
    response = await client.post(
        "/verify/webhook",
        content=payload,
        headers={"Content-Type": "application/json", "X-Didit-Signature": _sign(payload)},
    )
    assert response.status_code == 204

    status_response = await client.get(
        "/verify/status", headers={"Authorization": f"Bearer {token}"}
    )
    assert status_response.json()["status"] == "verified"


@pytest.mark.asyncio
async def test_webhook_replay_does_not_double_apply(client, monkeypatch, db_session):
    from app.models.verification import Verification

    _token, user_id = await _signup_and_get_token(client, monkeypatch, "dave@example.com")
    db_session.add(
        Verification(
            user_id=user_id,
            status="pending",
            method="age_estimation",
            provider_session_id="sess-dave",
        )
    )
    await db_session.commit()

    payload = json.dumps({"session_id": "sess-dave", "status": "Declined"}).encode()
    headers = {"Content-Type": "application/json", "X-Didit-Signature": _sign(payload)}

    first = await client.post("/verify/webhook", content=payload, headers=headers)
    assert first.status_code == 204

    replay_payload = json.dumps({"session_id": "sess-dave", "status": "Approved"}).encode()
    replay_headers = {
        "Content-Type": "application/json",
        "X-Didit-Signature": _sign(replay_payload),
    }
    second = await client.post("/verify/webhook", content=replay_payload, headers=replay_headers)
    assert second.status_code == 204

    from sqlalchemy import select

    result = await db_session.execute(
        select(Verification).where(Verification.provider_session_id == "sess-dave")
    )
    verification = result.scalar_one()
    # First callback (Declined) already moved this to a terminal state, so
    # the replayed "Approved" callback must not flip it.
    assert verification.status == "failed"


@pytest.mark.asyncio
async def test_webhook_payload_user_id_cannot_hijack_another_account(
    client, monkeypatch, db_session
):
    from sqlalchemy import select

    from app.models.verification import Verification

    _, grace_id = await _signup_and_get_token(client, monkeypatch, "grace@example.com")
    _, mallory_id = await _signup_and_get_token(client, monkeypatch, "mallory@example.com")
    db_session.add(
        Verification(
            user_id=grace_id,
            status="pending",
            method="age_estimation",
            provider_session_id="sess-grace",
        )
    )
    await db_session.commit()

    # Payload claims mallory's user_id but references grace's session - the
    # session_id (not the payload's user_id) must be what's authoritative.
    payload = json.dumps(
        {"session_id": "sess-grace", "status": "Approved", "user_id": str(mallory_id)}
    ).encode()
    response = await client.post(
        "/verify/webhook",
        content=payload,
        headers={"Content-Type": "application/json", "X-Didit-Signature": _sign(payload)},
    )
    assert response.status_code == 204

    result = await db_session.execute(
        select(Verification).where(Verification.provider_session_id == "sess-grace")
    )
    verification = result.scalar_one()
    assert str(verification.user_id) == grace_id
    assert verification.status == "verified"

    mallory_verification = await db_session.execute(
        select(Verification).where(Verification.user_id == mallory_id)
    )
    assert mallory_verification.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_start_verification_waitlists_once_cap_is_hit(client, monkeypatch):
    token, _ = await _signup_and_get_token(client, monkeypatch, "erin@example.com")
    monkeypatch.setattr(settings, "verification_monthly_cap", 0)

    response = await client.post(
        "/verify/start",
        json={"method": "age_estimation"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "waitlisted"
    assert body["session_token"] is None


@pytest.mark.asyncio
async def test_start_verification_is_noop_when_already_verified(client, monkeypatch, db_session):
    from sqlalchemy import select

    from app.models.verification import Verification

    token, user_id = await _signup_and_get_token(client, monkeypatch, "heidi@example.com")
    db_session.add(
        Verification(
            user_id=user_id,
            status="verified",
            method="age_estimation",
            provider_session_id="sess-heidi",
        )
    )
    await db_session.commit()

    response = await client.post(
        "/verify/start",
        json={"method": "age_estimation"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified"
    assert body["session_token"] is None

    # A redundant call must not shadow the still-valid verified row with a
    # new pending one - is_video_eligible would otherwise flip back to False.
    result = await db_session.execute(select(Verification).where(Verification.user_id == user_id))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "verified"


@pytest.mark.asyncio
async def test_start_verification_rate_limited_after_repeated_attempts(client, monkeypatch):
    token, _ = await _signup_and_get_token(client, monkeypatch, "frank@example.com")
    monkeypatch.setattr(settings, "verification_rate_limit_per_user", 1)
    monkeypatch.setattr(
        verify_router,
        "start_verification",
        lambda db, redis, user_id, method: _fake_start(db, redis, user_id, method),
    )

    first = await client.post(
        "/verify/start",
        json={"method": "age_estimation"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/verify/start",
        json={"method": "age_estimation"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 429
