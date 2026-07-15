# modeling — per-touchpoint model selection (full metric panel, ready for real data)

Same methodology validated on HYD's real EWS data — a model zoo compared by
expanding-window walk-forward, one winner per touchpoint. Reports a **full metric
panel**, because a single accuracy number hides how a model actually behaves.

## Metrics reported (per touchpoint × model)
**Regression** — how close predicted demand is to actual:
| Metric | Meaning | Good |
|---|---|---|
| Accuracy | symmetric min/max ratio (the project metric) | high (→100%) |
| RMSE | root-mean-square error — penalises big misses | low |
| MAE | mean absolute error (avg pax off) | low |
| MAPE | mean absolute % error | low |
| R² | variance explained | →1.0 |

**Classification — peak-hour detection** (peak = demand ≥ 80th percentile = the busy
hours you must staff for):
| Metric | Meaning | Good |
|---|---|---|
| PeakRecall | share of real peak hours the model **caught** (a miss = understaffing) | →1.0 |
| PeakPrecision | when it flags a peak, how often it's right (a false alarm = overstaffing) | →1.0 |
| PeakF1 | balance of the two | →1.0 |

## Why the panel matters (visible even on the twin)
A single number lies. On CheckIn the **naive baseline "wins" on accuracy (98.1)** —
but it has the **worst RMSE (14.8 vs XGBoost 7.2)** and weaker peak detection. Judge
by RMSE / R² / PeakRecall and **XGBoost and RandomForest are the real performers**.
This is exactly why we don't finalise a model on accuracy alone.

## The one line that changes for real data
`load_touchpoint_hourly()` in `train_touchpoints.py`. Today it reads the SIMULATED
twin; point it at the real EWS export when Bhogapuram opens (2026-07-08) and every
metric above becomes real. The zoo, features, walk-forward and metrics are untouched.

**Honest note:** on the twin the data is deterministic, so all scores are optimistic
and the naive baseline can tie — a pipeline/template check, not a real accuracy claim.

## VTZ touchpoints
`CheckIn, Security, Boarding` (departures) + `Belt` (arrivals). VTZ is domestic
point-to-point, so HYD's Emigration / Immigration / Transfers don't apply here.

## Run
```
pip install -r ../requirements.txt
python train_touchpoints.py        # -> prints the panel + writes analytics/model_selection_twin.csv
python registry.py                 # -> records the run in model_registry.json (champion/runner-up)
```

## Model registry (`registry.py` → `model_registry.json`)
MLflow-style governance: every selection run is recorded with its **data version**
(hash), simulator version, timestamp, and per-touchpoint **champion + runner-up +
whether it beat the naive baseline** — so any deployed model is traceable to the
exact data and run that produced it. One entry per data version.
