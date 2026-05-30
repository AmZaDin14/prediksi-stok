# 12 - Dashboard product management

**Type:** AFK

## Parent

PRD.md

## What to build

Forms on the Streamlit dashboard for managing the product catalog.

**Features:**
- **Add Product** form: name, initial stock, unit (dropdown: sak/dus/ton/kg/pak), depletion window (days), shelf life (days), lead time (days)
- **Edit Product** form: same fields pre-populated
- **Delete Product** button with confirmation dialog
- All changes write to `products.json` (preserve formatting and existing data)
- Validation: name required and unique, all numeric fields > 0

**Side effects:**
- Add new product → regenerate synthetic data for that product only (call Synthetic Data Generator)
- Delete product → remove its sales records from SQLite (cascade) — prompt confirmation that history will be lost
- Edit → no data regeneration unless depletion window changed significantly (>20% change), in which case re-generate synthetic data for that product

**Auth:** existing password gate from issue 03 still applies.

## Acceptance criteria

- [ ] Add form writes new product to `products.json` correctly
- [ ] Edit form modifies existing product in `products.json`
- [ ] Delete removes product from `products.json` and confirms
- [ ] Validation rejects empty name, duplicate name, zero/negative values
- [ ] New product gets synthetic data generated
- [ ] Dashboard reflects changes immediately (re-reads `products.json`)

## Blocked by

03 — needs dashboard running
