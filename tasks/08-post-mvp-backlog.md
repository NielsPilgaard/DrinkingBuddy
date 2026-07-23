---
title: Post-MVP backlog
status: pending
last_updated: 2026-07-13
depends_on: docs/prd.md
---

## Goal

Tracking file for PRD §13 parking-lot items — explicitly out of scope for MVP, not yet scoped enough to be standalone build tasks. Pull an item out into its own numbered task file when it's actually prioritized; check it off here once that happens (don't duplicate detail in both places).

## Backlog

- [ ] Gender filter — deferred, correlates with turning app into dating app per PRD §5.
- [ ] Age-range filter — deferred, same reasoning as gender filter.
- [ ] Group / "open room" matching (v1.1) — N-way WebRTC/SFU media routing, multi-party moderation. Ship after 1:1 retention validated (PRD §6).
- [ ] Browser/desktop client — only worth doing early if a single cross-platform tech with full webcam/mic control is excellent; otherwise after mobile MVP validated (PRD §3).
- [ ] Push notifications — nothing meaningful to notify about until retention data shows drop-off points (PRD §11).
- [ ] Monetization (ads / subscriptions / paid filters) — validate retention first, no payment infra pre-PMF (PRD §10).
- [ ] Precise GPS-based location matching — self-declared region chosen deliberately for safety + avoiding early-pool fragmentation (PRD §5); revisit only with real scale.
- [ ] Nordic eID (MitID/BankID/mobiilivarmenne) and EU AltID/EUDI wallet integration for age verification — not before 2027, Didit covers verification at launch instead (`tasks/10-age-verification.md`, PRD §8).
- [ ] Markets outside Denmark — Norway/Sweden ruled out by alcohol-marketing law, others need per-country legal review before adding (PRD §3). Not "Nordics-first" — MVP is Denmark-only.
- [ ] Non-alcohol variant ("HydrationBuddy") for markets with alcohol-advertising restrictions (Norway/Sweden) — revisit only if DrinkingBuddy hits product-market fit.

## Explicitly out of scope

- Friending / match history / reconnect — not backlog, permanently ruled out by core loop design (PRD §4: "fully ephemeral... no way to reconnect deliberately with the same person"). Do not resurrect without a product decision reversing that.
