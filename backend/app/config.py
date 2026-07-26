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


settings = Settings()
