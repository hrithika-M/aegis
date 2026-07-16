# Day-wise / week-wise model competition — Bhogapuram (VTZ) twin

Full write-up (both HYD-real and this twin section) lives in
[`models/selection/DAYWISE_WEEKWISE.md`](../../models/selection/DAYWISE_WEEKWISE.md)
at the repo root — kept together so the real-vs-simulated contrast is visible in
one place. Short version:

**⚠️ Simulated data — pipeline test, not a real-accuracy claim** (Bhogapuram opens
2026-07-08 with no operational history yet).

Reproduce: `python eval_daywise.py` then `python eval_weekwise.py`.

## Files
`analytics/twin_daywise_accuracy.csv` (3,960 rows, daily) ·
`analytics/twin_weekwise_accuracy.csv` (576 rows) ·
`analytics/twin_weekwise_winners.csv` (96 rows) ·
`analytics/twin_monthly_accuracy.csv` / `twin_monthly_winners.csv` (coarser view, kept).

## Finding
RandomForest wins almost every week on every touchpoint (17–21 of ~23–24 weeks),
but the **margin is usually small** (weekly gap mean 0.59, median 0.55 — close to
HYD's real 0.52/0.30). Don't read this as "RandomForest will dominate real
Bhogapuram" — it reflects the twin's smoother, generated data-process, not real
demand. Ready to produce a real week-by-week competition once
`load_touchpoint_hourly()` is swapped for Bhogapuram's real EWS data.
