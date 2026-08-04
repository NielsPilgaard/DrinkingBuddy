---
title: Matching queue
status: pending
last_updated: 2026-07-13
depends_on: tasks/02-auth-magic-link.md, docs/prd.md
---

## Goal

Pair authenticated users 1:1 based on MVP filters, using Redis as ephemeral queue state. Produces a "matched" event with both user IDs — actual call connection (signaling) is a separate task.

## Scope

### Backend (`/backend`)
- Redis-backed queue: user enters queue with filter set (language, drink type, location).
- Matching logic: pair two compatible users (matching filters), remove both from queue, emit match result.
- Filter compatibility rules per `docs/prd.md` MVP filters (language self-declared, drink type alcoholic/non-alcoholic, location broad self-declared region).
- Cold-start handling: no match within ~20-30s → return "widen search?" prompt to client (opt-in, not silent auto-widen, per PRD).
- Skip/next: user can leave current match and re-enter queue immediately, no cooldown, no penalty.
- Endpoint(s) or websocket channel for: join queue, leave queue, receive match result, skip.

## Explicitly out of scope

- WebRTC signaling (offer/answer/ICE relay) — next task, consumes the match result this task produces.
- coturn / TURN relay wiring — folded into signaling task.
- Group/open-room matching (v1.1, deferred per PRD).
- Gender/age-range filters (deferred per PRD).
- Report/block logic during active match.

## Done when

- Two clients with compatible filters joining the queue get paired within seconds.
- Incompatible filters correctly prevent pairing.
- No match after ~20-30s triggers widen-search prompt, not silent auto-widen.
- Skip immediately requeues a user with no cooldown/penalty.
- Queue state fully clears on disconnect (no ghost entries in Redis).
