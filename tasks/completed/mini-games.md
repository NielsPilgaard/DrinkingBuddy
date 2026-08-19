---
title: In-call mini-games (trivia, would-you-rather, never-have-I-ever)
status: pending
last_updated: 2026-08-15
depends_on: tasks/completed/04-webrtc-signaling.md, tasks/completed/13-chat-safety-filters.md, docs/prd.md
---

## Goal

Structured, repeatable in-call activities to give matched pairs something to do together beyond open-ended chat — three game types: trivia (multiple-choice, answer reveal, no scoring), would-you-rather, never-have-I-ever. Distinct from `tasks/ice-breaker.md` (bundled static prompt list with per-call dedup, no session/state) — mini-games are a structured, synced, multi-round activity.

## Scope

### Trigger & session model
- Entry point: "play game" button in the existing call drawer (`docs/mockups/prototype-match-screen.html`), available to either matched user regardless of video/audio toggle state (rides the always-on signaling channel, same as text chat).
- Starting a game **requires the other party to accept/decline** — a prompt shown before the game appears on their screen. Deliberate deviation from PRD §4's "no pre-connect friction" default: unlike the call itself, a game changes what's on someone's screen mid-conversation, so consent applies here even though it doesn't for the call/skip mechanic.
- Once accepted: open-ended session, one prompt at a time. Either party can advance ("next") or close the game entirely at any time — no fixed round count, no penalty, matches the free/unlimited-skip ethos (PRD §4).
- Game session state (current prompt, revealed/not, seen-prompt list) is in-memory, tied to the call session, and dies with it — no persistence, no history, consistent with PRD's fully-ephemeral match model. No new teardown logic needed: call-session teardown (`tasks/04-webrtc-signaling.md`) already tears down everything tied to the session.
- No-repeat-within-session: server excludes already-shown prompt IDs from the random pick for that call; resets every new call.

### Sync (backend)
- Game state changes (start, accept/decline, next, reveal) are relayed over the **existing signaling websocket** (`tasks/04-webrtc-signaling.md`) as a distinct message type from chat — structured control data (game type, prompt ID, action enum), not freeform text.
- These messages are **not** run through the chat-safety keyword/pattern filter (`tasks/13-chat-safety-filters.md`) — that filter scans freeform user-authored chat text; game-state messages carry no freeform input, so there's nothing for it to meaningfully match against.
- Both parties always see the same prompt/state at the same time — one party's "next"/"reveal" is authoritative and pushed to both, not tracked independently per client.

### Content sourcing
- **Trivia**: proxied server-side through [Open Trivia DB](https://opentdb.com) (opentdb.com) — free, no API key, CC BY-SA 4.0 licensed (requires attribution somewhere in-app, e.g. credits/about screen). Backend caches responses server-side rather than calling opentdb live per-round (their API asks for ~1 request per 5s per IP; don't hammer it from live traffic). Client gets question + 4 shuffled answer options from backend; reveal shows correct answer. No score tracked — reveal is just a talking point, not a quiz tally (keeps with ephemeral/no-persistent-state philosophy).
- **Would-you-rather** and **never-have-I-ever**: no solid canonical free API for either (WYR: only a thin unofficial GitHub-hosted API; NHIE: unofficial `api.nhie.io`, unknown size/reliability). Approach: **one-time scrape** of available free/open sources for both, into a **self-hosted static content bank** — no live runtime dependency on either third-party source.
  - Every scraped prompt set needs redistribution rights documented before shipping: source, license (or explicit permission from the source), attribution requirements if any, and provenance metadata (where each prompt came from). A manual human review pass (drop anything explicit/offensive/off-brand) is a content-quality step, not a substitute for this — reviewing a prompt for tone says nothing about whether it may be redistributed.
  - Bank is **backend-served** (DB or config table), not bundled into the app binary — same rationale as the chat-safety keyword lists (`tasks/13-chat-safety-filters.md`): lets content get tuned/expanded post-launch without an app store release cycle.

### Mobile app (`/app`)
- Game-picker UI in the call drawer, accept/decline prompt for the receiving party, prompt display + next/reveal/close controls.
- Trivia: render question + 4 answer buttons, reveal correct one on tap (no score UI).
- WYR/NHIE: render prompt text only, next/close controls.

## Explicitly out of scope

- Scoring/points/leaderboard for trivia or any other game — no persistent state, matches ephemeral-match philosophy.
- Fixed round counts or game "completion" states.
- LLM-generated content for any game type — `tasks/ice-breaker.md` uses a bundled static prompt list, not LLM generation either; not this task's pattern regardless.
- Live/runtime API calls to unofficial WYR/NHIE sources — one-time scrape only, baked into self-hosted static bank.
- Group/multi-party game modes (depends on `tasks/08-post-mvp-backlog.md` open-room work, not MVP 1:1 loop).
- Auto-suggesting games (e.g. after silence) — user-initiated only at MVP.

## Done when

- Either matched party can open the game drawer, pick trivia/WYR/NHIE, and the other party sees an accept/decline prompt.
- On accept, both clients show the same synced prompt; either party's next/reveal/close action updates both screens identically.
- Trivia questions/answers are served from a backend-cached proxy of opentdb.com, with CC BY-SA attribution present somewhere in-app.
- WYR and NHIE prompts are served from a self-hosted, manually-reviewed static content bank (backend-served, editable without app deploy) — no live dependency on third-party WYR/NHIE sources.
- No prompt repeats within the same call session.
- Game works identically regardless of video/audio toggle state.
- Game-state messages are confirmed to bypass the chat-safety keyword filter (verified as a distinct, non-freeform message type on the signaling channel).
- Call end (either side) tears down game state with no orphaned state, no history retained.
