"""Prediksi Stok -- Streamlit dashboard.

Simple password-protected single-page dashboard showing current stock levels
for all tracked products.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import streamlit as st

from app.data import get_expected_stock, record_sale
from app.synthetic_data import generate_synthetic_data

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PRODUCTS_PATH = Path(__file__).parent / "products.json"
DB_PATH = Path(__file__).parent / "data" / "prediksi.db"
MODELS_DIR = Path(__file__).parent / "data" / "models"
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


def save_products(products: dict) -> None:
    """Save product catalog to products.json."""
    with open(PRODUCTS_PATH, "w") as f:
        json.dump(products, f, indent=2)
        f.write("\n")


def _delete_product_data(product_name: str) -> None:
    """Delete all sales and snapshot records for a product from SQLite."""
    db = str(DB_PATH)
    conn = sqlite3.connect(db)
    try:
        conn.execute("DELETE FROM sales_reports WHERE product_name = ?", (product_name,))
        conn.execute("DELETE FROM stock_snapshots WHERE product_name = ?", (product_name,))
        conn.commit()
    finally:
        conn.close()
    # Delete model file if exists
    model_path = MODELS_DIR / f"{product_name}.pkl"
    if model_path.exists():
        model_path.unlink()


def _regenerate_synthetic_product(product_name: str, product_config: dict) -> None:
    """Regenerate synthetic data for a single product."""
    _delete_product_data(product_name)
    data = generate_synthetic_data({product_name: product_config}, days=90)
    for row in data:
        record_sale(str(DB_PATH), row["product_name"], row["quantity"], row["reported_at"])


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

# ---------------------------------------------------------------------------
# Add product
# ---------------------------------------------------------------------------
with st.expander("Tambah Produk Baru"):
    with st.form("add_product"):
        cols = st.columns(2)
        new_name = cols[0].text_input("Nama Produk").strip()
        new_stock = cols[1].number_input("Stok Awal", min_value=1, value=100)
        new_unit = cols[0].selectbox("Satuan", ["sak", "dus", "ton", "kg", "pak"])
        new_depletion = cols[1].number_input("Estimasi Waktu Habis (hari)", min_value=1, value=7)
        new_shelf = cols[0].number_input("Masa Simpan (hari)", min_value=1, value=365)
        new_lead = cols[1].number_input("Waktu Tunggu Pemasok (hari)", min_value=1, value=2)

        if st.form_submit_button("Tambah"):
            if not new_name:
                st.error("Nama produk wajib diisi.")
            elif new_name in products:
                st.error(f"Produk '{new_name}' sudah ada.")
            else:
                products[new_name] = {
                    "initial_stock": new_stock,
                    "unit": new_unit,
                    "depletion_window_days": new_depletion,
                    "shelf_life_days": new_shelf,
                    "supplier_lead_time_days": new_lead,
                }
                save_products(products)
                _regenerate_synthetic_product(new_name, products[new_name])
                st.success(f"Produk '{new_name}' berhasil ditambahkan.")
                st.rerun()

# ---------------------------------------------------------------------------
# Edit product
# ---------------------------------------------------------------------------
if products:
    with st.expander("Edit Produk"):
        edit_name = st.selectbox("Pilih Produk", sorted(products.keys()), key="edit_select")
        if edit_name:
            info = products[edit_name]
            with st.form("edit_product"):
                cols = st.columns(2)
                e_stock = cols[0].number_input("Stok Awal", min_value=1, value=info["initial_stock"])
                e_unit = cols[1].selectbox("Satuan", ["sak", "dus", "ton", "kg", "pak"],
                    index=["sak", "dus", "ton", "kg", "pak"].index(info["unit"]))
                e_depletion = cols[0].number_input("Estimasi Waktu Habis (hari)", min_value=1, value=info["depletion_window_days"])
                e_shelf = cols[1].number_input("Masa Simpan (hari)", min_value=1, value=info["shelf_life_days"])
                e_lead = cols[0].number_input("Waktu Tunggu Pemasok (hari)", min_value=1, value=info["supplier_lead_time_days"])

                if st.form_submit_button("Simpan"):
                    old_depletion = info["depletion_window_days"]
                    products[edit_name] = {
                        "initial_stock": e_stock,
                        "unit": e_unit,
                        "depletion_window_days": e_depletion,
                        "shelf_life_days": e_shelf,
                        "supplier_lead_time_days": e_lead,
                    }
                    save_products(products)
                    if abs(e_depletion - old_depletion) / old_depletion > 0.2:
                        _regenerate_synthetic_product(edit_name, products[edit_name])
                    st.success(f"Produk '{edit_name}' berhasil diperbarui.")
                    st.rerun()

# ---------------------------------------------------------------------------
# Delete product
# ---------------------------------------------------------------------------
if products:
    with st.expander("Hapus Produk"):
        del_name = st.selectbox("Pilih Produk", sorted(products.keys()), key="del_select")
        if del_name:
            st.warning(f"Hapus '{del_name}'? Semua data penjualan produk ini akan dihapus.")
            confirm = st.checkbox("Saya yakin ingin menghapus produk ini.")
            if st.button("Hapus", type="primary", disabled=not confirm):
                del products[del_name]
                save_products(products)
                _delete_product_data(del_name)
                st.success(f"Produk '{del_name}' berhasil dihapus.")
                st.rerun()
