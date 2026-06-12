"""Sales data access functions for Prediksi Stok.

Provides low-level SQLite operations for recording and querying sales reports,
stock confirmations, and computing expected stock levels.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist (for test isolation)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sales_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            reported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stock_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            snapshot_date TEXT NOT NULL,
            is_confirmation INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS outgoing_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0
        );
    """)


def _get_connection(db_path: str) -> sqlite3.Connection:
    """Get a connection with row factory and ensure tables exist."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def get_products_confirmed_today(db_path: str) -> list[str]:
    """Return list of product names already confirmed today."""
    today = date.today().isoformat()
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT product_name
            FROM stock_snapshots
            WHERE is_confirmation = 1 AND date(snapshot_date) = ?
            """,
            (today,),
        ).fetchall()
        return [r["product_name"] for r in rows]
    finally:
        conn.close()


def record_sale(db_path: str, product_name: str, quantity: float, timestamp: str) -> None:
    """Insert a sales report.

    Args:
        db_path: Path to the SQLite database file.
        product_name: Name of the product sold.
        quantity: Quantity sold.
        timestamp: ISO format datetime string (e.g. "2026-05-30T14:30:00").
    """
    conn = _get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO sales_reports (product_name, quantity, reported_at) VALUES (?, ?, ?)",
            (product_name, quantity, timestamp),
        )
        conn.commit()
    finally:
        conn.close()


def get_daily_sales(
    db_path: str,
    product_name: str,
    from_date: str,
    to_date: str,
) -> list[dict]:
    """Return daily aggregated sales for a product within a date range.

    Each result dict has keys ``sale_date`` (str ``YYYY-MM-DD``) and
    ``total_quantity`` (float).

    Args:
        db_path: Path to the SQLite database file.
        product_name: Name of the product.
        from_date: Inclusive start date (``YYYY-MM-DD``).
        to_date: Inclusive end date (``YYYY-MM-DD``).

    Returns:
        List of dicts ordered by date ascending.
    """
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT date(reported_at) AS sale_date, SUM(quantity) AS total_quantity
            FROM sales_reports
            WHERE product_name = ? AND date(reported_at) BETWEEN ? AND ?
            GROUP BY date(reported_at)
            ORDER BY sale_date
            """,
            (product_name, from_date, to_date),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_last_confirmation(db_path: str, product_name: str) -> dict | None:
    """Return the most recent stock confirmation for a product, or None.

    The returned dict has keys ``product_name``, ``quantity``, ``snapshot_date``,
    ``is_confirmation``.

    Args:
        db_path: Path to the SQLite database file.
        product_name: Name of the product.

    Returns:
        A dict representing the latest confirmation row, or None if no
        confirmation exists.
    """
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT product_name, quantity, snapshot_date, is_confirmation
            FROM stock_snapshots
            WHERE product_name = ? AND is_confirmation = 1
            ORDER BY snapshot_date DESC, id DESC
            LIMIT 1
            """,
            (product_name,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_expected_stock(db_path: str, product_name: str, initial_stock: float | None = None) -> float | None:
    """Compute expected current stock for a product.

    Expected stock is defined as::

        last_confirmed_quantity - sum_of_sales_since_last_confirmation

    If no confirmation exists and *initial_stock* is provided, returns
    ``initial_stock - today_sales`` so the dashboard shows real-time daily
    decrements even before the first EOD confirmation.

    Args:
        db_path: Path to the SQLite database file.
        product_name: Name of the product.
        initial_stock: Starting stock used before first confirmation.

    Returns:
        Expected stock level, or None if unknown.
    """
    conn = _get_connection(db_path)
    try:
        last_conf = conn.execute(
            """
            SELECT quantity, snapshot_date
            FROM stock_snapshots
            WHERE product_name = ? AND is_confirmation = 1
            ORDER BY snapshot_date DESC
            LIMIT 1
            """,
            (product_name,),
        ).fetchone()

        if last_conf is None:
            if initial_stock is not None:
                today = date.today().isoformat()
                total_sales = conn.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM sales_reports WHERE product_name = ? AND date(reported_at) = ?",
                    (product_name, today),
                ).fetchone()[0]
                return initial_stock - total_sales
            return None

        last_qty = last_conf["quantity"]
        last_date = last_conf["snapshot_date"]

        # Sum of all sales AFTER the confirmation timestamp
        total_sales_row = conn.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) AS total
            FROM sales_reports
            WHERE product_name = ? AND reported_at > ?
            """,
            (product_name, last_date),
        ).fetchone()

        total_sales = total_sales_row["total"]
        return last_qty - total_sales

    finally:
        conn.close()


def queue_outgoing_message(db_path: str, recipient: str, body: str) -> None:
    """Insert an outgoing message to be sent via WhatsApp.

    Args:
        db_path: Path to the SQLite database file.
        recipient: The recipient phone number.
        body: The message body text.
    """
    conn = _get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO outgoing_messages (recipient, body, created_at) VALUES (?, ?, ?)",
            (recipient, body, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_pending_outgoing(db_path: str, recipient: str | None = None) -> list[dict]:
    """Fetch pending outgoing messages and mark them as sent.

    Args:
        db_path: Path to the SQLite database file.
        recipient: Optional recipient filter. If provided, only messages
            for that recipient are returned.

    Returns:
        List of dicts with keys ``id``, ``recipient``, ``body``, ``created_at``.
    """
    conn = _get_connection(db_path)
    try:
        if recipient:
            rows = conn.execute(
                "SELECT id, recipient, body, created_at FROM outgoing_messages WHERE sent = 0 AND recipient = ? ORDER BY id ASC LIMIT 10",
                (recipient,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, recipient, body, created_at FROM outgoing_messages WHERE sent = 0 ORDER BY id ASC LIMIT 10",
            ).fetchall()
        # Mark as sent
        ids = [r["id"] for r in rows]
        if ids:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(f"UPDATE outgoing_messages SET sent = 1 WHERE id IN ({placeholders})", ids)
            conn.commit()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def record_confirmation(db_path: str, product_name: str, quantity: float) -> None:
    """Record an end-of-day stock confirmation.

    Inserts a row into ``stock_snapshots`` with ``is_confirmation=1`` and
    ``snapshot_date`` set to the current datetime (ISO format).

    Args:
        db_path: Path to the SQLite database file.
        product_name: Name of the product.
        quantity: Confirmed shelf stock quantity.
    """
    now = datetime.now().isoformat()
    conn = _get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO stock_snapshots (product_name, quantity, snapshot_date, is_confirmation) VALUES (?, ?, ?, 1)",
            (product_name, quantity, now),
        )
        conn.commit()
    finally:
        conn.close()
