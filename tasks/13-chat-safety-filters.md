---
title: Chat safety filters (keyword/pattern triggers)
status: pending
last_updated: 2026-07-23
depends_on: tasks/04-webrtc-signaling.md, tasks/06-report-block.md, docs/prd.md
---

## Goal

MVP-required (PRD §9) reactive text-chat safety net: server-side keyword/pattern matching over in-call text messages, flagging three risk categories for moderation review. Not ML/NLP — fixed pattern matching, fast to ship, good enough for launch-gate risk reduction.

## Scope

### Backend (`/backend`)
- Requires text chat to be server-relayed (see `tasks/04-webrtc-signaling.md` — deviation from pure-P2P WebRTC datachannel so the server can see plaintext).
- Pattern/keyword matcher run against every relayed text message, checking three trigger categories:
  1. **Meet-in-person proposals** — e.g. "skal vi mødes", "let's meet up", location-sharing intent.
  2. **Age-disclosure resolving under-18** — age-question pattern ("how old are you" / "hvor gammel er du") followed by an answer parsing to under 18.
  3. **External contact-info sharing** — social handles (Facebook, Instagram, Snapchat, etc.), phone numbers, other off-platform contact methods.
- On match: **silently flag** — write to the same moderation queue/store as report/block (`tasks/06-report-block.md`), including message content, call session id, both user ids, matched category, timestamp. No in-chat warning shown to either user, no auto-suspend triggered by a filter hit alone (keyword match has no context understanding — false positives expected, e.g. two adults discussing someone else's age).
- Config: keyword/pattern lists should be editable without a code deploy (e.g. DB table or config file), since language/slang patterns will need tuning post-launch.

### Mobile app (`/app`)
- No UI changes — filtering and flagging is entirely server-side and invisible to users.

## Explicitly out of scope

- ML/NLP-based moderation (e.g. OpenAI moderation API, AWS Comprehend) — fixed keyword/pattern matching only at MVP.
- In-chat warnings or nudges shown to users on a filter hit.
- Auto-suspend triggered directly by a filter hit (auto-suspend stays tied to report count, per `tasks/06-report-block.md`).
- Multi-language pattern coverage beyond Danish + English at launch (Denmark-only per PRD §3).

## Done when

- Text message containing a meet-in-person phrase, an age-reveal-under-18 exchange, or a shared contact handle/number gets flagged into the moderation queue with full context (message, users, call session, category, timestamp).
- No in-chat indication is shown to either user that a message was flagged.
- A filter hit alone does not trigger auto-suspend.
- Keyword/pattern lists can be updated without a code deploy.
