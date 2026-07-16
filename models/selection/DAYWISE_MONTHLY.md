# Day-wise / month-wise model competition — real HYD data

Naveen's ask: don't collapse walk-forward into one aggregate accuracy number —
show it **day-wise and month-wise**, per touchpoint, so we can see which models
actually compete well over time, not just on average.

Same real trusted HYD EWS data, same walk-forward (warmup=60, step=10), same
symmetric accuracy metric as the rest of `modeling/` — this keeps every
per-test-day result instead of discarding it after averaging.

Reproduce: `python -m modeling.eval_daywise` (in `DATA_POD/`).

## Files
- `daywise_accuracy.csv` — one row per (touchpoint, model, test date): accuracy, RMSE, MAE. **1,211 rows.**
- `monthly_accuracy.csv` — rolled up per (touchpoint, model, month): mean/std accuracy, mean RMSE, n days. **448 rows.**
- `monthly_winners.csv` — per (touchpoint, month): the winning model, its accuracy, the runner-up, and the gap. **64 rows.**

## Headline finding: the winner changes almost every month — by a hair

**Winner-count per touchpoint (how many months, of ~9–11, each model won):**

| Touchpoint | Winner months |
|---|---|
| Entry | Naive-7d 3 · LightGBM 2 · HistGB 2 · RandomForest 1 · XGBoost 1 |
| Check-In | LightGBM 5 · XGBoost 2 · Bagging 1 · HistGB 1 · Naive-7d 1 · RandomForest 1 |
| Emigration | LightGBM 4 · Naive-7d 2 · Bagging 2 · HistGB 1 · RandomForest 1 · XGBoost 1 |
| **Immigration** | **XGBoost 4** · RandomForest 3 · LightGBM 2 · HistGB 1 · ExtraTrees 1 |
| Security (PESC) | LightGBM 4 · XGBoost 3 · Bagging 2 · RandomForest 1 · ExtraTrees 1 |
| Transfers | Bagging 4 · LightGBM 3 · HistGB 2 · XGBoost 1 · RandomForest 1 |

**But the gap between the winner and the runner-up is almost always tiny** — from the
month-by-month detail (see `monthly_winners.csv`):

| Touchpoint | Example months | Winner acc. | Runner-up | Gap |
|---|---|---|---|---|
| Entry | 2025-07 | LightGBM 93.9 | XGBoost | **0.0** |
| Entry | 2025-06 | RandomForest 85.9 | Bagging | **0.1** |
| Transfers | 2025-06 | Bagging 78.4 | HistGB | **0.0** |
| Immigration | 2025-05 | RandomForest 68.1 | Bagging | **0.1** |

Typical gaps across all 64 touchpoint-months: **0.0 to ~2.1 points.** These models
are not really "beating" each other — they're trading first place within noise,
month after month. This is the month-by-month proof of what the aggregate
benchmark already implied ("every capable tree/boosting model ties within ~1 pt").

## So what do we do with this (the actionable read)

1. **Aggregate champion ≠ best-every-month, and that's fine.** E.g. Entry's aggregate
   champion is RandomForest, but Naive-7d actually wins the most individual months
   (3 of 9). Since the gap is inside noise, this doesn't mean Naive-7d is "better" —
   it means the aggregate pick is the right practical default (stable, doesn't need
   monthly swapping) rather than the wrong pick.
2. **Immigration is the one touchpoint with a real, consistent leader.** XGBoost wins
   4 months and RandomForest 3 — both boosting/ensemble families — while linear/GLM
   models never come close (established earlier). This matches the aggregate pick.
3. **A dip is visible and worth a data-quality look:** Transfers, **Oct 2025, winner
   accuracy only 59.0%** — well below its usual 75–85% band. Worth checking that
   month's EWS data (Aegis audit log) for an unresolved sensor issue.
4. **No touchpoint needs month-by-month model swapping.** Given the gaps, switching
   models monthly would chase noise, not signal, and complicate deployment for no
   measurable accuracy gain. The existing single-model-per-touchpoint choice stands,
   now with month-by-month evidence behind it instead of just the aggregate.

## Honesty note
This is real HYD data — the day-wise and month-wise numbers here are as real as the
aggregate walk-forward numbers already in `MODEL_SELECTION.md`. (Contrast with the
VTZ digital-twin model-selection run, which is a pipeline test on simulated data —
see `bhogapuram_digital_twin/modeling/README.md`.)
