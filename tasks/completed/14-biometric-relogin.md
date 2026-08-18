---
title: Biometric relogin gate
status: completed
last_updated: 2026-08-12
depends_on: tasks/completed/02-auth-magic-link.md, docs/prd.md
---

## Goal

Gate app cold-start session restore behind device biometric/passcode auth, so a stored session can't be silently used by whoever is holding the phone (e.g. a child picking up a parent's unlocked device). Covers both content-exposure risk (landing in a live match/webcam feed) and account-misuse risk (acting as the parent). Same spirit as the age-verification webcam gate (`tasks/completed/10-age-verification.md`) — a presence/identity check gating access, not a login-mechanism change.

## Scope

### Mobile app (`/app`)
- Add `expo-local-authentication` dependency.
- In `AuthProvider`'s `restore()` path (`app/src/auth/context.tsx`): when a stored session token+userId is found, run `LocalAuthentication.authenticateAsync()` before transitioning to `signed-in`. Only this silent-restore path is gated.
  - Success → proceed to `signed-in` as today.
  - `LocalAuthentication.hasHardwareAsync()` / `isEnrolledAsync()` both false (no biometric AND no device passcode/PIN configured at all) → skip gate, proceed to `signed-in` directly. Nothing to gate with; app-level check can't add security the OS doesn't have.
  - Prompt cancelled/failed → stay on a locked/gated screen with a retry affordance. No custom attempt counting or app-side lockout — rely on the OS's own biometric retry limits and passcode lockout timing.
- New `AuthState` member (e.g. `status: 'locked'`) distinct from `loading`/`signed-out`/`signed-in`, so the UI can render a dedicated "unlock to continue" screen with a retry button, not a blank loading state.
- Not gated (explicitly bypass the check):
  - Fresh magic-link verification (`verify()` path) — user already proved presence by completing the emailed link that session.
  - Any in-app state transition after that — this task only touches the cold-start silent-restore branch.

## Explicitly out of scope

- Background/foreground-resume re-locking (e.g. re-checking after N minutes backgrounded while app stays running). Cold-start only, per product decision — app is not expected to defend against a same-session handoff mid-use.
- Binding the SecureStore session-token item itself to biometric-gated Keychain/Keystore access control. This task is a UI-level lock screen only; the token is read normally once the gate passes. Defeats casual pickup, not forensic/jailbreak extraction — out of scope for this threat model.
- Settings toggle to disable the gate. Mandatory whenever the device has biometric or passcode configured, same non-optional stance as age verification.
- Any backend changes — this is a pure app-side gate in front of an already-issued session token. No new endpoints, no server-side state.
- Email+password or OTP-SMS as alternate relogin paths — unrelated, see `tasks/completed/02-auth-magic-link.md` follow-ups.

## Done when

- Killing and reopening the app with a valid stored session prompts Face ID/Touch ID/fingerprint (or device passcode fallback) before the app becomes usable.
- Passing the prompt lands the user in the normal signed-in app state.
- Cancelling or failing the prompt keeps the user on a locked screen with a way to retry; app never silently falls through to signed-in.
- Device with no biometric and no passcode/PIN enrolled restores the session directly, no gate shown.
- Completing a fresh magic-link login (new device, or after logout) does **not** additionally prompt for biometrics — only the silent stored-session restore path is gated.
- Tested on both iOS (Face ID/Touch ID) and Android (biometric/PIN) simulators or devices.
