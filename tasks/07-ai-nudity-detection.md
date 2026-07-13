---
title: Proactive AI nudity/content detection
status: pending
last_updated: 2026-07-13
depends_on: tasks/06-report-block.md, docs/prd.md
---

## Goal

Proactive frame-sampling nudity/inappropriate-content detection on live calls. PRD §9: required fast-follow **before public launch**, not MVP-day-one — this is the gap that got Omegle shut down. Must be roadmapped, budgeted, shipped before any public/scaled launch, but not blocking initial MVP ship to a small/invite pool.

## Scope

### Backend / infra
- Frame sampling approach: pull periodic frames from active call streams (needs media access — likely via SFU/relay tap or client-side sampled upload, since current WebRTC path (task 04) is P2P and server doesn't see media by default. This is an architecture decision to make explicitly in this task, not assumed.
- Integration with a detection API (e.g. AWS Rekognition or equivalent — vendor choice TBD in this task).
- Action on positive detection: auto-flag, auto-suspend, or auto-terminate call — decide threshold/response in this task, tie into auto-suspend mechanism from task 06.
- Budget/cost consideration: per-frame API cost scales with call volume/duration — needs a cost model before shipping, not just a feature flag.

## Explicitly out of scope

- This task does not need to ship for MVP-day-one launch to a small/invite pool.
- Full CSAM-grade detection pipeline — scope is nudity/inappropriate content per PRD framing, not a compliance-grade system (revisit if legal requirements demand more).

## Done when

- Architecture decision made + documented for how server gets frame access given P2P WebRTC (task 04).
- Detection API integrated, sampling live call frames at a defined interval.
- Positive detection triggers a defined action (flag/suspend/terminate), tied into task 06 auto-suspend.
- Cost-per-call-hour estimated and documented before this ships to any public/scaled traffic.
