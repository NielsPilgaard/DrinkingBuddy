---
title: Generated API client in RN app
status: in_progress
last_updated: 2026-07-14
depends_on: tasks/01-scaffold-repo.md
---

## Progress (2026-07-14)

Done:
- `/app`: `@hey-api/openapi-ts` (dev) + `@tanstack/react-query` deps added. `openapi-ts.config.ts` points at `${EXPO_PUBLIC_API_URL}/openapi.json`, plugins: client-fetch, typescript, sdk, `@tanstack/react-query`.
- `npm run codegen` → generates into `app/src/api/generated/` (committed, not gitignored — regen requires a running backend, so it's checked in like a lockfile).
- `App.tsx`: wrapped in `QueryClientProvider`; health check now uses generated `healthHealthGetOptions()` + `useQuery` instead of hand-rolled `fetch`. Client baseUrl set at runtime via `client.setConfig({ baseUrl: API_URL })` so `EXPO_PUBLIC_API_URL` still works without regenerating.
- Verified: backend run locally via `uv run uvicorn app.main:app` (no Docker needed just for schema) — documented in new `docs/local_dev.md`. `curl localhost:8000/openapi.json` confirmed schema; `npm run codegen` produced 5 files; `tsc --noEmit` clean.
- Side quest: repo had no documented Python dependency manager. Added `docs/local_dev.md` (uv usage) + pointers from `AGENTS.md` and `README.md`.

Not yet done:
- Manual simulator/device run of updated `App.tsx` (interrupted before this step — needs a real run to visually confirm the health-check screen still renders via the generated hook).
- Not yet committed to git.

## Goal

Type-safe client in `/app` generated from backend's OpenAPI schema — no hand-written fetch calls, no manual type drift between FastAPI and RN.

## Approach

- `@hey-api/openapi-ts` generates types + SDK from FastAPI's `/openapi.json`, plus its `@tanstack/react-query` plugin to emit query/mutation hooks.
- `@tanstack/react-query` added to `/app` as the data-fetching layer (not present yet — this task introduces it).
- Manual regen via npm script — no CI/pre-commit enforcement at this stage. Dev re-runs after pulling backend changes that touch routes.

## Scope

- `/app`: add `openapi-ts` config (`openapi-ts.config.ts`) pointing at backend's OpenAPI JSON.
- `package.json` script, e.g. `"codegen": "openapi-ts"`, run manually (backend must be running locally, or point at a static exported spec — pick whichever is less friction once wired up).
- Generated output directory (e.g. `app/src/api/generated/`) — decide committed vs. gitignored.
- Add `@tanstack/react-query`, wrap app root in `QueryClientProvider`.
- Replace existing hand-rolled `/health` fetch in `App.tsx` with generated hook, proving the pipeline end to end.

## Explicitly out of scope

- CI enforcement of generated-vs-committed diff (revisit once auth/matching endpoints land in tasks 02-04 and the schema stabilizes).
- Any endpoints beyond `/health` — this task scaffolds the pipeline, not new backend routes.
- Auth token wiring into generated client (depends on task 02).

## Done when

- `npm run codegen` in `/app` regenerates types/hooks from the running backend's OpenAPI schema without manual edits.
- `App.tsx` health check uses the generated react-query hook instead of a hand-written `fetch`.
- `tsc --noEmit` clean, app still runs and displays health-check result on simulator/device.
