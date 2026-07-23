---
name: verify
description: Lint, format-check, and typecheck DrinkingBuddy backend (ruff, ty) and app (biome, tsc). Run before committing or when asked to verify/lint the repo.
---

Run everything with one script:

```powershell
pwsh -File scripts/verify.ps1
```

Runs, in order, failing fast per step but continuing to report all failures:

| Step | Tool | Dir |
|---|---|---|
| Lint | `uv run ruff check .` | `backend/` |
| Format check | `uv run ruff format --check .` | `backend/` |
| Type check | `uv run ty check` | `backend/` |
| Lint + format check | `npx biome check .` | `app/` |
| Type check | `npx tsc --noEmit` | `app/` |

Exit 0 = all clean. Exit 1 = at least one step failed (see console for which).

## Fixing failures

- Backend lint/format: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- App lint/format: `cd app && npx biome check --write .`
- Type errors (`ty`, `tsc`) have no autofix — read the error and fix the code.

## Setup (first run / after dependency changes)

```powershell
cd backend; uv sync --extra dev
cd app; npm install
```

## Gotchas

- `ty` is prerelease (`ty>=0.0.1a1` in `backend/pyproject.toml`) — API/output may shift between versions.
- Biome config (`app/biome.json`) pins `$schema` to the installed `@biomejs/biome` version; if `npm install` bumps the version, update the schema URL or `npx biome check` prints a version-mismatch info line (harmless but noisy).
- `app/biome.json` excludes `src/api/generated` (openapi-ts codegen output) from lint/format — don't hand-fix lint issues there, regenerate instead.
