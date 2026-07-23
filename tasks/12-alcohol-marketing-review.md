---
title: Alcohol-marketing law review (Norway/Sweden)
status: pending
last_updated: 2026-07-23
depends_on: docs/prd.md
---

## Goal

Legal review, not engineering work: Norway (Alkoholloven §9-2) bans alcohol advertising near-totally — broad enough scope to plausibly cover anything read as promoting alcohol use, not just brand ads. Sweden (Alkohollagen) restricts alcohol marketing too. App's premise/branding ("hangout over a drink", name "DrinkingBuddy", drink-type filter per PRD §5) creates exposure specifically for the app's public-facing framing (name, store listing, marketing copy) — separate question from the in-app drink-type filter itself, which is personal-use context, not marketing.

Blocks Norway/Sweden going live (PRD §3, Nordics-first launch) — not a blocker for Denmark or Finland, which don't have the same near-total ad-ban framing.

## Scope

### Legal input (not code)
- Get local counsel read (Norwegian + Swedish) on whether:
  - App name ("DrinkingBuddy" or whatever it ships as) counts as alcohol marketing under Alkoholloven/Alkohollagen.
  - App store listing copy/screenshots count as marketing (public-facing, higher risk) vs. in-app drink-type filter (personal-use context inside an already-installed app, likely lower risk but confirm).
  - General marketing/acquisition copy (social ads, App Store optimization keywords, website) for NO/SE specifically.
- Determine if this requires: renaming for NO/SE listings, de-emphasizing alcohol framing in marketing copy while keeping the drink-type filter functional, or something else.

### Product (once legal input lands)
- If de-emphasis is required: adjust NO/SE-specific app store listing copy, marketing materials, possibly localized app name/tagline. Scope this out once legal answer is in — don't build ahead of the legal read.

## Explicitly out of scope

- Changing the drink-type filter functionality itself (PRD §5) — this task is about branding/marketing exposure, not the filter feature.
- Denmark/Finland-specific review — not flagged as having the same near-total ad-ban framing as NO/SE, revisit only if that assumption turns out wrong.

## Done when

- Written legal opinion (Norwegian + Swedish counsel) on app name/branding/store-listing exposure under Alkoholloven §9-2 and Alkohollagen.
- Decision made: ship as-is in NO/SE, or adjust branding/copy — documented here or in PRD.
- If adjustment needed: NO/SE-specific store listing and marketing copy updated before those markets go live.
