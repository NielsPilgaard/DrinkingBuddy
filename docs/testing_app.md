1. Install a dev build on the phone (`cd app && npx expo run:android` with the phone on USB, or `eas build --profile development`). Expo Go won't work because it lacks `react-native-webrtc` and the Didit SDK. Then `npx expo start --dev-client` and open the project from the dev build (same wifi).
2. If screen shows "Backend unreachable" — expected, localhost means phone not laptop. Edit app/.env:
    - EXPO_PUBLIC_API_URL=http://<your LAN IP>:8000, restart expo start.
    - Backend must actually be running: `./scripts/setup.ps1 -Up` (or `docker compose up -d` in /backend) if not already up.
    - Windows firewall may block phone→laptop:8000 — allow if prompted.
