---
title: Age verification — webcam gate
status: pending
last_updated: 2026-07-23
depends_on: tasks/02-auth-magic-link.md, tasks/03-matching-queue.md, docs/prd.md
---

## Goal

Real age verification gating webcam access, per PRD §8. Signup stays self-declared-birthdate-only (task 02, unchanged) — this task only affects when video is allowed to turn on for a matched pair. Audio and text are unaffected and remain available to any signed-up user.

Driven by launch-market law (UK OSA, EU DSA treat random stranger video contact as high-risk, self-declared birthdate alone doesn't clear the bar) — not by MVP scope creep. See PRD §3, §8.

## Scope

### Backend (`/backend`)
- `verifications` table: user_id, status (pending/verified/failed/revoked), method (age_estimation/cpr_passthrough), verified_at, expiry (if any), revoked_at (nullable — authoritative revocation marker; a non-null value means the row can never count as verified again, regardless of `status`).
- Didit integration: Age Estimation product (selfie + liveness) as default method; adaptive fallback to Didit's ID-verification for borderline cases; Denmark uses Didit's CPR-register passthrough instead of Age Estimation.
- Webcam-gate check: when a match is formed (task 03) or video is toggled on, both parties are re-evaluated fresh against the full predicate — `status = verified` AND not expired (if `expiry` set, `now < expiry`) AND `revoked_at IS NULL` — on every match/toggle gate evaluation, not just checked once at initial verification. If either party fails the predicate, video stays unavailable for the session.
- Cost control:
  - Hard monthly cap of 500 Didit verification calls, config via `.env`. Caps only Didit spend — signup/account creation stays uncapped and unaffected.
  - Budget alerts at 50%/80%/100% of cap (log/notify — exact channel TBD in this task, e.g. email to team).
  - When cap is hit: new verification requests do **not** error/block — user is added to a `verification_waitlist` table instead, gets a welcome-back email when next month's quota opens (don't hard-fail the user experience over a billing ceiling).
  - Rate-limit verification attempts: per-user (e.g. max N attempts before cooldown) **and** per-IP/device (catches bot-farm abuse creating many accounts to burn quota).
- Endpoints: `POST /verify/start` (kicks off Didit flow), webhook/callback to receive Didit result, `GET /verify/status`. `start`/`status` operate on the authenticated caller's own user id only (never a client-supplied user id). Webhook must verify Didit's signature, be replay-protected (reject/no-op already-processed callbacks), and update verification status idempotently — a forged, replayed, or cross-account callback must not be able to alter another user's verification state.

### Mobile app (`/app`)
- Webcam toggle: if either party unverified, toggle shows disabled state.
- In-call prompt on toggle attempt when unverified: "Verify your age to enable video" with deep-link into Didit verification flow (Didit has a React Native SDK — use it, not a custom camera/upload flow).
- Waitlisted state: clear messaging, not an error — "You're on the list, we'll email you."

## Explicitly out of scope

- Nordic eID (MitID/BankID/mobiilivarmenne) or EU AltID/EUDI wallet integration — priced out as more integration investment than justified right now (Idura/Criipto quote was cheap, ~$0.04-0.15/verification, but still a build the team isn't taking on). Revisit no earlier than 2027 per `tasks/08-post-mvp-backlog.md`.
- Verification for audio or text chat — video-only gate per PRD §8.
- Building a custom/self-hosted "wallet" or ZKP age-assertion system — not legally equivalent to a government-issued EUDI wallet, not worth the build.
- Admin UI for reviewing verification failures/waitlist — minimal queryable state only, same bar as task 06.

## Done when

- Signup remains unchanged (self-declared birthdate only, task 02).
- Matched pair with both parties verified can enable webcam; either-unverified pair cannot.
- Unverified user attempting to enable webcam gets a working Didit verification flow (Age Estimation, or CPR passthrough for DK-registered users).
- Monthly Didit spend cap is enforced; 50/80/100% alerts fire correctly (test via lowered cap in a non-prod environment).
- Users who hit the cap land on the waitlist, not an error state, and are queued for next-month verification + welcome-back email.
- Per-user and per-IP/device rate limiting on verification attempts is in place and tested against a simple abuse simulation (rapid repeated attempts).
- Didit webhook signature validation is enforced and tested (unsigned/forged payloads rejected).
- Webhook processing is idempotent — replaying the same callback does not double-apply or corrupt verification state.
- Verification expiry and revocation are handled: an expired or revoked verification no longer counts as `verified` for the webcam gate.
- Stale/cached verification status cannot be used to unlock video — status is checked fresh (or against a bounded-freshness cache) at match/toggle time, not just once at initial verification.
- Server enforces that both currently matched parties are verified at the moment video is negotiated, not just at some earlier point — re-checked if the pairing changes.
