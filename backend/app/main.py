from fastapi import FastAPI

from app.routers import auth, health, matching, moderation, signaling, verify
from app.telemetry import setup_telemetry

app = FastAPI(title="DrinkingBuddy API")

setup_telemetry(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(matching.router)
app.include_router(signaling.router)
app.include_router(moderation.router)
app.include_router(verify.router)
