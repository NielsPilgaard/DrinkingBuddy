---
title: Mobile E2E (Maestro)
status: pending
last_updated: 2026-08-15
---

## Goal

Full-stack E2E covering the actual Expo app UI, not just the backend HTTP/WS surface. `backend/tests/integration/test_call_flow_e2e.py` already chains signup -> match -> signaling -> report/block at the API level (two real websocket clients, real Postgres/Redis via testcontainers) — this task is the layer above that: two real app instances (simulator/emulator or device) tapping through the actual screens against a running backend.

## Why Maestro over Detox

Maestro drives via accessibility tree + YAML flows, no native test-target wiring into the Expo build, works against both a dev build and a release build. Detox needs a custom native build config per platform and is heavier to keep green. Given this repo's MVP stage and single-VPS deploy target, Maestro's lower setup cost wins.

## Scope

- `maestro/` dir at repo root, one YAML flow per journey:
  - `signup-login.yaml` — request magic link (deep link captured via `maestro studio` or a test-only endpoint that returns the token instead of emailing it), verify, land on `MatchScreen`.
  - `match-and-call.yaml` — two devices/simulators in parallel (Maestro supports multi-device flows), both hit "find match", assert both land on `CallScreen`, exchange a chat message, assert it appears on the peer's screen.
  - `report-block.yaml` — from an active call, open `ReportBlockSheet`, submit a report, assert call ends and returns to `MatchScreen`.
- Needs a real backend instance reachable from the simulator/device (local Docker Compose stack, per `docs/local_dev.md`) — not the in-process ASGI transport the pytest suite uses.
- Magic-link capture problem: production flow emails a deep link. Either (a) add a test-only backend flag that echoes the token in the API response when a header like `X-Test-Mode` is set (guarded so it can never be enabled outside local/CI config), or (b) point the test backend at a fake mail sink (e.g. Mailhog) and scrape it. Decide which before implementing — (a) is far less infra to stand up.
- CI: run on a schedule or pre-release, not per-commit — simulator boot + two-device flows are slow (minutes), matches the "E2E ... pre-deploy, not on every commit" guidance in this repo's testing-strategy conventions.

## Explicitly out of scope

- Real WebRTC media assertions (actual video frames flowing) — Maestro can't inspect `RTCView` pixel content meaningfully; the API-level E2E already proves signaling relay works, and real media is coturn/network-dependent, not something to gate CI on.
- Cross-platform parity runs (iOS + Android every run) — pick one platform for CI, run the other manually pre-release, until this becomes a pain point.
- Replacing `backend/tests/integration/test_call_flow_e2e.py` — that stays as the fast, deterministic flow check; this is the slower UI-truth layer on top.
