---
title: Ice-breaker conversation starter
status: pending
last_updated: 2026-08-15
depends_on: docs/prd.md (§4 text chat), docs/mockups/prototype-match-screen.html, tasks/completed/04-webrtc-signaling.md (chat transport)
---

## Goal

Give matched users a low-friction way to break silence. Especially relevant since video/audio are optional (PRD §4) — two blank-tile users need something to do besides stare at a skip button.

## Scope

- Static list of ~50-100 prompts, bundled client-side in `/app` (exact file TBD at implementation, e.g. `app/src/content/iceBreakers.ts`). Single flat array, no categories.
- Drawer button, alongside chat/mini-games/beer-counter actions (per `docs/mockups/prototype-match-screen.html` drawer pattern; `tasks/beer-counter.md` and `tasks/mini-games.md` are sibling drawer-action stubs — keep consistent with however those land).
- Tap posts a prompt as a message into the shared in-call text chat, visible to both matched users simultaneously (PRD §4 — text chat always-on). Not a private per-user overlay.
- Unlimited taps, no cooldown — same stance as skip/next (PRD §4.3).
- Client-side dedup: track shown-prompts in memory per call, don't repeat a prompt until the list is exhausted. Reset on new match (no persistence, consistent with fully-ephemeral-per-match PRD stance). Wrap back to full list once exhausted.
- Exempt from the `backend/app/chat_safety/` keyword/pattern pipeline (`tasks/completed/13-chat-safety-filters.md`) — content is pre-vetted/curated at build time, not arbitrary user input, so scanning it is redundant.
  - Goes through the server-relayed chat channel but skips the filter step (`backend/app/routers/signaling.py`), same channel as regular chat. Because this bypasses chat_safety, the server validates the `text` field against its own copy of the static prompt list (`backend/app/signaling/ice_breakers.py`) before relaying — a client can't use the `ice_breaker` message type to smuggle arbitrary freeform text past the filter.
- Prompt copy: seed a handful of examples in this file (below); full list authorship is a content deliverable, not blocking engineering scope, and can be split out separately.

### Seed examples

- "What's the most underrated drink you've ever had?"
- "Beach vacation or mountain cabin?"
- "What's a hobby you'd pick up if money/time weren't an issue?"
- "Dogs, cats, or neither?"
- "What's the last show you binged?"

## Explicitly out of scope

- LLM-generated/dynamic prompts. Deferred — revisit only if the static list feels stale post-launch.
- Server-hosted/editable prompt list — no backend endpoint, no DB table.
- Categorized/filter-tied prompts (by drink type, language, etc.) — scope creep for v1.
- Per-user rate limiting/cooldown.
- Routing prompt content through the chat-safety filter pipeline.

## Done when

- Drawer shows an ice-breaker action during any live call.
- Tapping it posts a random prompt into shared chat, visible to both matched users.
- Repeated taps don't show the same prompt twice until the list is exhausted for that call.
- New match resets the shown-prompts state.
- Works whether or not video/audio are on (chat is always available per PRD §4).
