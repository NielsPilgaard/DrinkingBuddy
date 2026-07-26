1. Scan QR w/ Expo Go on phone (same wifi).
2. If screen shows "Backend unreachable" — expected, localhost means phone not laptop. Edit app/.env:
    - EXPO_PUBLIC_API_URL=http://192.168.1.67:8000, restart expo start.
    - Backend must actually be running: docker compose up -d in /backend if not already up.
    - Windows firewall may block phone→laptop:8000 — allow if prompted.