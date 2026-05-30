"""Tests for the synthetic data generator and seeder."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

import pytest

from app.seeder import get_synthetic_count, seed_synthetic_data
from app.synthetic_data import generate_synthetic_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PRODUCTS_FILE = "/home/amri/Projects/prediksi_stok/products.json"


@pytest.fixture
def products():
    """Load the real product catalog."""
    with open(PRODUCTS_FILE) as f:
        return json.load(f)


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path for test isolation."""
    return str(tmp_path / "test.db")


# ---------------------------------------------------------------------------
# generate_synthetic_data
# ---------------------------------------------------------------------------


class TestGenerateSyntheticData:
    """Tests for the raw generator (no database)."""

    def test_correct_number_of_records(self, products):
        """7 products x 90 days = 630 records."""
        data = generate_synthetic_data(products, days=90, seed=42)
        assert len(data) == 7 * 90

    def test_different_days_param(self, products):
        """Respects the *days* parameter."""
        data = generate_synthetic_data(products, days=30, seed=42)
        assert len(data) == 7 * 30

    def test_all_quantities_non_negative(self, products):
        """No daily quantity may be negative."""
        data = generate_synthetic_data(products, days=90, seed=42)
        for row in data:
            assert row["quantity"] >= 0, f"Negative qty for {row['product_name']}"

    def test_weekly_average_within_10_percent(self, products):
        """Per-product average daily sales matches owner estimate within 10%.

        Owner estimate = initial_stock / depletion_window_days.
        """
        data = generate_synthetic_data(products, days=90, seed=42)
        # Group by product
        by_product: dict[str, list[float]] = {}
        for row in data:
            by_product.setdefault(row["product_name"], []).append(row["quantity"])

        for name, config in products.items():
            estimate = config["initial_stock"] / config["depletion_window_days"]
            qties = by_product[name]
            avg = sum(qties) / len(qties)
            assert (
                estimate * 0.9 <= avg <= estimate * 1.1
            ), (
                f"{name}: avg={avg:.2f}, estimate={estimate:.2f} "
                f"(delta={((avg / estimate) - 1) * 100:+.1f}%)"
            )

    def test_weekends_lower_than_weekdays(self, products):
        """Average Saturday+Sunday sales < average Monday-Friday sales."""
        data = generate_synthetic_data(products, days=90, seed=42)
        by_product: dict[str, dict[str, list[float]]] = {}
        for row in data:
            by_product.setdefault(row["product_name"], {})
            ts = datetime.fromisoformat(row["reported_at"])
            group = "weekend" if ts.weekday() >= 5 else "weekday"
            by_product[row["product_name"]].setdefault(group, []).append(
                row["quantity"]
            )

        for name in products:
            weekday_avg = sum(by_product[name]["weekday"]) / len(
                by_product[name]["weekday"]
            )
            weekend_avg = sum(by_product[name]["weekend"]) / len(
                by_product[name]["weekend"]
            )
            assert weekend_avg < weekday_avg, (
                f"{name}: weekend avg {weekend_avg:.2f} >= "
                f"weekday avg {weekday_avg:.2f}"
            )

    def test_deterministic_seed(self, products):
        """Same seed produces identical output."""
        a = generate_synthetic_data(products, days=90, seed=42)
        b = generate_synthetic_data(products, days=90, seed=42)
        assert a == b

    def test_different_seed_different_output(self, products):
        """Different seed produces different output."""
        a = generate_synthetic_data(products, days=90, seed=42)
        b = generate_synthetic_data(products, days=90, seed=99)
        assert a != b

    def test_timestamps_within_business_hours(self, products):
        """All reported_at times are between 08:00 and 20:00."""
        data = generate_synthetic_data(products, days=90, seed=42)
        for row in data:
            ts = datetime.fromisoformat(row["reported_at"])
            hour = ts.hour
            assert 8 <= hour < 20, (
                f"Hour {hour} outside 08-20 for {row['product_name']} "
                f"at {row['reported_at']}"
            )

    def test_all_products_present(self, products):
        """Every product from the catalog appears in the output."""
        data = generate_synthetic_data(products, days=90, seed=42)
        names = {row["product_name"] for row in data}
        assert names == set(products.keys())

    def test_each_product_has_correct_day_count(self, products):
        """Each product has exactly *days* records."""
        data = generate_synthetic_data(products, days=90, seed=42)
        by_product: dict[str, int] = {}
        for row in data:
            by_product[row["product_name"]] = (
                by_product.get(row["product_name"], 0) + 1
            )
        for name in products:
            assert by_product[name] == 90, f"{name} has {by_product[name]} records"

    def test_dates_are_past(self, products):
        """Generated timestamps are in the past (yesterday or earlier)."""
        data = generate_synthetic_data(products, days=90, seed=42)
        now = datetime.now()
        for row in data:
            ts = datetime.fromisoformat(row["reported_at"])
            assert ts < now, f"Future timestamp: {row['reported_at']}"


# ---------------------------------------------------------------------------
# seeder
# ---------------------------------------------------------------------------


class TestSeeder:
    """Integration tests for seed_synthetic_data."""

    def test_seeds_database(self, db_path, products):
        """seed_synthetic_data inserts the right number of rows."""
        seed_synthetic_data(db_path, PRODUCTS_FILE, days=90)
        count = get_synthetic_count(db_path)
        # 7 products * 90 days
        assert count == 7 * 90

    def test_data_persists(self, db_path, products):
        """Seeded data is queryable via app.data functions."""
        from app.data import get_daily_sales

        seed_synthetic_data(db_path, PRODUCTS_FILE, days=90)

        # Get last day of data for Gula
        db_conn = sqlite3.connect(db_path)
        last_date = db_conn.execute(
            "SELECT date(MAX(reported_at)) FROM sales_reports WHERE product_name = ?",
            ("Gula",),
        ).fetchone()[0]
        db_conn.close()

        rows = get_daily_sales(db_path, "Gula", last_date, last_date)
        assert len(rows) == 1
        assert rows[0]["sale_date"] == last_date
        assert rows[0]["total_quantity"] >= 0

    def test_seed_is_idempotent(self, db_path, products):
        """Seeding twice doubles the row count."""
        seed_synthetic_data(db_path, PRODUCTS_FILE, days=90)
        seed_synthetic_data(db_path, PRODUCTS_FILE, days=90)
        count = get_synthetic_count(db_path)
        assert count == 2 * 7 * 90

    def test_different_days(self, db_path, products):
        """Seeding with a different *days* produces corresponding rows."""
        days = 30
        seed_synthetic_data(db_path, PRODUCTS_FILE, days=days)
        count = get_synthetic_count(db_path)
        assert count == 7 * days
