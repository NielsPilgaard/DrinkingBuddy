---
title: Drink counter (in-call)
status: pending
last_updated: 2026-08-15
---

## Goal

Let a user tap to tally how many drinks they've had during the current call. Lighthearted, not tracked/analyzed — reinforces the "having a drink together" framing (PRD §1).

## Scope

- New component `app/src/call/DrinkCounter.tsx`, self-contained: owns its own `count` state (starts at 0) and `Animated` value internally. `CallScreen` just mounts it, doesn't lift state up.
- Rendered as a floating badge, top-left of `CallScreen` (mirrors the local-video PiP at top-right, PIP; clear of chat/report/verify bottom sheets).
- Badge shows icon + count (e.g. "🍺 2"). Tap increments by 1.
- Icon reflects the user's own `drink_type` filter: 🍺 for `alcoholic`, 🥤 for `non_alcoholic`. Requires threading `drinkType` as a new prop: `MatchScreen` → `CallScreen` → `DrinkCounter` (today `MatchScreen`'s `DEFAULT_FILTERS.drink_type` isn't passed to `CallScreen` at all — add it).
- One-way increment only. No decrement/undo/reset control — mis-taps are accepted, this is a tally not a precise counter.
- On tap: small scale-pulse on the badge + a "+1" text that floats up and fades, via React Native's core `Animated` API. No new dependency (`react-native-reanimated`/lottie/moti are not in `app/package.json` — don't add them for this).
- State is **client-only and ephemeral** — no backend call, no persistence. Resets to 0 every new match (component unmounts with `CallScreen` at call end, per PRD §4.5 fully-ephemeral matches).

## Explicitly out of scope

- Persisting count server-side (per-user lifetime total, streaks, stats/profile screen) — no such concept exists elsewhere in the app; would require new DB column/migration/API endpoint.
- Showing the partner's count — self only. Would require a new signaling message relayed live through `useCall.ts`/the signaling server; real scope increase, not justified yet.
- Decrement/undo/reset interaction.
- Building the drink-type filter picker UI — `drink_type` stays hardcoded in `MatchScreen.DEFAULT_FILTERS` for now; this task only threads the existing hardcoded value down as a prop.

## Done when

- Tapping the badge on `CallScreen` increments the count and plays the pulse + "+1" animation.
- Badge icon matches the user's own `drink_type` (hardcoded value, threaded through).
- Starting a new call resets the count to 0 (no state survives `CallScreen` unmount).
- No backend/API changes.
