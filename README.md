# DrinkingBuddy (working name)

Chat-roulette-style app for random 1:1 video/audio/text hangouts over a drink. iOS + Android MVP.

See [AGENTS.md](AGENTS.md) for full product/tech overview, [docs/prd.md](docs/prd.md) for product spec, [docs/tech-stack.md](docs/tech-stack.md) for stack decisions.

## Quickstart

Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/) (fetches Python 3.12+ itself), Node `^20.19.4 || ^22.13 || ^24.3` (see [app/.nvmrc](app/.nvmrc)), Docker (for the backend stack and integration tests).

```bash
./scripts/setup.sh          # macOS / Linux / Git Bash
./scripts/setup.ps1         # Windows (PowerShell 7)
```

Setup is idempotent. It checks prerequisites, creates `backend/.env` and `app/.env` from their `.env.example` (existing files are kept), and runs `uv sync --extra dev` and `npm ci`. Add `--up` / `-Up` to also start the backend stack and wait for `/health`.

Verify the install:

```bash
cd backend && uv run pytest tests/unit                                # fast, no Docker
cd backend && uv run pytest tests/integration -m integration          # testcontainers, needs Docker
pwsh -File scripts/verify.ps1                                         # ruff, ty, biome, tsc
```

The defaults in `.env.example` work for local dev. Didit keys (`DIDIT_*`) are only needed to exercise webcam age verification ([tasks/completed/10-age-verification.md](tasks/completed/10-age-verification.md)).

## Backend (`/backend`)

FastAPI + Postgres + Redis + coturn + Mailpit + Grafana/OTel, via Docker Compose. `setup --up` runs this for you:

```bash
cd backend
docker compose up -d --build --wait                                      # needs Loki logging plugin, see below
docker compose -f docker-compose.yml -f docker-compose.windows.yml up -d --build --wait   # without it
```

- API: `localhost:8000` (`/health` → `200`, `/docs` for OpenAPI). Migrations run automatically via the `migrate` service.
- Mailpit (magic-link emails): `localhost:8025`.
- Grafana: `localhost:3000` (`admin`/`admin`).

Container logs ship to Loki via a host-level Docker plugin (`docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions`). Windows can't install it, and other hosts may not have it. Use the `docker-compose.windows.yml` override in that case. Details: [docs/local_dev.md](docs/local_dev.md).

Running the API without Docker (e.g. for client codegen): see [docs/local_dev.md](docs/local_dev.md).

## Mobile app (`/app`)

Expo (React Native, TypeScript). The app uses native modules (`react-native-webrtc`, Didit SDK), so it needs a **development build**. Expo Go can't run it.

```bash
cd app
npx expo run:android        # or run:ios (macOS + Xcode); needs Android SDK / emulator
# or: eas build --profile development
npx expo start --dev-client
```

`EXPO_PUBLIC_API_URL` in `app/.env` points the app at the backend. Android emulator: `http://10.0.2.2:8000`. Physical device: your machine's LAN IP. See [docs/testing_app.md](docs/testing_app.md).

Mobile E2E (Maestro): [maestro/README.md](maestro/README.md).

## Repo layout

```
/backend   FastAPI app, routers/, models/, Alembic migrations, docker-compose*.yml
/app       Expo React Native app
/scripts   setup, test, verify
/maestro   Mobile E2E flows
/docs      PRD, tech stack, local dev, deploy, mockups
/tasks     Numbered task specs (completed/ for done)
```
