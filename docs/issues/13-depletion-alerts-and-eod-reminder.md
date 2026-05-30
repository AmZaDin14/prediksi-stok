# 13 - Depletion alerts + end-of-day reminder

**Type:** AFK

## Parent

PRD.md

## What to build

Two APScheduler jobs that deliver proactive WhatsApp messages.

**Depletion alert check (runs hourly or on retrain):**
- For each product, check if Depletion Days ≤ (Supplier Lead Time + 2 days buffer)
- If yes and alert not already sent today: send WhatsApp message
  - "PERINGATAN: [Product] akan habis dalam [N] hari ([Depletion Date]). Stok saat ini: [stock]. Segera lakukan reorder."
- Track which alerts have been sent per product per day (avoid spam)

**End-of-day reminder (daily at configurable time, e.g. 17:00):**
- If no sales reported today: send "Hari ini belum ada laporan penjualan. Kirimkan 'terjual [produk] [jumlah]' atau lakukan cek stok."
- If sales reported but no confirmation: send "Waktunya cek stok! Kirim stok terkini melalui chat."

**Delivery:** Both call Node `POST /send` endpoint to send via WhatsApp.

## Acceptance criteria

- [ ] Depletion alert fires correctly when depletion days crosses threshold
- [ ] Alert only sent once per product per day
- [ ] Alert text includes product name, days remaining, date, current stock, reorder call-to-action
- [ ] End-of-day reminder fires at configured time
- [ ] Reminder differentiates between "no sales" and "sales but no confirmation" cases
- [ ] Both use Node send endpoint for delivery

## Blocked by

09 — needs Node send endpoint
11 — needs EOD confirmation flow awareness
