# Prediksi Stok

AI-based inventory prediction system for stores/warehouses. Predicts when stock will run out using historical sales data, minimizing overstock (especially for short-expiry goods) and stockouts.

## Tech Stack

- **WhatsApp connectivity**: `whatsapp-web.js` (Node.js microservice)
- **Core logic & ML**: Python — `prophet` for time-series forecasting
- **Dashboard**: `streamlit` with simple password auth
- **Persistence**: SQLite via Python stdlib `sqlite3`
- **Product Catalog**: JSON config file (`products.json`)

## Language

**Product**:
A distinct SKU tracked as aggregate stock quantity (e.g., "30 sak of Gula", "1000 dus of Minyak"). Not an individually serialized unit.
_Avoid_: Item, barang, SKU (use Product instead)

**Depletion Date**:
The predicted date when a Product's stock will reach zero, based on historical consumption velocity. Primary output of the prediction engine.
_Avoid_: Stockout date, empty date

**Sales Report**:
A manual record of quantity sold for one or more Products. Sent via WhatsApp at any time (e.g., "terjual gula 5, minyak 20"). This is the primary signal for consumption velocity.
_Avoid_: Stock snapshot, inventory update

**End-of-Day Confirmation**:
A periodic reconciliation step triggered by the bot at the end of each day. The bot asks "cek stok" and the owner physically checks shelves and reports current stock. This detects loss/shrinkage (expected vs actual), confirms inventory accuracy after restocks, and sets the baseline for the next day's velocity calculation.

**Product Catalog**:
The set of tracked Products and their static attributes (name, initial stock, unit, depletion window, shelf life, supplier lead time). Seeded from a JSON config file, manageable through dashboard form.
_Avoid_: Managed through chat

**Unit**:
The measurement unit for a Product's quantity (sak, dus, ton, kg, pak). Display-only metadata — no conversion math performed across units.

**Supplier Lead Time**:
The estimated days between placing a reorder and receiving goods. Per-product estimate, 1-5 day range. Used to calculate Reorder Point from Depletion Date.

**Shelf Life**:
The maximum days a Product remains sellable. If consumption-based depletion would exceed Shelf Life, the Depletion Date is capped at Shelf Life (goods expire before selling out).

## Interaction Model

The owner interacts with the system through two channels:

- **WhatsApp chat bot** (primary input) — running locally via WhatsApp Web automation (`whatsapp-web.js` in Node). All data entry: sales reports and end-of-day confirmations. Single-owner, single-shop deployment.
- **Web dashboard** (single page) — Python via `streamlit` with simple password auth. Shows inventory overview, predictions, trends, confidence flags, product management forms, and WhatsApp connection status with QR re-pairing. Consumes the same SQLite database.

**Runtime split:** WhatsApp connectivity is a thin Node microservice. All business logic, prediction, and persistence is Python. Node ↔ Python communication via FastAPI HTTP endpoint on `localhost`. Python triggers outgoing WhatsApp messages by calling a small HTTP endpoint on the Node service.

**Inputs:**
- Sales reports (voluntary, anytime): `terjual <product> <qty>[, ...]`
- End-of-day confirmation (bot-prompted): owner reports current shelf stock per product

**Outputs:**
- Depletion alerts (proactive)
- End-of-day reminder (proactive, daily)
- Status report (on demand via `cek stok`)

## Commands (v1 surface)

- **Sales report**: `terjual <product> <qty>[, <product> <qty>...]` — records quantity sold since last report
- **End-of-day confirmation**: Bot prompts `cek stok` → owner responds with current shelf stock for each Product
- **Status overview**: Owner can also send `cek stok` anytime to see current predictions and reorder recommendations

**Reorder Point**:
A derived recommendation specifying quantity to order and target reorder date, informed by Depletion Date plus supplier lead time. Secondary output.
_Avoid_: Order trigger, threshold

**Alert**:
A proactive WhatsApp message from the bot. Two types: (1) **Depletion Alert** — fires when a Product's Depletion Date is within a configurable threshold (default: Lead Time + 2 days buffer); (2) **End-of-Day Reminder** — fires daily to prompt the End-of-Day Confirmation.

## Persistence

- **Product Catalog**: JSON config file (`products.json`), version-controlled
- **Sales Data**: SQLite database (`data/prediksi.db`) — stores daily sales reports with per-product quantities and timestamps
- **End-of-Day Confirmations**: Same SQLite database — stores shelf stock snapshots reconciled against expected values

## Runtime

- **Scheduling**: Python `APScheduler` runs in the FastAPI process. Jobs: end-of-day reminder (daily), depletion threshold check, retrain after confirmation, SQLite backup (daily, keeps 7 rolling copies).
- **Input parsing**: Strict format with silent auto-correction for casing and whitespace. Unknown product names are rejected with a list of available products.
- **Setup flow**: Single command generates synthetic data, trains initial models, starts services, and prints WhatsApp QR pairing code.
- **Prophet failure fallback**: If prophet fails to converge for a product, fall back to Phase 1 linear projection from owner estimates. No prediction gap. Auto-retry prophet on next retrain cycle. Dashboard flags the fallback status.
- **WhatsApp reconnection**: Auto-reconnect on disconnect. After 5 min of failed reconnection, dashboard shows connection status and QR code for manual re-pairing.

## Derivation

All consumption rates are owner estimates, not calculated from historical sales data. The prediction engine cannot train on past data — no digital records exist. Initial predictions use manual depletion windows; predictions will improve as the system accumulates snapshot data over time.

## Daily Data Flow

1. Owner sends sales reports in real-time as transactions happen: `terjual gula 5` → later `terjual gula 3, minyak 20`
2. System accumulates daily sales per Product. Running expected stock = last confirmed stock - cumulative sales
3. At end of day, bot prompts `cek stok` — owner physically checks shelves and reports current stock per Product
4. System reconciles: expected stock vs actual. Discrepancy flags potential loss/theft/spoilage
5. Actual stock becomes the new baseline for next day's velocity calculation
6. Daily sales totals feed velocity calculation
7. **Missed day handling:** If owner misses End-of-Day Confirmation → keep predicting from last known stock, dashboard shows yellow confidence flag ("stock unconfirmed"). If no sales data for a day → prediction continues, dashboard shows red flag ("no data for N days")

## Prediction Approach

**Phasing:**

| Phase | Condition | Data | Method |
|---|---|---|---|
| Bootstrap | Launch | Synthetic only (generated from owner estimates) | ML model trained on synthetic daily sales |
| Blend | 1-59 real days per product | Synthetic + real combined, rolling window | Re-train ML on merged data; synthetic dropped from window as real data fills it |
| Mature | ≥60 real days per product | Real only | ML model trained on real daily sales only |

**Synthetic data generation:** Auto-generated on first run from `products.json`. Each Product gets N days of daily sales at owner-estimated avg rate with injected noise and day-of-week variation. Re-generated if product catalog changes.

**Rolling window:** Fixed-size window (90 days). As real sales records fill the window, oldest entries (synthetic first, then earliest real) are evicted. Once ≥60 days of real data exist, no synthetic data remains.

**Model:** Daily sales forecast with day-of-week feature. Depletion Date derived by cumulative forecast crossing current stock.

**Prediction horizon:** Fixed 30 days ahead for all Products. Depletion date is where cumulative forecast crosses current stock. If stock exceeds 30-day forecast, shows ">30 days" with trend direction.

**Retrain cadence:** After every End-of-Day Confirmation. Model retrains on the latest data window for each Product.

## Example Dialogue

**Dev**: How do I record today's sales?
**Owner**: I send "terjual gula 5, minyak 20". At end of day, bot asks me to check shelves.
**Dev**: What if I sold 5 but 2 more were damaged?
**Owner**: I report actual stock as-is during cek stok. The system sees 7 missing but only counts 5 toward velocity.
**Dev**: What if a new shipment arrived?
**Owner**: My shelf stock will be higher than expected. The system handles it — it trusts the physical count as the new baseline.
