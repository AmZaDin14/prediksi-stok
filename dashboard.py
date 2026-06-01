"""Prediksi Stok -- Streamlit dashboard.

Simple password-protected single-page dashboard showing current stock levels
for all tracked products.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import json
import os
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app.data import get_daily_sales, get_expected_stock, record_sale
from app.predictor import get_forecast_data, predict_product, train_all_products
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
    """Check password via query param, session state, or text input.

    Survives page refreshes via ``auth_until`` query param (30 min expiry).
    Returns True if authenticated.
    """
    # 1) Expiring session via query param (survives page refresh)
    auth_until = st.query_params.get("auth_until")
    if auth_until:
        try:
            val = auth_until[0] if isinstance(auth_until, list) else auth_until
            if time.time() < float(val):
                return True
        except (ValueError, TypeError):
            pass

    # 2) Allow passing password as query parameter (e.g. ?password=admin123)
    query_pass = st.query_params.get("password", [None])
    if isinstance(query_pass, list):
        query_pass = query_pass[0] if query_pass else None
    if query_pass == DASHBOARD_PASSWORD:
        st.query_params["auth_until"] = str(time.time() + 1800)
        return True

    # 3) In-memory session state (fast, but lost on page refresh)
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    # 4) Login form
    with st.container():
        st.title("Prediksi Stok")
        st.markdown("Masukkan password untuk mengakses dashboard.")
        password = st.text_input("Password", type="password")
        if password:
            if password == DASHBOARD_PASSWORD:
                st.session_state.authenticated = True
                st.query_params["auth_until"] = str(time.time() + 1800)
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

# Auto-refresh every 10 seconds
st_autorefresh(interval=10000, key="dashboard_autorefresh")

# Load product catalog
products = load_products()

# Page header
st.title("Dashboard Stok")
st.markdown("Ringkasan stok semua produk.")

# ---------------------------------------------------------------------------
# WhatsApp Status
# ---------------------------------------------------------------------------
st.markdown("### Status WhatsApp")
status_path = Path(__file__).parent / "data" / "connection_status.json"
qr_path = Path(__file__).parent / "data" / "qr.png"

if status_path.exists():
    with open(status_path) as f:
        conn_status = json.load(f)
    wa_status = conn_status.get("status", "disconnected")

    if wa_status == "connected":
        st.success("WhatsApp Terhubung")
        phone = conn_status.get("phone_number")
        if phone:
            st.caption(f"Nomor: {phone}")
        last = conn_status.get("last_connected")
        if last:
            st.caption(f"Terakhir terhubung: {last}")
    elif wa_status == "connecting":
        st.warning("Menghubungkan...")
        if qr_path.exists():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(str(qr_path), width=250)
        else:
            st.text("QR code belum tersedia")
        st.caption("Scan QR code dengan WhatsApp Anda untuk menghubungkan")
    else:
        st.error("WhatsApp Terputus")
        last = conn_status.get("last_connected")
        if last:
            st.caption(f"Terakhir terhubung: {last}")
else:
    st.info("WhatsApp bot belum dijalankan")

# ---------------------------------------------------------------------------
# Train models if missing
# ---------------------------------------------------------------------------
if "models_trained" not in st.session_state:
    missing = [name for name in products if not (MODELS_DIR / f"{name}.pkl").exists()]
    if missing:
        with st.spinner(f"Melatih model untuk {len(missing)} produk..."):
            train_all_products(str(DB_PATH), str(PRODUCTS_PATH), models_dir=str(MODELS_DIR))
    st.session_state.models_trained = True

# ---------------------------------------------------------------------------
# Product table
# ---------------------------------------------------------------------------

# Build enriched table with predictions
rows = []
for name, info in products.items():
    stock = get_expected_stock(str(DB_PATH), name, initial_stock=float(info["initial_stock"]))
    unit = info["unit"]

    pred = predict_product(str(DB_PATH), info, name, models_dir=str(MODELS_DIR))
    stock_display = f"{stock:,.0f} {unit}"

    # Trend indicator
    trend_map = {"up": "\U0001f53c", "down": "\U0001f53d", "stable": "→"}
    trend_chr = trend_map.get(pred.trend, "")

    # Phase badge
    phase_map = {"bootstrap": "B", "blend": "BL", "mature": "M"}
    phase_chr = phase_map.get(pred.phase, "?")

    # Confidence display
    conf_map = {"low": "\U0001f534 Low", "medium": "\U0001f7e1 Med", "high": "\U0001f7e2 High"}
    conf_chr = conf_map.get(pred.confidence, "?")

    # Urgency color class
    urgent = pred.depletion_days is not None and pred.depletion_days <= 3
    warning = pred.depletion_days is not None and pred.depletion_days <= 7

    if urgent:
        status = "\U0001f534 Urgent"
    elif warning:
        status = "\U0001f7e1 Warning"
    elif pred.fallback_active:
        status = "\U0001f535 Estimasi"
    else:
        status = "\U0001f7e2 Aman"

    depletion_display = pred.depletion_date if pred.depletion_days else ">30 hari"

    rows.append({
        "Produk": name,
        "Stok": stock_display,
        "Prediksi Habis": depletion_display,
        "Tren": trend_chr,
        "Fase": phase_chr,
        "Status": status,
    })

rows.sort(key=lambda r: r["Produk"].lower())

st.dataframe(
    rows,
    column_config={
        "Produk": st.column_config.TextColumn("Produk"),
        "Stok": st.column_config.TextColumn("Stok Saat Ini"),
        "Prediksi Habis": st.column_config.TextColumn("Prediksi Habis"),
        "Tren": st.column_config.TextColumn("Tren", width="small"),
        "Fase": st.column_config.TextColumn("Fase", width="small"),
        "Status": st.column_config.TextColumn("Status"),
    },
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
st.markdown("### Grafik")

prod_list = sorted(products.keys())
sel = st.selectbox("Pilih produk", prod_list, key="chart_select")

if sel:
    col1, col2 = st.columns(2)

    with col1:
        st.caption("Penjualan Harian (30 hari terakhir)")
        end = date.today()
        start = end - timedelta(days=30)
        sales = get_daily_sales(str(DB_PATH), sel, start.isoformat(), end.isoformat())
        if sales:
            sdf = pd.DataFrame(sales)
            sdf["sale_date"] = pd.to_datetime(sdf["sale_date"])
            st.bar_chart(sdf.set_index("sale_date")["total_quantity"])
        else:
            st.info("Belum ada data penjualan")

    with col2:
        st.caption("Prediksi Stok (30 hari ke depan)")
        current = get_expected_stock(str(DB_PATH), sel, initial_stock=float(products[sel]["initial_stock"]))
        if current is not None:
            fdata = get_forecast_data(str(DB_PATH), sel, current_stock=current, models_dir=str(MODELS_DIR))
            if fdata:
                fdf = pd.DataFrame(fdata).rename(columns={"ds": "date", "sisa_stok": "Sisa Stok"})
                fdf["date"] = pd.to_datetime(fdf["date"])
                st.line_chart(fdf.set_index("date"))
        else:
            info = products[sel]
            daily_avg = float(info["initial_stock"]) / float(info["depletion_window_days"])
            st.info(f"Model belum dilatih. Estimasi: habis ~{int(info['initial_stock'] / daily_avg) if daily_avg > 0 else 'N/A'} hari")

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
