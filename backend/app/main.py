from fastapi import FastAPI

from app.routers import auth, health, matching
from app.telemetry import setup_telemetry

app = FastAPI(title="DrinkingBuddy API")

setup_telemetry(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(matching.router)
