# AGENTS.md — DrinkingBuddy (working name)

Chat-roulette-style app, random 1:1 pairing for virtual hangout over a drink. iOS + Android MVP, browser later.

## Setup (fresh clone)

Prereqs: `uv`, Node `^20.19.4 || ^22.13 || ^24.3`, Docker (stack + integration tests only). Android dev build: JDK 17–21 (24+ breaks CMake configure) + Android SDK via `ANDROID_HOME`.

1. `./scripts/setup.sh` (bash) or `./scripts/setup.ps1` (pwsh 7). This creates `.env` files from `.env.example`, then runs `uv sync --extra dev` and `npm ci`. It's idempotent and never overwrites an existing `.env`.
2. Verify: `cd backend && uv run pytest tests/unit`, then `pwsh -File scripts/verify.ps1` (or the raw commands in `.claude/skills/verify/SKILL.md` if pwsh is missing).
3. Optional backend stack: `./scripts/setup.sh --up` / `./scripts/setup.ps1 -Up`. It picks `docker-compose.windows.yml` (json-file logs) when the host lacks the Loki Docker plugin. Then `curl localhost:8000/health` → 200.

Don'ts: don't `docker plugin install` on the user's behalf (host-level, needs `--grant-all-permissions`). Don't set `CHAT_SAFETY_FLAG_ENCRYPTION_KEY=` empty, because an empty value overrides the dev default. Don't use Expo Go: the app needs a dev build (`npx expo run:android|ios`) for `react-native-webrtc` and Didit.

## Docs map

- `docs/prd.md` — product spec, source of truth for scope/behavior.
- `docs/tech-stack.md` — stack decisions.
- `docs/local_dev.md` — local dev setup (dependency managers, running services outside Docker).
- `tasks/` — open task specs; `tasks/completed/` — done. `tasks/README.md` — ordered index, shows next task.
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

Deferred: gender filter, age-range filter, group/open-room (v1.1), browser client, notifications, monetization, proactive AI moderation (required pre-public-launch, not MVP), Nordic eID/EU wallet integration (not before 2027).

## Launch markets

**Denmark only at MVP.** Any expansion beyond Denmark is post-MVP and requires its own alcohol-marketing + age-verification legal check before adding — see PRD §3, §8, §9 (authoritative).

## Identity & safety

- Lightweight accounts required (email + OTP/magic-link, no password, no full-anon mode). Signup: 18+, self-declared birthdate, no verification tax (PRD §7, §8).
- Webcam access gated on real age verification (both matched parties), via **Didit** (selfie + liveness age estimation, CPR passthrough for DK) — audio/text stay open to any signed-up user, unverified or not. Details + cost-control (spend cap, waitlist-not-block, rate limits): `tasks/10-age-verification.md`, PRD §8.
- Reactive report+block during/after calls. Auto-suspend (e.g. 24h) after N reports in time window, pending manual review.
- Fast-follow before public launch: proactive AI nudity detection (frame sampling). Not MVP-day-one but must be roadmapped.
- CSAM detection is a separate legal/reporting workstream from report+block — `tasks/11-csam-reporting.md`, PRD §9.
- Alcohol-marketing law (Norway/Sweden) needs review before those markets go live — `tasks/12-alcohol-marketing-review.md`, PRD §9.

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
| Hosting | Single OVHcloud VPS, Docker Compose |
| Auth | OTP/magic-link only, no password (PRD §7) |
| Browser (later) | Plain React web client, same backend |
| Desktop (later, optional) | Tauri wrapper |

## Repo layout

- `/backend` — FastAPI app entrypoint, routers/, models/, Alembic migrations. Docker Compose runs API + Postgres + Redis + coturn. `GET /health` → 200.
- `/app` — Expo (React Native, TypeScript). `eas.json` present. MVP screen calls backend `/health` to prove connectivity.
- Root `README.md` documents local run steps for both.

Implemented: see `tasks/completed/` (auth, matching, WebRTC signaling + coturn TURN creds, report/block, age verification, chat safety, monitoring, mini-games). Deploy config (`docker-compose.prod.yml`, `docs/deploy.md`) exists but nothing is deployed yet — see `tasks/05-ovhcloud-deploy.md` (pending) for the actual go-live work.

## Conventions for agents working in this repo

- Treat `docs/prd.md` as authoritative for product behavior; `docs/tech-stack.md` for stack/infra choices. Don't re-derive decisions already settled there — link back instead of restating.
- Files under `docs/mockups/` are throwaway prototypes (see HTML comment headers), not implementation references for exact code structure.
- Task files in `tasks/` define scope boundaries explicitly (see "Explicitly out of scope" sections) — respect them, don't pull forward later-task work.
- Local dev setup (backend `uv` usage, running services outside Docker) — see `docs/local_dev.md`.
