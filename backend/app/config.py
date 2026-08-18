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

    # When environment == "development", /auth/request-link echoes the
    # magic-link token back in the response (if the caller also sends
    # X-Test-Mode: 1), so E2E clients (Maestro) can complete sign-in without
    # an email inbox. Never enabled outside "development" - see
    # tasks/completed/mobile-e2e-maestro.md and
    # tasks/NEEDS-HUMAN-REVIEW-maestro-e2e.md.


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

if (
    settings.environment != "development"
    and settings.chat_safety_flag_encryption_key == "CQ02dBuJfDFA30Yq9q3kdyoaC9YGYbZsDzWxi8Qects="
):
    raise RuntimeError(
        "chat_safety_flag_encryption_key must be set to a real secret outside development "
        "environments"
    )
