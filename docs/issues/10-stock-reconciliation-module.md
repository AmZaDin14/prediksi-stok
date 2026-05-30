# 10 - Stock Reconciliation module

**Type:** AFK

## Parent

PRD.md

## What to build

Module that compares expected stock vs actual shelf stock reported during End-of-Day Confirmation.

Module interface:
- `reconcile(product_name, expected_stock, actual_stock, threshold=0.1)` returns `ReconciliationResult`
- `ReconciliationResult` = `{ "match": bool, "discrepancy": float, "discrepancy_pct": float, "shrinkage": bool, "restock": bool }`
- Exact match or below threshold (default 10% or 1 unit, whichever is larger): `match=true`, no alert
- actual < expected - threshold: `match=false, shrinkage=true` — flag discrepancy (potential theft/spoilage)
- actual > expected: `match=false, restock=true` — new shipment arrived. Baseline updated to actual without alert
- Does NOT treat discrepancy as consumption for velocity calculations

Also provides high-level API:
- `get_expected_stock(product_name)` — last confirmed stock minus sum of sales since that confirmation
- `confirm_stock(product_name, actual_quantity, date)` — records snapshot + runs reconciliation

## Acceptance criteria

- [ ] Exact match: `reconcile("Gula", 25, 25)` returns match=true, shrinkage=false
- [ ] Small discrepancy within 10%: no alert
- [ ] Large discrepancy: shrinkage=true, `discrepancy` correctly calculated
- [ ] Restock detected: actual > expected, `restock=true`, no shrinkage alert
- [ ] `get_expected_stock` returns correct value after sequence of sales + confirmation
- [ ] `confirm_stock` inserts snapshot with `is_confirmation=1`

## Blocked by

03 — needs Sales Data module for last confirmation and sales queries
