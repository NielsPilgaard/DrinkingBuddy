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

To reach the API from the Expo app on an emulator/device, bind to all interfaces instead:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0
```

- **Android emulator**: use `http://10.0.2.2:8000` (emulator's alias for the host machine).
- **Physical device**: use your host machine's LAN IP (e.g. `http://192.168.1.x:8000`), device and host must be on the same network.

### Full `docker compose up` — Loki logging driver

`docker-compose.yml` ships container stdout logs (api, postgres, redis, coturn) to Loki via the Docker Loki logging driver. That driver is a host-level Docker plugin, not something Compose installs for you — one-time setup before your first `docker compose up`:

```bash
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

Without it, those services fail to start with a "plugin not found" error.

**Windows**: Docker logging-driver plugins (`docker plugin install`) require a Linux Docker daemon and are not supported by Docker Desktop's Windows/WSL2 engine — the command above will not work here. Use the override file to swap the `json-file` driver in instead:

```powershell
docker compose -f docker-compose.yml -f docker-compose.windows.yml up
```

Container logs still reach stdout/`docker logs` as usual; they just aren't shipped to Loki/Grafana on Windows. Use `docker compose up` (no override) on Linux/macOS hosts where the Loki plugin is installed.

## App (`/app`)

```bash
cd app
npm install
npx expo start
```

`EXPO_PUBLIC_API_URL` controls which backend the app/codegen point at. Unset: codegen uses `http://localhost:8000`, and dev builds of the app use port 8000 on the Metro host (`app/src/api/baseUrl.ts`).
