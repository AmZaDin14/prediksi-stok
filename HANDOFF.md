# Handoff: Prediksi Stok

## Session Summary

Full design and planning session for an AI-based inventory prediction system. Everything is designed, nothing is built — the repo is a scaffold (`main.py` prints "Hello from prediksi-stok!").

## What Was Produced

| Artifact | Path | Content |
|---|---|---|
| Domain glossary | `CONTEXT.md` | All domain terms, interaction model, daily flow, prediction approach, tech stack, runtime decisions |
| Agent guide | `CLAUDE.md` | Project overview, commands, architecture, structure |
| PRD (EN) | `PRD.md` | Full problem statement, 22 user stories, module specs, validation rules, testing decisions |
| PRD (ID) | `PRD_id.md` | Indonesian translation of PRD |
| Issues (15) | `docs/issues/01-*.md` through `docs/issues/15-*.md` | Vertical-slice issues with AFK/HITL types, dependencies, acceptance criteria |

## Key Design Decisions (not duplicated in CONTEXT.md)

- **Data origin**: No historical data. Owner estimates only. Synthetic data generated on first run to bootstrap Prophet.
- **Prediction phases**: Bootstrap (synthetic) → Blend (synthetic+real, 90-day rolling) → Mature (real only, ≥60 days).
- **Input mechanism**: WhatsApp bot (`whatsapp-web.js` in Node microservice) + FastAPI webhook in Python.
- **Runtime split**: Node only handles WhatsApp I/O. Python (FastAPI + APScheduler) handles all business logic, ML, scheduling.
- **Node ↔ Python**: Bidirectional HTTP on localhost. Node POSTs incoming messages to FastAPI `/webhook`. Python calls Node `/send` endpoint for outgoing messages.
- **Dashboard**: Streamlit, single page, password auth, product management forms + read-only predictions.
- **Reconciliation**: End-of-day confirmation compares expected stock vs actual. Detects shrinkage/restock separately from sales velocity.
- **Missed days**: Predictions continue with degraded confidence flags (yellow=unconfirmed stock, red=stale data).
- **Backup**: Daily APScheduler job, 7 rolling SQLite copies.
- **No ML models beyond Prophet** — explicitly deferred.

## Issue Dependency Order (recommended execution)

```
01 (scaffold) ─┬─ 02 (synthetic data) ──┐
               ├─ 03 (sales data + dashboard) ─┬─ 10 (reconciliation)
               └─ 04 (parser) ──┬─ 05 (webhook) ──┬─ 08 (WhatsApp recv) ── 09 (WhatsApp send) ─┬─ 11 (EOD flow)
                                │                  │                                            ├─ 13 (alerts)
                                │                  │                                            └─ 14 (dashboard status)
                                └─ 06 (prediction) ── 07 (prediction endpoint + dashboard)
```

Issues 12 (product mgmt) and 15 (backup + setup script) have lighter dependencies.

## What the Next Agent Needs to Know

- **No remote configured** — `gh` is authenticated as AmZaDin14 but no git remote exists. Issues are local files only. User may push to GitHub later.
- **Python 3.14** via `uv`. **Node** via `npm` in `whatsapp-bot/` directory.
- **No code written yet** — everything is design docs. First task: implement issue 01 (scaffold).
- **Language preference**: Indonesian for UI text (WhatsApp messages, dashboard labels). Code and technical comments in English.
- **User**: responsive to concise questions, prefers recommendations over open-ended questions, grounded in this project (not generic advice).

## Suggested Skills

- `/init` — to initialize CLAUDE.md if more structure is added
- `/tdd` — for test-first development of modules like Input Parser and Stock Reconciliation
- `/simplify` — for code review and cleanup
- `/verify` — to test the running system end-to-end
- `/code-review` — before merging any PRs
- `/grill-with-docs` — if new domain questions arise during implementation
- `/caveman` — user prefers ultra-concise communication

## Sensitive Info

- GitHub token is scoped for public repos only (no write access to private)
- No API keys, passwords, or PII in any artifact
- Dashboard password is not yet configured (will be env var)
