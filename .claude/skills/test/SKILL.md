---
name: test
description: Run DrinkingBuddy backend test suite (unit/integration/all) via scripts/test.ps1. Use when asked to run tests, add a test, or check CI-equivalent status locally.
---

# test

Wraps `scripts/test.ps1`. Backend only — `/app` (Expo/RN) consumes the generated client and health query already, but has no test suite yet.

## Run

```powershell
./scripts/test.ps1                          # unit only (fast, no Docker)
./scripts/test.ps1 -Suite integration       # testcontainers Postgres, needs Docker
./scripts/test.ps1 -Suite all               # unit + integration
./scripts/test.ps1 -K health                # pytest -k filter
./scripts/test.ps1 -VerboseOutput
```

## Tiers

- `tests/unit/` — no I/O, ASGI transport against `app.main.app` directly.
- `tests/integration/` — real Postgres via testcontainers (session-scoped fixture in `tests/integration/conftest.py`), auth/DB deps not yet present to override (no auth exists yet per AGENTS.md scope).

See `testing-strategy` skill for tier conventions (fixture patterns, testcontainers images) if extending — e.g. adding E2E once app has a real client.

## Adding a test

- New endpoint/pure logic → `tests/unit/test_<name>.py`, no fixtures beyond `ASGITransport`.
- New DB-backed behavior → `tests/integration/test_<name>.py`, use `postgres_container` fixture, mark module `pytestmark = pytest.mark.integration`.

## Gotchas

- Integration tier needs Docker daemon running; script checks and errors clearly if not.
- Don't add auth overrides yet — no auth implemented (see tasks/ for scope boundaries).
- Keep container fixtures session-scoped — don't spin one per test.
