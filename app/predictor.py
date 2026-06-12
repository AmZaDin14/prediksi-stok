"""Prediction engine using Prophet with 3-phase training.

Phases:
- bootstrap: synthetic data only (launch)
- blend: synthetic + real combined (1-59 real days)
- mature: real data only (>=60 real days)
"""

from __future__ import annotations

import os
import pickle
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from prophet import Prophet

from app.data import get_daily_sales, get_expected_stock

DEFAULT_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


@dataclass
class PredictionResult:
    product: str
    depletion_days: Optional[int]
    depletion_date: str
    phase: str
    trend: str
    confidence: str
    fallback_active: bool


def _trend_from_forecast(forecast) -> str:
    """Determine trend from last 7 days of forecast."""
    tail = forecast.tail(7)
    if len(tail) < 2:
        return "stable"
    first = tail.iloc[0]["yhat"]
    last = tail.iloc[-1]["yhat"]
    if first == 0:
        return "stable"
    pct_change = (last - first) / abs(first)
    if pct_change > 0.05:
        return "up"
    if pct_change < -0.05:
        return "down"
    return "stable"


def get_phase(db_path: str, product_name: str) -> str:
    """Determine training phase based on days of real sales data."""
    daily = get_daily_sales(db_path, product_name, "2000-01-01", date.today().isoformat())
    real_days = len(daily)
    if real_days == 0:
        return "bootstrap"
    if real_days < 60:
        return "blend"
    return "mature"


def train_product(
    db_path: str,
    product: dict,
    product_name: str,
    synthetic_data: Optional[list[dict]] = None,
    models_dir: Optional[str] = None,
) -> None:
    """Train Prophet model for a single product."""
    phase = get_phase(db_path, product_name)
    md = models_dir or DEFAULT_MODELS_DIR
    os.makedirs(md, exist_ok=True)

    real = get_daily_sales(db_path, product_name, "2000-01-01", date.today().isoformat())

    df_rows = []
    if phase in ("bootstrap", "blend") and synthetic_data:
        for row in synthetic_data:
            if row["product_name"] == product_name:
                dt = datetime.fromisoformat(row["reported_at"])
                df_rows.append({"ds": dt, "y": row["quantity"]})

    # Add real data (overwrites synthetic for same dates in blend)
    seen_dates = {r["ds"].date() for r in df_rows}
    for row in real:
        d = datetime.strptime(row["sale_date"], "%Y-%m-%d")
        if phase == "blend" and d.date() not in seen_dates:
            df_rows.append({"ds": d, "y": row["total_quantity"]})
        elif phase == "mature":
            df_rows.append({"ds": d, "y": row["total_quantity"]})
        elif phase == "blend":
            # Replace synthetic with real for matching dates
            df_rows = [r for r in df_rows if r["ds"].date() != d.date()]
            df_rows.append({"ds": d, "y": row["total_quantity"]})

    if not df_rows:
        return

    import pandas as pd
    df = pd.DataFrame(df_rows).sort_values("ds").reset_index(drop=True)

    try:
        model = Prophet(weekly_seasonality=True, daily_seasonality=False)
        model.fit(df)
        model_path = os.path.join(md, f"{product_name}.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
    except Exception:
        pass  # fallback handled at prediction time


def predict_product(
    db_path: str,
    product: dict,
    product_name: str,
    horizon_days: int = 30,
    models_dir: Optional[str] = None,
) -> PredictionResult:
    """Predict depletion date for a product."""
    current_stock = get_expected_stock(db_path, product_name)
    if current_stock is None:
        current_stock = float(product["initial_stock"])

    phase = get_phase(db_path, product_name)
    md = models_dir or DEFAULT_MODELS_DIR
    model_path = os.path.join(md, f"{product_name}.pkl")
    fallback = False

    if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)

            future = model.make_future_dataframe(periods=horizon_days, freq="D")
            forecast = model.predict(future)

            # Cumulative sales projection
            recent = forecast.tail(horizon_days)
            cum_sales = recent["yhat"].cumsum()
            crossing = cum_sales[cum_sales >= current_stock]

            if len(crossing) == 0:
                depletion_days = None
                depletion_date = ">30 hari"
            else:
                depletion_days = int(crossing.index[0] - recent.index[0]) + 1
                dep_date = date.today() + timedelta(days=depletion_days)
                depletion_date = dep_date.isoformat()

            trend = _trend_from_forecast(forecast)
        except Exception:
            fallback = True
    else:
        fallback = True

    if fallback:
        daily_avg = float(product["initial_stock"]) / float(product["depletion_window_days"])
        if daily_avg <= 0:
            depletion_days = None
            depletion_date = ">30 hari"
        else:
            depletion_days = int(current_stock / daily_avg)
            dep_date = date.today() + timedelta(days=depletion_days)
            depletion_date = dep_date.isoformat()
        trend = "stable"

    confidence = "medium"
    if fallback or phase == "bootstrap":
        confidence = "low"
    elif phase == "mature":
        confidence = "high"

    return PredictionResult(
        product=product_name,
        depletion_days=depletion_days,
        depletion_date=depletion_date,
        phase=phase,
        trend=trend,
        confidence=confidence,
        fallback_active=fallback,
    )


def get_forecast_data(
    db_path: str,
    product_name: str,
    current_stock: float | None = None,
    models_dir: str | None = None,
) -> list[dict]:
    """Return 30-day Prophet forecast for charting.

    Returns list of ``{ds, sisa_stok}`` dicts (remaining stock declining
    toward zero), or empty list if no model available.

    *current_stock* is the starting stock level.  If omitted, stock is
    fetched from ``products.json``.
    """
    md = models_dir or DEFAULT_MODELS_DIR
    model_path = os.path.join(md, f"{product_name}.pkl")
    if not os.path.exists(model_path) or os.path.getsize(model_path) == 0:
        return []
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        future = model.make_future_dataframe(periods=30, freq="D")
        forecast = model.predict(future)
        recent = forecast.tail(30)
        if current_stock is None:
            current_stock = 0
        cum_sales = recent["yhat"].cumsum()
        result = []
        for i in range(len(recent)):
            remaining = max(0.0, float(current_stock - cum_sales.iloc[i]))
            result.append({"ds": recent.iloc[i]["ds"].isoformat(), "sisa_stok": remaining})
        return result
    except Exception:
        return []


def train_specific_products(
    db_path: str,
    products_file: str,
    product_names: list[str],
    models_dir: Optional[str] = None,
) -> None:
    """Train models for specific products only.

    Generates synthetic data once and trains only the named products.
    Useful after EOD confirmation to retrain just the confirmed products.
    """
    import json

    with open(products_file) as f:
        products = json.load(f)

    from app.synthetic_data import generate_synthetic_data
    synthetic = generate_synthetic_data(products, days=90)

    for name in product_names:
        if name in products:
            train_product(db_path, products[name], name, synthetic, models_dir=models_dir)
        else:
            print(f"[train_specific_products] Unknown product '{name}' — skipped")


def train_all_products(
    db_path: str,
    products_file: str,
    models_dir: Optional[str] = None,
) -> None:
    """Train models for all products."""
    import json

    with open(products_file) as f:
        products = json.load(f)

    from app.synthetic_data import generate_synthetic_data
    synthetic = generate_synthetic_data(products, days=90)

    for name, config in products.items():
        train_product(db_path, config, name, synthetic, models_dir=models_dir)
