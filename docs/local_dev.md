---
description: Local dev setup for backend + app — dependency managers, running services outside Docker.
---

## Backend (`/backend`)

Dependency management is [`uv`](https://docs.astral.sh/uv/), not raw `pip`/`venv`.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Use this (instead of full `docker compose up`) when you only need the API process — e.g. generating the OpenAPI schema for client codegen — without Postgres/Redis/coturn.

## App (`/app`)

```bash
cd app
npm install
npx expo start
```

`EXPO_PUBLIC_API_URL` controls which backend the app/codegen point at (defaults to `http://localhost:8000`).
