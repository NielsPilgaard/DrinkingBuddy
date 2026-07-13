---
title: Scaffold repo skeleton
status: in-progress
last_updated: 2026-07-13
depends_on: docs/prd.md, docs/tech-stack.md
---

## Progress (2026-07-13)

Done:
- `/backend`: FastAPI app (`app/main.py`, `routers/health.py`, `config.py`), `pyproject.toml`, `Dockerfile`, `docker-compose.yml` (api+postgres+redis+coturn), `.env.example`, Alembic wired (`alembic.ini`, `alembic/env.py`, empty initial migration `b0153df16b06_initial.py`).
- Verified: `docker compose up -d --build` brings up all 4 containers; `curl localhost:8000/health` → `200 {"status":"ok"}`; `alembic upgrade head` applied cleanly against dockerized Postgres.
- `/app`: Expo TypeScript app scaffolded (`create-expo-app` blank-typescript), stripped template noise (its own AGENTS.md/CLAUDE.md/.claude/LICENSE — unrelated to this repo's conventions). `App.tsx` calls `EXPO_PUBLIC_API_URL` + `/health`, renders ok/error state. `eas.json` added (dev/preview/production profiles). `tsc --noEmit` clean.
- Root `.gitignore` covers Python + Node/Expo/RN artifacts. Root `README.md` already matched target layout (pre-existing).

Not yet done:
- Manual verification of Expo app on simulator/device (dev server smoke test was interrupted mid-session — needs a real run + visual confirm of health-check screen, per "Done when" criteria).
- Not yet committed to git.

## Goal

Stand up empty-but-runnable skeletons for backend and mobile app, matching `docs/tech-stack.md`. No feature logic yet — just structure, tooling, and a working "hello world" round trip.

## Scope

### Backend (`/backend`)
- FastAPI project structure (app entrypoint, routers folder, models folder).
- Docker Compose: FastAPI app, Postgres, Redis, coturn — all four services running locally.
- `.env`-based config (DB url, Redis url, coturn secret).
- Health check endpoint (`GET /health`) returning 200.
- Alembic (or equivalent) migration setup, wired to Postgres, empty initial migration.

### Mobile app (`/app`)
- Expo project init (React Native, TypeScript template).
- EAS Build config present (`eas.json`), not necessarily submitted anywhere yet.
- Single screen that calls backend `/health` and displays result — proves app-to-API connectivity end to end.

### Repo-level
- Root `README.md`: how to run backend (`docker compose up`) and app (`expo start`) locally.
- `.gitignore` covering both Python and RN/Expo/Node artifacts.

## Explicitly out of scope

- Auth (OTP/magic-link, email+password) — next task.
- Matching queue, WebRTC signaling — later task.
- Any Hetzner deployment — local dev only for this task.
- coturn actually wired into a WebRTC call — just runs as a service for now.

## Done when

- `docker compose up` brings up API + Postgres + Redis + coturn cleanly.
- `curl localhost:<port>/health` returns 200 from the dockerized API.
- Expo app runs on a simulator/device and successfully displays the health check result from the API.
