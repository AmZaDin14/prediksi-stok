"""Synthetic daily sales data generator for Prediksi Stok.

Generates realistic-looking sales data based on owner estimates from
products.json.  Used to bootstrap the ML model before real data accumulates.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

# Day-of-week multipliers (applied multiplicatively to daily baseline).
# Monday=0 ... Sunday=6
_DAY_FACTORS: dict[int, float] = {
    0: 1.0,  # Monday
    1: 1.0,  # Tuesday
    2: 1.0,  # Wednesday
    3: 1.0,  # Thursday
    4: 1.1,  # Friday
    5: 0.8,  # Saturday
    6: 0.7,  # Sunday
}


def _random_time_on_date(date: date, rng: random.Random) -> datetime:
    """Return a datetime on *date* with a time uniformly between 08:00-20:00."""
    hour = rng.randint(8, 19)  # 08:00 through 19:00 (last valid start hour)
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    return datetime(date.year, date.month, date.day, hour, minute, second)


def generate_synthetic_data(
    products: dict, days: int = 90, seed: int = 42
) -> list[dict]:
    """Generate synthetic daily sales for each product.

    Parameters
    ----------
    products:
        Dictionary from products.json mapping product name to its config.
        Each config must contain *initial_stock* and *depletion_window_days*.
    days:
        Number of historical days to generate (default 90).
    seed:
        Random seed for reproducibility (default 42).

    Returns
    -------
    list[dict]:
        A list of dicts with keys *product_name*, *quantity*, *reported_at*
        (ISO-format timestamp).

    The algorithm for each product:

    1. ``daily_avg = initial_stock / depletion_window_days``
    2. For each of the last *days* days (ending yesterday):
       a. Apply the day-of-week factor (e.g. Friday **1.1**, Sunday **0.7**).
       b. Add Gaussian noise with ``stddev = 0.15 * daily_avg``.
       c. Floor the result at 0 (no negative sales).
    3. Timestamps are spread uniformly between 08:00-20:00 on each day.
    """
    rng = random.Random(seed)
    today = datetime.now().date()
    results: list[dict] = []

    for product_name, config in products.items():
        initial = config["initial_stock"]
        window = config["depletion_window_days"]
        daily_avg = initial / window

        for day_offset in range(days, 0, -1):
            sale_date = today - timedelta(days=day_offset)
            dow = sale_date.weekday()
            factor = _DAY_FACTORS[dow]

            # Baseline = daily_avg * day-of-week factor + Gaussian noise
            noise = rng.gauss(0, 0.15 * daily_avg)
            quantity = daily_avg * factor + noise

            # Floor at zero
            quantity = max(0.0, quantity)

            timestamp = _random_time_on_date(sale_date, rng).isoformat()

            results.append(
                {
                    "product_name": product_name,
                    "quantity": round(quantity, 2),
                    "reported_at": timestamp,
                }
            )

    return results
