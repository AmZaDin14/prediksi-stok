# 05 - FastAPI webhook

**Type:** AFK

## Parent

PRD.md

## What to build

FastAPI HTTP server with a webhook endpoint that the WhatsApp bot will POST incoming messages to.

- `POST /webhook` — accepts `{ "from": "phone_number", "body": "message_text" }`
- Calls Input Parser to parse the message
- If valid sales: calls Sales Data module to record, returns `{ "status": "ok", "response": "response text" }`
- If errors: returns `{ "status": "error", "response": "error text" }`
- If `"cek stok"` (exact match after lowering): returns current status for all products (their stock, expected depletion)
- `GET /health` — returns `{ "status": "ok" }` for heartbeat/liveness

Server runs on `localhost:8765` (configurable via env var `FASTAPI_PORT`).

## Acceptance criteria

- [ ] `POST /webhook` with valid `terjual` message records sale and returns OK response
- [ ] `POST /webhook` with invalid message returns error response with helpful text
- [ ] `POST /webhook` with `cek stok` returns product status overview
- [ ] `GET /health` returns 200
- [ ] Server starts with `uv run main.py` (or equivalent)

## Blocked by

03 — needs Sales Data module
04 — needs Input Parser module
