# 11 - EOD confirmation flow

**Type:** HITL

## Parent

PRD.md

## What to build

End-of-day flow: bot prompts owner, owner confirms stock, system reconciles.

**APScheduler job (daily at configurable time, default 18:00):**
- Sends WhatsApp message: "Waktunya cek stok! Laporkan stok terkini: [product list]"
- Example: "Waktunya cek stok! Laporkan stok terkini: gula, minyak, tepung, beras, aqua, roti, garam"

**Owner response handling:**
- Owner sends: `gula 25, minyak 980, tepung 290` (or partial: only products they checked)
- For each reported product: `confirm_stock(product, quantity, today)`
- For unreported products: assume no change from expected stock? Or flag as unconfirmed?
  - Decision: unreported products are flagged as "stock unconfirmed" (yellow confidence)

**Missed day handling:**
- If no confirmation received within 2 hours of prompt: mark all products as "unconfirmed"
- Dashboard shows yellow flag: "Stock unconfirmed since YYYY-MM-DD"
- No sales data for ≥3 days: red flag "No data for N days"
- Predictions continue regardless — only flags change

**APScheduler job also handles:**
- `cek stok` anytime: responds with same prompt format (existing from issue 05)

## Acceptance criteria

- [ ] APScheduler fires at configured time and triggers WhatsApp message via Node send endpoint
- [ ] Owner response with stock data records confirmation via Stock Reconciliation
- [ ] Partially reported products flagged as unconfirmed (yellow)
- [ ] No response within 2 hours → auto-flag all as unconfirmed
- [ ] Missed sales data tracking: flag escalates from yellow to red after 3 days
- [ ] `cek stok` command still works on-demand

## Blocked by

09 — needs Node send endpoint for bot to message owner
10 — needs Stock Reconciliation module
