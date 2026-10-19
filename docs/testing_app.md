# Testing the app on a physical phone (Android, no USB cable, Linux host)

Phone and PC on the same wifi. From the repo root:

```bash
./scripts/phone.sh --build   # first time: backend + firewall + cloud-built dev APK + Metro
./scripts/phone.sh           # after that: backend + Metro
```

1. `--build` runs `eas build --profile development --platform android` (needs a free Expo account; first run links the EAS project). Open the printed link/QR on the phone and install the APK (allow installs from unknown sources). Rebuild only when native deps change. Expo Go won't work because it lacks `react-native-webrtc` and the Didit SDK.
2. Open DrinkingBuddy on the phone and pick the PC's dev server (or scan the Metro QR code).
3. Sign in with any email (plus birthdate the first time). Dev builds against the local stack sign in immediately: the backend echoes the magic-link token in development (`X-Test-Mode`, see `backend/app/routers/auth.py`), so no email step is needed.

The app finds the backend by itself: with `EXPO_PUBLIC_API_URL` unset, it uses port 8000 on the host Metro serves from. Set `EXPO_PUBLIC_API_URL` in `app/.env` only to force a different backend.

Troubleshooting:
- "Backend unreachable": a firewall is blocking inbound TCP 8000/8081. `phone.sh` opens them in ufw when ufw is active; open them by hand for any other firewall.
- Matching needs two users: use a second phone or an emulator.
