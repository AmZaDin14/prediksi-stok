"""Tests for the stock reconciliation module."""

from __future__ import annotations

import sqlite3

import pytest

from app.data import _ensure_tables, get_expected_stock, record_confirmation, record_sale
from app.reconciliation import confirm_and_reconcile, reconcile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path for test isolation."""
    return str(tmp_path / "test.db")


def _seed_confirmation(db_path: str, product: str, qty: float, date: str) -> None:
    """Direct-insert a confirmation row for test setup."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
        (product, qty, date),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# reconcile
# ---------------------------------------------------------------------------


class TestReconcile:
    """reconcile compares expected vs actual stock correctly."""

    def test_exact_match(self, db_path):
        """Reconcile returns is_match=True when actual equals expected."""
        record_confirmation(db_path, "Gula", 30.0)
        result = reconcile(db_path, "Gula", 30.0)
        assert result.is_match is True
        assert result.shrinkage_detected is False
        assert result.restock_detected is False
        assert result.discrepancy == 0.0

    def test_small_discrepancy_within_threshold(self, db_path):
        """Small discrepancy within 10% returns is_match=True."""
        _ensure_tables(sqlite3.connect(db_path))
        _seed_confirmation(db_path, "Gula", 30.0, "2026-05-29")
        result = reconcile(db_path, "Gula", 28.0)
        # discrepancy = -2, bound = max(0.1*30, 1) = 3, | -2 | <= 3
        assert result.is_match is True
        assert result.shrinkage_detected is False
        assert result.restock_detected is False

    def test_large_negative_discrepancy_shrinkage(self, db_path):
        """Large negative discrepancy detects shrinkage."""
        _ensure_tables(sqlite3.connect(db_path))
        _seed_confirmation(db_path, "Gula", 30.0, "2026-05-29")
        result = reconcile(db_path, "Gula", 20.0)
        # discrepancy = -10, bound = max(0.1*30, 1) = 3, -10 < -3
        assert result.is_match is False
        assert result.shrinkage_detected is True
        assert result.restock_detected is False

    def test_large_positive_discrepancy_restock(self, db_path):
        """Large positive discrepancy detects restock."""
        _ensure_tables(sqlite3.connect(db_path))
        _seed_confirmation(db_path, "Gula", 30.0, "2026-05-29")
        result = reconcile(db_path, "Gula", 50.0)
        # discrepancy = 20, bound = max(0.1*30, 1) = 3, 20 > 3
        assert result.is_match is False
        assert result.shrinkage_detected is False
        assert result.restock_detected is True

    def test_no_previous_confirmation_baseline(self, db_path):
        """No previous confirmation: is_match=True (baseline established)."""
        result = reconcile(db_path, "Gula", 30.0)
        assert result.is_match is True
        assert result.shrinkage_detected is False
        assert result.restock_detected is False

    def test_discrepancy_within_absolute_threshold(self, db_path):
        """Small absolute discrepancy passes when expected is tiny."""
        _ensure_tables(sqlite3.connect(db_path))
        _seed_confirmation(db_path, "Roti hitam manis", 2.0, "2026-05-29")
        result = reconcile(db_path, "Roti hitam manis", 1.0)
        # discrepancy = -1, bound = max(0.1*2, 1) = 1, | -1 | <= 1
        assert result.is_match is True

    def test_discrepancy_exceeds_absolute_threshold(self, db_path):
        """Discrepancy exceeds absolute threshold when expected is tiny."""
        _ensure_tables(sqlite3.connect(db_path))
        _seed_confirmation(db_path, "Roti hitam manis", 2.0, "2026-05-29")
        result = reconcile(db_path, "Roti hitam manis", 0.5)
        # discrepancy = -1.5, bound = max(0.1*2, 1) = 1, -1.5 < -1
        assert result.is_match is False
        assert result.shrinkage_detected is True


# ---------------------------------------------------------------------------
# confirm_and_reconcile
# ---------------------------------------------------------------------------


class TestConfirmAndReconcile:
    """confirm_and_reconcile records confirmation and returns result."""

    def test_records_confirmation_and_returns_result(self, db_path):
        """Records a confirmation and reconciles against it."""
        result = confirm_and_reconcile(db_path, "Gula", 25.0)
        # The confirmation was just recorded, so expected stock = 25.0
        assert result.product_name == "Gula"
        assert result.actual_stock == 25.0
        assert result.expected_stock == 25.0
        assert result.is_match is True

    def test_confirmation_persisted(self, db_path):
        """The confirmation is persisted in the database."""
        confirm_and_reconcile(db_path, "Gula", 25.0)
        # After recording, the confirmation should be retrievable
        expected = get_expected_stock(db_path, "Gula")
        assert expected == 25.0

    def test_returns_reconciled_result_after_sales(self, db_path):
        """Reconciliation accounts for sales after the last confirmation."""
        _ensure_tables(sqlite3.connect(db_path))
        # Seed a confirmation from yesterday so today's sale is deducted.
        _seed_confirmation(db_path, "Gula", 30.0, "2026-05-29")
        record_sale(db_path, "Gula", 5.0, "2026-05-30T06:00:00")
        # Expected = 30 - 5 = 25, actual = 24 -> discrepancy = -1 (within 10%)
        result = confirm_and_reconcile(db_path, "Gula", 24.0)
        assert result.product_name == "Gula"
        assert result.actual_stock == 24.0
        assert result.is_match is True
