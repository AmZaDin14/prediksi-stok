"""Prediksi Stok -- Streamlit dashboard.

Simple password-protected single-page dashboard showing current stock levels
for all tracked products.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from app.data import get_expected_stock

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PRODUCTS_PATH = Path(__file__).parent / "products.json"
DB_PATH = Path(__file__).parent / "data" / "prediksi.db"
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _check_password() -> bool:
    """Check password via query param or text input.

    Returns True if authenticated.
    """
    # Allow passing password as query parameter (e.g. ?password=admin123)
    query_pass = st.query_params.get("password", [None])
    if isinstance(query_pass, list):
        query_pass = query_pass[0] if query_pass else None

    if query_pass == DASHBOARD_PASSWORD:
        return True

    # Fall back to text input widget
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    with st.container():
        st.title("Prediksi Stok")
        st.markdown("Masukkan password untuk mengakses dashboard.")
        password = st.text_input("Password", type="password")
        if password:
            if password == DASHBOARD_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password salah.")

    return False


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def load_products() -> dict:
    """Load product catalog from products.json."""
    with open(PRODUCTS_PATH) as f:
        return json.load(f)


def get_stock_display(product_name: str, product_info: dict) -> str:
    """Get formatted stock string for a product.

    Tries SQLite via get_expected_stock first; falls back to initial_stock
    from products.json.
    """
    expected = get_expected_stock(str(DB_PATH), product_name)
    if expected is not None:
        qty = expected
    else:
        qty = product_info["initial_stock"]
    unit = product_info["unit"]
    return f"{qty:,.0f} {unit}"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Prediksi Stok",
    page_icon=":package:",
    layout="centered",
)

if not _check_password():
    st.stop()

# Load product catalog
products = load_products()

# Page header
st.title("Dashboard Stok")
st.markdown("Ringkasan stok semua produk.")

# Build table data from products.json
rows = []
for name, info in products.items():
    stock_display = get_stock_display(name, info)
    rows.append(
        {
            "Produk": name,
            "Stok Saat Ini": stock_display,
            "Satuan": info["unit"],
        }
    )

# Sort by product name
rows.sort(key=lambda r: r["Produk"].lower())

st.dataframe(rows, use_container_width=True, hide_index=True)
