---
title: Task index
status: active
last_updated: 2026-10-19
description: >-
  Ordered list of open tasks with what each one waits on, plus a one-line
  index of completed tasks. Start here to pick the next task.
purpose: Entry point for tasks/; shows build order and blockers at a glance.
---

## TL;DR

**Next up: [05 — OVHcloud deploy](05-ovhcloud-deploy.md)**, with the human-only steps in [16](16-manual-launch-steps.md) done alongside it. Then [11 — CSAM runbook](11-csam-reporting.md) before any real users. Everything below the "Before public launch" line can wait.

Keep this file in sync when a task is added, finished (moved to `completed/`), or reprioritized.

## Open tasks, in order

| # | Task | Who | Waits on | Why this slot |
|---|---|---|---|---|
| 1 | [05 — OVHcloud deploy](05-ovhcloud-deploy.md) | human | 16 → "Deploy" | Repo side done (see task Progress). Left: buy domain + VPS, deploy, run the checks in `docs/deploy.md`. |
| 2 | [16 — Manual launch steps](16-manual-launch-steps.md) | human | — | Didit account/keys, Apple Developer + EAS, VPS firewall. Unblocks 05 (firewall), 15 (Didit) and iOS testing. |
| 3 | [11 — CSAM reporting runbook](11-csam-reporting.md) | human (legal) | — | Repo side done (backend case flow + [draft runbook](../docs/csam-runbook.md)). Left: counsel review, names, prod secrets, daily sweep. Needed before the invite pool goes live; must precede 07. |
| 4 | [15 — Age verification live test](15-age-verification-live-test.md) | agent | 16 (Didit keys) | Turns mock-tested Didit into verified. Video stays gated until then; audio/text work without it. |

### Before public launch (not blocking invite-only MVP)

| # | Task | Who | Waits on | Why this slot |
|---|---|---|---|---|
| 5 | [07 — AI nudity detection](07-ai-nudity-detection.md) | agent | 11, cost model | PRD §9 fast-follow: required before any public/scaled launch. |

### Post-MVP / non-Denmark only

| # | Task | Who | Waits on | Why this slot |
|---|---|---|---|---|
| 6 | [12 — Alcohol-marketing review (NO/SE)](12-alcohol-marketing-review.md) | human (legal) | — | Blocks Norway/Sweden only. Denmark is the only MVP market. |
| 7 | [13 — HydrationBuddy reskin](13-hydrationbuddy-reskin.md) | agent | 12, product-market fit in DK | Only if expanding to alcohol-restricted markets. |
| — | [08 — Post-MVP backlog](08-post-mvp-backlog.md) | — | — | Parking lot (PRD §13). Pull items into numbered tasks when prioritized. |

## Completed

In [`completed/`](completed/). Their frontmatter `status` fields are stale; being in `completed/` is what counts.

| Task | Summary |
|---|---|
| [01 — Scaffold repo](completed/01-scaffold-repo.md) | Backend + Expo skeletons, `/health` round trip. |
| [02 — Auth magic-link](completed/02-auth-magic-link.md) | Email magic-link accounts, no password. |
| [03 — Matching queue](completed/03-matching-queue.md) | Redis 1:1 pairing on MVP filters. |
| [04 — WebRTC signaling](completed/04-webrtc-signaling.md) | WebSocket signaling relay + coturn TURN creds. |
| [06 — Alembic migrations flow](completed/06-improve-alembic-migrations-flow.md) | Migrations run as their own compose service. |
| [06 — Report + block](completed/06-report-block.md) | Report/block + auto-suspend circuit breaker. |
| [07 — API codegen](completed/07-api-codegen.md) | Generated typed client from OpenAPI. |
| [09 — Monitoring](completed/09-monitoring.md) | Monitoring stack + pydantic settings. |
| [10 — Age verification](completed/10-age-verification.md) | Didit webcam gate (mock-tested; live test is 15). |
| [13 — Chat safety filters](completed/13-chat-safety-filters.md) | Keyword/pattern flagging of in-call chat. |
| [14 — Biometric relogin](completed/14-biometric-relogin.md) | Biometric/passcode gate on session restore. |
| [Drink counter](completed/beer-counter.md) | In-call drink tally. |
| [Ice-breaker](completed/ice-breaker.md) | Conversation-starter prompts. |
| [Mini-games](completed/mini-games.md) | Trivia, would-you-rather, never-have-I-ever. |
| [Mobile E2E (Maestro)](completed/mobile-e2e-maestro.md) | Two-device app-level E2E. |
