# POD Demand Model — Selection & Justification

**The question this answers:** "You used model X — why that one and not the others?"
We benchmarked **20 algorithms** on the same task, the same honest ruler, and the
same trusted data. This is the record.

> Reproduce: `python -m modeling.benchmark` (batch 1) and
> `python -m modeling.benchmark --extra` (batch 2). Raw run log:
> `docs/model_trials.md`. Generate a Plan of the Day: `python -m modeling.plan`.

---

## Method (why these numbers are trustworthy)

- **Task:** predict hourly passenger count per touchpoint from calendar features.
- **Target:** the **trusted (corrected) actuals** from our data-trust engine — not
  raw camera data (which contains blackouts/phantoms that would corrupt scoring).
- **Evaluation:** **expanding-window walk-forward** over 25–30 held-out days per
  touchpoint (train on all prior days, predict the next, repeat) — *not* a single
  lucky holdout. Symmetric min/max accuracy (matches the project's own metric).
- **Fairness:** every algorithm is fed identical rows; only the estimator changes.

---

## Full results — 20 models, average accuracy across all 6 touchpoints

| # | Model | AVG | Entry | CheckIn | Emig | Immig | PESC | Transf | Family |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **RandomForest [Naveen]** | **81.7** | 87.6 | 87.9 | 80.0 | 66.9 | 90.6 | 77.1 | tree ensemble |
| 2 | **LightGBM** | **81.7** | 86.9 | 88.3 | 80.1 | 66.5 | 90.9 | 77.8 | gradient boosting |
| 3 | Bagging (trees) | 81.6 | 87.5 | 87.9 | 80.0 | 66.9 | 90.6 | 77.0 | tree ensemble |
| 4 | HistGradientBoosting | 81.5 | 86.8 | 88.2 | 79.4 | 66.3 | 90.8 | 77.6 | gradient boosting |
| 5 | XGBoost | 81.5 | 86.7 | 87.8 | 79.5 | 67.1 | 90.7 | 77.3 | gradient boosting |
| 6 | ExtraTrees | 80.5 | 86.6 | 87.3 | 78.0 | 65.7 | 90.2 | 75.1 | tree ensemble |
| 7 | GradientBoosting | 80.4 | 86.5 | 87.7 | 77.5 | 64.5 | 89.6 | 76.7 | gradient boosting |
| 8 | kNN-7 | 80.0 | 88.0 | 87.4 | 76.8 | 62.6 | 89.6 | 75.9 | instance |
| 9 | Naive-seasonal-7d | 79.3 | 86.5 | 86.7 | 77.7 | 63.0 | 87.9 | 73.8 | **baseline** |
| 10 | DecisionTree (single) | 79.1 | 86.0 | 85.9 | 77.1 | 63.2 | 89.1 | 73.1 | tree |
| 11 | Naive-median(dow,hour) | 78.4 | 88.2 | 87.2 | 77.3 | 63.2 | 82.1 | 72.5 | **baseline** |
| 12 | AdaBoost | 76.9 | 85.2 | 85.4 | 70.4 | 59.6 | 88.5 | 72.0 | boosting |
| 13 | MLP neural-net | 74.5 | 80.1 | 82.0 | 72.6 | 57.5 | 82.4 | 72.2 | neural net |
| 14 | SVR (RBF kernel) | 70.8 | 78.0 | 79.1 | 66.0 | 54.9 | 80.4 | 66.3 | kernel |
| 15 | ElasticNet | 66.2 | 74.9 | 78.8 | 58.1 | 52.0 | 75.2 | 58.4 | linear |
| 16 | TweedieGLM (count) | 66.1 | 73.9 | 78.7 | 58.1 | 52.4 | 75.2 | 58.3 | GLM |
| 17 | Lasso | 66.0 | 73.7 | 78.8 | 58.0 | 51.6 | 75.1 | 58.7 | linear |
| 18 | PoissonGLM (count) | 66.0 | 73.7 | 78.7 | 58.1 | 52.3 | 75.2 | 58.3 | GLM |
| 19 | Ridge | 66.0 | 73.8 | 78.7 | 58.0 | 51.4 | 75.1 | 58.7 | linear |
| 20 | HuberRegressor (robust) | 65.7 | 73.6 | 78.6 | 58.9 | 50.1 | 74.6 | 58.6 | linear |

---

## The three findings (the defensible answer)

**1. Every strong model ties at 81.5–81.7%.** RandomForest, LightGBM, Bagging,
HistGradientBoosting and XGBoost are separated by **0.2 points** — far inside the
**±4–10% day-to-day variance**. They are statistically indistinguishable. There is
no "better algorithm" hiding here.

**2. A naive "same hour last week" baseline scores 79.3%** — within ~2.4 points of
the best model. The predictable weekly/hourly pattern does most of the work; the
ML models add a small, real, but limited edge.

**3. This is the third independent proof that the model is not the bottleneck.**
Alongside our earlier findings (cleaning actuals ≈ accuracy-neutral; richer
features ≈ neutral), the model sweep confirms the white papers' and the Bhogapuram
proposal's thesis: **accuracy is bounded by input-data quality, not by the
algorithm.** That is why our effort went into the data-trust layer.

---

## Why not the other families (pre-answered)

| If asked "why not…" | Answer (measured) |
|---|---|
| **Deep learning (MLP)?** | Tried — **74.5%, 7 points worse.** Neural nets need far more data than we have and overkill a strongly-seasonal signal; they overfit the noisy actuals. |
| **SVR / kernel methods?** | **70.8%** and by far the slowest. Kernels don't scale to this volume and didn't help. |
| **Poisson / Tweedie (proper count models)?** | **66%** — no better than plain linear. The load-vs-time relationship is nonlinear/threshold-shaped; trees capture it, GLMs cannot, so being "statistically correct for counts" bought nothing. |
| **Linear (Ridge/Lasso/ElasticNet/Huber)?** | **~66% — the floor.** Relationship is too nonlinear for a linear fit. |
| **A single decision tree?** | 79.1% — decent, but ensembles beat it by reducing variance. |
| **AdaBoost?** | 76.9% — too sensitive to residual noise in the actuals. |

---

## Decision & recommendation

Because the top models are tied on accuracy, the choice is decided by **secondary
criteria** (integration, speed, dependencies, future fit) — which is the honest,
sophisticated basis for the call:

- **Now — keep RandomForest (Naveen's incumbent).** It is tied for #1, already
  integrated across his pipeline, needs no tuning, and adds **zero new dependency
  or migration risk.** There is no accuracy reason to change it today.
- **Later — adopt LightGBM when the real flight data arrives.** It exactly ties RF
  today and slightly wins the harder touchpoints (PESC, CheckIn, Transfers,
  Emigration). More importantly, when the rich features land (PNR/booking load,
  aircraft type, airline, destination, events, weather — mostly categorical),
  gradient boosting typically pulls ahead of RF and trains/infers much faster.
  LightGBM is the natural upgrade path; the benchmark harness will re-decide it on
  data, not opinion.

**Bottom line for stakeholders:** we tested 20 algorithms spanning every major
family. RandomForest and LightGBM are the joint best; deep learning, SVR, count
GLMs and linear models all lose. The winners are within noise of each other and
only ~2 points above a trivial baseline — proving the algorithm is not the lever.
We therefore keep the incumbent now and have a measured, ready upgrade for when
better data makes a better model worth it.

---

## Per-touchpoint selection

Best model **for each touchpoint** (mean±std, walk-forward, trusted actuals). 'Chosen' keeps RandomForest unless another model beats it by >1.0 pt (a real gap vs the ±4-10% day noise).

| Touchpoint | Naive-seasonal-7d | RandomForest | ExtraTrees | HistGradientBoosting | LightGBM | XGBoost | Bagging(trees) | Winner | vs RF | **Chosen** |
|---|---|---|---|---|---|---|---|---|---|---|
| Entry Gates | 86.5±8.5 | **87.6±8.8** | 86.6±10.5 | 86.8±12.7 | 86.9±12.3 | 86.7±12.0 | 87.5±8.9 | RandomForest | +0.0 | RandomForest |
| Check-In Counters | 86.7±4.5 | 87.9±5.1 | 87.3±5.0 | 88.2±5.0 | **88.3±5.1** | 87.8±5.3 | 87.9±5.1 | LightGBM | +0.4 | RandomForest |
| Departure Emigration | 77.7±7.4 | 80.0±6.1 | 78.0±6.0 | 79.4±6.7 | **80.1±6.1** | 79.5±6.0 | 80.0±5.9 | LightGBM | +0.1 | RandomForest |
| Arrival Immigration | 63.0±12.0 | 66.9±8.1 | 65.7±8.0 | 66.3±8.5 | 66.5±8.7 | **67.1±8.0** | 66.9±8.0 | XGBoost | +0.2 | RandomForest |
| Security Screening | 87.9±6.9 | 90.6±4.1 | 90.2±4.5 | 90.8±3.6 | **90.9±3.6** | 90.7±3.7 | 90.6±4.1 | LightGBM | +0.3 | RandomForest |
| Transfer Desks | 73.8±9.9 | 77.1±10.4 | 75.1±10.1 | 77.6±10.1 | **77.8±10.1** | 77.3±9.7 | 77.0±10.3 | LightGBM | +0.7 | RandomForest |

**Per-touchpoint model map** (feed to `PODModel(algorithm=...)`):

```python
PER_TOUCHPOINT = {'Entry': 'randomforest', 'CheckIn': 'randomforest', 'Emigration': 'randomforest', 'Immigration': 'randomforest', 'PESC': 'randomforest', 'Transfers': 'randomforest'}
```
