import base64
import hashlib
import hmac
import time
import uuid

from pydantic import BaseModel

from app.config import settings

TURN_CREDENTIAL_TTL_SECONDS = 3600
PLACEHOLDER_COTURN_SECRET = "changeme"
MIN_COTURN_SECRET_LENGTH = 16


def validate_coturn_secret(secret: str) -> None:
    if secret == PLACEHOLDER_COTURN_SECRET or len(secret) < MIN_COTURN_SECRET_LENGTH:
        raise ValueError(
            "COTURN_SECRET must be set to a strong, non-default value "
            f"(min {MIN_COTURN_SECRET_LENGTH} chars)"
        )


class IceServer(BaseModel):
    urls: list[str]
    username: str | None = None
    credential: str | None = None


class TurnCredentials(BaseModel):
    ice_servers: list[IceServer]


def generate_turn_credentials(user_id: uuid.UUID) -> TurnCredentials:
    """Time-limited TURN credentials for coturn's --use-auth-secret scheme.

    Username is `<expiry_unix_ts>:<user_id>`; coturn derives the shared
    password itself via HMAC-SHA1(secret, username) and rejects the
    credential once expiry passes, so nothing needs to be persisted or
    revoked server-side.
    """
    expiry = int(time.time()) + TURN_CREDENTIAL_TTL_SECONDS
    username = f"{expiry}:{user_id}"
    digest = hmac.new(
        settings.coturn_secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1
    ).digest()
    password = base64.b64encode(digest).decode("utf-8")

    return TurnCredentials(
        ice_servers=[
            IceServer(urls=[f"stun:{settings.coturn_host}:3478"]),
            IceServer(
                urls=[
                    f"turn:{settings.coturn_host}:3478?transport=udp",
                    f"turn:{settings.coturn_host}:3478?transport=tcp",
                ],
                username=username,
                credential=password,
            ),
        ]
    )
