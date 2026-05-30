"""FastAPI server for Prediksi Stok webhook.

Handles incoming WhatsApp messages: sales reports (``terjual``),
stock status queries (``cek stok``), and unknown command fallback.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import json
import os
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI
from pydantic import BaseModel

from app.data import get_daily_sales, get_expected_stock, get_pending_outgoing, queue_outgoing_message, record_sale
from app.parser import parse_sales_message
from app.predictor import PredictionResult, predict_product, train_all_products

# --- Config from environment -------------------------------------------
DB_PATH = os.environ.get("DB_PATH", "data/prediksi.db")
PRODUCTS_FILE = os.environ.get("PRODUCTS_FILE", "products.json")
FASTAPI_PORT = int(os.environ.get("FASTAPI_PORT", "8765"))


def _load_products() -> dict:
    """Load product catalog from JSON file."""
    with open(PRODUCTS_FILE) as f:
        return json.load(f)


def _get_valid_products() -> list[str]:
    """Return list of canonical product names."""
    return list(_load_products().keys())


def _get_daily_estimates() -> dict[str, float]:
    """Return mapping of lowercase product name to estimated daily sales.

    Estimate = initial_stock / depletion_window_days.
    """
    products = _load_products()
    estimates: dict[str, float] = {}
    for name, attrs in products.items():
        window = attrs["depletion_window_days"]
        estimates[name.lower()] = attrs["initial_stock"] / window if window > 0 else 0
    return estimates


# --- FastAPI app --------------------------------------------------------

app = FastAPI(title="Prediksi Stok")


class WebhookMessage(BaseModel):
    from_number: str
    body: str


class WebhookResponse(BaseModel):
    status: str
    response: str


@app.post("/webhook")
async def webhook(msg: WebhookMessage) -> WebhookResponse:
    """Handle incoming WhatsApp messages."""
    body = msg.body.strip().lower()

    if body == "cek stok":
        return _handle_cek_stok()

    if body.startswith("terjual"):
        return _handle_terjual(msg.body)

    return WebhookResponse(
        status="error",
        response=(
            "Maaf, perintah tidak dikenal. Kirim 'terjual [produk] [jumlah]' "
            "untuk mencatat penjualan, atau 'cek stok' untuk status."
        ),
    )


# --- Handlers ----------------------------------------------------------

def _handle_cek_stok() -> WebhookResponse:
    """Build status overview for all products using prediction engine."""
    products = _load_products()
    lines: list[str] = []

    for name, attrs in products.items():
        unit = attrs["unit"]
        stock = get_expected_stock(DB_PATH, name)
        if stock is None:
            stock = float(attrs["initial_stock"])

        pred = predict_product(DB_PATH, attrs, name)

        icon = "   " if pred.confidence == "high" else " ?" if pred.confidence == "medium" else "??"
        trend_chr = {"up": "\U0001f53c", "down": "\U0001f53d", "stable": "→"}.get(pred.trend, "")

        dep = pred.depletion_date if pred.depletion_days else "N/A"
        phase_chr = {"bootstrap": "B", "blend": "BL", "mature": "M"}.get(pred.phase, "?")

        lines.append(
            f"{icon} {name}: {stock:.0f} {unit} "
            f"| habis: {dep} {trend_chr}"
            f" | {phase_chr}/{pred.confidence}"
        )

    return WebhookResponse(status="ok", response="\n".join(lines))


def _handle_terjual(raw_text: str) -> WebhookResponse:
    """Process a ``terjual`` sales report."""
    valid_products = _get_valid_products()
    daily_estimates = _get_daily_estimates()

    result = parse_sales_message(raw_text, valid_products, daily_estimates)

    if result.errors:
        return WebhookResponse(
            status="error",
            response="; ".join(result.errors),
        )

    now = datetime.now(timezone.utc).isoformat()
    today_str = date.today().isoformat()
    products = _load_products()
    sale_parts: list[str] = []

    # Record each sale, building response parts
    all_entries = result.sales + result.needs_confirmation
    for product_name, qty in all_entries:
        record_sale(DB_PATH, product_name, qty, now)

        unit = products.get(product_name, {}).get("unit", "")
        today_sales = get_daily_sales(DB_PATH, product_name, today_str, today_str)
        total_today = sum(s["total_quantity"] for s in today_sales)

        part = f"{product_name} +{qty:.0f} {unit} (total hari ini: {total_today:.0f})"
        sale_parts.append(part)

    if not sale_parts:
        return WebhookResponse(
            status="error",
            response="Tidak ada penjualan yang valid untuk dicatat.",
        )

    return WebhookResponse(status="ok", response="OK. " + ", ".join(sale_parts))


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Prediction endpoints ------------------------------------------------


@app.get("/predict/{product_name}")
async def predict_single(product_name: str) -> PredictionResult:
    """Get depletion prediction for a single product."""
    products = _load_products()
    if product_name not in products:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Product '{product_name}' not found")
    return predict_product(DB_PATH, products[product_name], product_name)


@app.get("/predict")
async def predict_all() -> dict[str, PredictionResult]:
    """Get depletion predictions for all products."""
    products = _load_products()
    results: dict[str, PredictionResult] = {}
    for name, config in products.items():
        results[name] = predict_product(DB_PATH, config, name)
    return results


@app.get("/outgoing")
async def get_outgoing(recipient: str | None = None) -> list[dict]:
    """Get pending outgoing WhatsApp messages (marks them sent)."""
    return get_pending_outgoing(DB_PATH, recipient)
