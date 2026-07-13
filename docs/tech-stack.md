---
title: Tech Stack — DrinkingBuddy (working name)
status: draft
last_updated: 2026-07-10
owners: Niels (eng)
---

## TL;DR

Python (FastAPI) backend for API + WebRTC signaling, self-hosted coturn for TURN/STUN, Postgres + Redis, all on a single Hetzner VPS via Docker Compose. React Native (Expo) for iOS + Android MVP. Auth supports both OTP/magic-link and email+password. Browser client deferred but cheap to add later — plain React web app reusing the same backend, WebRTC is native to browsers.

---

## 1. Mobile app — React Native (Expo)

- **React Native**, not Flutter. Chosen over Flutter for WebRTC library maturity (`react-native-webrtc` has longer track record on codec/background-camera edge cases) and larger community for troubleshooting.
- **Expo** + EAS Build: enables iOS builds/TestFlight submission without owning Mac hardware, and Play Store internal track from the same pipeline. Matches PRD §2 requirement (Christian gets both tracks day one).
- Most app code (UI, navigation, state) doesn't require deep JS expertise — WebRTC is consumed via library calls, not built from scratch.

## 2. Backend — Python / FastAPI

Swapped from Node.js to Python per engineering preference. No meaningful capability loss for this workload — WebRTC signaling is plain message relay (JSON offer/answer/ICE candidates), not JS-specific.

- **API service**: FastAPI. Async native, auto-generated OpenAPI docs, handles accounts, filters, matching queue admin, report/block/auto-suspend logic.
- **Signaling server**: FastAPI + `websockets` (or same process as API, separate route) — relays WebRTC offer/answer/ICE between paired clients. Tiny traffic, no media flows through it.
- **DB**: Postgres — users, reports, suspensions, auth credentials.
- **Queue/matching state**: Redis — fast push/pop for matching queue, ephemeral by design (matches PRD's stateless match model).

## 3. Auth — OTP/magic-link AND email+password

Both supported from day one (cheap to add together, not worth doing as separate fast-follows):

- **Magic-link/OTP**: email-based (avoid SMS cost at MVP volume).
- **Email + password**: bcrypt/argon2 hashing, rate-limited login attempts, "forgot password" flow reuses magic-link email infra.
- No ID verification — self-declared birthdate per PRD §8.

## 4. WebRTC transport

- **STUN/TURN**: self-hosted **coturn** on the same VPS (or split to a second small VPS if load demands). Handles the ~15-20% of connections needing TURN relay (NAT traversal failure). Avoids per-minute fees from Twilio/Agora/Daily.co at MVP scale.
- P2P direct connection (no TURN) for the majority of calls — near-zero bandwidth cost.

## 5. Hosting — Hetzner VPS

- Single Hetzner VPS (e.g. CX22 or similar tier), Docker Compose running: FastAPI app, coturn, Postgres, Redis.
- Scale path: pull coturn and/or Postgres onto a second box when load demands — not needed at MVP.

## 6. Moderation infra

- MVP: report/block + auto-suspend logic lives in the FastAPI app against Postgres — no external service needed.
- Fast-follow (pre-public-launch, per PRD §9): proactive AI nudity detection (AWS Rekognition or equivalent) via frame sampling. Since WebRTC is P2P, this requires either routing media through an SFU or client-side frame capture + upload — a real architecture fork, not a bolt-on. Design this when the fast-follow is scheduled, not now.

## 7. Browser/desktop — deferred, path is cheap

No single stack unifies app+web+desktop with full webcam/mic control better than what's already true: **WebRTC is native in browsers** (`getUserMedia`, `RTCPeerConnection`, no library needed).

- **Browser**: plain React web client, hits the same FastAPI backend + signaling server. New frontend only, zero backend changes.
- **Desktop** (if an installable "laptop app" is wanted beyond a browser tab): wrap the same web client in **Tauri** (Rust-based, much lighter than Electron).
- Sequencing: mobile MVP ships first per PRD §3; browser client is additive later, not a rebuild.

## 8. Summary table

| Layer | Choice |
|---|---|
| Mobile | React Native (Expo, EAS Build) |
| Backend API | Python (FastAPI) |
| Signaling | FastAPI + websockets |
| DB | Postgres |
| Queue/matching state | Redis |
| TURN/STUN | Self-hosted coturn |
| Hosting | Hetzner VPS, Docker Compose |
| Auth | OTP/magic-link + email/password |
| Browser (later) | React web, same backend |
| Desktop (later, optional) | Tauri wrapper around web client |
