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
- Identify which mandatory-reporting regimes actually apply given the launch footprint (MVP Denmark, plus any prospective future markets per PRD §3) and any US-based infra/vendor nexus (e.g. if any US cloud service touches this data path) — confirm with counsel, don't assume.
- Define an incident-response runbook: what to preserve (minimum necessary evidence only — do not over-retain), who reports it and to whom (NCMEC, Danish authorities, other national bodies), what the internal escalation path is when a report or (later) task 07's detector flags CSAM specifically vs. generic nudity/inappropriate content.
- Explicit **do-not-locally-view** policy: define who (if anyone) at the company is authorized to view flagged content, and under what constraints — mishandling this internally can itself create legal exposure.

### Backend (`/backend`)
- Distinguish "CSAM suspected" from generic nudity-report categories in the report/flag data model (task 06's `reports` table or a new flag) — needs its own escalation path, not lumped into the standard 3-reports-in-24h auto-suspend flow.
- Evidence retention: minimal, time-boxed, access-controlled storage for what's legally required to preserve — not indefinite, not broadly accessible. Concretely: encrypted at rest and in transit; access restricted to the narrow authorized set defined in the runbook's do-not-locally-view policy; all access logged/audited; explicit retention window with a deletion deadline (per counsel's legally-required minimum, not indefinite); legal-hold override that pauses scheduled deletion only while a hold is active and resumes normal deletion once lifted.

## Progress

Repo side done (2026-10-24). Left: human/legal work below.

- Runbook drafted: [`docs/csam-runbook.md`](../docs/csam-runbook.md). Covers triggers, authorized set, do-not-view policy, escalation steps, where to report, retention, and the candidate legal regimes plus US-nexus inventory.
- Report reason `csam` ("Sexual content involving a minor") opens a `csam_cases` row with an encrypted evidence snapshot and a precautionary suspension (`CSAM_SUSPENSION_HOURS`), and emails `CSAM_ONCALL_EMAIL` the case id. The report still counts toward task 06's breaker.
- Chat-safety moderators can escalate a flag: `POST /moderation/chat-safety/flags/{id}/escalate-csam`.
- `/moderation/csam/*` uses its own secret plus `X-Actor`, and every action goes to `csam_audit_log`. Supports report (sets legal hold), dismiss (lifts suspension) and legal hold on/off.
- Retention: `purge_expired_cases` deletes after `CSAM_EVIDENCE_RETENTION_DAYS` unless a hold is on.
- App: new reason in the report sheet, with a "don't screenshot or record" hint.

**Still open (human):**
- Counsel reviews runbook §7 and answers §9. Then fix the retention days, the suspension length and the reporting channel, and drop "draft".
- Fill in the names in runbook §3. Set the `CSAM_*` secrets in prod env.
- Schedule `purge_expired_cases` daily at deploy (no scheduler exists yet; same gap as the chat-safety sweep). Task 05.

## Explicitly out of scope

- Full CSAM-grade automated detection pipeline — that's task 07's concern (nudity/inappropriate-content detection generally); this task is the reporting/response duty once something is flagged, by any means.
- Building an internal content-review team/tooling beyond the minimal runbook — small-team reality, keep this lean.

## Done when

- Runbook document exists: what counts as CSAM-suspected, who reports it, where, what's preserved, who (if anyone) may view it.
- Legal regimes applicable to MVP Denmark plus any prospective markets (+ any US nexus) are identified and cited in the runbook, confirmed against actual counsel input, not assumed.
- Backend can flag a report as CSAM-suspected distinct from generic categories, routing to the runbook's escalation path instead of (or in addition to) task 06's auto-suspend.
- This ships before task 07 (AI nudity detection) goes live on real traffic.
