from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = (
        "postgresql+asyncpg://drinkingbuddy:drinkingbuddy@postgres:5432/drinkingbuddy"
    )
    redis_url: str = "redis://redis:6379/0"
    coturn_secret: str = "changeme"
    coturn_host: str = "localhost"

    otel_enabled: bool = False
    otel_service_name: str = "drinkingbuddy-api"
    otel_exporter_otlp_endpoint: str = "http://otel-lgtm:4317"

    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    email_from: str = "noreply@drinkingbuddy.local"

    app_deep_link_scheme: str = "drinkingbuddy"
    app_universal_link_base: str = "https://app.drinking-buddy.app"
    # Served as /.well-known/apple-app-site-association and assetlinks.json on
    # app.<DOMAIN> so iOS/Android verify the magic-link host. Empty -> 404.
    app_bundle_id: str = "com.drinkingbuddy.app"
    apple_team_id: str = ""
    # Comma-separated SHA-256 signing cert fingerprints (AA:BB:...).
    android_sha256_cert_fingerprints: str = ""

    magic_link_ttl_minutes: int = 15
    session_ttl_days: int = 30

    didit_api_key: str = ""
    didit_webhook_secret: str = "changeme"
    didit_base_url: str = "https://verification.didit.me"
    didit_age_estimation_workflow_id: str = ""
    didit_cpr_passthrough_workflow_id: str = ""

    verification_monthly_cap: int = 500
    verification_expiry_days: int = 365
    verification_rate_limit_per_user: int = 3
    verification_rate_limit_user_window_minutes: int = 60
    verification_rate_limit_per_ip: int = 10
    verification_rate_limit_ip_window_minutes: int = 60

    report_auto_suspend_threshold: int = 3
    report_window_hours: int = 24
    suspension_duration_hours: int = 24

    chat_safety_flag_encryption_key: str = "CQ02dBuJfDFA30Yq9q3kdyoaC9YGYbZsDzWxi8Qects="
    chat_safety_retention_days: int = 30
    chat_safety_retention_grace_hours: int = 24
    chat_safety_moderation_secret: str = "changeme"
    chat_safety_oncall_email: str = "moderation-oncall@drinkingbuddy.local"

    # CSAM-suspected cases (tasks/11-csam-reporting.md, docs/csam-runbook.md).
    # Separate key + secret from chat safety so the authorized set stays
    # narrower than general moderation. Retention is a placeholder until
    # counsel sets the legally-required minimum.
    csam_evidence_encryption_key: str = "aBsi6dGJr72_y8oNjBLiRwmeMQreG5x3Vlwu605zTRM="
    csam_evidence_retention_days: int = 90
    csam_moderation_secret: str = "changeme"
    csam_oncall_email: str = "csam-oncall@drinkingbuddy.local"
    csam_suspension_hours: int = 720

    # When environment == "development", /auth/request-link echoes the
    # magic-link token back in the response (if the caller also sends
    # X-Test-Mode: 1), so E2E clients (Maestro) can complete sign-in without
    # an email inbox. Never enabled outside "development" - see
    # tasks/completed/mobile-e2e-maestro.md.


settings = Settings()

if settings.environment != "development" and settings.didit_webhook_secret == "changeme":
    raise RuntimeError(
        "didit_webhook_secret must be set to a real secret outside development environments"
    )

if settings.environment != "development" and settings.chat_safety_moderation_secret == "changeme":
    raise RuntimeError(
        "chat_safety_moderation_secret must be set to a real secret outside development "
        "environments"
    )

if settings.environment != "development" and settings.csam_moderation_secret == "changeme":
    raise RuntimeError(
        "csam_moderation_secret must be set to a real secret outside development environments"
    )


def _require_real_fernet_key(name: str, value: str, dev_default: str) -> None:
    try:
        Fernet(value)
        valid_key = True
    except ValueError:
        valid_key = False
    if not valid_key or value == dev_default:
        raise RuntimeError(
            f"{name} must be set to a real Fernet key outside development environments"
        )


if settings.environment != "development":
    _require_real_fernet_key(
        "chat_safety_flag_encryption_key",
        settings.chat_safety_flag_encryption_key,
        "CQ02dBuJfDFA30Yq9q3kdyoaC9YGYbZsDzWxi8Qects=",
    )
    _require_real_fernet_key(
        "csam_evidence_encryption_key",
        settings.csam_evidence_encryption_key,
        "aBsi6dGJr72_y8oNjBLiRwmeMQreG5x3Vlwu605zTRM=",
    )
