import hashlib
import hmac
import uuid
from dataclasses import dataclass

import httpx

from app.config import settings
from app.verification.schemas import VerificationMethod

_WORKFLOW_IDS: dict[VerificationMethod, str] = {
    "age_estimation": settings.didit_age_estimation_workflow_id,
    "cpr_passthrough": settings.didit_cpr_passthrough_workflow_id,
}


class DiditRequestError(Exception):
    """Didit call failed for an unknown/ambiguous reason (e.g. a transport
    timeout) - the request may or may not have reached Didit, so callers
    should not assume the attempt was safely rejected."""


class DiditRequestRejectedError(DiditRequestError):
    """Didit gave a confirmed non-2xx response - the request definitely
    reached Didit and was rejected, so it's safe to reconcile as such."""


@dataclass(frozen=True)
class DiditSession:
    session_id: str
    """Stable id the webhook callback correlates on - persisted server-side."""
    session_token: str
    """Short-lived token handed to the client's `startVerification` SDK call."""


async def create_verification_session(
    user_id: uuid.UUID, method: VerificationMethod
) -> DiditSession:
    """Kicks off a Didit verification session for `user_id`. Raises
    DiditRequestError on any non-2xx response so callers can surface a
    retryable failure instead of a silently-broken verification flow."""
    workflow_id = _WORKFLOW_IDS[method]
    try:
        async with httpx.AsyncClient(base_url=settings.didit_base_url, timeout=10) as client:
            response = await client.post(
                "/v3/session/",
                headers={"x-api-key": settings.didit_api_key},
                json={"workflow_id": workflow_id, "vendor_data": str(user_id)},
            )
    except httpx.HTTPError as exc:
        raise DiditRequestError(f"Didit session create request failed: {exc}") from exc

    if response.is_error:
        raise DiditRequestRejectedError(f"Didit session create failed: {response.status_code}")

    try:
        data = response.json()
        return DiditSession(
            session_id=str(data["session_id"]), session_token=str(data["session_token"])
        )
    except (ValueError, KeyError) as exc:
        raise DiditRequestError(f"Didit session create returned malformed response: {exc}") from exc


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Constant-time check that `signature_header` (hex HMAC-SHA256) matches
    the body, using DIDIT_WEBHOOK_SECRET. Rejects forged/unsigned callbacks."""
    if not signature_header:
        return False
    expected = hmac.new(
        settings.didit_webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
