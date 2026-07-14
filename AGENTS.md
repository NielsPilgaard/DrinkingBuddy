# AGENTS.md — DrinkingBuddy (working name)

Chat-roulette-style app, random 1:1 pairing for virtual hangout over a drink. iOS + Android MVP, browser later.

## Docs map

- `docs/prd.md` — product spec, source of truth for scope/behavior.
- `docs/tech-stack.md` — stack decisions.
- `docs/local_dev.md` — local dev setup (dependency managers, running services outside Docker).
- `tasks/01-scaffold-repo.md` — current task: repo skeleton.
- `docs/mockups/prototype-match-screen.html` — throwaway UI mockup of in-call screen (full-bleed video + fly-in chat/menu drawer). Not production code.

## Core loop

1. Open app → optional filters → hit match.
2. Instant connect, no pre-connect screen. Video optional, audio optional, text chat always available.
3. Free unlimited skip/next, no cooldown, no penalty.
4. No call time limit.
5. Call ends → fully ephemeral. No friending, no history, no reconnect.

Cold start: no match within ~20-30s → prompt opt-in widen search. Never silent auto-widen.

## MVP filters

Language (self-declared), drink type (alcoholic/non-alcoholic), location (broad self-declared country/region, no GPS).

Deferred: gender filter, age-range filter, group/open-room (v1.1), browser client, notifications, monetization, ID-verified age gate, proactive AI moderation (required pre-public-launch, not MVP).

## Identity & safety

- Lightweight accounts required (email/phone + OTP/magic-link or email+password, no full-anon mode). 18+, self-declared birthdate, no ID check at MVP.
- Reactive report+block during/after calls. Auto-suspend (e.g. 24h) after N reports in time window, pending manual review.
- Fast-follow before public launch: proactive AI nudity detection (frame sampling). Not MVP-day-one but must be roadmapped.

## Success metric

North star: D7 retention. Secondary: avg call duration.

## Tech stack

| Layer | Choice |
|---|---|
| Mobile | React Native (Expo, EAS Build) — chosen over Flutter for `react-native-webrtc` maturity |
| Backend API | Python FastAPI (async, handles accounts/filters/matching/report-block) |
| Signaling | FastAPI + `websockets`, relays WebRTC offer/answer/ICE only, no media |
| DB | Postgres |
| Matching queue state | Redis (ephemeral) |
| TURN/STUN | Self-hosted coturn (~15-20% of calls need TURN relay) |
| Hosting | Single Hetzner VPS, Docker Compose |
| Auth | OTP/magic-link + email/password, bcrypt/argon2, both from day one |
| Browser (later) | Plain React web client, same backend |
| Desktop (later, optional) | Tauri wrapper |

## Repo layout (target, per tasks/01-scaffold-repo.md)

- `/backend` — FastAPI app entrypoint, routers/, models/, Alembic migrations. Docker Compose runs API + Postgres + Redis + coturn. `GET /health` → 200.
- `/app` — Expo (React Native, TypeScript). `eas.json` present. MVP screen calls backend `/health` to prove connectivity.
- Root `README.md` documents local run steps for both.

Current task scope is skeleton only: no auth, no matching/signaling logic, no Hetzner deploy, coturn not yet wired into an actual call.

## Conventions for agents working in this repo

- Treat `docs/prd.md` as authoritative for product behavior; `docs/tech-stack.md` for stack/infra choices. Don't re-derive decisions already settled there — link back instead of restating.
- Files under `docs/mockups/` are throwaway prototypes (see HTML comment headers), not implementation references for exact code structure.
- Task files in `tasks/` define scope boundaries explicitly (see "Explicitly out of scope" sections) — respect them, don't pull forward later-task work.
- Local dev setup (backend `uv` usage, running services outside Docker) — see `docs/local_dev.md`.
