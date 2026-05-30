# 14 - Dashboard WhatsApp status + QR re-pairing

**Type:** AFK

## Parent

PRD.md

## What to build

Dashboard components showing WhatsApp connection status and allowing QR re-pairing.

**Connection status indicator:**
- Reads `data/connection_status.json`
- Displays badge: Connected (green) / Disconnected (red) / Connecting (yellow)
- Shows phone number when connected
- Auto-refreshes every 30 seconds

**QR re-pairing:**
- When status is "disconnected", display the QR code image from `data/qr.png`
- Show instructions: "Scan QR code with WhatsApp to reconnect"
- Button: "Refresh QR" — calls Node status endpoint to regenerate if needed

**Layout:**
- Status indicator in dashboard header or sidebar (always visible)
- QR section appears inline below status when disconnected

## Acceptance criteria

- [ ] Dashboard shows green "Connected" badge with phone number when connected
- [ ] Dashboard shows red "Disconnected" badge when disconnected
- [ ] Dashboard shows yellow "Connecting" badge during reconnect attempts
- [ ] QR code image displays when disconnected
- [ ] Refresh QR button works
- [ ] Status auto-refreshes every 30s without page reload

## Blocked by

09 — needs Node status endpoint and connection_status.json
