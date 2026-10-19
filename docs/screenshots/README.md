---
title: App screenshots
description: >-
  Android emulator screenshots of every main app state, taken 2026-10-19 after
  the dark theme and call-screen redesign, plus design issues spotted while
  taking them.
status: current
purpose: Reference set for refining the app's look; retake after visual changes.
---

Taken on Android emulators (API 36, 1080x2400) against the local stack. The grey gear button is the dev build's tools menu, not part of the app; release builds don't show it. The emulator's fake camera supplies the video.

| File | State |
|---|---|
| 01-login.png | Sign-in, empty |
| 02-login-filled.png | Sign-in, filled, keyboard open |
| 03-login-link-sent.png | "Check your email" |
| 04-match-filters.png | Filter picker, defaults (Dansk, alcoholic) |
| 05-match-filters-changed.png | English + non-alcoholic selected |
| 06-searching.png | Looking for a match |
| 07-widen-prompt.png | No match after ~30s, offer any language |
| 08-call-idle.png | Audio-only call: pills, self PiP, bottom bar |
| 09-verify-sheet.png | Camera tapped while unverified |
| 10-chat-empty.png | Chat sheet, no messages |
| 11-chat.png | Chat sheet with messages |
| 12-menu.png | Menu sheet, drink counter at 2 |
| 13-games-picker.png | Mini games list |
| 14-game-invite-sent.png | Waiting for partner to accept |
| 15-game-invite-received.png | Partner's accept/decline |
| 16-game-trivia.png | Trivia question |
| 17-game-trivia-answered.png | Trivia answer revealed |
| 18-report-sheet.png | Report sheet over menu |
| 19-call-ended.png | Call ended |
| 20-call-video.png | Video call, both verified |
| 21-call-video-chat.png | Chat open over video |

Not captured: suspended account, Face ID re-login, verification waitlist (each needs a staged backend state).

## Design issues spotted

- The Android keyboard stays light on the dark login (02). `keyboardAppearance` only affects iOS.
