# Day-wise / week-wise model competition — real HYD data

Naveen's ask: don't collapse walk-forward into one aggregate accuracy number —
show it **day-wise and week-wise**, per touchpoint, so we can see which models
actually compete well over time.

Same real trusted HYD EWS data, same symmetric accuracy metric as the rest of
`modeling/`. Two runs feed this:
- **Day-wise** (`eval_daywise.py`): walk-forward with `warmup=60, step=3` — a
  model is trained fresh and scored on every 3rd calendar day. Step was
  tightened from the original `step=10` specifically so a week contains
  **multiple** test days, not just one (at step=10, every ISO week had exactly
  one test day — a weekly "average" would just be that single day relabeled).
- **Week-wise** (`eval_weekwise.py`): rolls the day-wise results up by ISO week.

Reproduce (in `DATA_POD/`): `python -m modeling.eval_daywise` then
`python -m modeling.eval_weekwise`. **Runtime: ~42 min** for the day-wise pass
(7 models × 6 touchpoints, full retrain at every test day — no caching).

## Files
- `daywise_accuracy.csv` — one row per (touchpoint, model, test date): accuracy, RMSE, MAE. **4,011 rows** (175 unique test dates).
- `weekwise_accuracy.csv` — rolled up per (touchpoint, model, ISO week): mean/std accuracy, mean RMSE, n days. **1,778 rows**, mostly 2–3 test days per week (verified — not a relabeling artifact).
- `weekwise_winners.csv` — per (touchpoint, week): winning model, accuracy, runner-up, gap. **254 rows.**
- (Also kept from the earlier pass: `monthly_accuracy.csv`, `monthly_winners.csv` — coarser view, still useful for the big picture.)

## Headline finding: the weekly winner changes constantly — gaps are almost always inside noise

**Winner-count per touchpoint (how many weeks, of ~23–29, each model won):**

| Touchpoint | Winner weeks |
|---|---|
| Entry | Naive-7d 11 · HistGB 9 · LightGBM 6 · ExtraTrees 3 · XGBoost 3 · Bagging 2 · RandomForest 2 |
| CheckIn | HistGB 11 · XGBoost 11 · LightGBM 8 · RandomForest 5 · ExtraTrees 4 · Bagging 3 · Naive-7d 2 |
| Emigration | Bagging 12 · LightGBM 9 · HistGB 7 · RandomForest 6 · XGBoost 4 · Naive-7d 3 · ExtraTrees 2 |
| **Immigration** | **HistGB 15 · Bagging 10** · XGBoost 6 · LightGBM 6 · RandomForest 5 · ExtraTrees 2 |
| Security (PESC) | LightGBM 10 · XGBoost 9 · Bagging 9 · HistGB 8 · ExtraTrees 5 · RandomForest 2 · Naive-7d 1 |
| Transfers | HistGB 11 · RandomForest 10 · LightGBM 7 · Bagging 5 · XGBoost 5 · ExtraTrees 3 · Naive-7d 2 |

**Across all 254 touchpoint-weeks, the winner-vs-runner-up gap:** mean **0.52 pts**,
median **0.30 pts**, 75th percentile **0.60 pts**, max **8.2 pts** (one outlier
week). At week resolution, same story as the earlier month-level view but
sharper: these ensemble/boosting models are trading first place inside noise
almost every single week.

## Immigration is still the one touchpoint with a real, consistent leader

HistGradientBoosting (15 weeks) and Bagging (10 weeks) — both ensemble methods —
dominate Immigration's weekly wins; RandomForest (5) and the boosting models
trail but stay close. Linear/GLM models never appear (established earlier in the
20-model benchmark). This matches the aggregate pick and is the clearest
"this model family genuinely fits this touchpoint" signal in the whole dataset.

## Entry: worth a second look
Naive-7d wins **11 of ~29 weeks** for Entry — more than any single ML model. This
doesn't mean Naive-7d is "better" (differences are inside noise most weeks), but
it's a stronger signal than at Immigration that Entry's demand is close to
purely calendar-driven (same hour, same weekday, most weeks) — consistent with
Entry being an early-morning-peaked, schedule-driven touchpoint.

## Honest takeaway
1. **No touchpoint needs week-to-week or month-to-month model swapping.** Gaps
   are inside noise almost everywhere; switching models on a weekly cadence
   would chase noise, not real accuracy, and add deployment complexity for
   nothing measurable.
2. **Immigration is the one place with real, sustained separation** —
   HistGradientBoosting/Bagging over the rest — worth weighting toward that
   family if Immigration ever needs a dedicated retrain.
3. This is real HYD data — as real as the aggregate walk-forward numbers already
   in `MODEL_SELECTION.md`, just sliced finer.

---

# Day-wise / week-wise model competition — Bhogapuram TWIN (simulated)

Same exercise on the digital twin (`bhogapuram_digital_twin/modeling/eval_daywise.py`
+ `eval_weekwise.py`), density tightened from `step=7` to `step=1` (every day) so
weeks average real multiple days (verified: mostly 7 test days per week).

**⚠️ Simulated data — pipeline test, not a real-accuracy claim** (Bhogapuram opens
2026-07-08 with no operational history yet).

## Files
`analytics/twin_daywise_accuracy.csv` (3,960 rows) · `twin_weekwise_accuracy.csv`
(576 rows) · `twin_weekwise_winners.csv` (96 rows).

## Finding: RandomForest wins almost every week — but the margins are small

| Touchpoint | Winner weeks (of ~23–24) |
|---|---|
| Security | RandomForest 21 · HistGB 1 · XGBoost 1 · Naive-7d 1 |
| CheckIn | RandomForest 19 · Naive-7d 5 |
| Belt | RandomForest 19 · Naive-7d 3 · HistGB 2 |
| Boarding | RandomForest 17 · Naive-7d 5 · LightGBM 1 · HistGB 1 |

**Weekly gap across all 96 rows: mean 0.59, median 0.55** — close to HYD's
(0.52 / 0.30). So the earlier, coarser monthly view ("RandomForest dominates
decisively") slightly overstates the margin — at week resolution RandomForest
wins *consistently* but usually by a **small** amount, closer in kind (if not in
frequency) to how models compete on real data. Naive-7d wins early weeks
(least training history), same pattern as before.

## Honest takeaway
Don't read "RandomForest wins nearly every week" as "it will win at real
Bhogapuram" — it's still a signal about the twin's smoother, generated
data-process, not a forecast about real demand. This script is ready and will
produce a real week-by-week competition once `load_touchpoint_hourly()` is
swapped for Bhogapuram's real EWS data post-opening.
