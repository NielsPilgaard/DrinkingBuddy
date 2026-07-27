from urllib.parse import parse_qs, urlparse

import pytest

import app.auth.service as auth_service

pytestmark = pytest.mark.integration

FILTERS_DK_EN_ALC = {"language": "en", "drink_type": "alcoholic", "location": "dk"}
FILTERS_DK_EN_NONALC = {"language": "en", "drink_type": "non_alcoholic", "location": "dk"}


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


@pytest.mark.asyncio
async def test_compatible_users_are_paired(ws_client, monkeypatch):
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "alice@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "bob@example.com")

    async with ws_client.websocket(f"/matching/ws?token={token_a}") as ws_a:
        await ws_a.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
        waiting = await ws_a.receive_json()
        assert waiting["type"] == "waiting"

        async with ws_client.websocket(f"/matching/ws?token={token_b}") as ws_b:
            await ws_b.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})

            matched_b = await ws_b.receive_json()
            matched_a = await ws_a.receive_json()

    assert matched_a["type"] == "matched"
    assert matched_b["type"] == "matched"
    assert matched_a["partner_id"] == user_b_id
    assert matched_b["partner_id"] == user_a_id


@pytest.mark.asyncio
async def test_incompatible_filters_do_not_pair(ws_client, monkeypatch):
    token_a, _ = await _signup_and_get_token(ws_client, monkeypatch, "carol@example.com")
    token_b, _ = await _signup_and_get_token(ws_client, monkeypatch, "dave@example.com")

    async with (
        ws_client.websocket(f"/matching/ws?token={token_a}") as ws_a,
        ws_client.websocket(f"/matching/ws?token={token_b}") as ws_b,
    ):
        await ws_a.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
        waiting_a = await ws_a.receive_json()
        assert waiting_a["type"] == "waiting"

        await ws_b.send_json({"type": "join", "filters": FILTERS_DK_EN_NONALC})
        waiting_b = await ws_b.receive_json()
        assert waiting_b["type"] == "waiting"

        await ws_a.send_json({"type": "leave"})
        await ws_b.send_json({"type": "leave"})


@pytest.mark.asyncio
async def test_cold_start_triggers_widen_search_prompt(ws_client, monkeypatch):
    import app.routers.matching as matching_router

    monkeypatch.setattr(matching_router, "COLD_START_TIMEOUT_SECONDS", 0.2)

    token, _ = await _signup_and_get_token(ws_client, monkeypatch, "erin@example.com")

    async with ws_client.websocket(f"/matching/ws?token={token}") as ws:
        await ws.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
        waiting = await ws.receive_json()
        assert waiting["type"] == "waiting"

        prompt = await ws.receive_json(timeout=5)
        assert prompt["type"] == "widen_search_prompt"


@pytest.mark.asyncio
async def test_skip_requeues_without_cooldown(ws_client, monkeypatch):
    token_a, _ = await _signup_and_get_token(ws_client, monkeypatch, "frank@example.com")
    token_b, _ = await _signup_and_get_token(ws_client, monkeypatch, "grace@example.com")
    token_c, _ = await _signup_and_get_token(ws_client, monkeypatch, "heidi@example.com")

    async with (
        ws_client.websocket(f"/matching/ws?token={token_a}") as ws_a,
        ws_client.websocket(f"/matching/ws?token={token_b}") as ws_b,
    ):
        await ws_a.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
        await ws_a.receive_json()

        await ws_b.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
        await ws_b.receive_json()
        matched_a = await ws_a.receive_json()
        assert matched_a["type"] == "matched"

        await ws_a.send_json({"type": "skip"})
        waiting_after_skip = await ws_a.receive_json()
        assert waiting_after_skip["type"] == "waiting"

        async with ws_client.websocket(f"/matching/ws?token={token_c}") as ws_c:
            await ws_c.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
            matched_c = await ws_c.receive_json()
            matched_a_again = await ws_a.receive_json()

    assert matched_c["type"] == "matched"
    assert matched_a_again["type"] == "matched"


@pytest.mark.asyncio
async def test_disconnect_clears_queue_state(ws_client, redis_container, monkeypatch):
    from redis.asyncio import Redis

    token_a, _ = await _signup_and_get_token(ws_client, monkeypatch, "ivan@example.com")
    token_b, _ = await _signup_and_get_token(ws_client, monkeypatch, "judy@example.com")

    async with ws_client.websocket(f"/matching/ws?token={token_a}") as ws_a:
        await ws_a.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
        await ws_a.receive_json()

    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis = Redis.from_url(f"redis://{host}:{port}/0", decode_responses=True)
    try:
        keys = await redis.keys("queue:*")
        assert keys == []
    finally:
        await redis.aclose()

    async with ws_client.websocket(f"/matching/ws?token={token_b}") as ws_b:
        await ws_b.send_json({"type": "join", "filters": FILTERS_DK_EN_ALC})
        waiting = await ws_b.receive_json()
        assert waiting["type"] == "waiting"
        await ws_b.send_json({"type": "leave"})
