---
title: Report + block, auto-suspend
status: pending
last_updated: 2026-07-13
depends_on: tasks/04-webrtc-signaling.md, docs/prd.md
---

## Goal

MVP-required (PRD §9) reactive moderation: report + block button during/after every call, plus auto-suspend circuit breaker after N reports in a time window, pending manual review. Not deferred — this is a launch gate, not a nice-to-have.

## Scope

### Backend (`/backend`)
- `reports` table: reporter_id, reported_id, call_session_id, reason, created_at.
- `blocks` table: blocker_id, blocked_id, created_at — blocked users never matched together again.
- Auto-suspend rule: N reports (e.g. 3) against same user within time window (e.g. 24h) → suspend account (e.g. 24h), pending manual review. Configurable via `.env`.
- Suspended account: login/match blocked, clear error state to client.
- Manual review queue: minimal — flagged users listed somewhere queryable (DB query or basic admin endpoint), no full admin UI required at MVP.
- Endpoints: `POST /report` (during or after call), `POST /block`.
- Matching queue (task 03) must respect blocks: never pair two users who've blocked each other.

### Mobile app (`/app`)
- Report + block UI accessible during call and immediately after (e.g. on call-end screen), per PRD.
- Reason selection (simple category list, not free text required at MVP).
- Suspended-account state: clear message, no silent failure.

## Explicitly out of scope

- Proactive AI nudity/content detection — separate task (07-ai-nudity-detection.md), pre-public-launch not MVP-day-one.
- Full admin dashboard/UI for manual review — minimal queryable state only.
- Appeals process for suspensions.

## Done when

- User can report + block during an active call and immediately after it ends.
- 3rd report against same user within 24h auto-suspends that account for 24h.
- Suspended user cannot log in / enter matching queue during suspension.
- Two users who've blocked each other are never paired again by the matching queue.
