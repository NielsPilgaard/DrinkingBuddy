# Testing the app on a physical phone (Android, no USB cable)

Phone and PC on the same wifi. From the repo root:

```powershell
./scripts/phone.ps1 -Build   # first time: backend + firewall + cloud-built dev APK + Metro
./scripts/phone.ps1          # after that: backend + Metro
```

1. `-Build` runs `eas build --profile development --platform android` (needs a free Expo account; first run links the EAS project). Open the printed link/QR on the phone and install the APK (allow installs from unknown sources). Rebuild only when native deps change. Expo Go won't work because it lacks `react-native-webrtc` and the Didit SDK.
2. Open DrinkingBuddy on the phone and pick the PC's dev server (or scan the Metro QR code).
3. Sign in with any email (plus birthdate the first time). Dev builds against the local stack sign in immediately: the backend echoes the magic-link token in development (`X-Test-Mode`, see `backend/app/routers/auth.py`), so no email step is needed.

The app finds the backend by itself: with `EXPO_PUBLIC_API_URL` unset, it uses port 8000 on the host Metro serves from. Set `EXPO_PUBLIC_API_URL` in `app/.env` only to force a different backend.

Troubleshooting:
- "Backend unreachable": the Windows network is probably set to Public. The firewall rule `phone.ps1` adds only covers Private networks. Switch the wifi to Private (trusted networks only).
- Matching needs two users: use a second phone or an emulator.
