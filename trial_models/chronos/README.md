# Chronos — foundation model trial

**Model:** Chronos-Bolt (`amazon/chronos-bolt-base`) — Amazon's pretrained
time-series foundation model.
**Type:** zero-shot forecasting — **no training on our data**. We only load the
pretrained weights (`from_pretrained`) and feed it recent demand history as
context; it forecasts the next 24 hours.

## How to run
```bash
pip install chronos-forecasting torch scikit-learn     # one-time
cd trial_models/chronos
python chronos_benchmark.py            # Entry touchpoint
python chronos_benchmark.py --tp pesc  # Security/PESC
```
Reads `../../data/<tp>.csv` (the committed EWS export).

## Results — EWS hourly demand, walk-forward, 30 held-out days

| Method | Accuracy | Trained on our data? |
|---|---|---|
| **Chronos-Bolt (zero-shot)** | **89.8%** | **No** |
| RandomForest (our ML) | 88.3% | Yes (per test day) |
| Naive-7d (same hour last week) | 85.9% | — |

*Touchpoint: Entry. Metric: project symmetric min/max accuracy, averaged over
the held-out days. The only model trained here is the RandomForest baseline.*

## What it means
- The foundation model, with **zero training**, matched-and-slightly-beat our
  tuned RandomForest (+1.5 pts) and clearly beat the naive floor (+4 pts).
- **Why:** Chronos reads the *recent* history each time, so it adapts to the
  recent level/trend — something our calendar-only RandomForest structurally
  cannot do.

## Honest caveats
- +1.5 vs RF is small — likely within the ±4–10% day-to-day noise we measured
  elsewhere. Fair statement: *competitive with / nominally ahead of* our ML,
  not "crushes it." Beating naive by 4 pts is the solid signal.
- One touchpoint (Entry), raw data, 30 days. Confirm on PESC + more days.
- Slower than RF (~1s/forecast) — fine for daily planning, not ms serving.
- Not tested yet: **covariates** (weather/flights as extra streams) — that's the
  multivariate angle, better suited to Moirai / Chronos-2.
