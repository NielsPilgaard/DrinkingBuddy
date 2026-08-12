from app.config import settings
from app.verification.didit import verify_webhook_signature


def test_verify_webhook_signature_accepts_correctly_signed_body(monkeypatch) -> None:
    monkeypatch.setattr(settings, "didit_webhook_secret", "test-secret")
    body = b'{"session_id": "abc", "status": "Approved"}'

    import hashlib
    import hmac

    signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(body, signature) is True


def test_verify_webhook_signature_rejects_forged_signature(monkeypatch) -> None:
    monkeypatch.setattr(settings, "didit_webhook_secret", "test-secret")
    body = b'{"session_id": "abc", "status": "Approved"}'

    assert verify_webhook_signature(body, "0" * 64) is False


def test_verify_webhook_signature_rejects_missing_signature(monkeypatch) -> None:
    monkeypatch.setattr(settings, "didit_webhook_secret", "test-secret")
    body = b'{"session_id": "abc", "status": "Approved"}'

    assert verify_webhook_signature(body, "") is False


def test_verify_webhook_signature_rejects_body_tampered_after_signing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "didit_webhook_secret", "test-secret")
    original_body = b'{"session_id": "abc", "status": "Approved"}'

    import hashlib
    import hmac

    signature = hmac.new(b"test-secret", original_body, hashlib.sha256).hexdigest()
    tampered_body = b'{"session_id": "abc", "status": "Declined"}'

    assert verify_webhook_signature(tampered_body, signature) is False
