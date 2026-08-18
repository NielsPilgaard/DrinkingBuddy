from datetime import UTC, date, datetime
from urllib.parse import parse_qs, urlparse

import pytest

import app.auth.service as auth_service
import app.routers.auth as auth_router

pytestmark = pytest.mark.integration

# Fixed, non-leap reference date so year-17 arithmetic never lands on Feb 29.
REFERENCE_TODAY = date(2025, 6, 15)


def _capture_deep_links(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service, "send_magic_link_email", lambda email, link: sent.append(link)
    )
    return sent


def _token_from_deep_link(deep_link: str) -> str:
    return parse_qs(urlparse(deep_link).query)["token"][0]


@pytest.mark.asyncio
async def test_signup_and_verify(client, monkeypatch) -> None:
    sent = _capture_deep_links(monkeypatch)

    response = await client.post(
        "/auth/request-link",
        json={"email": "new-user@example.com", "birthdate": "2000-01-01"},
    )
    assert response.status_code == 200
    assert len(sent) == 1

    token = _token_from_deep_link(sent[0])
    verify_response = await client.get("/auth/verify", params={"token": token})

    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["email"] == "new-user@example.com"
    assert body["session_token"]


@pytest.mark.asyncio
async def test_returning_user_ignores_birthdate(client, monkeypatch) -> None:
    sent = _capture_deep_links(monkeypatch)

    await client.post(
        "/auth/request-link",
        json={"email": "returning@example.com", "birthdate": "2000-01-01"},
    )
    response = await client.post(
        "/auth/request-link",
        json={"email": "returning@example.com", "birthdate": "1990-01-01"},
    )

    assert response.status_code == 200
    assert len(sent) == 2

    token = _token_from_deep_link(sent[1])
    verify_response = await client.get("/auth/verify", params={"token": token})
    assert verify_response.status_code == 200


@pytest.mark.asyncio
async def test_underage_signup_silently_rejected(client, monkeypatch) -> None:
    sent = _capture_deep_links(monkeypatch)

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(
                REFERENCE_TODAY.year, REFERENCE_TODAY.month, REFERENCE_TODAY.day, tzinfo=tz or UTC
            )

    monkeypatch.setattr(auth_service, "datetime", _FrozenDatetime)
    underage_birthdate = date(REFERENCE_TODAY.year - 17, REFERENCE_TODAY.month, REFERENCE_TODAY.day)

    response = await client.post(
        "/auth/request-link",
        json={"email": "minor@example.com", "birthdate": underage_birthdate.isoformat()},
    )

    assert response.status_code == 200
    assert len(sent) == 0

    verify_response = await client.get("/auth/verify", params={"token": "irrelevant"})
    assert verify_response.status_code == 401


@pytest.mark.asyncio
async def test_new_user_without_birthdate_gets_same_response_as_existing_user(
    client, monkeypatch
) -> None:
    """Missing birthdate for a brand-new email must look identical to an
    existing-user request — otherwise the response leaks whether the email
    is already registered."""
    sent = _capture_deep_links(monkeypatch)

    new_user_response = await client.post(
        "/auth/request-link",
        json={"email": "no-birthdate@example.com"},
    )
    existing_user_response = await client.post(
        "/auth/request-link",
        json={"email": "returning-no-bday@example.com", "birthdate": "2000-01-01"},
    )

    assert new_user_response.status_code == existing_user_response.status_code == 200
    assert new_user_response.json() == existing_user_response.json()
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_email_lookup_is_case_insensitive(client, monkeypatch) -> None:
    sent = _capture_deep_links(monkeypatch)

    await client.post(
        "/auth/request-link",
        json={"email": "Mixed-Case@Example.com", "birthdate": "2000-01-01"},
    )
    response = await client.post(
        "/auth/request-link",
        json={"email": "mixed-case@example.com"},
    )

    assert response.status_code == 200
    assert len(sent) == 2

    token = _token_from_deep_link(sent[1])
    verify_response = await client.get("/auth/verify", params={"token": token})
    assert verify_response.status_code == 200
    assert verify_response.json()["email"] == "mixed-case@example.com"


@pytest.mark.asyncio
async def test_verify_rejects_unknown_token(client) -> None:
    response = await client.get("/auth/verify", params={"token": "not-a-real-token"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_magic_link_is_single_use(client, monkeypatch) -> None:
    sent = _capture_deep_links(monkeypatch)

    await client.post(
        "/auth/request-link",
        json={"email": "single-use@example.com", "birthdate": "2000-01-01"},
    )
    token = _token_from_deep_link(sent[0])

    first = await client.get("/auth/verify", params={"token": token})
    assert first.status_code == 200

    second = await client.get("/auth/verify", params={"token": token})
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(client, db_session, monkeypatch) -> None:
    sent = _capture_deep_links(monkeypatch)

    await client.post(
        "/auth/request-link",
        json={"email": "logout@example.com", "birthdate": "2000-01-01"},
    )
    token = _token_from_deep_link(sent[0])
    verify_response = await client.get("/auth/verify", params={"token": token})
    session_token = verify_response.json()["session_token"]

    assert await auth_service.get_user_for_session_token(db_session, session_token) is not None

    logout_response = await client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {session_token}"}
    )
    assert logout_response.status_code == 204

    assert await auth_service.get_user_for_session_token(db_session, session_token) is None


@pytest.mark.asyncio
async def test_logout_is_idempotent_on_already_revoked_session(client, monkeypatch) -> None:
    sent = _capture_deep_links(monkeypatch)

    await client.post(
        "/auth/request-link",
        json={"email": "logout-twice@example.com", "birthdate": "2000-01-01"},
    )
    token = _token_from_deep_link(sent[0])
    verify_response = await client.get("/auth/verify", params={"token": token})
    session_token = verify_response.json()["session_token"]

    headers = {"Authorization": f"Bearer {session_token}"}
    first = await client.post("/auth/logout", headers=headers)
    second = await client.post("/auth/logout", headers=headers)

    assert first.status_code == 204
    assert second.status_code == 204


@pytest.mark.asyncio
async def test_logout_is_idempotent_on_unknown_token(client) -> None:
    response = await client.post(
        "/auth/logout", headers={"Authorization": "Bearer not-a-real-session-token"}
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_without_authorization_header_is_noop(client) -> None:
    response = await client.post("/auth/logout")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_debug_token_withheld_outside_development_environment(client, monkeypatch) -> None:
    """Non-'development' environment - debug_token must stay null even when
    the X-Test-Mode header is sent, so a production/staging deployment can
    never leak sign-in tokens to anyone who can reach it. Environment is
    pinned explicitly so this test doesn't depend on how the process/Docker
    environment happens to be configured."""
    _capture_deep_links(monkeypatch)
    monkeypatch.setattr(auth_router.settings, "environment", "production")

    response = await client.post(
        "/auth/request-link",
        json={"email": "no-leak@example.com", "birthdate": "2000-01-01"},
        headers={"X-Test-Mode": "1"},
    )

    assert response.status_code == 200
    assert response.json()["debug_token"] is None


@pytest.mark.asyncio
async def test_debug_token_withheld_without_test_mode_header(client, monkeypatch) -> None:
    _capture_deep_links(monkeypatch)
    monkeypatch.setattr(auth_router.settings, "environment", "development")

    response = await client.post(
        "/auth/request-link",
        json={"email": "no-header@example.com", "birthdate": "2000-01-01"},
    )

    assert response.status_code == 200
    assert response.json()["debug_token"] is None


@pytest.mark.asyncio
async def test_debug_token_returned_in_development_environment_with_header(
    client, monkeypatch
) -> None:
    sent = _capture_deep_links(monkeypatch)
    monkeypatch.setattr(auth_router.settings, "environment", "development")

    response = await client.post(
        "/auth/request-link",
        json={"email": "e2e-user@example.com", "birthdate": "2000-01-01"},
        headers={"X-Test-Mode": "1"},
    )

    assert response.status_code == 200
    debug_token = response.json()["debug_token"]
    assert debug_token
    assert debug_token == _token_from_deep_link(sent[0])

    verify_response = await client.get("/auth/verify", params={"token": debug_token})
    assert verify_response.status_code == 200


@pytest.mark.asyncio
async def test_debug_token_absent_for_silently_rejected_signup(client, monkeypatch) -> None:
    """The underage/no-birthdate no-op path returns raw_token=None from the
    service - debug_token must stay null even in test mode, since there's no
    token to echo."""
    sent = _capture_deep_links(monkeypatch)
    monkeypatch.setattr(auth_router.settings, "environment", "development")

    response = await client.post(
        "/auth/request-link",
        json={"email": "e2e-no-birthdate@example.com"},
        headers={"X-Test-Mode": "1"},
    )

    assert response.status_code == 200
    assert response.json()["debug_token"] is None
    assert len(sent) == 0
