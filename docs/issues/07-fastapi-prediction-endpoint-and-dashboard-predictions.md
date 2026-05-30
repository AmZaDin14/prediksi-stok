# 07 - FastAPI prediction endpoint + Dashboard predictions

**Type:** AFK

## Parent

PRD.md

## What to build

Expose prediction results through FastAPI and show them on the dashboard.

**FastAPI:**
- `GET /predict/<product_name>` — returns depletion date, days remaining, phase, trend, confidence flag
- `GET /predict` — returns predictions for all products
- Responses include: `{ "product": "Gula", "depletion_days": 7, "depletion_date": "2026-06-05", "phase": "bootstrap", "trend": "stable", "confidence": "high" }`

**Dashboard:**
- Table columns: Product, Current Stock, Depletion (days), Phase, Confidence, Trend Arrow
- Color coding: green (>2x lead time), yellow (within depletion alert threshold), red (past depletion date)
- Confidence flags: "high" (confirmed stock, recent data), "yellow" (stock unconfirmed), "red" (stale data >N days)
- Phase shown as badge (Bootstrap/Blend/Mature)
- Trend: up/down/stable arrow based on forecast slope

## Acceptance criteria

- [ ] `GET /predict/<product>` returns correct depletion data from Prediction Engine
- [ ] `GET /predict` returns predictions for all products
- [ ] Dashboard table populates from `/predict` endpoint
- [ ] Color coding works correctly for each threshold
- [ ] Confidence flags display correctly based on stock confirmation and data freshness
- [ ] Phase badges display correctly
- [ ] Trend arrows display correctly

## Blocked by

06 — needs Prediction Engine
