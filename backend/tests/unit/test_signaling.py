import base64
import hashlib
import hmac
import uuid

import pytest

from app.config import settings
from app.signaling.session import call_id_for_pair
from app.signaling.turn import generate_turn_credentials, validate_coturn_secret


def test_call_id_for_pair_is_order_independent():
    user_a, user_b = uuid.uuid4(), uuid.uuid4()

    assert call_id_for_pair(user_a, user_b) == call_id_for_pair(user_b, user_a)


def test_call_id_for_pair_differs_for_different_pairs():
    user_a, user_b, user_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    assert call_id_for_pair(user_a, user_b) != call_id_for_pair(user_a, user_c)


def test_generate_turn_credentials_includes_stun_and_turn_servers():
    creds = generate_turn_credentials(uuid.uuid4())

    urls = [url for server in creds.ice_servers for url in server.urls]
    assert any(url.startswith("stun:") for url in urls)
    assert any(url.startswith("turn:") for url in urls)


def test_generate_turn_credentials_password_matches_coturn_hmac_scheme():
    user_id = uuid.uuid4()
    creds = generate_turn_credentials(user_id)

    turn_server = next(s for s in creds.ice_servers if s.username is not None)
    assert turn_server.username is not None
    expected_digest = hmac.new(
        settings.coturn_secret.encode("utf-8"),
        turn_server.username.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    expected_password = base64.b64encode(expected_digest).decode("utf-8")

    assert turn_server.credential == expected_password
    assert turn_server.username.endswith(f":{user_id}")


def test_validate_coturn_secret_rejects_placeholder():
    with pytest.raises(ValueError, match="COTURN_SECRET"):
        validate_coturn_secret("changeme")


def test_validate_coturn_secret_rejects_short_secret():
    with pytest.raises(ValueError, match="COTURN_SECRET"):
        validate_coturn_secret("short")


def test_validate_coturn_secret_accepts_strong_secret():
    validate_coturn_secret("a" * 32)
