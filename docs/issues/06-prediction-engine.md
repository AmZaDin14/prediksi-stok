# 06 - Prediction Engine

**Type:** AFK

## Parent

PRD.md

## What to build

Core prediction module using Prophet with 3-phase training.

Module interface:
- `train_product(product_name, daily_sales_data)` — trains/retrains Prophet model
- `predict_product(product_name, horizon_days=30)` — returns daily forecast
- `get_depletion_date(product_name, current_stock)` — where cumulative forecast crosses stock
- `get_phase(product_name)` — returns "bootstrap", "blend", or "mature"

**Phases:**
- Bootstrap: only synthetic data in training set
- Blend: synthetic + real merged. Rolling 90-day window. Oldest entries dropped first (synthetic oldest evicted first). Real days < 60.
- Mature: real data only, ≥60 real days of sales. Rolling 90-day window.

**Training:**
- Prophet with `daily_seasonality=False`, `weekly_seasonality=True` (day-of-week)
- Fit on daily aggregated sales (date, quantity_ds, quantity_y)
- Serialize model to `data/models/<product>_prophet.pkl` for fast reload

**Fallback:**
- If Prophet.fit() fails to converge (exception): fall back to linear projection
- Linear: daily_avg = (sum of sales over window) / (days in window), depletion = current_stock / daily_avg
- Retry Prophet on next train cycle
- Dashboard flags fallback status

## Acceptance criteria

- [ ] Bootstrap phase: trains on synthetic data only, produces reasonable forecast
- [ ] Blend phase: mixed data produces forecast closer to real than synthetic alone
- [ ] Mature phase: real data only after ≥60 real days
- [ ] Fallback: when Prophet errors, linear projection returns sensible depletion date
- [ ] Fallback retries Prophet on next train cycle, re-promotes on success
- [ ] `get_depletion_date` returns correct day count for known stock + forecast
- [ ] Model serialization/deserialization works across restarts
- [ ] Rolling window evicts oldest entries correctly

## Blocked by

02 — needs Synthetic Data Generator to seed training
03 — needs Sales Data module for real sales access
