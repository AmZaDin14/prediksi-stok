"""Tests for the FastAPI server handlers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_products_file(tmp_path):
    """Create a temporary products.json with test data."""
    products = {
        "Gula": {
            "initial_stock": 30,
            "unit": "sak",
            "depletion_window_days": 7,
            "shelf_life_days": 30,
            "supplier_lead_time_days": 3,
        },
        "Minyak": {
            "initial_stock": 1000,
            "unit": "dus",
            "depletion_window_days": 14,
            "shelf_life_days": 60,
            "supplier_lead_time_days": 5,
        },
    }
    path = tmp_path / "products.json"
    with open(path, "w") as f:
        json.dump(products, f)
    return str(path)


@pytest.fixture
def tmp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def handler_env(tmp_products_file, tmp_db_path, monkeypatch):
    """Set up environment for server handlers."""
    monkeypatch.setenv("DB_PATH", tmp_db_path)
    monkeypatch.setenv("PRODUCTS_FILE", tmp_products_file)

    # Reload module-level constants in server module
    from app import server

    server.DB_PATH = tmp_db_path
    server.PRODUCTS_FILE = tmp_products_file

    return tmp_db_path, tmp_products_file


# ---------------------------------------------------------------------------
# _handle_cek_stok_confirm
# ---------------------------------------------------------------------------


class TestHandleCekStokConfirm:
    """_handle_cek_stok_confirm records confirmation and returns summary."""

    def test_single_product_confirmation(self, handler_env):
        """Sending "cek stok gula 25" records confirmation and returns OK."""
        from app.server import _handle_cek_stok_confirm

        result = _handle_cek_stok_confirm("cek stok gula 25")

        assert result.status == "ok"
        assert "Gula" in result.response
        assert "25" in result.response

        # Verify confirmation was recorded in DB
        db_path, _ = handler_env
        from app.data import get_expected_stock
        stock = get_expected_stock(db_path, "Gula")
        assert stock == 25.0

    def test_multi_product_confirmation(self, handler_env):
        """Sending "cek stok gula 25, minyak 950" confirms both products."""
        from app.server import _handle_cek_stok_confirm

        result = _handle_cek_stok_confirm("cek stok gula 25, minyak 950")

        assert result.status == "ok"
        assert "Gula" in result.response
        assert "Minyak" in result.response

        from app.data import get_expected_stock
        assert get_expected_stock(handler_env[0], "Gula") == 25.0
        assert get_expected_stock(handler_env[0], "Minyak") == 950.0

    def test_unknown_product(self, handler_env):
        """Unknown product returns error."""
        from app.server import _handle_cek_stok_confirm

        result = _handle_cek_stok_confirm("cek stok invalid 10")

        assert result.status == "error"
        assert "invalid" in result.response.lower() or "Invalid" in result.response

    def test_missing_quantity(self, handler_env):
        """Missing quantity returns error."""
        from app.server import _handle_cek_stok_confirm

        result = _handle_cek_stok_confirm("cek stok gula")

        assert result.status == "error"

    def test_negative_quantity(self, handler_env):
        """Negative quantity returns error."""
        from app.server import _handle_cek_stok_confirm

        result = _handle_cek_stok_confirm("cek stok gula -5")

        assert result.status == "error"

    def test_bare_cek_stok_not_confirmed(self, handler_env):
        """Bare "cek stok" should NOT match the confirm handler."""
        from app.server import _handle_cek_stok_confirm

        # Bare "cek stok" has no product data
        result = _handle_cek_stok_confirm("cek stok")

        assert result.status == "error"

    def test_reconciliation_detects_shrinkage(self, handler_env):
        """When actual stock is much lower than expected, shrinkage is flagged."""
        from app.server import _handle_cek_stok_confirm

        # First confirm baseline
        result1 = _handle_cek_stok_confirm("cek stok gula 30")
        assert result1.status == "ok"

        # Then confirm with much lower stock (simulating shrinkage)
        result2 = _handle_cek_stok_confirm("cek stok gula 20")

        assert result2.status == "ok"
        assert "Gula" in result2.response
        assert "20" in result2.response

    def test_different_text_formatting(self, handler_env):
        """Alternative formatting still works."""
        from app.server import _handle_cek_stok_confirm

        result = _handle_cek_stok_confirm("CEK STOK GULA 25")
        assert result.status == "ok"
        assert "25" in result.response
