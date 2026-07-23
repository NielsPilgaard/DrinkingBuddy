from fastapi import FastAPI

from app.routers import health
from app.telemetry import setup_telemetry

app = FastAPI(title="DrinkingBuddy API")

setup_telemetry(app)

app.include_router(health.router)
