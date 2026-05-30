# 01 - Project scaffold + SQLite schema

**Type:** AFK

## Parent

PRD.md

## What to build

Set up the Python and Node project shells and the database schema.

- Python: `pyproject.toml` with `fastapi`, `uvicorn`, `prophet`, `streamlit`, `apscheduler` deps. Managed via `uv`.
- Node: `whatsapp-bot/package.json` with `whatsapp-web.js` dep. Managed via `npm`.
- SQLite schema in `data/prediksi.db` with two tables:
  - `sales_reports(id INTEGER PK, product_name TEXT NOT NULL, quantity REAL NOT NULL, reported_at TEXT NOT NULL)`
  - `stock_snapshots(id INTEGER PK, product_name TEXT NOT NULL, quantity REAL NOT NULL, snapshot_date TEXT NOT NULL, is_confirmation INTEGER NOT NULL DEFAULT 0)`
- `products.json` with the 7 default products from info.md (Gula, Minyak, Tepung, Beras, Aqua, Roti hitam manis, Garam) with their initial stock, unit, depletion_window_days, shelf_life_days, supplier_lead_time_days attributes.
- Create `docs/adr/` directory for future ADRs.
- `.gitignore` already covers Python + Node artifacts.

No business logic yet — just the skeleton that everything else plugs into.

## Acceptance criteria

- [ ] `uv sync` installs all Python dependencies without error
- [ ] `cd whatsapp-bot && npm i` installs all Node dependencies without error
- [ ] Running a setup script creates `data/prediksi.db` with both tables
- [ ] `products.json` has all 7 products with correct attributes
- [ ] Schema columns are correct types and constraints

## Blocked by

None — can start immediately
