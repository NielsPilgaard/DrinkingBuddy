---
title: CSAM mandatory-reporting runbook
status: pending
last_updated: 2026-07-23
depends_on: tasks/06-report-block.md, docs/prd.md
---

## Goal

Legal duty, distinct from user-facing report/block (task 06): when CSAM (child sexual abuse material) specifically is flagged — by a user report or, later, the AI nudity detector (task 07) — the company itself has mandatory-reporting obligations (e.g. NCMEC if there's a US nexus, Danish straffelov obligations, EU CSAM regulation). This is not the same as the auto-suspend circuit breaker in task 06, which handles the user-facing consequence; this task handles what the *company* must do once CSAM is suspected.

Needs to exist before task 07 (AI nudity detection) ships to any real traffic, since that's when the company first has technical capability to detect this at scale — but the reporting duty applies to user-reported CSAM today, independent of task 07's timeline.

## Scope

### Legal / process (not pure engineering — needs input beyond this repo)
- Identify which mandatory-reporting regimes actually apply given launch markets (DK/SE/NO/FI, PRD §3) and any US-based infra/vendor nexus (e.g. if any US cloud service touches this data path) — confirm with counsel, don't assume.
- Define an incident-response runbook: what to preserve (minimum necessary evidence only — do not over-retain), who reports it and to whom (NCMEC, Danish authorities, other national bodies), what the internal escalation path is when a report or (later) task 07's detector flags CSAM specifically vs. generic nudity/inappropriate content.
- Explicit **do-not-locally-view** policy: define who (if anyone) at the company is authorized to view flagged content, and under what constraints — mishandling this internally can itself create legal exposure.

### Backend (`/backend`)
- Distinguish "CSAM suspected" from generic nudity-report categories in the report/flag data model (task 06's `reports` table or a new flag) — needs its own escalation path, not lumped into the standard 3-reports-in-24h auto-suspend flow.
- Evidence retention: minimal, time-boxed, access-controlled storage for what's legally required to preserve — not indefinite, not broadly accessible.

## Explicitly out of scope

- Full CSAM-grade automated detection pipeline — that's task 07's concern (nudity/inappropriate-content detection generally); this task is the reporting/response duty once something is flagged, by any means.
- Building an internal content-review team/tooling beyond the minimal runbook — small-team reality, keep this lean.

## Done when

- Runbook document exists: what counts as CSAM-suspected, who reports it, where, what's preserved, who (if anyone) may view it.
- Legal regimes applicable to DK/SE/NO/FI (+ any US nexus) are identified and cited in the runbook, confirmed against actual counsel input, not assumed.
- Backend can flag a report as CSAM-suspected distinct from generic categories, routing to the runbook's escalation path instead of (or in addition to) task 06's auto-suspend.
- This ships before task 07 (AI nudity detection) goes live on real traffic.
