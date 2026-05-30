# PRD: Prediksi Stok — AI-based Inventory Prediction System

## Problem Statement

A small shop owner tracks inventory manually on paper. For perishable goods with short shelf lives, overstocking causes financial loss from expired goods, while understocking loses sales. The owner has rough mental estimates of how fast each product sells (e.g., "30 sak of Gula lasts about 7 days"), but no systematic way to predict when to reorder or to detect shrinkage. There is no historical digital sales data — only paper records have ever been kept.

## Solution

A locally-deployed system with two interfaces:

1. **WhatsApp chat bot** — the owner sends real-time sales reports by messaging the bot (e.g., "terjual gula 5"). At end of day, the bot prompts a shelf check; the owner confirms actual stock, and the system reconciles expected vs actual to detect discrepancies. The bot proactively sends depletion alerts and end-of-day reminders.

2. **Web dashboard** — a single-page Streamlit dashboard with simple password auth. Shows inventory overview, depletion predictions, confidence flags, product management forms, and WhatsApp connection status with QR re-pairing.

The system generates synthetic historical data from the owner's estimates to seed a Prophet model at launch, so predictions are available immediately. As real sales data accumulates, synthetic data is phased out via a rolling 90-day window.

## User Stories

1. As a shop owner, I want to send a sales report via WhatsApp ("terjual gula 5, minyak 20"), so that the system tracks what I've sold in real-time.
2. As a shop owner, I want to send sales reports throughout the day as transactions happen, so that the system accumulates accurate daily totals.
3. As a shop owner, I want the bot to prompt me at end of day to confirm shelf stock ("cek stok"), so that I reconcile physical inventory against expected stock.
4. As a shop owner, I want the system to detect discrepancies between expected stock and actual shelf stock, so that I'm alerted to potential theft, spoilage, or recording errors.
5. As a shop owner, I want the system to handle restocks automatically (when I report higher stock than expected during confirmation), so that I don't need a separate "restock" command.
6. As a shop owner, I want to check current predictions anytime by sending "cek stok" via WhatsApp, so that I can see depletion dates and reorder recommendations on demand.
7. As a shop owner, I want the bot to send a proactive depletion alert when a Product's Depletion Date is within a configurable threshold (default: Supplier Lead Time + 2 days), so that I know when to reorder without constant monitoring.
8. As a shop owner, I want the bot to send a daily end-of-day reminder, so that I don't forget to confirm shelf stock.
9. As a shop owner, I want the web dashboard to show all Products with current stock, depletion predictions, trend direction, and confidence flags, so that I can get a visual overview at a glance.
10. As a shop owner, I want the web dashboard to show a confidence flag when stock is unconfirmed (yellow) or when sales data is stale (red), so that I know how reliable the predictions are.
11. As a shop owner, I want to add new Products through the dashboard form, so that I can start tracking new inventory items without editing config files.
12. As a shop owner, I want to edit or remove existing Products through the dashboard form, so that my product catalog stays current.
13. As a shop owner, I want the dashboard to show WhatsApp connection status and provide a QR code for re-pairing if disconnected, so that I can fix connection issues from the dashboard.
14. As a shop owner, I want predictions available from day one, even though I have no historical digital data, so that I don't have to wait weeks for the system to become useful.
15. As a shop owner, I want the system to handle typing mistakes in WhatsApp messages (casing, extra spaces) automatically, so that I don't get frustrated by strict formatting.
16. As a shop owner, I want the system to reject clearly invalid input (negative quantities, missing values) with a clear error message, so that I know what went wrong.
17. As a shop owner, I want to be asked for confirmation if I enter an absurdly high quantity, so that fat-finger errors are caught.
18. As a shop owner, I want predictions to continue even if I miss a day of reporting, with the dashboard showing a confidence flag instead of silently becoming unreliable.
19. As a shop owner, I want the system to survive a machine restart or power loss, with all data persisted in SQLite and auto-recovery on startup.
20. As a shop owner, I want the WhatsApp bot to auto-reconnect if the session drops, so that I don't need to restart the system manually.
21. As a shop owner, I want a one-command setup that generates initial data, starts all services, and shows the QR code for WhatsApp pairing, so that I can get started with minimal effort.
22. As a shop owner, I want the system to keep daily SQLite backups (7 rolling copies), so that historical data is not lost if the database corrupts.

## Implementation Decisions

### Modules

**1. Product Catalog** (`products.json` + dashboard CRUD)
- Static attributes per Product: name, initial stock, unit, depletion window (days), shelf life (days), supplier lead time (days)
- Seeded from `products.json` on first run
- Managed through Streamlit dashboard forms (add, edit, delete)
- Product list used by all other modules as the source of truth for valid Product names

**2. Sales Data** (SQLite — `data/prediksi.db`)
- Stores individual Sales Reports with timestamp, Product, quantity
- Accumulates daily totals per Product for prediction input
- Running expected stock = last confirmed stock - cumulative sales
- Schema: `sales_reports(id, product_name, quantity, reported_at)`, `stock_snapshots(id, product_name, quantity, snapshot_date, is_confirmation)`
- Queries exposed via a data access layer with functions like `record_sale()`, `get_daily_sales()`, `get_expected_stock()`, `get_last_confirmation()`

**3. Stock Reconciliation**
- Triggered by End-of-Day Confirmation
- Compares expected stock vs actual reported stock
- Flags discrepancies above a threshold (configurable, default 10% or 1 unit)
- Updates the new baseline stock for each Product
- Does not treat discrepancy as consumption for velocity calculations

**4. Synthetic Data Generator**
- Called on first run (and when product catalog changes)
- Generates 90 days of daily sales per Product at owner-estimated avg rate
- Injects Gaussian noise + day-of-week variation around the mean
- Output format matches the real Sales Report schema so both can be merged

**5. Prediction Engine** (Prophet)
- Daily sales forecast with day-of-week seasonality
- Three phases: bootstrap (synthetic only), blend (synthetic+real, rolling 90-day window), mature (real only after ≥60 real days)
- Fixed 30-day prediction horizon for all Products
- Depletion Date derived from cumulative forecast crossing current stock
- Retrains after every End-of-Day Confirmation
- Fallback to linear projection (stock / depletion_window) if Prophet fails to converge
- Next retrain cycle re-attempts Prophet; auto-promotes back when successful
- Dashboard flags which phase and fallback status per Product

**6. Input Parser** (WhatsApp message parsing)
- Strict format with silent auto-correction: lowercase, strip extra whitespace
- Handles: `terjual gula 5, minyak 20`, `terjual gula5` (missing space → healed), `Terjual Gula 5` (casing → healed)
- Rejects: unknown product names (returns available products list), negative quantities, missing quantities
- Prompts confirmation on absurd quantities (>10x typical daily sale)
- Accepts zero as valid

**7. WhatsApp Bot** (Node.js — `whatsapp-web.js`)
- Thin microservice: receives messages → POST to FastAPI webhook; receives send requests from Python → sends via WhatsApp
- Auto-reconnect with 5-minute retry window
- On persistent failure: exposes QR re-pairing endpoint consumed by dashboard
- One owner, one phone number

**8. FastAPI Service** (Python)
- Single HTTP server hosting the prediction/sales endpoint and the webhook from WhatsApp
- APScheduler: end-of-day reminder, depletion threshold check, daily SQLite backup, retrain after confirmation
- All business logic coordination lives here

**9. Dashboard** (Streamlit, single page, password auth)
- Table overview: all Products with stock, depletion prediction, trend, confidence flags
- Product management forms (add/edit/delete)
- WhatsApp connection status indicator + QR re-pairing
- Reads/writes shared SQLite database

### Runtime Architecture

- Node microservice ↔ Python FastAPI via HTTP on `localhost` (bidirectional: Node POSTs incoming messages to FastAPI; FastAPI calls Node endpoint to trigger outgoing messages)
- APScheduler in the FastAPI process handles all timed jobs
- Dashboard and FastAPI share the same SQLite database (dashboard is read-write for product catalog, read-only for sales/prediction data)
- Single-command setup: generates synthetic data → trains initial models → starts FastAPI → starts Node → prints WhatsApp QR

### Input Validation Rules

| Input | Action |
|---|---|
| Negative quantity | Reject with error |
| Zero quantity | Accept (valid — no sales recorded) |
| Absurd quantity (>10x daily avg) | Ask confirmation ("y" to accept) |
| Unknown product name | Reject, list available Products |
| Missing quantity | Reject with format reminder |
| Extra whitespace / wrong casing | Auto-correct silently |

### Prediction Phasing

| Phase | Condition | Data Source | Window |
|---|---|---|---|
| Bootstrap | Launch | Synthetic only | N/A |
| Blend | 1-59 real days | Synthetic + real merged | 90-day rolling |
| Mature | ≥60 real days | Real only | 90-day rolling |

## Testing Decisions

- **Test external behavior, not implementation details.** A test for "given these Sales Reports, the expected stock equals X" is good. A test for "the Prediction Engine calls Prophet.train() with exactly these params" is not.
- **Prediction Engine** — test: fallback triggers when Prophet errors, depletion date moves correctly as stock changes, phase transitions work, blended prediction with known synthetic+real data gives expected results, 30-day horizon correctly shows ">30 days" when stock exceeds forecast. Use dependency injection to pass a mock or wrapper around Prophet so tests don't require the actual prophet C compiler.
- **Input Parser** — test: all correction rules (casing, spacing), all rejection cases (negative, missing, unknown), confirmation prompt for absurd values. The parser is pure string → structured data, so it's fast and deterministic.
- **Sales Data** — test: record retrieval by date range, daily aggregation correctness, expected stock calculation with known sales sequence. Use an in-memory SQLite for test isolation.
- **Stock Reconciliation** — test: exact match produces no alert, small discrepancy below threshold produces no alert, large discrepancy above threshold flags correctly, restock (actual > expected) updates baseline without alert.
- **Synthetic Data Generator** — test: output has correct number of days for each Product, daily values are non-negative, weekly average matches the owner estimate within statistical bounds, day-of-week pattern is present.
- **WhatsApp Bot** — not unit tested (I/O-heavy). Tested via integration with the FastAPI webhook endpoint.
- **Dashboard** — not unit tested (UI-heavy).
- **Syntax/lint**: no test infrastructure exists yet.

## Out of Scope

- Multi-shop or multi-user deployment
- Mobile app (native or otherwise) — WhatsApp is the mobile interface
- Automatic data import from POS systems or existing digital records
- Real-time inventory tracking via IoT/barcode scanning
- Financial calculations (profit margins, cost of goods sold, ROI)
- Supplier management or purchase order generation
- Complex ML models beyond Prophet (LSTM, ARIMA, etc.) — deferred until sufficient real data exists
- Multi-currency or multi-unit conversion
- SMS or Telegram bot (WhatsApp only)
- Cloud hosting or remote access — local deployment only

## Further Notes

- All consumption rates start as owner estimates. The system is honest about this: predictions from synthetic data are not presented as "trained on real data." The dashboard indicates which phase each Product is in.
- The "Depletion Date" is the core concept users will interact with. All UI and alerts center around this single number.
- The system should gracefully handle a scenario where the owner stops using it entirely for weeks — predictions continue from the last good data point with red confidence flags, and the end-of-day reminder fires daily.
- If the product catalog is edited (add/remove product), synthetic data is regenerated for new products only. Existing products retain their real data.
