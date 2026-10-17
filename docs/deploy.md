---
description: VPS deploy notes — host-level setup steps not captured in docker-compose.yml. Living doc, grows as deploy work lands.
---

## Docker plugins (one-time host setup)

Container logs (Postgres, Redis, coturn, API) ship to Loki via the Docker Loki logging driver ([`backend/docker-compose.yml`](../backend/docker-compose.yml)). Install the driver on the VPS before first `docker compose up`:

```bash
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

## Dokploy setup

Prod stack: [`backend/docker-compose.prod.yml`](../backend/docker-compose.prod.yml). Paste as a Dokploy "Docker Compose" app. Differences from local [`docker-compose.yml`](../backend/docker-compose.yml):

- No host port publishing for `api` / `otel-lgtm` — routed via Dokploy's Traefik through labels instead.
- Both attach to the `dokploy-network` external network (created by Dokploy) so Traefik can reach them.
- `coturn` still publishes host ports directly (`3478/udp+tcp`, `49152-49172/udp`) — TURN relay is real UDP media, Traefik/HTTP reverse proxy can't front it. Open these in the Hetzner cloud firewall.
- `coturn` is pinned to that relay range with `--min-port`/`--max-port`. Its default is 49152-65535, so without the pin most relay allocations would land on unpublished ports and relayed media would be dropped. 21 ports is tight: each peer allocates one relay port per local network it gathers on (an Android emulator took 4 per peer, so 8 for one call), so expect only a handful of concurrent relayed calls. Widen the range (flags, published ports and firewall together) before launch. Publishing hundreds of ports through Docker is slow, so consider `network_mode: host` for coturn at that point.
- `coturn` needs `--external-ip=${COTURN_PUBLIC_IP}` set to the VPS's public IP, or NAT traversal breaks (container only sees its private Docker IP otherwise).
- Grafana (via `otel-lgtm`, ships with no built-in auth) is fronted by Traefik basic-auth middleware — set `GRAFANA_BASICAUTH_USERS` (generate with `openssl passwd -apr1`, escape every literal `$` as `$$` in the `.env` file).
- Copy [`backend/.env.prod.example`](../backend/.env.prod.example) → `.env` on the server (or into Dokploy's env UI) and fill real secrets + `DOMAIN` + `COTURN_PUBLIC_IP`.

DNS: point `api.<DOMAIN>` and `grafana.<DOMAIN>` A records at the VPS IP. `drinkingbuddy.app` is taken — real domain still TBD, `DOMAIN` env var keeps the compose file domain-agnostic.

## Postgres backups

Dokploy's native per-database backup UI expects Postgres registered as its own Dokploy "Database" resource, which `postgres` here isn't (it's a plain service inside this compose). Instead, use Dokploy's **Schedules** feature on this compose app: a cron-style job running `pg_dump` inside the running `postgres` container, output pushed to S3-compatible storage (Dokploy supports configuring a destination for scheduled backups). Configure in the Dokploy UI once the stack is deployed — not expressible in the compose file itself.

Verify restore periodically — an untested backup is not a backup.
