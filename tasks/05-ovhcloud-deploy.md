---
title: OVHcloud deployment
status: pending
last_updated: 2026-10-19
depends_on: tasks/04-webrtc-signaling.md, docs/tech-stack.md
---

## Goal

Move the local Docker Compose stack (API, Postgres, Redis, coturn) to a single OVHcloud VPS, publicly reachable, with signaling and TURN actually working over the public internet (not just localhost/LAN).

## Scope

### Infra
- Provision OVHcloud VPS.
- Docker Compose stack running on the VPS: FastAPI app, Postgres, Redis, coturn. Deploy tooling TBD — Dokploy (self-hosted, Traefik + Let's Encrypt built in) is an option to evaluate before hand-rolling Compose + reverse proxy + certbot.
- **Domain required.** Buy one (~$10-15/yr) before TLS/deploy work. Why: magic-link emails need stable `https://` host (bare IP looks phishy, breaks if IP changes); Let's Encrypt won't cert bare IPs; coturn `turns:` needs hostname too; mobile deep-links (iOS/Android) require domain, not IP.
- Domain/TLS for API + websocket signaling (Let's Encrypt).
- coturn public IP / port config correct for real NAT traversal (not just Docker-internal networking).
- `.env` / secrets management for production (DB creds, coturn secret, email provider keys from task 02).
- Basic persistence/backup story for Postgres data.

### Mobile app (`/app`)
- Point app config (dev/staging/prod) at the deployed API/websocket URLs instead of localhost.

## Progress

Repo side is ready; what's left is human-only (`tasks/16-manual-launch-steps.md` → "Deploy") plus the checks in `docs/deploy.md` → "Done-when checks".

- Prod compose for Dokploy, coturn on host networking, Grafana behind basic auth (`backend/docker-compose.prod.yml`).
- Domain: `drinking-buddy.app`. EAS `preview`/`production` profiles bake in `https://api.drinking-buddy.app`.
- `ENVIRONMENT=production` pinned in compose. Startup refuses placeholder COTURN/Didit/chat-safety secrets.
- Magic-link host `app.<DOMAIN>` served by the API: AASA, `assetlinks.json`, `/verify` browser fallback.
- Postgres backups: Dokploy Schedules, configured in its UI after deploy.

## Explicitly out of scope

- Auto-scaling / multi-VPS / load balancing (single VPS is the stated target per `docs/tech-stack.md`).
- CI/CD pipeline (unless already decided elsewhere — not in current docs).
- Monitoring/alerting stack (not in MVP scope per PRD).

## Done when

- API health check reachable over public URL with TLS.
- Two clients on different real networks (not same LAN) can match and complete a WebRTC call end-to-end against the deployed stack, including a TURN-relayed case.
- Postgres data survives a container restart.
