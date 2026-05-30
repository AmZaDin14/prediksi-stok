"""Stock reconciliation module for Prediksi Stok.

Compares expected stock (based on last confirmation minus sales) against
actual shelf stock reported during end-of-day confirmation. Detects
shrinkage (loss/theft/spoilage) and restocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.data import get_expected_stock, record_confirmation


@dataclass
class ReconciliationResult:
    product_name: str
    expected_stock: float
    actual_stock: float
    discrepancy: float
    discrepancy_pct: float
    is_match: bool
    shrinkage_detected: bool
    restock_detected: bool


def reconcile(
    db_path: str,
    product_name: str,
    actual_stock: float,
    threshold: float = 0.10,
    threshold_absolute: float = 1.0,
) -> ReconciliationResult:
    """Compare expected stock vs actual shelf stock.

    Args:
        db_path: Path to the SQLite database file.
        product_name: Name of the product.
        actual_stock: Quantity observed on the shelf.
        threshold: Relative threshold as a fraction of expected stock (default 10%).
        threshold_absolute: Minimum absolute threshold in units (default 1.0).

    Returns:
        A ReconciliationResult summarising the comparison.
    """
    expected = get_expected_stock(db_path, product_name)

    # No previous confirmation -- this is a baseline establishment.
    if expected is None:
        return ReconciliationResult(
            product_name=product_name,
            expected_stock=0.0,
            actual_stock=actual_stock,
            discrepancy=0.0,
            discrepancy_pct=0.0,
            is_match=True,
            shrinkage_detected=False,
            restock_detected=False,
        )

    discrepancy = actual_stock - expected
    bound = max(threshold * expected, threshold_absolute)
    discrepancy_pct = discrepancy / expected if expected != 0 else 0.0

    if abs(discrepancy) <= bound:
        return ReconciliationResult(
            product_name=product_name,
            expected_stock=expected,
            actual_stock=actual_stock,
            discrepancy=discrepancy,
            discrepancy_pct=round(discrepancy_pct, 4),
            is_match=True,
            shrinkage_detected=False,
            restock_detected=False,
        )

    if discrepancy < -bound:
        return ReconciliationResult(
            product_name=product_name,
            expected_stock=expected,
            actual_stock=actual_stock,
            discrepancy=discrepancy,
            discrepancy_pct=round(discrepancy_pct, 4),
            is_match=False,
            shrinkage_detected=True,
            restock_detected=False,
        )

    # discrepancy > bound
    return ReconciliationResult(
        product_name=product_name,
        expected_stock=expected,
        actual_stock=actual_stock,
        discrepancy=discrepancy,
        discrepancy_pct=round(discrepancy_pct, 4),
        is_match=False,
        shrinkage_detected=False,
        restock_detected=True,
    )


def confirm_and_reconcile(
    db_path: str,
    product_name: str,
    actual_stock: float,
    threshold: float = 0.10,
) -> ReconciliationResult:
    """Record a confirmation and run reconciliation in one step.

    Calls :func:`record_confirmation` then :func:`reconcile`.

    Args:
        db_path: Path to the SQLite database file.
        product_name: Name of the product.
        actual_stock: Quantity observed on the shelf.
        threshold: Relative threshold passed to ``reconcile``.

    Returns:
        A ReconciliationResult summarising the comparison.
    """
    record_confirmation(db_path, product_name, actual_stock)
    return reconcile(db_path, product_name, actual_stock, threshold=threshold)
