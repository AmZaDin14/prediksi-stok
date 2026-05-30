# 02 - Synthetic Data Generator

**Type:** AFK

## Parent

PRD.md

## What to build

A module that generates synthetic daily sales data from `products.json` owner estimates. Called on first run and when new Products are added.

Module interface:
- `generate_synthetic_data(products: list[Product], days: int = 90) -> list[DailySale]`
- For each Product: compute daily avg = initial_stock / depletion_window_days
- Inject Gaussian noise (stddev = 0.15 * mean)
- Inject day-of-week variation (weekdays +10%, weekends -20%)
- All values are non-negative (floor at 0)
- Output is a list of records matching the `sales_reports` schema shape

Write the generated records directly to the `sales_reports` table with `reported_at` timestamps on the generated dates.

## Acceptance criteria

- [ ] 90 days of synthetic data generated for each of the 7 default Products
- [ ] Daily values are non-negative
- [ ] Weekly average for each Product matches owner estimate within 5%
- [ ] Day-of-week pattern visible: weekends lower than weekdays
- [ ] Repeated generation with same seed produces identical output
- [ ] Generates only for new products when catalog changes (existing products untouched)

## Blocked by

01 — needs SQLite schema and products.json
