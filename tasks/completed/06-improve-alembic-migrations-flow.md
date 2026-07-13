---
description: Migrations run as dedicated compose service before api starts, not inside api process.
---

Done. `backend/docker-compose.yml`:

- New `migrate` service: `command: alembic upgrade head`, `depends_on: postgres (healthy)`.
- `api` gets `depends_on: migrate (service_completed_successfully)` — never starts on migration failure.

Each migration runs in its own transaction (alembic default for Postgres DDL) — a failing script auto-reverts itself, `migrate` exits non-zero, `api` never starts. No automated cross-release rollback.

**Convention going forward:** every new migration must implement a working `downgrade()`, not `pass`. Lets a dev manually `alembic downgrade -1` to back out a bad release. Current initial migration is a no-op (`pass`/`pass`) since no models exist yet — fine as-is, revisit once real schema lands.

Verified manually: happy path (migrate exits 0 → api starts healthy) and failure path (broken migration → migrate exits 1 → `docker compose up api` refuses to start api).
