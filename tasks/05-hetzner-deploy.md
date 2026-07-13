---
title: Hetzner deployment
status: pending
last_updated: 2026-07-13
depends_on: tasks/04-webrtc-signaling.md, docs/tech-stack.md
---

## Goal

Move the local Docker Compose stack (API, Postgres, Redis, coturn) to a single Hetzner VPS, publicly reachable, with signaling and TURN actually working over the public internet (not just localhost/LAN).

## Scope

### Infra
- Provision Hetzner VPS.
- Docker Compose stack running on the VPS: FastAPI app, Postgres, Redis, coturn.
- Domain/TLS for the API and websocket signaling endpoint (e.g. Let's Encrypt).
- coturn public IP / port config correct for real NAT traversal (not just Docker-internal networking).
- `.env` / secrets management for production (DB creds, coturn secret, email provider keys from task 02).
- Basic persistence/backup story for Postgres data.

### Mobile app (`/app`)
- Point app config (dev/staging/prod) at the deployed API/websocket URLs instead of localhost.

## Explicitly out of scope

- Auto-scaling / multi-VPS / load balancing (single VPS is the stated target per `docs/tech-stack.md`).
- CI/CD pipeline (unless already decided elsewhere — not in current docs).
- Monitoring/alerting stack (not in MVP scope per PRD).

## Done when

- API health check reachable over public URL with TLS.
- Two clients on different real networks (not same LAN) can match and complete a WebRTC call end-to-end against the deployed stack, including a TURN-relayed case.
- Postgres data survives a container restart.
