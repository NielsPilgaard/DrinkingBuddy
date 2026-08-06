from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = (
        "postgresql+asyncpg://drinkingbuddy:drinkingbuddy@postgres:5432/drinkingbuddy"
    )
    redis_url: str = "redis://redis:6379/0"
    coturn_secret: str = "changeme"

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


settings = Settings()

if settings.environment != "development" and settings.didit_webhook_secret == "changeme":
    raise RuntimeError(
        "didit_webhook_secret must be set to a real secret outside development environments"
    )
