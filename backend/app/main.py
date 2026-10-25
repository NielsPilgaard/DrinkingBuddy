from fastapi import FastAPI

from app.config import settings
from app.routers import (
    app_links,
    auth,
    chat_safety,
    csam,
    health,
    matching,
    moderation,
    signaling,
    verify,
)
from app.signaling.turn import validate_coturn_secret
from app.telemetry import setup_telemetry

if settings.environment != "development":
    validate_coturn_secret(settings.coturn_secret)

app = FastAPI(title="DrinkingBuddy API")

setup_telemetry(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(matching.router)
app.include_router(signaling.router)
app.include_router(moderation.router)
app.include_router(chat_safety.router)
app.include_router(csam.router)
app.include_router(verify.router)
app.include_router(app_links.router)
