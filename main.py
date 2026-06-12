"""Prediksi Stok — AI-based inventory prediction system."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import json
import os
import shutil
from datetime import date, datetime
from pathlib import Path

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from app.data import get_expected_stock, get_products_confirmed_today, queue_outgoing_message, record_confirmation
from app.predictor import predict_product, train_specific_products
from app.server import app, _build_eod_reminder_body

OWNER_NUMBER = os.environ.get("OWNER_NUMBER", "")


def _backup_job() -> None:
    """Backup prediksi.db and products.json, retaining 7 most recent backups."""
    src_dir = Path(__file__).parent
    dst_dir = src_dir / "data" / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()

    files = [
        (src_dir / "data" / "prediksi.db", dst_dir / f"prediksi-{today}.db"),
        (src_dir / "products.json", dst_dir / f"products-{today}.json"),
    ]

    for src, dst in files:
        if src.exists():
            shutil.copy2(str(src), str(dst))
            print(f"[{datetime.now().isoformat()}] Backup: {src.name} -> {dst.name}")

    # Rolling retention: keep 7 newest
    for pattern in ["prediksi-*.db", "products-*.json"]:
        backups = sorted(dst_dir.glob(pattern), reverse=True)
        for old in backups[7:]:
            old.unlink()
            print(f"[{datetime.now().isoformat()}] Cleanup: removed old backup {old.name}")


def _depletion_alert_job() -> None:
    """Check all products. Alert if depletion <= supplier lead time."""
    if not OWNER_NUMBER:
        return
    db_path = "data/prediksi.db"
    with open("products.json") as f:
        products = json.load(f)

    for name, config in products.items():
        try:
            pred = predict_product(db_path, config, name)
            lt = config["supplier_lead_time_days"]
            if pred.depletion_days is not None and pred.depletion_days <= lt:
                msg = (
                    f"⚠️ PERINGATAN: {name} diperkirakan habis dalam "
                    f"{pred.depletion_days} hari (lead time {lt} hari). "
                    f"Segera lakukan pemesanan!"
                )
                queue_outgoing_message(db_path, OWNER_NUMBER, msg)
                print(f"[{datetime.now().isoformat()}] Alert: {name} depletion in {pred.depletion_days}d <= {lt}d lead time")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error checking {name}: {e}")


def _eod_reminder_job() -> None:
    """Send end-of-day stock confirmation reminder with expected stock."""
    if not OWNER_NUMBER:
        return
    db_path = "data/prediksi.db"
    msg = _build_eod_reminder_body()
    queue_outgoing_message(db_path, OWNER_NUMBER, msg)
    print(f"[{datetime.now().isoformat()}] EOD reminder queued")


def _eod_escalation_job() -> None:
    """Second reminder at 21:30 if products are still unconfirmed."""
    if not OWNER_NUMBER:
        return
    db_path = "data/prediksi.db"
    with open("products.json") as f:
        products = json.load(f)

    confirmed_today = set(get_products_confirmed_today(db_path))
    missing = [name for name in products if name not in confirmed_today]

    if not missing:
        return

    product_lines = ", ".join(missing)
    msg = (
        f"⚠️ Stok BELUM dikonfirmasi untuk: {product_lines}.\n\n"
        "Kirim \"ok\" jika semua sesuai,\n"
        "atau kirim: cek stok [produk] [jumlah]"
    )
    queue_outgoing_message(db_path, OWNER_NUMBER, msg)
    print(f"[{datetime.now().isoformat()}] EOD escalation queued for: {product_lines}")


def _eod_auto_confirm_job() -> None:
    """Auto-confirm all unconfirmed products at 23:00 with expected stock."""
    if not OWNER_NUMBER:
        return
    db_path = "data/prediksi.db"
    with open("products.json") as f:
        products = json.load(f)

    confirmed_today = set(get_products_confirmed_today(db_path))
    auto_confirmed: list[str] = []
    retrain_names: list[str] = []

    for name, attrs in products.items():
        if name in confirmed_today:
            continue
        stock = get_expected_stock(db_path, name, initial_stock=float(attrs["initial_stock"]))
        if stock is not None:
            record_confirmation(db_path, name, stock)
            auto_confirmed.append(f"✓ {name}: {stock:.0f} {attrs['unit']} (expected)")
            retrain_names.append(name)
        else:
            auto_confirmed.append(f"❌ {name}: stok tidak diketahui")

    if not auto_confirmed:
        return  # All were already confirmed

    # Retrain models for auto-confirmed products
    if retrain_names:
        try:
            train_specific_products(db_path, "products.json", retrain_names)
        except Exception:
            pass

    msg = (
        "\U0001f504 Stok otomatis dikonfirmasi:\n"
        + "\n".join(auto_confirmed)
        + "\n\nAda selisih? Kirim \"cek stok [produk] [jumlah]\" besok pagi."
    )
    queue_outgoing_message(db_path, OWNER_NUMBER, msg)
    print(f"[{datetime.now().isoformat()}] Auto-confirmed {len(auto_confirmed)} product(s)")


def main() -> None:
    port = int(os.environ.get("FASTAPI_PORT", "8765"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(_backup_job, "cron", hour=23, minute=0)
    scheduler.add_job(_depletion_alert_job, "cron", hour=8, minute=0)  # Daily 08:00
    scheduler.add_job(_eod_reminder_job, "cron", hour=20, minute=0)    # Daily 20:00
    scheduler.add_job(_eod_escalation_job, "cron", hour=21, minute=30)  # Daily 21:30
    scheduler.add_job(_eod_auto_confirm_job, "cron", hour=23, minute=0)  # Daily 23:00
    scheduler.start()
    print(f"[{datetime.now()}] Scheduler started. Backup 23:00, alerts 08:00, EOD reminder 20:00, escalation 21:30, auto-confirm 23:00.")

    _backup_job()  # Run once at startup

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
