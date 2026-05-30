"""Prediksi Stok — AI-based inventory prediction system."""

from __future__ import annotations

import os
import shutil
from datetime import date, datetime
from pathlib import Path

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from app.server import app


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


def main() -> None:
    port = int(os.environ.get("FASTAPI_PORT", "8765"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(_backup_job, "cron", hour=23, minute=0)
    scheduler.start()
    print(f"[{datetime.now()}] Scheduler started. Daily backup at 23:00.")

    _backup_job()  # Run once at startup

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
