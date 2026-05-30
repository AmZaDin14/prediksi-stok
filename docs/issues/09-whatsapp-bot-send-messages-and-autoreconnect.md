# 09 - WhatsApp bot: send messages + auto-reconnect

**Type:** AFK

## Parent

PRD.md

## What to build

Extend the Node microservice to accept send requests from Python and auto-reconnect on disconnect.

**Send endpoint:** Express.js (minimal, or Node built-in http)
- `POST /send` — accepts `{ "to": "phone_number", "body": "message_text" }`, sends via WhatsApp
- Returns `{ "status": "sent" }` or error
- Runs on `localhost:PORT` (configurable via env var `NODE_PORT`, default `8766`)

**Auto-reconnect:**
- On `disconnected` event: wait 5 seconds, attempt reconnect
- If still disconnected after 5 minutes: update `data/connection_status.json` to `{ "status": "disconnected", "qr_path": "data/qr.png" }` with new QR
- On `ready` after reconnect: update status to "connected"

**Status endpoint:**
- `GET /status` — returns `{ "status": "connected" | "disconnected" | "connecting" }`
- FastAPI polls this for dashboard display

## Acceptance criteria

- [ ] `POST /send` successfully sends WhatsApp messages
- [ ] Bot auto-reconnects on temporary disconnect (session still valid)
- [ ] After 5-min reconnect failure, QR is regenerated and status updated
- [ ] `GET /status` returns current connection state
- [ ] All status updates reflected in `data/connection_status.json`

## Blocked by

08 — needs base WhatsApp bot running
