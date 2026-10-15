#!/usr/bin/env bash
# One-shot local setup for DrinkingBuddy (backend + app). Idempotent - safe to re-run.
#
#   ./scripts/setup.sh        # check prereqs, create .env files, install deps
#   ./scripts/setup.sh --up   # ...then start the backend stack (Docker) and wait for /health
#
# PowerShell equivalent: scripts/setup.ps1
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend="$repo_root/backend"
app="$repo_root/app"

up=false
for arg in "$@"; do
  case "$arg" in
    --up) up=true ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }

step "Checking prerequisites"
command -v uv >/dev/null || fail "uv not found - install: https://docs.astral.sh/uv/getting-started/installation/"
command -v node >/dev/null || fail "node not found - install Node 20.19.4+ / 22.13+ / 24.3+ (see app/.nvmrc)"
command -v npm >/dev/null || fail "npm not found (ships with Node)"
node -e '
  const [maj, min, pat] = process.versions.node.split(".").map(Number);
  const ok = (maj === 20 && (min > 19 || (min === 19 && pat >= 4))) ||
             (maj === 22 && min >= 13) || (maj === 24 && min >= 3) || maj >= 25;
  if (!ok) { console.error("Node " + process.versions.node + " too old for React Native 0.86 (need ^20.19.4 || ^22.13.0 || ^24.3.0 || >=25)"); process.exit(1); }
' || exit 1
echo "uv $(uv --version | cut -d' ' -f2), node $(node --version)"

docker_ok=false
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  docker_ok=true
  echo "docker daemon reachable"
else
  echo "WARNING: Docker daemon not reachable - needed for the backend stack and integration tests, not for install."
fi

step "Creating .env files (existing ones are left alone)"
for dir in "$backend" "$app"; do
  if [ -f "$dir/.env" ]; then
    echo "keep   ${dir#"$repo_root"/}/.env"
  else
    cp "$dir/.env.example" "$dir/.env"
    echo "create ${dir#"$repo_root"/}/.env"
  fi
done

step "Backend: uv sync --extra dev"
(cd "$backend" && uv sync --extra dev)

step "App: npm ci"
(cd "$app" && npm ci)

if [ "$up" = true ]; then
  [ "$docker_ok" = true ] || fail "--up needs a running Docker daemon"
  compose=(docker compose -f docker-compose.yml)
  if ! docker plugin ls --format '{{.Name}}' 2>/dev/null | grep -q loki; then
    echo "Loki logging plugin not installed - using docker-compose.windows.yml (json-file logs). See docs/local_dev.md."
    compose+=(-f docker-compose.windows.yml)
  fi
  step "Backend stack: ${compose[*]} up -d --build --wait"
  (cd "$backend" && "${compose[@]}" up -d --build --wait)
  curl -fsS http://localhost:8000/health && echo
fi

step "Done"
cat <<'EOF'
Next:
  Backend tests:  cd backend && uv run pytest tests/unit         (integration: tests/integration -m integration, needs Docker)
  Lint/typecheck: pwsh -File scripts/verify.ps1                  (or the raw commands in .claude/skills/verify/SKILL.md)
  Backend stack:  ./scripts/setup.sh --up                        (API :8000, Mailpit :8025, Grafana :3000)
  App:            cd app && npx expo run:android | run:ios       (dev build - Expo Go lacks react-native-webrtc)
EOF
