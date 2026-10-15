import os

# Tests must never ship telemetry. `.env` (copied from `.env.example`) sets
# OTEL_ENABLED=true with a Compose-network endpoint that doesn't resolve from
# the host, so exporters retry against it and stall interpreter exit. Env vars
# take precedence over `.env` in pydantic-settings, and this conftest loads
# before any `app` import.
os.environ["OTEL_ENABLED"] = "false"
