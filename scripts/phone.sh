#!/usr/bin/env bash
# Run DrinkingBuddy on a physical Android phone over wifi - no USB cable. Linux.
#
#   ./scripts/phone.sh --build   # first time: backend + firewall + cloud-built dev APK + Metro
#   ./scripts/phone.sh           # after that: backend + Metro
#
# --build runs `eas build --profile development --platform android`; install the APK
# from the printed link/QR. Needed once, or after native deps change.
# Then open DrinkingBuddy on the phone (same wifi) and pick this machine.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
app="$repo_root/app"

build=false
for arg in "$@"; do
  case "$arg" in
    --build) build=true ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }

step "Backend"
if curl -fsS --max-time 3 http://localhost:8000/health >/dev/null 2>&1; then
  echo "already running on :8000"
else
  "$repo_root/scripts/setup.sh" --up
fi

step "Firewall"
# Phone -> this machine on 8000 (API) and 8081 (Metro). Only touches ufw when it's active.
if command -v ufw >/dev/null; then
  if sudo ufw status | grep -q '^Status: active'; then
    sudo ufw allow 8000,8081/tcp comment 'DrinkingBuddy dev' >/dev/null
    echo "ufw: allowed 8000,8081/tcp"
  else
    echo "ufw inactive - nothing to do"
  fi
else
  echo "no ufw - if another firewall is on, allow inbound TCP 8000 and 8081"
fi

if $build; then
  step "Cloud build: dev-client APK (EAS)"
  (cd "$app" && npx eas-cli build --profile development --platform android) || fail "eas build failed"
  echo "Open the link/QR above on the phone and install the APK, then come back here."
fi

step "Metro (dev client)"
lan_ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}')"
[ -n "$lan_ip" ] || fail "couldn't find this machine's LAN IP - is wifi up?"
echo "Phone must be on the same wifi. PC address: $lan_ip (API http://$lan_ip:8000)"
# Pin Metro to the LAN interface - otherwise it can advertise a Docker bridge IP,
# and the app derives the API host from it.
export REACT_NATIVE_PACKAGER_HOSTNAME="$lan_ip"
cd "$app"
exec npx expo start --dev-client
