---
description: Maestro E2E flows driving the real Expo app UI against a running backend. Read this before running or editing anything in maestro/.
---

# Maestro E2E

See `tasks/completed/mobile-e2e-maestro.md` for scope/rationale and
`tasks/NEEDS-HUMAN-REVIEW-maestro-e2e.md` for open questions/unverified
assumptions an implementer flagged — **read that file before trusting these
flows in CI**, several pieces (Maestro CLI multi-device behavior, the exact
`appId`) were written from docs, not a live run.

## Prerequisites

- [Maestro CLI](https://maestro.mobile.dev) installed.
- A running backend, reachable from the simulator/emulator, booted with
  `ENVIRONMENT=development` so `/auth/request-link` echoes the sign-in token (see
  `backend/app/routers/auth.py`):

  ```powershell
  cd backend
  docker compose -f docker-compose.yml -f docker-compose.e2e.yml up
  ```

- The Expo app built and installed on a simulator/emulator/device — a dev
  build is fine, Maestro doesn't need a native test target. `appId` in
  `config.yaml` (`com.drinkingbuddy.app`) matches `app/app.json`'s
  `expo.android.package`. `ios.bundleIdentifier` is not yet pinned.

## Flows

| File | Journey | Devices |
|---|---|---|
| `signup-login.yaml` | Request link → verify → land on MatchScreen | 1 |
| `match-and-call.yaml` | Both devices match, land on CallScreen, exchange chat | 2 |
| `report-block.yaml` | Report+block from an active call, call ends | 2 |

Single-device flow:

```powershell
maestro test maestro/signup-login.yaml -e API_BASE_URL=http://10.0.2.2:8000
```

Two-device flows need the wrapper script (see caveat in
`tasks/NEEDS-HUMAN-REVIEW-maestro-e2e.md` item 6 — Maestro CLI, as opposed to
Maestro Cloud, drives one device per invocation, so the wrapper just runs two
`maestro test` processes in parallel against two device serials):

```powershell
./maestro/run-two-device-flow.ps1 -FlowFile match-and-call.yaml -DeviceA emulator-5554 -DeviceB emulator-5556
```

```bash
./maestro/run-two-device-flow.sh match-and-call.yaml emulator-5554 emulator-5556
```

List available device serials with `adb devices` (Android) or `xcrun simctl list` (iOS — note CI here targets Android only, see scope).

## How magic-link sign-in works in these flows

Flows call `POST /auth/request-link` directly with header `X-Test-Mode: 1`
and read `debug_token` from the JSON response, then open
`drinkingbuddy://verify?token=<token>` via Maestro's `openLink` — no email
inbox involved. This only works when the backend is booted with
`ENVIRONMENT=development`; see `backend/docker-compose.e2e.yml` and
`app/routers/auth.py`. Never point these flows at a non-test backend — the
header alone does nothing there by design.

## CI

Runs nightly + on-demand via `.github/workflows/e2e-maestro.yml`, Android
only (see task's "Explicitly out of scope" — cross-platform parity isn't a
CI gate yet). Not run per-commit: simulator boot + two-device flows are
slow, matching this repo's E2E-is-pre-deploy testing-strategy convention.
