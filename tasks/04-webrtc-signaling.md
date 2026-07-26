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
- Websocket endpoint: relays offer/answer/ICE candidates and text chat messages between the two matched clients. Audio/video media never touches the server (P2P only).
- **Text chat is server-relayed, not a P2P WebRTC datachannel.** Messages go over the same signaling websocket connection and are relayed server-side (not just offer/answer/ICE). This is a deliberate deviation from "pure P2P" for video/audio — required so the server can see plaintext message content for the chat safety filters (`tasks/13-chat-safety-filters.md`, PRD §9). Video/audio stay P2P as originally planned; only text is routed through the server.
- coturn config: generate/serve TURN credentials (time-limited, per-call or per-session) to clients so they can use the self-hosted coturn instance.
- Call-session bookkeeping: map matched pair → active signaling session, teardown on either side leaving.

### Mobile app (`/app`)
- `react-native-webrtc` integration: create peer connection, exchange SDP/ICE via the signaling websocket.
- Use STUN first, fall back to TURN (coturn) when direct/STUN connection fails.
- Video optional, audio optional, text chat always available (per PRD core loop) — this task covers the call transport; UI for toggling video/audio/chat may already exist per mockup, wire it to real streams here. Text chat sends/receives over the signaling websocket (server-relayed), not a WebRTC datachannel.
- Call end → fully ephemeral, no history/reconnect (per PRD).

## Explicitly out of scope

- Hetzner deployment — coturn/signaling proven locally or on staging first; production deploy is a separate task.
- Report/block during calls — separate task.
- Reconnect-on-drop — PRD says ephemeral, no reconnect, so a dropped call just ends.

## Done when

- Two matched clients establish a live WebRTC connection (audio at minimum, video when enabled) via the signaling relay.
- Text chat works over the signaling websocket (server-relayed, not a WebRTC datachannel) — confirmed the server actually receives plaintext message content (needed for `tasks/13-chat-safety-filters.md`).
- Forcing a non-direct network path (e.g. symmetric NAT test) confirms TURN relay via coturn actually kicks in and call still connects.
- Either side leaving/closing tears down the session cleanly, no orphaned state.
