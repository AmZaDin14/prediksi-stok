"""Initialize the SQLite database schema for Prediksi Stok."""

import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "prediksi.db")

SCHEMA_SALES_REPORTS = """
CREATE TABLE IF NOT EXISTS sales_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    reported_at TEXT NOT NULL
)
"""

SCHEMA_STOCK_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS stock_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    snapshot_date TEXT NOT NULL,
    is_confirmation INTEGER NOT NULL DEFAULT 0
)
"""


def setup_database():
    """Create the data directory and database with all tables."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(SCHEMA_SALES_REPORTS)
    cursor.execute(SCHEMA_STOCK_SNAPSHOTS)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    setup_database()
