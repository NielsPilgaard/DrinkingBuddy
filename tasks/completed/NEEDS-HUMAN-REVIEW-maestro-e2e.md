---
title: Human review flags — Mobile E2E (Maestro)
status: needs-review
created: 2026-08-15
---

Implementer (agent) has no prior Maestro/mobile-E2E experience. Flagging
decisions made solo so a human can sanity-check before this ships.

## 1. New `environment: "test"` setting value

`backend/app/config.py` only had `"development"` vs everything-else. Added a
third value, `"test"`, and gated the magic-link token echo on
`settings.environment == "test"` (not `"development"`) **and** an
`X-Test-Mode: 1` header, both required. Reasoning: a developer's own phone
hitting their laptop's `uv run uvicorn --host 0.0.0.0` backend during normal
manual dev is still `environment=development` and must NOT leak tokens over
LAN. Only a backend explicitly booted with `ENVIRONMENT=test` (Docker Compose
override, CI) echoes the token. Please confirm this is the right boundary —
if `development` was actually meant to double as the test-echo gate, that's a
one-line config change but changes the LAN-exposure story.

User note: development was meant to double as the test-echo gate, change it

## 2. Token echoed in response body, not just a header

Added `debug_token: str | None = None` to `RequestLinkResponse`, populated
only under the double-gate above. Alternative was a response header
(`X-Debug-Token`) — went with body since Maestro's `evalJS`/`http.post`
assertions are easier against JSON body than headers in what I could find in
Maestro docs. **I have not run this against a real Maestro install** — no
Maestro binary available on this dev machine (not installed, this repo
targeting has no `maestro/` dir prior to this task). The flows are written
per Maestro's documented YAML syntax but are UNVERIFIED against a live run.

install maestro and run it!

**Resolution (2026-08-18):** No Maestro binary/ADB/Android SDK available in
agent sandbox — can't install or run here. Left unverified against a live
run; not blocking merge. Flows are still only checked against Maestro's
documented YAML syntax, not exercised on a real device. Run manually before
relying on these in CI.

## 3. No `.github/` CI directory exists yet in this repo

Task says "CI: run on a schedule or pre-release, not per-commit" but there is
currently zero CI in this repo (no `.github/workflows/`). Added
`.github/workflows/e2e-maestro.yml` as a new file — scheduled nightly +
manual `workflow_dispatch`, Android only (per scope: "pick one platform for
CI"). This is the first CI workflow in the repo; please review whether GH
Actions is even the intended CI system before this merges — nothing in
AGENTS.md/docs confirms it.

It is.

## 4. testID props added across screens

No `testID` existed anywhere in `app/src`. Maestro selects by visible text
where possible (label copy is fairly stable: "Send sign-in link", "Chat",
"Report", etc.) but a few elements need `testID` because content is dynamic
or ambiguous (chat message bubbles, the email/birthdate inputs, the "find
match" implicit state). Added minimal testIDs only where text-matching
wouldn't work reliably. Please review the actual testID names chosen
(`app/src/screens/LoginScreen.tsx`, `MatchScreen.tsx`, `CallScreen.tsx`,
`ReportBlockSheet.tsx`) — renaming them later is a breaking change for the
Maestro flows.

Fine

## 5. Deep-link capture in `signup-login.yaml`

Maestro's `openLink` can open a `drinkingbuddy://verify?token=...` deep link
directly (per docs), so the flow builds the link client-side from the echoed
`debug_token` via `http.post` + string interpolation rather than driving
email/inbox UI at all. This sidesteps needing Mailhog/inbox scraping (matches
task's stated preference for option (a)). Confirm this is acceptable — it
means the flow never exercises `Linking` cold-start-vs-warm handling
differences that a *real* tapped-link-from-email would hit; it only proves
`extractToken` + `verify()` work when Expo's `Linking` fires from
`openLink`.

Fine

## 6. Multi-device flow (`match-and-call.yaml`)

Written using Maestro's multi-device `--device` flag pattern via two runner
invocations orchestrated by a wrapper script
(`maestro/run-match-and-call.sh`), not a single YAML with an in-file
multi-device block — as far as I could determine from docs, Maestro CLI
(non-Cloud) drives one device per `maestro test` invocation, and true
"two devices in one flow" is a Maestro Cloud feature. If this repo has (or
plans) Maestro Cloud access, the wrapper-script approach should likely be
replaced. **This is the part I'm least confident about — please verify
against current Maestro CLI docs/version before relying on it.**

Make sure it works then. We won't use Maestro Cloud

**Resolution (2026-08-18):** Confirmed against Maestro CLI docs: `--device`
scopes one `test` invocation to one connected device/emulator; true
same-YAML multi-device blocks are Cloud-only. `run-two-device-flow.sh`/`.ps1`
approach (two backgrounded `maestro test` invocations, `DEVICE_ROLE=a`/`b`,
wait on both, non-zero exit if either fails) is the correct CLI-only shape —
no Cloud, per decision above. Script logic reviewed and sound. Not exercised
against a live two-emulator run (no Android SDK/emulator available in agent
sandbox) — run manually before relying on it in CI.

## 6a. Task spec says "returns to MatchScreen" but code returns to CallEndedScreen

Task spec for `report-block.yaml`: "assert call ends and returns to
MatchScreen." Reading `app/src/screens/MatchScreen.tsx` and
`CallEndedScreen.tsx`: ending a call (via report+block, hangup, or peer
leaving) always routes through an intermediate `CallEndedScreen` ("Call
ended" / "Find next match" button) — never straight back to the
searching-for-a-match `MatchScreen` UI. I wrote the flow to assert
`call-ended-screen` (matching actual code) rather than `match-screen`
(matching the spec's literal wording). Please confirm this is the intended
UX — if MatchScreen really is supposed to be the landing state,
CallEndedScreen may need to auto-continue or be removed from this flow.

Intended

## 7a. CI workflow is a stub, not a working pipeline

`.github/workflows/e2e-maestro.yml` intentionally `exit 1`s at the "Build/fetch
Android app" step — this repo has no CI-buildable Android artifact yet (EAS
Build needs `EXPO_TOKEN` + a build profile, or a local `eas build --local`
with Android SDK/NDK on the runner, neither of which exists). I did not want
to silently fake success or skip the step. Also:
`reactivecircus/android-emulator-runner` only boots one emulator per job, so
`match-and-call.yaml`/`report-block.yaml` (both two-device) aren't wired into
CI at all yet — only `signup-login.yaml` is. Getting two emulators running
concurrently in one GH Actions job (or fanning out to two parallel jobs
sharing one backend + one Redis matching queue) needs a design decision
before this is real CI, not just a task for me to push through solo.

Grill me on it then

**Resolution (2026-08-18):** Grilled. Decisions: (1) one GH Actions job runs
both emulators (not two parallel jobs), via `reactivecircus/android-emulator-runner`
invoked twice with distinct `avd-name`/`port`; (2) APK comes from EAS Build
cloud (new `e2e` profile in `app/eas.json`, APK output, `EXPO_PUBLIC_API_URL`
baked to `http://localhost:8000`), not `--local`, to avoid provisioning
Android SDK/NDK on the runner — needs an `EXPO_TOKEN` repo secret.
`.github/workflows/e2e-maestro.yml` rewritten accordingly: builds via EAS,
boots two emulators, runs `signup-login.yaml` on device A alone then both
two-device flows via `run-two-device-flow.sh`. **Still unverified**: whether
calling `android-emulator-runner` twice in one job actually keeps both
emulators alive concurrently (the action's own docs describe one emulator
per job) — flagged inline in the workflow. Needs a real run to confirm; if
the second invocation tears down the first, device B needs a manual
`emulator` binary boot instead of a second action call.

## 7. `report-block.yaml` assumes English UI copy

Uses `REPORT_REASONS` label text from `app/src/call/moderation.ts` for
tapping a reason row — if those labels change, flow breaks silently until
next run. Considered testID-per-reason instead; skipped for now since the
list is short and dynamic per-item testIDs felt like overkill, but flag it
in case reasons list is expected to grow/change often.

Add testID then