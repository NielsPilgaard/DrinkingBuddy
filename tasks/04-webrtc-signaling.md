---
title: WebRTC signaling + coturn wiring
status: pending
last_updated: 2026-07-13
depends_on: tasks/03-matching-queue.md, docs/tech-stack.md
---

## Goal

Given a match result from the queue task, establish an actual WebRTC call between the two clients: signaling relay via FastAPI websockets, plus coturn (TURN/STUN) wired in for the ~15-20% of calls that need relay. This is the task where coturn goes from "runs as a service" (task 01) to "actually used by a call."

## Scope

### Backend (`/backend`)
- Websocket endpoint: relay offer/answer/ICE candidates between the two matched clients only. No media touches the server.
- coturn config: generate/serve TURN credentials (time-limited, per-call or per-session) to clients so they can use the self-hosted coturn instance.
- Call-session bookkeeping: map matched pair → active signaling session, teardown on either side leaving.

### Mobile app (`/app`)
- `react-native-webrtc` integration: create peer connection, exchange SDP/ICE via the signaling websocket.
- Use STUN first, fall back to TURN (coturn) when direct/STUN connection fails.
- Video optional, audio optional, text chat always available (per PRD core loop) — this task covers the call transport; UI for toggling video/audio/chat may already exist per mockup, wire it to real streams here.
- Call end → fully ephemeral, no history/reconnect (per PRD).

## Explicitly out of scope

- Hetzner deployment — coturn/signaling proven locally or on staging first; production deploy is a separate task.
- Report/block during calls — separate task.
- Reconnect-on-drop — PRD says ephemeral, no reconnect, so a dropped call just ends.

## Done when

- Two matched clients establish a live WebRTC connection (audio at minimum, video when enabled) via the signaling relay.
- Text chat works over the same session.
- Forcing a non-direct network path (e.g. symmetric NAT test) confirms TURN relay via coturn actually kicks in and call still connects.
- Either side leaving/closing tears down the session cleanly, no orphaned state.
