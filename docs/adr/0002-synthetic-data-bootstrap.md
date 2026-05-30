# 0002 - Synthetic data bootstrap for ML training

Context: No historical digital sales data exists (paper records only). Prophet requires training data. Owner has rough depletion estimates for each product.

Decision: On first run, generate 90 days of synthetic daily sales per product from owner estimates in `products.json`. Daily values = (initial_stock / depletion_window_days) + Gaussian noise + day-of-week variation. Train Prophet on synthetic data at launch. Use a rolling 90-day window: as real sales data accumulates, oldest entries (synthetic first, then real) are evicted. After ≥60 real days per product, no synthetic data remains.

The dashboard shows which phase each product is in (bootstrap/blend/mature) so the owner knows predictions are not yet based on real data.

Rejected options: (1) No ML at launch, switch from linear projection to ML later — wastes early data collection period, delays value. (2) Wait for N real days before enabling predictions — system provides no value for months. (3) Overweigh synthetic data indefinitely — distorts predictions permanently.

Risk: synthetic patterns may not match reality. Mitigated by decreasing weight of synthetic data as real data arrives, and transparent phase labeling.
