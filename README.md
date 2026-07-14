# DrinkingBuddy (working name)

Chat-roulette-style app for random 1:1 video/audio/text hangouts over a drink. iOS + Android MVP.

See [AGENTS.md](AGENTS.md) for full product/tech overview, [docs/prd.md](docs/prd.md) for product spec, [docs/tech-stack.md](docs/tech-stack.md) for stack decisions.

> Status: repo skeleton in progress ([tasks/01-scaffold-repo.md](tasks/01-scaffold-repo.md)). Commands below reflect target structure.

## Backend (`/backend`)

FastAPI app + Postgres + Redis + coturn, via Docker Compose.

```bash
cd backend
cp .env.example .env   # fill in DB url, Redis url, coturn secret
docker compose up
```

Health check: `curl localhost:8000/health` → `200`.

Migrations (Alembic):

```bash
docker compose exec api alembic upgrade head
```

Running the API without Docker (e.g. for client codegen): see [docs/local_dev.md](docs/local_dev.md).

## Mobile app (`/app`)

Expo (React Native, TypeScript).

```bash
cd app
npm install
npx expo start
```

Scan QR with Expo Go, or run on simulator. App calls backend `/health` on launch to confirm connectivity — point it at your local backend URL in `.env`.

## Repo layout

```
/backend   FastAPI app, routers/, models/, Alembic migrations, docker-compose.yml
/app       Expo React Native app
/docs      PRD, tech stack, ADRs, mockups
/tasks     Numbered task specs
```
