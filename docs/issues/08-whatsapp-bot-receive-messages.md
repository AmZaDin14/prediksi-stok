# 08 - WhatsApp bot: receive messages

**Type:** HITL

## Parent

PRD.md

## What to build

Node.js microservice using `whatsapp-web.js` that receives WhatsApp messages and forwards them to FastAPI.

- `whatsapp-bot/index.js` — initializes WhatsApp client
- On QR code generation: logs QR to console (ASCII) and saves as image `data/qr.png`
- On message received: POST to `http://localhost:8765/webhook` with `{ "from": sender_number, "body": message_body }`
- On response from FastAPI: send the response text back to the sender via WhatsApp
- On ready: log "WhatsApp bot connected: <phone number>" and update a `data/connection_status.json` file with status "connected"

Single phone number, single session. No multi-device handling.

## Acceptance criteria

- [ ] Bot starts and shows QR code in console for pairing
- [ ] After QR scan, bot connects and confirms
- [ ] Incoming message triggers POST to FastAPI webhook
- [ ] FastAPI response is sent back as WhatsApp reply
- [ ] Connection status file is updated on connect/disconnect
- [ ] QR image saved to `data/qr.png` for dashboard to display

## Blocked by

05 — needs FastAPI webhook to forward messages to
