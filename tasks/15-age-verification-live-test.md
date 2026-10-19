---
title: Age verification — live Didit test
status: pending
last_updated: 2026-10-18
depends_on: tasks/completed/10-age-verification.md, tasks/16-manual-launch-steps.md
description: >-
  Exercise the task-10 Didit integration against real Didit (not mocks) once
  an API key exists, and remove the hand-verified local test users. Low
  priority: video gating can wait until the manual Didit setup is done.
purpose: Follow-up that turns the mock-tested Didit integration into a verified one.
---

## TL;DR

Task 10 shipped with unit/integration tests against a mocked Didit. Nobody has run it against the real service: there's no Didit key locally, so "Verify now" fails with "Could not start verification." To test video, three local test users were marked verified directly in the `verifications` table. Blocked on the Didit account in `tasks/16-manual-launch-steps.md`.

## Scope

- With real `DIDIT_*` values in `backend/.env`, run the in-app flow on an Android dev build: tap "Verify now", complete selfie + liveness, confirm the webhook lands and `GET /verify/status` flips to `verified`.
- The webhook needs a public URL. Use a tunnel (cloudflared/ngrok) to the local API, or run this against the deployed stack once `tasks/05-ovhcloud-deploy.md` is done.
- Check the CPR passthrough workflow with a Danish test identity if Didit's sandbox offers one. Otherwise note it as untested.
- Check a failed/under-18 result keeps video locked.
- Confirm the real webhook signature passes our validation (the mocked tests only prove we reject bad ones).
- Run the cap/waitlist path once with a lowered `VERIFICATION_MONTHLY_CAP` against real Didit.
- Fix anything the live run surfaces, e.g. payload shape differences from the mocks.
- Delete the hand-inserted `verifications` rows for the local test users so the gate reflects real state again.

## Explicitly out of scope

- iOS run of the Didit SDK. That rides on the iOS build in `tasks/16-manual-launch-steps.md`. Do it there if a Mac is available, otherwise as a separate pass.
- Changing vendor, cap or pricing decisions (PRD §8).

## Done when

- One real end-to-end verification on Android flips a user to `verified` via the real webhook, and two such users get video.
- Real webhook signatures validate; failed results keep video locked.
- No hand-verified rows left in the local DB.
