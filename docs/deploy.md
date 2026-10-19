---
title: VPS deploy
status: active
description: VPS deploy notes — go-live runbook plus host-level setup steps not captured in docker-compose.yml. Living doc, grows as deploy work lands.
purpose: How to take the backend stack live on the OVHcloud VPS and check it works.
---

## Go-live runbook

Order matters: DNS must resolve before Traefik can get Let's Encrypt certs.

1. Buy `drinking-buddy.app` and order the OVHcloud VPS (human, `tasks/16-manual-launch-steps.md`).
2. DNS: A records for `api.`, `app.` and `grafana.drinking-buddy.app` → VPS IP.
3. On the VPS: install Docker, the Loki plugin (below), then Dokploy (`curl -sSL https://dokploy.com/install.sh | sh`). Open `80/tcp`, `443/tcp`, the coturn ports (below) and Dokploy's `3000/tcp` (close it again once Dokploy sits behind its own domain).
4. In Dokploy: new Docker Compose app from this repo, compose path `backend/docker-compose.prod.yml`. Paste [`backend/.env.prod.example`](../backend/.env.prod.example) into the env UI and replace every `changeme`, `COTURN_PUBLIC_IP`/`COTURN_HOST` and the SMTP credentials. The API refuses to start while a secret is still a placeholder.
5. Deploy, then run the checks below.
6. Set up Postgres backups (below).

### Done-when checks (task 05)

- `curl https://api.drinking-buddy.app/health` → `{"status":"ok"}` with a valid cert.
- `curl -i https://api.drinking-buddy.app/auth/request-link -H 'X-Test-Mode: 1' -H 'content-type: application/json' -d '{"email":"you@example.com"}'` → response has **no** token. If it does, `ENVIRONMENT` isn't `production`.
- `https://app.drinking-buddy.app/.well-known/assetlinks.json` and `/apple-app-site-association` return JSON once `ANDROID_SHA256_CERT_FINGERPRINTS` / `APPLE_TEAM_ID` are set (404 before).
- TURN reachable from outside: make a credential on the server with `docker compose exec api python -c "import uuid; from app.signaling.turn import generate_turn_credentials as g; print(g(uuid.uuid4()).ice_servers[1])"`, then paste the `turn:` URL, username and credential into https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/ from a machine on another network. A `relay` candidate with the VPS IP means TURN works.
- Two phones on different networks (e.g. one on Wi-Fi, one on mobile data) built with the `preview`/`production` EAS profile (both bake in `https://api.drinking-buddy.app`) match and hold a call. Repeat with one phone forced through TURN (Trickle ICE check above, or a mobile carrier that blocks direct UDP).
- `docker restart` the `postgres` container; existing accounts still sign in.

## Docker plugins (one-time host setup)

Container logs (Postgres, Redis, coturn, API) ship to Loki via the Docker Loki logging driver ([`backend/docker-compose.yml`](../backend/docker-compose.yml)). Install the driver on the VPS before first `docker compose up`:

```bash
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

## Dokploy setup

Prod stack: [`backend/docker-compose.prod.yml`](../backend/docker-compose.prod.yml). Paste as a Dokploy "Docker Compose" app. Differences from local [`docker-compose.yml`](../backend/docker-compose.yml):

- No host port publishing for `api` / `otel-lgtm` — routed via Dokploy's Traefik through labels instead.
- Both attach to the `dokploy-network` external network (created by Dokploy) so Traefik can reach them.
- `coturn` runs with `network_mode: host` and binds `3478/udp+tcp` plus relay ports `49152-50151/udp` straight on the VPS — TURN relay is real UDP media, Traefik/HTTP reverse proxy can't front it, and publishing 1000 ports through docker-proxy is slow. Open exactly these in the VPS firewall (OVHcloud Edge Network Firewall if enabled, plus `ufw` or similar on the host). Host networking means host firewall rules apply to coturn, unlike Docker-published ports, which bypass `ufw`.
- The relay range is pinned with `--min-port`/`--max-port` (coturn's default is 49152-65535) so it matches the firewall. Each peer takes one relay port per local network it gathers on: ~1-2 on a phone, 4 on an Android emulator. 1000 ports ≈ 250+ concurrent relayed calls, i.e. well over 1000 concurrent calls at the ~15-20% relay rate. VPS bandwidth runs out before ports do: a relayed video call is roughly 1-3 Mbit/s each way through the server. Local `docker-compose.yml` keeps 21 published ports, enough for dev.
- `coturn` needs `--external-ip=${COTURN_PUBLIC_IP}` set to the VPS's public IP, or NAT traversal breaks (container only sees its private Docker IP otherwise).
- Grafana (via `otel-lgtm`, ships with no built-in auth) is fronted by Traefik basic-auth middleware — set `GRAFANA_BASICAUTH_USERS` (generate with `openssl passwd -apr1`, escape every literal `$` as `$$` in the `.env` file).
- Copy [`backend/.env.prod.example`](../backend/.env.prod.example) → `.env` on the server (or into Dokploy's env UI) and fill real secrets + `DOMAIN` + `COTURN_PUBLIC_IP`.

DNS: point `api.<DOMAIN>`, `app.<DOMAIN>` and `grafana.<DOMAIN>` A records at the VPS IP. Domain is `drinking-buddy.app`; the `DOMAIN` env var keeps the compose file domain-agnostic.

`app.<DOMAIN>` is the magic-link host. Traefik routes only `/verify` and `/.well-known/*` there to the API ([`app/routers/app_links.py`](../backend/app/routers/app_links.py)), which serves the iOS/Android link-verification files from `APPLE_TEAM_ID` / `ANDROID_SHA256_CERT_FINGERPRINTS` plus a browser fallback that bounces to the `drinkingbuddy://` scheme.

`ENVIRONMENT=production` is pinned in the compose file for `api` and `migrate`, not read from `.env`: `development` would echo magic-link tokens to any caller sending `X-Test-Mode: 1`.

## Postgres backups

Dokploy's native per-database backup UI expects Postgres registered as its own Dokploy "Database" resource, which `postgres` here isn't (it's a plain service inside this compose). Instead, use Dokploy's **Schedules** feature on this compose app: a cron-style job running `pg_dump` inside the running `postgres` container, output pushed to S3-compatible storage (Dokploy supports configuring a destination for scheduled backups). Configure in the Dokploy UI once the stack is deployed — not expressible in the compose file itself.

Verify restore periodically — an untested backup is not a backup.
