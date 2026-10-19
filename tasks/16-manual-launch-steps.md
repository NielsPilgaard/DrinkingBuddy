---
title: Manual setup steps (human-only)
status: pending
last_updated: 2026-10-18
depends_on: docs/deploy.md, tasks/05-ovhcloud-deploy.md
description: >-
  Account sign-ups, credentials and hardware steps an agent can't do: Didit
  account and keys, Apple Developer + EAS for iOS builds, and the firewall
  range for coturn. Each item lists what unblocks once it's done.
purpose: Checklist of human-only steps that block agent tasks.
---

## TL;DR

Agents can't create accounts, pay for programs, or run Xcode on this Windows machine. These steps unblock iOS testing (`app/app.json` now has `ios.bundleIdentifier`, and the iOS prebuild generates cleanly from Linux, but nothing has been compiled or run) and live age verification (`tasks/15-age-verification-live-test.md`).

## Didit (unblocks task 15)

- [ ] Create a Didit account. Set up two workflows: Age Estimation, and CPR passthrough for Denmark.
- [ ] Put these values in `backend/.env` locally and in the prod env later: `DIDIT_API_KEY`, `DIDIT_WEBHOOK_SECRET`, `DIDIT_AGE_ESTIMATION_WORKFLOW_ID`, `DIDIT_CPR_PASSTHROUGH_WORKFLOW_ID`.
- [ ] Point the Didit webhook at `https://api.<DOMAIN>/verify/webhook`, or at a tunnel URL for local testing.
- [ ] Set a spend alert in the Didit dashboard as a backstop to our own monthly cap.

## iOS

- [ ] Enroll in the Apple Developer Program ($99/yr). It's needed for any device build, TestFlight and the App Store.
- [ ] Register the bundle ID `com.drinkingbuddy.app` with the Associated Domains capability enabled.
- [ ] Create an Expo account and run `npx eas-cli login` (currently not logged in).
- [ ] Pick a way to test:
  - **Mac available:** `cd app && npx expo run:ios`. This builds locally and runs on the simulator or a plugged-in device. It's the fastest loop.
  - **No Mac:** `npx eas-cli build -p ios --profile development` builds in the cloud. Register test iPhones first with `npx eas-cli device:create`. This needs the Apple Developer account.
  - **No Mac, no Apple account (UI look only):** `npx eas-cli build -p ios --profile preview` makes a simulator build on the EAS free tier. Upload the `.app` to Appetize.io to click through it in a browser. The simulator has no real camera, so this won't show video.
- [ ] Smoke-test on a real iPhone: sign up via magic link, pick filters, match with an Android device, use audio, video (with verified users), chat, report and Face ID re-login.
- [ ] Magic links on iOS: host `https://app.drinking-buddy.app/.well-known/apple-app-site-association` with your Team ID and the bundle ID. Until then, use the `drinkingbuddy://` scheme.

## coturn relay ports (with task 05)

- [ ] Open `3478/udp+tcp` and the relay range in `backend/docker-compose.prod.yml` (`49152-50151/udp`) in the OVHcloud VPS firewall and host `ufw`. See `docs/deploy.md`.

## Done when

All boxes above are checked, or explicitly deferred with a note here.
