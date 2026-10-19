import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


async def _get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_aasa_404_without_team_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "apple_team_id", "")

    response = await _get("/.well-known/apple-app-site-association")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_aasa_lists_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "apple_team_id", "TEAM123")

    response = await _get("/.well-known/apple-app-site-association")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    detail = response.json()["applinks"]["details"][0]
    assert detail["appIDs"] == ["TEAM123.com.drinkingbuddy.app"]
    assert detail["components"] == [{"/": "/verify"}]


@pytest.mark.asyncio
async def test_assetlinks_404_without_fingerprints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "android_sha256_cert_fingerprints", "")

    response = await _get("/.well-known/assetlinks.json")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assetlinks_lists_fingerprints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "android_sha256_cert_fingerprints", "AA:BB, CC:DD ,")

    response = await _get("/.well-known/assetlinks.json")

    assert response.status_code == 200
    target = response.json()[0]["target"]
    assert target["package_name"] == "com.drinkingbuddy.app"
    assert target["sha256_cert_fingerprints"] == ["AA:BB", "CC:DD"]


@pytest.mark.asyncio
async def test_verify_fallback_bounces_to_app_scheme() -> None:
    response = await _get("/verify?token=abc-123_XYZ")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert 'href="drinkingbuddy://verify?token=abc-123_XYZ"' in response.text
    assert 'location.replace("drinkingbuddy://verify?token=abc-123_XYZ")' in response.text


@pytest.mark.asyncio
async def test_verify_fallback_encodes_hostile_token() -> None:
    response = await _get('/verify?token="></a><script>alert(1)</script>')

    assert "<script>alert" not in response.text
    assert '"></a>' not in response.text
    assert "token=%22%3E%3C%2Fa%3E%3Cscript%3Ealert%281%29%3C%2Fscript%3E" in response.text
