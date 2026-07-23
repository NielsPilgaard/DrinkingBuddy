---
title: PRD — DrinkingBuddy (working name)
status: draft
last_updated: 2026-07-23
owners: Niels (eng), Christian (vision/QA/marketing)
---

## TL;DR

Chat-roulette-style app that randomly pairs bored/lonely people for a virtual hangout over a drink. iOS + Android MVP (cross-platform framework), browser later. Core loop: instant random 1:1 video/audio/text match, optional filters (language, drink type, broad location), free skip, free to use. Lightweight accounts (18+, OTP/magic-link, self-declared birthdate), reactive report/block moderation with auto-suspend circuit breaker, proactive AI nudity detection required before public launch. Fully ephemeral matches — no friending, no history. North star metric: D7 retention.

---

## 1. Problem & premise

People get bored/lonely, want casual company and a drink, but going out is impractical. App recreates "having a beer with someone" virtually, via random pairing — like chat-roulette, but framed around drinking-as-social-ritual rather than dating or shock content.

## 2. Team

- **Niels** — engineering (this repo).
- **Christian** — vision, QA, marketing. Gets TestFlight (iOS) + Play Store internal testing track access from day one for hands-on build QA.

## 3. Platform strategy

- **iOS + Android simultaneously**, via cross-platform framework (React Native or Flutter — tech stack decision separate from PRD). No sequential single-platform launch: this is a matching app, splitting the pool by launching one platform first directly hurts match quality/wait time on both.
- **Browser/desktop**: explicitly deferred. Only worth doing early if a single cross-platform tech (app+web+desktop) with full webcam/mic control exists and is excellent — otherwise browser comes after mobile MVP is validated.

### Launch geography

- **Denmark only at MVP.** Norway and Sweden have anti-alcohol-promotion advertising laws (Alkoholloven / Alkohollagen) that create real legal exposure for an app framed around drinking-as-social-ritual — ruled out for initial launch, not "Nordics-first," not "later." Finland not included either — no legal review done for it yet, don't assume it's clear.
- Small single-country pool is an accepted tradeoff at MVP (matches existing PRD stance that early pool size is secondary to validating the core loop).
- Expanding to another country requires a per-country legal check on alcohol-marketing/advertising rules (and any local age-verification regulation, §8) before that market is added — not an assumed rollout. "Global"/multi-country is a post-PMF roadmap item, not a v1 target.

## 4. Core loop (MVP)

1. User opens app → optionally sets filters (see §5) → hits match.
2. **Instant connect**: no pre-connect/profile-glance screen. Paired user drops straight into a live session (video optional, audio optional, text chat always available).
3. Either party can **skip/next** at any time — free, unlimited, no cooldown, no penalty for skip-happy behavior at MVP. Matching-quality/anti-abuse signals (e.g. dedupe frequent skippers) are a later refinement, not an MVP gate.
4. **No call time limit.** Calls run as long as both stay connected — the whole point is an actual hangout, not speed-dating.
5. Call ends (either skip or explicit hangup) → **fully ephemeral**. No friending, no match history, no way to reconnect deliberately with the same person. Every match is stateless, like classic Chatroulette.

### Text chat

In-call text messaging ships in MVP alongside video/audio (same session, not a separate mode). Required because both camera and mic are optional — two users who leave both off need *some* channel to interact, otherwise it's two blank tiles doing nothing.

### Cold start / empty queue handling

If no match found within a timeout (~20-30s) under current filters, prompt user to **opt-in** widen search (e.g. "No one found nearby. Search all regions instead? [Yes/No]"). Never silently auto-widen — that breaks trust in filters the user explicitly set.

## 5. Matching filters (MVP scope)

Ship at MVP:
- **Language** (spoken language(s), self-declared)
- **Drink type** (alcoholic vs non-alcoholic — "what's in your hand")
- **Location** — broad only: self-declared country/region picker, **not** device GPS. Avoids location-permission friction on iOS/Android, avoids exposing precise whereabouts of strangers to each other (safety plus), and self-declared avoids fragmenting a small early pool the way precise-GPS proximity matching would.

**Explicitly deferred** (not MVP): gender filter, age-range filter. Both correlate strongly with turning this into a dating app — out of scope for "drinking buddy" premise — and further fragment an early, small matching pool.

## 6. Group / "open room" feature

**Deferred to v1.1, not MVP.** Letting a paired session open up for others to join at random is a second hard problem (N-way WebRTC/SFU media routing, multi-party moderation, more complex UI) layered on top of the 1:1 core loop, which is already the hardest part to get right (matching queue, WebRTC signaling, moderation, skip mechanic). Ship and validate 1:1 retention first.

## 7. Identity & accounts

- **Lightweight accounts required** — no fully-anonymous mode. Email or phone + OTP/magic-link, no password.
- Reasoning: pairing strangers on live video with alcohol involved needs *some* identity anchor from day one for safety/ban-evasion resistance, or the app inherits Omegle-style abuse/reputation problems immediately. Fully anonymous is much harder to retrofit trust/safety onto later.

## 8. Age gate

- **18+ only.**
- **Signup**: self-declared birthdate, no verification tax at account creation. Matches industry-standard MVP bar (e.g. Tinder) — keeps signup friction low.
- **Webcam access**: gated on real age verification, both matched parties must be verified before video unlocks for that pair. Audio + text remain available to any signed-up self-declared-18+ user, unverified or not (PRD §4 — video is optional, so this doesn't block the core loop). Reasoning: regulators (UK OSA, EU DSA) treat live video/image contact with strangers as the named high-risk surface — not audio or text — so verification cost/friction is concentrated exactly there. Tracked in `tasks/10-age-verification.md`.
- Verification vendor: **Didit** (Age Estimation product — selfie + liveness, ~$0.10/check, adaptive ID-verify fallback for borderline cases), plus CPR-register passthrough for Denmark. No per-country eID (MitID/BankID) integration at launch — cost was confirmed cheap (~$0.04-0.15/verification via Idura/Criipto) but ruled out as more integration investment than the team wants to take on now. Revisit Nordic eID and the EU's AltID/EUDI wallet (Danish pilot, ships spring 2026, not yet open to private relying parties) once mature — not before 2027.
- Mismatch handling: if either matched party is unverified, webcam stays off for both; unverified party gets an in-call prompt to verify.
- Cost control: hard monthly cap on verification-vendor spend with 50/80/100% budget alerts. Users who hit the cap go on a **waitlist** (not blocked/errored) and get a welcome email when next month's quota opens. Rate-limit verification attempts per-user and per-IP/device against bot abuse.

## 9. Moderation & safety

- **MVP**: reactive **report + block** button available during/after every call.
- **Enforcement mechanism**: **auto-suspend** (e.g. 24h) after N reports (e.g. 3) within a time window, pending manual review — not a pure manual-review queue. With no proactive detection at MVP, reports are the only signal; a 2-person team can't guarantee fast manual review, so an automatic circuit breaker is required to stop repeat bad actors between reports and human review.
- **Required fast-follow before public launch** (not MVP-day-one, but not "later, maybe" either): **proactive AI nudity/inappropriate-content detection** via frame sampling (e.g. AWS Rekognition or equivalent). This is the exact gap that got Omegle shut down and Chatroulette regulated — must be roadmapped explicitly, budgeted, and shipped before any public/scaled launch.
- **CSAM handling is a separate legal workstream from user-facing report/block.** When CSAM specifically is flagged (by report or, later, the AI detector), the company has its own mandatory-reporting duty (e.g. NCMEC, Danish straffelov) distinct from the auto-suspend circuit breaker above — needs its own incident-response runbook (evidence preservation minimums, reporting channel, do-not-locally-view policy). Tracked in `tasks/11-csam-reporting.md`.
- **Alcohol-marketing law note**: Norway (Alkoholloven §9-2) and Sweden (Alkohollagen) restrict alcohol marketing heavily enough that both are excluded from MVP launch entirely (§3), not just "needs review" — app name/branding/store listing would need dedicated legal review before either market could ever go live. Any future market beyond Denmark needs the same check before launch, not just these two. Tracked in `tasks/12-alcohol-marketing-review.md`.
- **Chat safety filters (MVP)**: server-side keyword/pattern matching over in-call text chat, checking for three trigger categories — (1) proposing to meet in person, (2) an age-disclosure exchange resolving to under-18, (3) sharing external contact info (social handles, phone number). A match silently flags the message + call/user context into the same moderation queue as report/block (§9 above) — no in-chat warning shown, no auto-suspend from a filter hit alone (avoids tipping off bad actors, avoids false-positive friction). Requires text chat to be server-relayed rather than pure P2P WebRTC datachannel, since the server must see plaintext to filter it — see `tasks/04-webrtc-signaling.md` note and `tasks/13-chat-safety-filters.md`.

## 10. Monetization

**Free entirely for MVP.** No paywall, no ads, no premium filters. Validate core loop retention with real usage data before deciding monetization shape (ads vs. subscription vs. paid filters) — adding payment infra now is pure scope tax on a pre-PMF product.

Note on call costs: video calls are not literally free infra-wise even though no per-user paywall exists. WebRTC P2P direct connection is near-free (tiny signaling traffic); ~15-20% of connections fall back to a TURN relay (NAT traversal failure) which does carry real bandwidth cost, scaling with call volume/duration. At MVP scale (cheap VPS, low volume) this is near-zero self-hosted (e.g. coturn) — becomes a real infra line item at scale. Tech stack decision, not PRD scope, but the cost floor is not zero.

## 11. Notifications

**None for MVP.** With no persistent matches (§4) and no social graph (§7 accounts are lightweight, not friend-graph), there's nothing meaningful to notify about yet. Revisit once retention data shows *when* users drop off.

## 12. Success metrics

- **North star: D7 retention.** Tells us if people come back for more hangouts — the actual product question ("do bored/lonely people make this a habit").
- **Secondary/diagnostic: average call duration.** Signals whether individual matches are good, but doesn't answer the habit-formation question alone.

## 13. Explicitly out of scope for MVP (parking lot)

- Browser/desktop client
- Group/open-room matching (v1.1)
- Gender and age-range filters
- Friending / match history / reconnect
- Push notifications
- Any monetization (ads, subscriptions, paid filters)
- Proactive AI moderation (required pre-public-launch, but not MVP-day-one)
- Precise GPS-based location matching
- Nordic eID (MitID/BankID/mobiilivarmenne) and EU AltID/EUDI wallet integration for age verification — revisit once mature (not before 2027), Didit covers verification at launch instead (§8)
- Markets outside Denmark — Norway/Sweden ruled out by alcohol-marketing law, others need per-country legal review before adding, see §3
