"""Prediksi Stok — AI-based inventory prediction system."""

from __future__ import annotations

import json
import os
import shutil
from datetime import date, datetime
from pathlib import Path

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from app.data import queue_outgoing_message
from app.predictor import predict_product
from app.server import app

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
    """Send end-of-day stock confirmation reminder."""
    if not OWNER_NUMBER:
        return
    db_path = "data/prediksi.db"
    msg = "\U0001f514 Waktunya cek stok! Kirim 'cek stok' untuk mengetahui status stok hari ini."
    queue_outgoing_message(db_path, OWNER_NUMBER, msg)
    print(f"[{datetime.now().isoformat()}] EOD reminder queued")


def main() -> None:
    port = int(os.environ.get("FASTAPI_PORT", "8765"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(_backup_job, "cron", hour=23, minute=0)
    scheduler.add_job(_depletion_alert_job, "cron", hour=8, minute=0)  # Daily 08:00
    scheduler.add_job(_eod_reminder_job, "cron", hour=20, minute=0)    # Daily 20:00
    scheduler.start()
    print(f"[{datetime.now()}] Scheduler started. Daily backup at 23:00, alerts at 08:00, EOD reminder at 20:00.")

    _backup_job()  # Run once at startup

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
