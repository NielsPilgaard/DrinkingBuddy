---
title: HydrationBuddy reskin (alcohol-restricted markets)
status: pending
last_updated: 2026-07-24
depends_on: tasks/12-alcohol-marketing-review.md, docs/age-verification-legal-review-no-se.md (not yet created), docs/prd.md
---

## Goal

Non-alcohol-branded reskin of the app for markets where alcohol-marketing law blocks the "DrinkingBuddy" framing (Norway/Sweden, per `tasks/12-alcohol-marketing-review.md`). Same product, same backend, same core loop (PRD §4) — different name/branding/store listing, drink-type filter reframed or dropped depending on what task 12's legal read requires.

Not a new product. A reskin: one codebase, market-specific branding layer. Revisit only if DrinkingBuddy hits product-market fit in Denmark (PRD §13/`tasks/08-post-mvp-backlog.md`) — not worth building before that's proven.

Two independent legal blockers gate NO/SE launch, not one: alcohol-marketing law (`tasks/12-alcohol-marketing-review.md`) and age-verification law (webcam-gate legal basis for a new market — a **separate** written legal opinion, not covered by `tasks/10-age-verification.md`, which is engineering only and doesn't establish legal sufficiency for NO/SE). Both must land before this reskin ships; neither substitutes for the other.

## Scope

### Product / branding
- New name ("HydrationBuddy" working title), logo, app store listing copy, marketing copy for NO/SE — scoped once task 12's legal opinion lands (don't guess at what needs changing before that answer exists).
- Decide: does the drink-type filter (PRD §5, alcoholic/non-alcoholic) stay functional but unmarketed, get relabeled, or get dropped entirely for this variant — depends on task 12's read on what counts as "marketing" vs. in-app personal-use context.

### Engineering
- Same backend, same matching/signaling/moderation — no new infra. This is a client-side branding/config layer (app name, icon, copy strings, possibly a build-time flag or separate Expo app config) plus separate app store listings for NO/SE.
- Confirm whether NO/SE users on this variant match into the same pool as Denmark's "DrinkingBuddy" users, or a separate pool — likely same backend matching queue regardless of client branding, since the underlying product/core loop is identical (PRD §4). Decide explicitly, don't assume.

## Explicitly out of scope

- Any product/feature divergence from the Denmark MVP — this is branding only, not a second product.
- Building this before task 12's legal review lands, before the age-verification legal review for NO/SE lands, or before Denmark MVP shows product-market fit (PRD §13 backlog gate).

## Done when

- Task 12 legal review has landed and specifies what branding/copy must change for NO/SE.
- A dedicated age-verification legal review for NO/SE has landed (written opinion confirming the Didit-based webcam gate, task 10, is legally sufficient for launching video contact between strangers in Norway/Sweden) — `tasks/10-age-verification.md` alone does not satisfy this; it must explicitly contain or link the legal approval to count.
- Decision made and documented: shared matching pool vs. separate pool for this variant's users.
- Separate app store listing(s) live for NO/SE under the new name/branding, same backend.
