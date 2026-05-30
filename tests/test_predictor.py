"""Tests for the prediction engine."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, timedelta

import pytest

from app.predictor import (
    get_phase,
    predict_product,
    train_all_products,
    train_product,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRODUCTS = {
    "TestGula": {
        "initial_stock": 30,
        "unit": "sak",
        "depletion_window_days": 7,
        "shelf_life_days": 365,
        "supplier_lead_time_days": 2,
    }
}


def _init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sales_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            reported_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stock_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            snapshot_date TEXT NOT NULL,
            is_confirmation INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


def _confirm(db_path: str, product: str, qty: float, days_ago: int = 0) -> None:
    d = (date.today() - timedelta(days=days_ago)).isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
        (product, qty, d),
    )
    conn.commit()
    conn.close()


def _add_sale(db_path: str, product: str, qty: float, days_ago: int = 0) -> None:
    d = (date.today() - timedelta(days=days_ago)).isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sales_reports (product_name, quantity, reported_at) VALUES (?, ?, ?)",
        (product, qty, d + "T10:00:00"),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    _init_db(path)
    return path


@pytest.fixture
def products_file(tmp_path):
    path = tmp_path / "products.json"
    with open(path, "w") as f:
        json.dump(PRODUCTS, f)
    return str(path)


@pytest.fixture
def models_dir(tmp_path):
    md = tmp_path / "models"
    md.mkdir()
    return str(md)


# ---------------------------------------------------------------------------
# get_phase
# ---------------------------------------------------------------------------


class TestGetPhase:
    def test_bootstrap_no_data(self, db_path):
        assert get_phase(db_path, "TestGula") == "bootstrap"

    def test_blend_few_days(self, db_path):
        for i in range(5):
            _add_sale(db_path, "TestGula", 4.0, days_ago=i)
        assert get_phase(db_path, "TestGula") == "blend"

    def test_mature_many_days(self, db_path):
        for i in range(60):
            _add_sale(db_path, "TestGula", 4.0, days_ago=i)
        assert get_phase(db_path, "TestGula") == "mature"


# ---------------------------------------------------------------------------
# predict_product fallback
# ---------------------------------------------------------------------------


class TestPredictFallback:
    def test_fallback_linear_projection(self, db_path, models_dir):
        _confirm(db_path, "TestGula", 30.0, days_ago=1)
        result = predict_product(db_path, PRODUCTS["TestGula"], "TestGula", models_dir=models_dir)
        assert result.product == "TestGula"
        assert result.depletion_days is not None
        assert result.depletion_days <= 8
        assert result.fallback_active is True
        assert result.confidence == "low"
        assert result.phase == "bootstrap"

    def test_depletion_changes_with_stock(self, db_path, models_dir):
        _confirm(db_path, "TestGula", 30.0, days_ago=1)
        result_full = predict_product(db_path, PRODUCTS["TestGula"], "TestGula", models_dir=models_dir)

        _confirm(db_path, "TestGula", 15.0)
        result_half = predict_product(db_path, PRODUCTS["TestGula"], "TestGula", models_dir=models_dir)

        assert result_half.depletion_days is not None
        assert result_full.depletion_days is not None
        assert result_half.depletion_days < result_full.depletion_days


# ---------------------------------------------------------------------------
# train + predict
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestTrainAndPredict:
    def test_train_and_predict(self, db_path, models_dir):
        from app.synthetic_data import generate_synthetic_data

        synthetic = generate_synthetic_data(PRODUCTS, days=90)
        train_product(db_path, PRODUCTS["TestGula"], "TestGula", synthetic, models_dir=models_dir)

        _confirm(db_path, "TestGula", 30.0, days_ago=1)
        result = predict_product(db_path, PRODUCTS["TestGula"], "TestGula", models_dir=models_dir)
        assert result.product == "TestGula"
        assert result.phase in ("bootstrap", "blend")
        assert result.confidence in ("low", "medium", "high")

    def test_train_all(self, db_path, products_file, models_dir):
        train_all_products(db_path, products_file, models_dir=models_dir)
        _confirm(db_path, "TestGula", 30.0)
        result = predict_product(db_path, PRODUCTS["TestGula"], "TestGula", models_dir=models_dir)
        assert result.depletion_days is not None

    def test_forecast_non_negative(self, db_path, models_dir):
        from app.synthetic_data import generate_synthetic_data

        synthetic = generate_synthetic_data(PRODUCTS, days=90)
        train_product(db_path, PRODUCTS["TestGula"], "TestGula", synthetic, models_dir=models_dir)
        _confirm(db_path, "TestGula", 30.0)

        model_path = os.path.join(models_dir, "TestGula.pkl")
        if os.path.exists(model_path):
            import pickle
            from prophet import Prophet

            with open(model_path, "rb") as f:
                model = pickle.load(f)
            future = model.make_future_dataframe(periods=30)
            forecast = model.predict(future)
            assert (forecast["yhat"] >= 0).all()
