"""Tests for the sales data access module."""

from __future__ import annotations

import sqlite3

import pytest

from app.data import (
    get_daily_sales,
    get_expected_stock,
    get_last_confirmation,
    record_confirmation,
    record_sale,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_schema(db_path: str) -> None:
    """Create the schema on a test database for direct-sql tests."""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path for test isolation."""
    return str(tmp_path / "test.db")


# ---------------------------------------------------------------------------
# record_sale
# ---------------------------------------------------------------------------


class TestRecordSale:
    """record_sale inserts correctly."""

    def test_inserts_row(self, db_path):
        record_sale(db_path, "Gula", 5.0, "2026-05-30T10:00:00")
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT * FROM sales_reports").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][1] == "Gula"
        assert rows[0][2] == 5.0
        assert rows[0][3] == "2026-05-30T10:00:00"

    def test_multiple_inserts(self, db_path):
        record_sale(db_path, "Gula", 3.0, "2026-05-30T10:00:00")
        record_sale(db_path, "Minyak", 20.0, "2026-05-30T11:00:00")
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT COUNT(*) FROM sales_reports").fetchall()
        conn.close()
        assert rows[0][0] == 2


# ---------------------------------------------------------------------------
# get_daily_sales
# ---------------------------------------------------------------------------


class TestGetDailySales:
    """get_daily_sales aggregates correctly for a date range."""

    def test_aggregates_same_day(self, db_path):
        record_sale(db_path, "Gula", 3.0, "2026-05-30T10:00:00")
        record_sale(db_path, "Gula", 2.0, "2026-05-30T14:00:00")
        result = get_daily_sales(db_path, "Gula", "2026-05-30", "2026-05-30")
        assert len(result) == 1
        assert result[0]["sale_date"] == "2026-05-30"
        assert result[0]["total_quantity"] == 5.0

    def test_multiple_days(self, db_path):
        record_sale(db_path, "Gula", 5.0, "2026-05-28T10:00:00")
        record_sale(db_path, "Gula", 3.0, "2026-05-29T10:00:00")
        record_sale(db_path, "Gula", 2.0, "2026-05-30T10:00:00")
        result = get_daily_sales(db_path, "Gula", "2026-05-28", "2026-05-30")
        assert len(result) == 3
        assert result[0]["sale_date"] == "2026-05-28"
        assert result[0]["total_quantity"] == 5.0
        assert result[2]["sale_date"] == "2026-05-30"
        assert result[2]["total_quantity"] == 2.0

    def test_date_range_filters(self, db_path):
        record_sale(db_path, "Gula", 5.0, "2026-05-28T10:00:00")
        record_sale(db_path, "Gula", 3.0, "2026-05-30T10:00:00")
        result = get_daily_sales(db_path, "Gula", "2026-05-29", "2026-05-30")
        assert len(result) == 1
        assert result[0]["sale_date"] == "2026-05-30"
        assert result[0]["total_quantity"] == 3.0

    def test_no_sales_in_range(self, db_path):
        record_sale(db_path, "Gula", 5.0, "2026-05-28T10:00:00")
        result = get_daily_sales(db_path, "Gula", "2026-05-29", "2026-05-30")
        assert result == []

    def test_filters_by_product(self, db_path):
        record_sale(db_path, "Gula", 5.0, "2026-05-30T10:00:00")
        record_sale(db_path, "Minyak", 20.0, "2026-05-30T11:00:00")
        result = get_daily_sales(db_path, "Gula", "2026-05-30", "2026-05-30")
        assert len(result) == 1
        assert result[0]["total_quantity"] == 5.0

    def test_returns_empty_list_when_no_data(self, db_path):
        result = get_daily_sales(db_path, "Gula", "2026-05-01", "2026-05-30")
        assert result == []


# ---------------------------------------------------------------------------
# get_expected_stock -- no confirmations
# ---------------------------------------------------------------------------


class TestExpectedStockNoConfirmation:
    def test_returns_none_no_confirmation(self, db_path):
        """No confirmations at all."""
        result = get_expected_stock(db_path, "Gula")
        assert result is None

    def test_returns_none_with_sales_but_no_confirmation(self, db_path):
        """Sales exist but no confirmation."""
        record_sale(db_path, "Gula", 5.0, "2026-05-30T10:00:00")
        result = get_expected_stock(db_path, "Gula")
        assert result is None


# ---------------------------------------------------------------------------
# get_expected_stock -- with confirmations
# ---------------------------------------------------------------------------


class TestExpectedStockWithConfirmation:
    def test_no_sales_after_confirmation(self, db_path):
        """Confirmation exists but no sales after it."""
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()
        result = get_expected_stock(db_path, "Gula")
        assert result == 30.0

    def test_with_sales_after_confirmation(self, db_path):
        """Confirmation followed by sales."""
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()

        record_sale(db_path, "Gula", 5.0, "2026-05-30T10:00:00")
        record_sale(db_path, "Gula", 3.0, "2026-05-30T14:00:00")

        result = get_expected_stock(db_path, "Gula")
        # 30 - (5 + 3) = 22
        assert result == 22.0

    def test_sales_before_confirmation_not_deducted(self, db_path):
        """Sales before the confirmation timestamp are not deducted."""
        _init_schema(db_path)
        # Sale at 10:00
        record_sale(db_path, "Gula", 5.0, "2026-05-29T10:00:00")
        # Confirmation at 17:00 (after the sale)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29T17:00:00"),
        )
        conn.commit()
        conn.close()

        result = get_expected_stock(db_path, "Gula")
        # Sale at 10:00 is before confirmation at 17:00 — not deducted
        assert result == 30.0

    def test_sales_after_confirmation_deducted(self, db_path):
        """Sales after the confirmation timestamp are deducted."""
        _init_schema(db_path)
        # Confirmation at 10:00
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29T10:00:00"),
        )
        conn.commit()
        conn.close()

        # Sale at 17:00 (after confirmation)
        record_sale(db_path, "Gula", 5.0, "2026-05-29T17:00:00")
        result = get_expected_stock(db_path, "Gula")
        # 30 - 5 = 25
        assert result == 25.0

    def test_multiple_confirmations_uses_latest(self, db_path):
        """Only the most recent confirmation is used."""
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 10.0, "2026-05-28"),
        )
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()

        record_sale(db_path, "Gula", 5.0, "2026-05-30T10:00:00")
        result = get_expected_stock(db_path, "Gula")
        # Uses latest: 30 - 5 = 25
        assert result == 25.0

    def test_non_confirmation_snapshots_ignored(self, db_path):
        """Snapshots with is_confirmation=0 are ignored."""
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        # A non-confirmation snapshot (e.g. a draft)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 0)",
            ("Gula", 100.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()

        result = get_expected_stock(db_path, "Gula")
        assert result is None

    def test_multiple_products_independent(self, db_path):
        """Expected stock for each product is independent."""
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29"),
        )
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Minyak", 1000.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()

        record_sale(db_path, "Gula", 5.0, "2026-05-30T10:00:00")
        record_sale(db_path, "Minyak", 20.0, "2026-05-30T11:00:00")

        assert get_expected_stock(db_path, "Gula") == 25.0
        assert get_expected_stock(db_path, "Minyak") == 980.0


# ---------------------------------------------------------------------------
# get_last_confirmation
# ---------------------------------------------------------------------------


class TestGetLastConfirmation:
    def test_no_confirmations_returns_none(self, db_path):
        result = get_last_confirmation(db_path, "Gula")
        assert result is None

    def test_returns_latest_confirmation(self, db_path):
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()

        result = get_last_confirmation(db_path, "Gula")
        assert result is not None
        assert result["product_name"] == "Gula"
        assert result["quantity"] == 30.0
        assert result["snapshot_date"] == "2026-05-29"

    def test_returns_most_recent_of_multiple(self, db_path):
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 10.0, "2026-05-28"),
        )
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()

        result = get_last_confirmation(db_path, "Gula")
        assert result["quantity"] == 30.0
        assert result["snapshot_date"] == "2026-05-29"

    def test_excludes_non_confirmations(self, db_path):
        _init_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            ("Gula", 30.0, "2026-05-28"),
        )
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 0)",
            ("Gula", 999.0, "2026-05-29"),
        )
        conn.commit()
        conn.close()

        result = get_last_confirmation(db_path, "Gula")
        assert result["quantity"] == 30.0


# ---------------------------------------------------------------------------
# record_confirmation
# ---------------------------------------------------------------------------


class TestRecordConfirmation:
    def test_inserts_confirmation(self, db_path):
        record_confirmation(db_path, "Gula", 25.0)
        result = get_last_confirmation(db_path, "Gula")
        assert result is not None
        assert result["product_name"] == "Gula"
        assert result["quantity"] == 25.0
        assert result["is_confirmation"] == 1

    def test_multiple_confirmations(self, db_path):
        """Both confirmations on the same day; last inserted has id > first."""
        record_confirmation(db_path, "Gula", 30.0)
        record_confirmation(db_path, "Gula", 25.0)
        result = get_last_confirmation(db_path, "Gula")
        # Both records have the same snapshot_date (today), so we add id as
        # tiebreaker.  The second insert has a higher rowid so it should be
        # returned.
        assert result["quantity"] == 25.0
