# Day-wise / month-wise model competition — Bhogapuram (VTZ) twin

Same idea as the real-HYD version (`models/selection/DAYWISE_MONTHLY.md`): don't
collapse walk-forward into one number, keep every test-day result and roll it up
per month, per touchpoint, per model.

**⚠️ This runs on the simulated twin, not real data** — Bhogapuram has no
operational history until it opens (2026-07-08). Treat this as a pipeline test,
not a real-accuracy claim. Reproduce: `python eval_daywise.py`.

## Files
- `analytics/twin_daywise_accuracy.csv` — 576 rows (touchpoint, model, test date, accuracy, RMSE)
- `analytics/twin_monthly_accuracy.csv` — 144 rows (rolled up per month)
- `analytics/twin_monthly_winners.csv` — 24 rows (winner, runner-up, gap per touchpoint-month)

## Finding: RandomForest wins almost every month, decisively

| Touchpoint | Winner months (of 6) |
|---|---|
| CheckIn | RandomForest 5 · Naive-7d 1 |
| Security | RandomForest 5 · Naive-7d 1 |
| Boarding | RandomForest 4 · Naive-7d 1 · HistGradientBoosting 1 |
| Belt | RandomForest 5 · Naive-7d 1 |

Naive-7d wins only **May** (the first test month, least training history) on every
touchpoint — then RandomForest takes over decisively from June onward, usually by
0.2–1.6 points, sometimes with real separation from the pack.

## This is a genuinely different pattern than real HYD data — and that's the tell

On real HYD data (`models/selection/DAYWISE_MONTHLY.md`), the monthly winner
constantly changes and gaps are near-zero (0.0–2.1 pts) — models trade first place
within noise because real demand has real-world variance no single model captures
perfectly.

On the **twin**, one model (RandomForest) wins consistently, month after month.
That's expected and consistent with everything already established about the
twin: the data is generated deterministically (schedule × modelled load factor),
so it's smoother and more learnable than reality — a capable ensemble model can
fit it well and keep winning, because there's less real-world noise to trade
places over. This is the same signal the synthetic-data validation and the
single-run twin evaluation already surfaced (naive baseline ties/wins on the
twin's simpler touchpoints too).

## Honest takeaway
- **Don't read "RandomForest dominates the twin" as "RandomForest will dominate
  Bhogapuram."** It's evidence about the twin's data-generating process, not
  about real airport demand.
- The **real** signal on which models compete well comes from HYD
  (`models/selection/DAYWISE_MONTHLY.md`): ensemble/boosting models tie closely,
  Immigration has a real leader (XGBoost/RandomForest), no touchpoint needs
  monthly model-swapping.
- This script is ready and will produce a real month-by-month competition once
  `load_touchpoint_hourly()` is swapped for Bhogapuram's real EWS data.
