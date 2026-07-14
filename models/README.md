# models — best forecasting model per touchpoint

The POD demand forecast runs one model **per touchpoint**. We benchmarked 21
algorithms with walk-forward backtesting (expanding window, symmetric min/max
metric) on the trusted hourly actuals, and kept **the single best model for each
touchpoint** — not the full 4 GB zoo. These six artifacts total **~12 MB**.

## The winners

| Touchpoint | Best model | Walk-forward accuracy | Artifact |
|---|---|---|---|
| Security (PESC) | LightGBM | **90.9%** | `best_per_touchpoint/pesc_lightgbm.pkl` |
| Check-In | LightGBM | **88.3%** | `best_per_touchpoint/checkin_lightgbm.pkl` |
| Entry | RandomForest | **87.6%** | `best_per_touchpoint/entry_randomforest.pkl` |
| Emigration | LightGBM | **80.1%** | `best_per_touchpoint/emigration_lightgbm.pkl` |
| Transfers | LightGBM | **77.8%** | `best_per_touchpoint/transfers_lightgbm.pkl` |
| Immigration | XGBoost | **67.1%** | `best_per_touchpoint/immigration_xgboost.pkl` |

`best_per_touchpoint/manifest.json` records the algorithm, accuracy, feature list,
target, row count, and size for each.

## Honesty note (important)
These are the **nominal** winners. Every one of them is within **~1 point** of a
plain RandomForest — inside the ±4–10% day-to-day noise. So "RandomForest for all
six" is an equally defensible production choice; the per-touchpoint winners are not
a statistically meaningful upgrade. The reason they all tie is that every capable
tree/boosting model extracts the same signal from the same 7 calendar features —
the ceiling is the **data**, not the algorithm. (We later added CatBoost too: 81.3%
avg, also a tie. See `selection/try_catboost.py`.)

## What the models take as input
All six use the **same 7 calendar features** (no weather/flight data — those were
tested and add nothing beyond the calendar):
`DayOfWeek, Month, IsWeekend, WeekOfYear, Hour, IsHoliday, HolidayImpact`
→ target: `adj` (the Aegis-corrected hourly passenger throughput).

## Load and predict
```python
import joblib, pandas as pd
model = joblib.load("best_per_touchpoint/pesc_lightgbm.pkl")
X = pd.DataFrame([{ "DayOfWeek": 2, "Month": 7, "IsWeekend": 0, "WeekOfYear": 28,
                    "Hour": 18, "IsHoliday": 0, "HolidayImpact": 0 }])
print(model.predict(X))   # predicted passengers for that hour
```

## Files
- `best_per_touchpoint/` — the six trained artifacts + `manifest.json`.
- `train_best.py` — the recipe: fits each touchpoint's winner on the full trusted
  history and re-saves the artifacts (reproducible).
- `selection/` — the evidence that picked the winners: the 21-model benchmark
  (`benchmark.py`, `estimators.py`), the per-touchpoint selection (`select.py`),
  the CatBoost trial (`try_catboost.py`), the eval harness (`evaluate.py`,
  `dataset.py`), prediction-interval + plan builders, and the full results write-up
  `MODEL_SELECTION.md`.

> Note: `train_best.py` and `selection/*` import the POD project's data layer
> (`data_trust`, `training.common`, `config`, `data_processor`) and are run from
> the POD project. They are included here as the reproducible record; the loadable
> deliverable is the artifacts + manifest above.
