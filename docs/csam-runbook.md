---
title: CSAM incident-response runbook
status: draft (awaiting counsel review)
last_updated: 2026-10-24
description: >-
  What DrinkingBuddy does when child sexual abuse material (CSAM) is suspected:
  what triggers a case, who handles it, who it is reported to, what evidence is
  kept and for how long, and who may look at it. Legal regimes listed here are
  candidates until counsel confirms them.
purpose: Operational source of truth for the company's CSAM reporting duty (tasks/11-csam-reporting.md, PRD §9).
---

# CSAM incident-response runbook

## TL;DR

- A user report with reason **"Sexual content involving a minor"** (`csam`), or a moderator escalating a chat flag, opens a **CSAM case** automatically. The reported user is suspended at once and on-call gets an email with the case id.
- An authorized person triages within **24 hours**, using the audited `/moderation/csam` API. When in doubt, **report to Danish police**, then record their journal number. Dismiss only clearly bogus reports.
- **Nobody at the company views, downloads, keeps or forwards images or video.** The server never holds call media. If someone sends us material, don't open it. Report the fact to police and follow their instructions.
- Evidence is a small encrypted metadata snapshot. It's deleted after `CSAM_EVIDENCE_RETENTION_DAYS` (placeholder: 90) unless a legal hold is on. Reporting a case sets the hold automatically.
- **Status: draft.** The legal section and the open questions need counsel before the invite pool goes live.

## 1. What counts as CSAM-suspected

| Trigger | Becomes a CSAM case? |
|---|---|
| User report, reason `csam` ("Sexual content involving a minor") | Yes, automatically |
| Chat-safety flag a moderator judges to be sexual content involving a minor (e.g. sexual talk with someone who said they're under 18) | Yes, via `POST /moderation/chat-safety/flags/{id}/escalate-csam` |
| AI detector hit (task 07, not built) | Yes, once task 07 exists. It must call `app.csam.service.open_case(source="ai_detector", ...)` |
| User report, reason `underage` (a minor on the platform, no sexual content reported) | No. It's an account problem: the generic report flow handles it, and the account is removed per ToS. Escalate manually only if the evidence shows sexual content |
| Adult nudity (`nudity`) | No. Generic report flow |

A `csam` report also counts toward the normal 3-in-24h auto-suspend breaker (task 06). The CSAM path is in addition to that flow, not instead of it.

## 2. What we hold, and what we don't

- **Call media (video/audio): never.** It's peer-to-peer WebRTC (or relayed through coturn, which doesn't record), so the server has no imagery to preserve or hand over.
- **Chat text:** relayed through the server but stored only when a chat-safety pattern matches (encrypted, 30-day purge; task 13).
- **Case evidence snapshot** (taken when the case opens, Fernet-encrypted, separate key):
  - reported user's id, email, self-declared birthdate, account creation time
  - age-verification records (status, method, time). No Didit selfie: we never receive it
  - all reports against that user for that call (reporter id, reason, time)
  - flagged chat messages from that call (decrypted text), copied so they outlive the 30-day chat purge

This is the minimum the police are likely to need to identify the account. Don't add to it ad hoc. Changes go through counsel.

## 3. Who is authorized

| Role | Who | May |
|---|---|---|
| CSAM officer (primary) | _[name, to fill]_ | Triage, view evidence, report to police, dismiss, set or lift legal hold |
| CSAM officer (backup) | _[name, to fill]_ | Same, when the primary is unavailable for more than 24h |
| Chat-safety moderators | Holders of `CHAT_SAFETY_MODERATION_SECRET` | Escalate a chat flag into a case. **Cannot** list cases or view evidence |
| Counsel | _[firm/contact, to fill]_ | Advises. Instructs on holds and on what may be shared |

Access mechanics:
- `CSAM_MODERATION_SECRET` is held only by the officers, in a password manager. Never in chat, email, tickets or the repo.
- Every `/moderation/csam` call needs `X-Csam-Secret` plus `X-Actor: <your name>`. Every action is written to `csam_audit_log` with the actor. The actor name is honor-system at MVP: use your real name.
- Rotate the secret when an officer leaves.

## 4. Do-not-view policy

Possessing or spreading CSAM is itself a crime (DK straffeloven §235, see §7), including for the company and its staff. So:

1. **Never view, download, screenshot or keep visual material**, ever, for any reason, including "to check if the report is real". The report is enough to forward.
2. **Never ask a user for screenshots or recordings.** The app tells reporters not to capture anything.
3. **If material reaches us anyway** (e.g. an attachment in a support email):
   - Do not open the attachment or preview it. Do not forward it, not even internally.
   - Write down sender, time and subject only.
   - Report to police that the company received suspected material, and ask how to preserve or delete it. Follow their instruction, then record what you did in the case.
4. **Evidence snapshots (text/metadata)** may be viewed by officers only, only through the API, only for triage or reporting, and only on a company-controlled device. Don't paste them into chat, email, tickets or AI tools. When police need the content, give it to them through the channel they specify.

## 5. Escalation steps

| When | Who | Step |
|---|---|---|
| T+0 (automatic) | System | Case opened, evidence snapshot encrypted, reported user suspended (`CSAM_SUSPENSION_HOURS`, default 30 days), on-call email sent to `CSAM_ONCALL_EMAIL` (case id only) |
| Daily | Officer | Check `GET /moderation/csam/cases` for `open` cases. This catches failed emails, which show up in `csam_audit_log` as `notify_oncall` with `success=false` |
| ≤ 24h | Officer | Triage: `GET /moderation/csam/cases/{id}/evidence`. Look at other reports on the same user, flagged chat and verification status |
| ≤ 24h | Officer | **Report**, the default whenever there's any real indication. Use the channel in §6. Then `POST /cases/{id}/reported` with the police journal number. This sets the legal hold and keeps the suspension |
| ≤ 24h | Officer | **Or dismiss**, only for clearly bogus reports (griefing, obvious misclick). `POST /cases/{id}/dismiss` with a reason. This lifts the precautionary suspension |
| After police feedback | Officer + counsel | Decide on a permanent ban. Release the hold (`PUT /cases/{id}/legal-hold` with `active=false`) only when counsel or police say so |
| Any time | Officer | Preservation request from authority → `PUT /cases/{id}/legal-hold` with `active=true` |

A case that is neither reported nor dismissed within 24h is a process failure. Note it in the case's audit trail (via the reason on the eventual action) and tell counsel.

## 6. Where to report

| Situation | Channel | Status |
|---|---|---|
| Any CSAM-suspected case (DK) | **Danish police**: National Cyber Crime Center (NC3) under Rigspolitiet, reached via politi.dk or 114. Ask for a journal number | Counsel to confirm the preferred intake route |
| Material that exists online (a URL, not a live call) | Red Barnet's hotline (Denmark's INHOPE member) | Verify current reporting URL |
| US nexus applies (see §7) | NCMEC CyberTipline | Only if counsel confirms 18 U.S.C. §2258A applies |
| Child in immediate danger | 112 | Always |

## 7. Legal regimes, candidates until counsel confirms

| Regime | Why it may apply | Status |
|---|---|---|
| **DK straffeloven §235** (possession/distribution of child sexual abuse material) | Basis for the do-not-view policy. Company staff holding material could commit the offence | Counsel to confirm; also list any other relevant sections (e.g. grooming) |
| **DK: platform reporting duty** | We know of no Danish statute that obliges a platform to report like US §2258A does. Reporting is presumed voluntary but expected | **Counsel to confirm.** Key question |
| **GDPR Art. 10 + databeskyttelsesloven §8** | The evidence snapshot is personal data about suspected criminal offences, and a private company needs a legal basis to process it. Minimisation and storage limits (Art. 5(1)(c),(e)) drive the retention window | Counsel to confirm the legal basis and retention period |
| **EU DSA (Reg. 2022/2065) Art. 18** | Hosting providers must tell police about suspected crimes that threaten someone's life or safety. Live P2P video is likely not "hosting", and the chat relay may be "mere conduit", but this is not settled | Counsel to classify the service |
| **EU interim ePrivacy derogation (Reg. 2021/1232, extended by 2024/1307 to 3 Apr 2026)** | Allows *voluntary detection* in interpersonal communications. Relevant to task 07, not to user reports | Check current status before task 07 |
| **Proposed EU CSA Regulation (COM(2022) 209)** | Would add detection and reporting duties plus an EU Centre | Not adopted when this was written; re-check before task 07 |
| **US 18 U.S.C. §2258A** (NCMEC reporting; the REPORT Act 2024 extended preservation to 1 year) | Applies to electronic communication / remote computing service "providers". Whether a DK company with no US infra counts is a nexus question, see below | Counsel to confirm |
| **Norway / Sweden** | Prospective markets (PRD §3) | Check before market entry, alongside task 12 |

### US nexus inventory (re-check whenever a vendor is added)

| Vendor | Role | Touches case data? |
|---|---|---|
| OVHcloud (EU) | Hosting, Postgres, coturn | Yes, hosts the DB |
| Didit (EU, verify) | Age verification | No case data; we receive only a result |
| SMTP provider (to pick at deploy) | On-call email | Case id only. If it's a US provider, that's a weak nexus, still worth telling counsel |
| Expo / EAS (US) | App builds | No user data |
| Google Play / Apple (US) | Distribution | No user data |

## 8. Retention

- Case evidence: deleted `CSAM_EVIDENCE_RETENTION_DAYS` after opening (**placeholder 90**; counsel sets the real value) by `app.csam.service.purge_expired_cases`.
- **Legal hold** pauses deletion. Lifting it resumes normal deletion on the next sweep. If the window has already passed, that sweep deletes the case.
- Marking a case `reported` turns the hold on automatically, because the authority may still need the evidence.
- `csam_audit_log` holds case ids, actors and actions, no evidence. Counsel to set its retention.
- **Gap:** no scheduler runs the sweep yet (same as the chat-safety sweep). Wire up a daily run during deploy (task 05).

## 9. Open questions for counsel

1. Is there a Danish legal *duty* to report, or is it voluntary? Same question for each prospective market.
2. What is the GDPR/databeskyttelsesloven legal basis for the evidence snapshot, and the minimum and maximum retention?
3. DSA classification of the service (hosting vs. mere conduit vs. neither) and whether Art. 18 applies.
4. Does any vendor create a US nexus under §2258A?
5. Is the precautionary 30-day suspension on a single `csam` report proportionate, or should it be shorter or longer?
6. What should the policy be if staff accidentally see material (e.g. an unexpected attachment)?
7. Preferred police intake route and contact for a small platform.

## API reference

All endpoints need `X-Csam-Secret` and `X-Actor`.

| Method | Path | Effect |
|---|---|---|
| GET | `/moderation/csam/cases` | List cases (metadata only) |
| GET | `/moderation/csam/cases/{id}/evidence` | Decrypt and return the snapshot (audited) |
| POST | `/moderation/csam/cases/{id}/reported` | `{external_reference}`. Status `reported`, legal hold on |
| POST | `/moderation/csam/cases/{id}/dismiss` | `{reason}`. Status `dismissed`, suspension lifted |
| PUT | `/moderation/csam/cases/{id}/legal-hold` | `{active, reason}` |

Chat-safety moderators escalate with `POST /moderation/chat-safety/flags/{id}/escalate-csam` (`X-Moderation-Secret`).
