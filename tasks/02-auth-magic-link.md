---
title: Auth — magic-link (email)
status: pending
last_updated: 2026-07-13
depends_on: tasks/01-scaffold-repo.md, docs/prd.md
---

## Goal

Lightweight account creation and login via email magic-link. No password, no OTP-SMS. First auth mechanism shipped; email+password and/or OTP-SMS are separate later tasks if needed.

## Scope

### Backend (`/backend`)
- `users` table: id, email (unique), birthdate, created_at.
- Magic-link token table (or signed JWT, no persistence) — single-use, short expiry (e.g. 15 min).
- Transactional email sending wired up (SMTP or provider e.g. Resend/SES) — pick one, config via `.env`.
- Endpoints:
  - `POST /auth/request-link` — body: email, birthdate (on first-ever request = signup). Sends magic-link email.
  - `GET /auth/verify?token=...` — validates token, creates session, returns session/JWT.
- Session/JWT issuance for authenticated requests (used by later tasks — matching, etc.).
- 18+ check: reject signup if birthdate implies under 18.

### Mobile app (`/app`)
- Email entry screen → "check your email" state.
- Deep link handling to catch the magic-link and complete verification in-app.
- Store session token (secure storage), basic authenticated-state check on app launch.

## Explicitly out of scope

- OTP-SMS login — needs paid SMS provider, not planned.
- Password reset / account recovery flows.
- Profile fields beyond email + birthdate (language/drink-type/location filters are captured later, not at signup).
- Rate limiting / abuse prevention on the request-link endpoint (flag for before public launch).

## Done when

- New user can enter email + birthdate, receive magic-link email, tap it, and land authenticated in the app.
- Returning user can enter email, receive link, tap it, and land authenticated (no birthdate re-ask).
- Under-18 birthdate is rejected at signup.
- Session persists across app restart until expiry/logout.

## Follow-ups (separate session, same file)

- [ ] Email+password login as second auth option — same `users` table, add password_hash column (bcrypt/argon2), login/register endpoints alongside magic-link. Not needed for MVP-day-one, add if magic-link email deliverability becomes a friction point.
