# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prediksi Stok — AI-based inventory prediction system for stores/warehouses. Predicts when stock will run out using historical sales data, minimizing overstock (especially for short-expiry goods) and stockouts.

## Stack

- **WhatsApp connectivity**: Node.js — `whatsapp-web.js`
- **Core logic & ML**: Python >=3.14 — `prophet` for forecasting
- **Dashboard**: Python — `streamlit`
- **Persistence**: SQLite (Python stdlib `sqlite3`)
- **Product Catalog**: JSON config (`products.json`)
- **Package manager**: `uv` (Python), `npm` (Node)

## Commands

```bash
uv run main.py              # Run Python app (prediction, scheduler)
uv add <package>            # Add Python dependency
uv sync                     # Sync Python environment

cd whatsapp-bot && npm i    # Install Node WhatsApp microservice
node whatsapp-bot/index.js  # Start WhatsApp bot

streamlit run dashboard.py  # Launch web dashboard
```

No test/lint infrastructure exists yet.

## Current State

Scaffold only — `main.py` just prints "Hello from prediksi-stok!". No models, no data pipeline, no prediction logic.

## Domain Context (from info.md)

Perishable/short-expiry goods tracked by stock level and typical depletion time:

| Item | Current Stock | Depletion Window |
|------|--------------|-----------------|
| Gula (sugar) | 30 sak | 7 days |
| Minyak (oil) | 1000 dus | 14 days |
| Tepung (flour) | 300 | 14 days |
| Beras (rice) | 3 ton | 7 days |
| Aqua (water) | 300 dus | 14 days |
| Roti hitam manis (bread) | 35 dus | 30 days |
| Garam (salt) | 500 pak | 7 days |

Core problem: overstocking short-expiry goods causes losses; understocking loses sales. System should predict optimal reorder timing per product.

## Architecture

### Channels
- **WhatsApp bot** (primary input) — Sales reports (`terjual`) and end-of-day stock confirmations
- **Web dashboard** (read-only) — Visualization of predictions, trends, stock levels

### Data Flow
1. Owner sends `terjual <product> <qty>` messages via WhatsApp throughout the day
2. System accumulates daily sales per product, tracks expected stock = last confirmed - sales
3. At end of day, bot prompts `cek stok` → owner reports actual shelf stock
4. System reconciles expected vs actual (detects shrinkage/restocks), sets new baseline
5. Velocity calculated from sales data (Phase 1: owner estimates; Phase 2: blended measured velocity after ≥10 days)

### Storage
- **Product Catalog**: `products.json` (static attributes per product)
- **SQLite**: `data/prediksi.db` (sales records, stock confirmations)

### Prediction
- Bootstrap: synthetic historical data generated from owner estimates, ML model trained at launch
- Blend: retrain on synthetic + real combined, rolling window phases synthetic out
- Mature: ML on real daily sales only (≥60 days per product)
- Features: day-of-week, daily sales volume. Forecast next N days → derive depletion date

## Project Structure

```
pyproject.toml           # Python project config, dependencies
main.py                  # Python entry point (scheduler, prediction)
products.json            # Product catalog config
CONTEXT.md               # Domain glossary & design decisions
data/prediksi.db         # SQLite (sales, stock confirmations)
dashboard.py             # Streamlit dashboard

whatsapp-bot/
  index.js               # Node microservice: WhatsApp connectivity
  package.json           # Node dependencies (whatsapp-web.js)
```
