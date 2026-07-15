# modeling — per-touchpoint model selection (ready for real data)

The same methodology validated on HYD's real EWS data — a model zoo compared by
expanding-window walk-forward on the symmetric min/max accuracy metric, one winner
picked per touchpoint. Built so it retrains on real Bhogapuram data with a **one-line
change** the day the airport opens.

## The one line that changes when real data arrives
`load_touchpoint_hourly()` in `train_touchpoints.py`. Today it reads the SIMULATED
twin (`generated/passenger_5min.csv`). Point it at the real EWS sensor export
instead — the zoo, features, metric, walk-forward and selection are untouched, and
the printed accuracies become **real** accuracies.

## VTZ touchpoints
`CheckIn, Security, Boarding` (departures) + `Belt` (arrivals). VTZ is a domestic
point-to-point airport, so HYD's Emigration / Immigration / Transfers don't
meaningfully exist here.

## Today's output is a PIPELINE TEST, not a real accuracy claim
Run on the twin, every model scores **94–98%** and the naive "same as last week"
baseline **ties or beats** the ML models:

| Touchpoint | RF | XGBoost | LightGBM | ExtraTrees | HistGB | Naive-7d | winner |
|---|---|---|---|---|---|---|---|
| CheckIn | 97.5 | 95.8 | 94.1 | 95.1 | 93.2 | **98.1** | Naive-7d |
| Security | **98.0** | 97.2 | 94.9 | 96.2 | 94.3 | 98.0 | RandomForest |
| Boarding | **98.0** | 96.5 | 94.0 | 97.0 | 92.7 | 97.9 | RandomForest |
| Belt | **98.3** | 94.9 | 91.6 | 97.8 | 90.4 | 97.8 | RandomForest |

**Why a naive baseline winning is the tell:** it means there is no hard signal to
learn — the demand just repeats weekly, because we generated it deterministically
from the schedule. On *real* sensor data (noisy, event-driven) the ML models will
separate from the baseline and land at realistic HYD-like accuracies. **Do not
quote these 98s as Bhogapuram's accuracy** — they measure the simulation, not skill.

## When real data lands (post 2026-07-08)
1. Export real touchpoint counts to the same shape (Date, Hour, demand).
2. Repoint `load_touchpoint_hourly()`.
3. `python train_touchpoints.py` → real per-touchpoint winners + accuracies.
Output: `analytics/model_selection_twin.csv` (rename for the real run).
