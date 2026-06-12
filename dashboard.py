"""Prediksi Stok -- Streamlit dashboard.

Multi-tab dashboard with Teknokrat branding, KPI cards, stock overview,
charts, product management, and about page.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app.data import get_daily_sales, get_expected_stock, record_sale
from app.predictor import PredictionResult, get_forecast_data, predict_product, train_all_products
from app.synthetic_data import generate_synthetic_data

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
PRODUCTS_PATH = PROJECT_ROOT / "products.json"
DB_PATH = PROJECT_ROOT / "data" / "prediksi.db"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
LOGO_PATH = PROJECT_ROOT / "data" / "logo-teknokrat.png"
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

# ---------------------------------------------------------------------------
# Teknokrat brand colors
# ---------------------------------------------------------------------------
TEKNOKRAT_BLUE = "#003D7A"
TEKNOKRAT_ORANGE = "#F7941E"
TEKNOKRAT_LIGHT_BLUE = "#E8F0FE"
TEKNOKRAT_DARK = "#1A1A2E"

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
_CUSTOM_CSS = """
<style>
    /* ----- Global ----- */
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 1rem;}
    .stApp {background-color: #F8F9FA;}

    /* ----- Header banner ----- */
    .header-banner {
        background: linear-gradient(135deg, #003D7A 0%, #002B5A 100%);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,61,122,0.15);
    }
    .header-banner img {
        height: 56px;
        width: auto;
        border-radius: 6px;
        background: white;
        padding: 4px;
    }
    .header-text h1 {
        color: white;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .header-text .subtitle {
        color: rgba(255,255,255,0.8);
        font-size: 0.85rem;
        margin: 0;
    }
    .header-text .univ {
        color: #F7941E;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0;
    }

    /* ----- KPI cards ----- */
    .kpi-card {
        background: white;
        padding: 1rem 1.2rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        text-align: center;
        border-left: 4px solid #003D7A;
    }
    .kpi-card .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #003D7A;
        line-height: 1;
    }
    .kpi-card .kpi-label {
        font-size: 0.8rem;
        color: #6B7280;
        margin-top: 0.3rem;
    }
    .kpi-card.warning {border-left-color: #F59E0B;}
    .kpi-card.warning .kpi-value {color: #D97706;}
    .kpi-card.danger {border-left-color: #EF4444;}
    .kpi-card.danger .kpi-value {color: #DC2626;}

    /* ----- Status badges ----- */
    .badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-aman {background: #DCFCE7; color: #166534;}
    .badge-warning {background: #FEF3C7; color: #92400E;}
    .badge-urgent {background: #FEE2E2; color: #991B1B;}
    .badge-estimasi {background: #DBEAFE; color: #1E40AF;}

    /* ----- WhatsApp status ----- */
    .wa-status {padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.85rem; font-weight: 500;}
    .wa-connected {background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0;}
    .wa-disconnected {background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA;}
    .wa-connecting {background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;}

    /* ----- About page ----- */
    .about-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
    }
    .about-card h3 {
        color: #003D7A;
        margin-top: 0;
        border-bottom: 2px solid #F7941E;
        padding-bottom: 0.5rem;
    }
    .team-member {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.6rem 0;
        border-bottom: 1px solid #F3F4F6;
    }
    .team-member:last-child {border-bottom: none;}
    .team-member .avatar {
        width: 40px; height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #003D7A, #F7941E);
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: 700; font-size: 0.9rem;
        flex-shrink: 0;
    }
    .team-member .name {font-weight: 600; color: #1F2937;}
    .team-member .npm {font-size: 0.8rem; color: #6B7280;}

    /* ----- Footer ----- */
    .app-footer {
        text-align: center;
        color: #9CA3AF;
        font-size: 0.7rem;
        padding: 2rem 0 0.5rem 0;
        border-top: 1px solid #E5E7EB;
        margin-top: 2rem;
    }

    /* ----- Table styling ----- */
    .dataframe {font-size: 0.85rem;}
    .stDataFrame {border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden;}
</style>
"""


def _render_header() -> None:
    """Render Teknokrat-branded header."""
    logo_html = ""
    if LOGO_PATH.exists():
        import base64
        b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" alt="Teknokrat Logo">'

    st.markdown(
        f"""
        {_CUSTOM_CSS}
        <div class="header-banner">
            {logo_html}
            <div class="header-text">
                <h1>Sistem Prediksi Stok</h1>
                <p class="subtitle">AI-based Inventory Prediction System</p>
                <p class="univ">Universitas Teknokrat Indonesia</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _check_password() -> bool:
    """Check password via query param, session state, or text input."""
    # 1) Expiring session via query param (survives page refresh)
    auth_until = st.query_params.get("auth_until")
    if auth_until:
        try:
            val = auth_until[0] if isinstance(auth_until, list) else auth_until
            if time.time() < float(val):
                return True
        except (ValueError, TypeError):
            pass

    # 2) Allow passing password as query parameter
    query_pass = st.query_params.get("password", [None])
    if isinstance(query_pass, list):
        query_pass = query_pass[0] if query_pass else None
    if query_pass == DASHBOARD_PASSWORD:
        st.query_params["auth_until"] = str(time.time() + 1800)
        return True

    # 3) In-memory session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    # 4) Login form
    _render_header()
    with st.container():
        st.markdown("### 🔐 Masuk ke Dashboard")
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
    with open(PRODUCTS_PATH) as f:
        return json.load(f)


def save_products(products: dict) -> None:
    with open(PRODUCTS_PATH, "w") as f:
        json.dump(products, f, indent=2)
        f.write("\n")


def _delete_product_data(product_name: str) -> None:
    db = str(DB_PATH)
    conn = __import__("sqlite3").connect(db)
    try:
        conn.execute("DELETE FROM sales_reports WHERE product_name = ?", (product_name,))
        conn.execute("DELETE FROM stock_snapshots WHERE product_name = ?", (product_name,))
        conn.commit()
    finally:
        conn.close()
    model_path = MODELS_DIR / f"{product_name}.pkl"
    if model_path.exists():
        model_path.unlink()


def _regenerate_synthetic_product(product_name: str, product_config: dict) -> None:
    _delete_product_data(product_name)
    data = generate_synthetic_data({product_name: product_config}, days=90)
    for row in data:
        record_sale(str(DB_PATH), row["product_name"], row["quantity"], row["reported_at"])


def _status_badge_html(status_key: str) -> str:
    mapping = {
        "Aman": "badge badge-aman",
        "Warning": "badge badge-warning",
        "Urgent": "badge badge-urgent",
        "Estimasi": "badge badge-estimasi",
    }
    cls = mapping.get(status_key, "badge badge-aman")
    return f'<span class="{cls}">{status_key}</span>'


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Prediksi Stok | Teknokrat",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if not _check_password():
    st.stop()

# Auto-refresh every 10 seconds
st_autorefresh(interval=10000, key="dashboard_autorefresh")

# Render branded header
_render_header()

# Load products
products = load_products()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_dash, tab_charts, tab_manage, tab_about = st.tabs(
    ["📊 Dashboard", "📈 Charts", "⚙️ Kelola", "ℹ️ Tentang"]
)

# ===========================================================================
# TAB 1 — DASHBOARD
# ===========================================================================

with tab_dash:
    # --- KPI Cards ---
    total = len(products)
    urgent_count = 0
    warning_count = 0
    predictions: dict[str, PredictionResult] = {}

    for name, info in products.items():
        pred = predict_product(str(DB_PATH), info, name, models_dir=str(MODELS_DIR))
        predictions[name] = pred
        if pred.depletion_days is not None and pred.depletion_days <= 3:
            urgent_count += 1
        elif pred.depletion_days is not None and pred.depletion_days <= 7:
            warning_count += 1

    safe_count = total - urgent_count - warning_count

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-value">{total}</div>'
            f'<div class="kpi-label">Total Produk</div></div>',
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f'<div class="kpi-card danger"><div class="kpi-value">{urgent_count}</div>'
            f'<div class="kpi-label">🛑 Perlu Segera Dipesan</div></div>',
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f'<div class="kpi-card warning"><div class="kpi-value">{warning_count}</div>'
            f'<div class="kpi-label">⚠️ Stok Menipis</div></div>',
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-value">{safe_count}</div>'
            f'<div class="kpi-label">✅ Stok Aman</div></div>',
            unsafe_allow_html=True,
        )

    # --- WhatsApp Status Compact ---
    status_path = PROJECT_ROOT / "data" / "connection_status.json"
    if status_path.exists():
        with open(status_path) as f:
            conn_status = json.load(f)
        wa_status = conn_status.get("status", "disconnected")
        phone = conn_status.get("phone_number", "")
        if wa_status == "connected":
            wa_html = f'<div class="wa-status wa-connected">✅ WhatsApp Terhubung &nbsp;|&nbsp; {phone}</div>'
        elif wa_status == "connecting":
            wa_html = '<div class="wa-status wa-connecting">⏳ Menghubungkan... Scan QR code di dashboard</div>'
        else:
            wa_html = '<div class="wa-status wa-disconnected">❌ WhatsApp Terputus</div>'
        st.markdown(wa_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Product Table ---
    rows = []
    for name, info in products.items():
        stock = get_expected_stock(str(DB_PATH), name, initial_stock=float(info.get("initial_stock", 0)))
        unit = info.get("unit", "")
        pred = predictions[name]
        stock_val = stock if stock is not None else float(info.get("initial_stock", 0))
        pct = min(stock_val / float(info.get("initial_stock", 1)) * 100, 100)

        trend_map = {"up": "📈", "down": "📉", "stable": "→"}
        trend_chr = trend_map.get(pred.trend, "")

        phase_map = {"bootstrap": "🟡 B", "blend": "🟠 BL", "mature": "🟢 M"}
        phase_chr = phase_map.get(pred.phase, "?")

        # Status
        if pred.depletion_days is not None and pred.depletion_days <= 3:
            status_label = "Urgent"
        elif pred.depletion_days is not None and pred.depletion_days <= 7:
            status_label = "Warning"
        elif pred.fallback_active:
            status_label = "Estimasi"
        else:
            status_label = "Aman"

        depletion_display = pred.depletion_date if pred.depletion_days else ">30 hari"

        rows.append({
            "Produk": name,
            "Stok": f"{stock_val:,.0f} {unit}",
            "Sisa %": pct,
            "Prediksi Habis": depletion_display,
            "Tren": trend_chr,
            "Fase": phase_chr,
            "Status": _status_badge_html(status_label),
        })

    rows.sort(key=lambda r: r["Produk"].lower())

    st.markdown("### 📋 Status Stok")
    st.markdown(
        """
        <style>
        .stock-table {width: 100%; border-collapse: collapse; font-size: 0.85rem;}
        .stock-table th {background: #003D7A; color: white; padding: 0.6rem 0.8rem; text-align: left; font-weight: 600;}
        .stock-table td {padding: 0.5rem 0.8rem; border-bottom: 1px solid #E5E7EB;}
        .stock-table tr:hover {background: #F3F4F6;}
        .bar-bg {background: #E5E7EB; border-radius: 10px; height: 8px; width: 100px; overflow: hidden;}
        .bar-fill {height: 8px; border-radius: 10px;}
        </style>
        <table class="stock-table">
            <thead>
                <tr>
                    <th>Produk</th>
                    <th>Stok</th>
                    <th>Sisa</th>
                    <th>Prediksi Habis</th>
                    <th>Tren</th>
                    <th>Fase</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """,
        unsafe_allow_html=True,
    )
    for r in rows:
        pct = r["Sisa %"]
        bar_color = "#EF4444" if pct < 25 else "#F59E0B" if pct < 50 else "#10B981"
        stk = r["Stok"]
        dep = r["Prediksi Habis"]
        tr = r["Tren"]
        ph = r["Fase"]
        sts = r["Status"]
        st.markdown(
            f"<tr>"
            f"<td><strong>{r['Produk']}</strong></td>"
            f"<td>{stk}</td>"
            f"<td><div class='bar-bg'><div class='bar-fill' style='width:{pct:.0f}%;background:{bar_color}'></div></div></td>"
            f"<td>{dep}</td>"
            f"<td>{tr}</td>"
            f"<td>{ph}</td>"
            f"<td>{sts}</td>"
            f"</tr>",
            unsafe_allow_html=True,
        )
    st.markdown("</tbody></table>", unsafe_allow_html=True)

# ===========================================================================
# TAB 2 — CHARTS
# ===========================================================================

with tab_charts:
    st.markdown("### 📈 Grafik Penjualan & Prediksi")
    prod_list = sorted(products.keys())
    sel = st.selectbox("Pilih produk", prod_list, key="chart_tab_select")

    if sel:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Penjualan Harian (30 hari terakhir)**")
            end = date.today()
            start = end - timedelta(days=30)
            sales = get_daily_sales(str(DB_PATH), sel, start.isoformat(), end.isoformat())
            if sales:
                sdf = pd.DataFrame(sales)
                sdf["sale_date"] = pd.to_datetime(sdf["sale_date"])
                sdf = sdf.set_index("sale_date")
                st.bar_chart(sdf["total_quantity"], height=300)
            else:
                st.info("Belum ada data penjualan")

        with col2:
            st.markdown("**Prediksi Stok (30 hari ke depan)**")
            current = get_expected_stock(str(DB_PATH), sel, initial_stock=float(products[sel]["initial_stock"]))
            if current is not None:
                fdata = get_forecast_data(str(DB_PATH), sel, current_stock=current, models_dir=str(MODELS_DIR))
                if fdata:
                    fdf = pd.DataFrame(fdata).rename(columns={"ds": "date", "sisa_stok": "Sisa Stok"})
                    fdf["date"] = pd.to_datetime(fdf["date"])
                    fdf = fdf.set_index("date")
                    st.line_chart(fdf["Sisa Stok"], height=300, color="#003D7A")
                    # Mark depletion point
                    pred = predict_product(str(DB_PATH), products[sel], sel, models_dir=str(MODELS_DIR))
                    if pred.depletion_days:
                        st.caption(f"🔴 Perkiraan habis: **{pred.depletion_date}** ({pred.depletion_days} hari lagi)")
                else:
                    st.info("Model belum dilatih.")
            else:
                info = products[sel]
                daily_avg = float(info["initial_stock"]) / float(info["depletion_window_days"])
                st.info(f"Estimasi: habis ~{int(info['initial_stock'] / daily_avg) if daily_avg > 0 else 'N/A'} hari")

        # Prediction details
        pred = predict_product(str(DB_PATH), products[sel], sel, models_dir=str(MODELS_DIR))
        meta_cols = st.columns(4)
        conf_map = {"low": "🔴 Low", "medium": "🟡 Medium", "high": "🟢 High"}
        phase_full = {"bootstrap": "Bootstrap (synthetic)", "blend": "Blend", "mature": "Mature (real data)"}
        trend_full = {"up": "📈 Meningkat", "down": "📉 Menurun", "stable": "→ Stabil"}
        with meta_cols[0]:
            st.metric("Konfidensi", conf_map.get(pred.confidence, "?"))
        with meta_cols[1]:
            st.metric("Fase", phase_full.get(pred.phase, "?"))
        with meta_cols[2]:
            st.metric("Tren", trend_full.get(pred.trend, "?"))
        with meta_cols[3]:
            st.metric("Fallback", "Ya ⚠️" if pred.fallback_active else "Tidak ✅")

# ===========================================================================
# TAB 3 — MANAGE (Add / Edit / Delete Products)
# ===========================================================================

with tab_manage:
    st.markdown("### ⚙️ Kelola Produk")

    col_add, col_edit, col_del = st.columns([1, 1, 1])

    # --- Add Product ---
    with col_add:
        st.markdown("**Tambah Produk Baru**")
        with st.form("add_product", clear_on_submit=True):
            new_name = st.text_input("Nama Produk").strip()
            cols = st.columns(2)
            new_stock = cols[0].number_input("Stok Awal", min_value=1, value=100)
            new_unit = cols[1].selectbox("Satuan", ["sak", "dus", "ton", "kg", "pak"])
            new_depletion = cols[0].number_input("Estimasi Habis (hari)", min_value=1, value=7)
            new_shelf = cols[1].number_input("Masa Simpan (hari)", min_value=1, value=365)
            new_lead = cols[0].number_input("Lead Time (hari)", min_value=1, value=2)

            if st.form_submit_button("➕ Tambah", use_container_width=True):
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
                    st.success(f"✅ Produk '{new_name}' berhasil ditambahkan.")
                    st.rerun()

    # --- Edit Product ---
    with col_edit:
        st.markdown("**Edit Produk**")
        edit_name = st.selectbox("Pilih Produk", sorted(products.keys()), key="edit_tab_select")
        if edit_name:
            info = products[edit_name]
            with st.form("edit_product"):
                cols = st.columns(2)
                e_stock = cols[0].number_input("Stok Awal", min_value=1, value=int(info["initial_stock"]))
                e_unit = cols[1].selectbox(
                    "Satuan",
                    ["sak", "dus", "ton", "kg", "pak"],
                    index=["sak", "dus", "ton", "kg", "pak"].index(info["unit"]),
                )
                e_depletion = cols[0].number_input("Estimasi Habis (hari)", min_value=1, value=int(info["depletion_window_days"]))
                e_shelf = cols[1].number_input("Masa Simpan (hari)", min_value=1, value=int(info["shelf_life_days"]))
                e_lead = cols[0].number_input("Lead Time (hari)", min_value=1, value=int(info["supplier_lead_time_days"]))

                if st.form_submit_button("💾 Simpan", use_container_width=True):
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
                    st.success(f"✅ Produk '{edit_name}' berhasil diperbarui.")
                    st.rerun()

    # --- Delete Product ---
    with col_del:
        st.markdown("**Hapus Produk**")
        del_name = st.selectbox("Pilih Produk", sorted(products.keys()), key="del_tab_select")
        if del_name:
            st.warning(f"Hapus **{del_name}**? Semua data penjualan akan dihapus.")
            confirm = st.checkbox("Saya yakin ingin menghapus", key="del_confirm")
            if st.button("🗑️ Hapus", type="primary", disabled=not confirm, use_container_width=True):
                del products[del_name]
                save_products(products)
                _delete_product_data(del_name)
                st.success(f"✅ Produk '{del_name}' berhasil dihapus.")
                st.rerun()

# ===========================================================================
# TAB 4 — ABOUT
# ===========================================================================

with tab_about:
    # Logo + Title
    col_logo, col_title = st.columns([1, 3])
    with col_logo:
        if LOGO_PATH.exists():
            import base64
            b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
            st.markdown(
                f'<img src="data:image/png;base64,{b64}" style="width:120px;border-radius:8px;">',
                unsafe_allow_html=True,
            )
    with col_title:
        st.markdown(
            f"""
            <h2 style="color:#003D7A; margin-bottom:0;">Sistem Prediksi Stok</h2>
            <p style="color:#6B7280; font-size:1rem;">
                <em>AI-based Inventory Prediction System</em>
            </p>
            """,
            unsafe_allow_html=True,
        )

    # Project Description
    st.markdown(
        """
        <div class="about-card">
            <h3>📖 Tentang Sistem</h3>
            <p>
                Sistem Prediksi Stok adalah aplikasi berbasis <strong>kecerdasan buatan</strong> 
                yang memprediksi kapan stok produk akan habis menggunakan data penjualan historis. 
                Sistem membantu meminimalkan kerugian akibat <em>overstock</em> (barang kadaluarsa) 
                dan <em>stockout</em> (kehilangan penjualan).
            </p>
            <p>
                Input penjualan dilakukan melalui <strong>WhatsApp</strong>, prediksi menggunakan 
                <strong>Prophet</strong> (time-series forecasting), dan visualisasi melalui 
                <strong>web dashboard</strong> ini.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Team
    st.markdown(
        """
        <div class="about-card">
            <h3>👥 Tim Pengembang</h3>
        """,
        unsafe_allow_html=True,
    )
    team = [
        ("AR", "Amri Reza Wahyudin", "25321019"),
        ("FA", "Fillaah Al Farizi", "25321022"),
        ("TD", "Tia Dwi Anggra Yani", "25321010"),
    ]
    for initials, name, npm in team:
        st.markdown(
            f"""
            <div class="team-member">
                <div class="avatar">{initials}</div>
                <div>
                    <div class="name">{name}</div>
                    <div class="npm">{npm}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Supervisor
    st.markdown(
        f"""
        <div class="about-card">
            <h3>🎓 Pembimbing</h3>
            <p style="font-size:1.05rem; font-weight:500; color:#1F2937;">
                Dr.Sc. Dedi Darwis, M.Kom., CDSP.
            </p>
            <p style="color:#6B7280; font-size:0.9rem;">
                Fakultas Teknik dan Ilmu Komputer<br>
                Universitas Teknokrat Indonesia
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tech Stack
    st.markdown(
        """
        <div class="about-card">
            <h3>⚡ Tech Stack</h3>
            <p>
                <code>Python</code> •
                <code>Prophet (Meta)</code> •
                <code>Streamlit</code> •
                <code>FastAPI</code> •
                <code>SQLite</code> •
                <code>WhatsApp Web.js</code> •
                <code>APScheduler</code>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Footer
    st.markdown(
        """
        <div class="app-footer">
            <strong>Universitas Teknokrat Indonesia</strong> &nbsp;—&nbsp;
            Fakultas Teknik dan Ilmu Komputer &nbsp;—&nbsp;
            Program Studi Magister Ilmu Komputer<br>
            © 2026
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Train models on first load (triggered once)
# ---------------------------------------------------------------------------
if "models_trained" not in st.session_state:
    missing = [name for name in products if not (MODELS_DIR / f"{name}.pkl").exists()]
    if missing:
        with st.spinner(f"Melatih model untuk {len(missing)} produk..."):
            train_all_products(str(DB_PATH), str(PRODUCTS_PATH), models_dir=str(MODELS_DIR))
    st.session_state.models_trained = True
