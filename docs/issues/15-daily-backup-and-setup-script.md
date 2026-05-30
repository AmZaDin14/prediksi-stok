# 15 - Daily backup + one-command setup script

**Type:** AFK

## Parent

PRD.md

## What to build

Two operational pieces: automated backups and a single setup command.

**Daily SQLite backup (APScheduler job):**
- Runs daily after EOD confirmation (or at midnight)
- Copies `data/prediksi.db` to `data/backups/prediksi-YYYY-MM-DD.db`
- Keeps 7 most recent backups, deletes oldest beyond that
- Backup failures logged but do not crash the scheduler

**One-command setup script (`python setup.py`):**
- Check if `products.json` exists; if not, scaffold with defaults from info.md
- Create SQLite schema (if not exist)
- Generate synthetic data (skip if already exists and catalog unchanged)
- Train initial Prophet models for all products
- Start FastAPI server (subprocess or `uvicorn.run`)
- Start Node WhatsApp bot (subprocess)
- Print QR pairing instructions
- Print Streamlit run command (or auto-launch)

Flags:
- `--reset` — regenerate everything (delete existing data)
- `--skip-whatsapp` — skip Node bot startup (for development)

## Acceptance criteria

- [ ] Backup job creates timestamped `.db` copy
- [ ] Only 7 most recent backups are retained
- [ ] Backup failure doesn't crash scheduler
- [ ] `python setup.py` scaffolds products.json, creates DB, generates synthetic data, trains models
- [ ] `python setup.py --reset` removes existing data and starts fresh
- [ ] `python setup.py --skip-whatsapp` starts everything except Node bot
- [ ] Setup script exits with clear instructions for next step

## Blocked by

01 — needs project scaffold and schema
02 — needs Synthetic Data Generator
07 — needs prediction working (for model training in setup)
09 — needs WhatsApp bot (for --skip-whatsapp flag)
