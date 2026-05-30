# 03 - Sales Data module + Dashboard overview

**Type:** AFK

## Parent

PRD.md

## What to build

Data access layer for sales records and stock snapshots, plus the initial Streamlit dashboard.

**Sales Data module:**
- `record_sale(product_name, quantity, timestamp)` — inserts into `sales_reports`
- `get_daily_sales(product_name, from_date, to_date)` — aggregates daily totals
- `get_expected_stock(product_name)` — last confirmed stock minus cumulative sales since
- `get_last_confirmation(product_name)` — most recent stock snapshot with `is_confirmation=1`
- Uses Python stdlib `sqlite3`, accepts a connection parameter for testability

**Dashboard:**
- Streamlit app with simple password auth (hardcoded env var or config)
- Single page: table of all Products from `products.json` with current stock levels
- Stock level sourced from last confirmation, falling back to `products.json` initial stock
- No predictions yet — just static stock display

## Acceptance criteria

- [ ] `record_sale` correctly inserts and timestamps
- [ ] `get_daily_sales` returns correct daily aggregation for a date range
- [ ] `get_expected_stock` calculates correctly for a known sequence of sales + confirmation
- [ ] `get_last_confirmation` returns most recent confirmation (or None if none exist)
- [ ] Dashboard starts with `streamlit run dashboard.py` and shows password prompt
- [ ] Dashboard table shows all 7 products with current stock

## Blocked by

01 — needs SQLite schema
