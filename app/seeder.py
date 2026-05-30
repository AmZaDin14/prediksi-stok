"""Seed the database with synthetic sales data.

Used to bootstrap the prediction model before real-world data accumulates.
"""

from __future__ import annotations

import json
import sqlite3


def seed_synthetic_data(
    db_path: str, products_file: str, days: int = 90
) -> None:
    """Load *products_file*, generate synthetic data, insert into SQLite.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.
    products_file:
        Path to the JSON product catalog.
    days:
        Number of historical days to generate (default 90).
    """
    with open(products_file) as f:
        products = json.load(f)

    from app.synthetic_data import generate_synthetic_data

    data = generate_synthetic_data(products, days)

    from app.data import record_sale

    for row in data:
        record_sale(db_path, row["product_name"], row["quantity"], row["reported_at"])


def get_synthetic_count(db_path: str) -> int:
    """Return the total number of rows in ``sales_reports``.

    .. note::

        Synthetic and real records cannot be distinguished at the row level
        after seeding, so this is a simple full-table count.
    """
    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM sales_reports").fetchone()[0]
    finally:
        conn.close()
    return count
