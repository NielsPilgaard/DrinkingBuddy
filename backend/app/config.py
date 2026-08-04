from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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


settings = Settings()
