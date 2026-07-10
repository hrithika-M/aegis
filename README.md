# Aegis

Our POD (Plan of the Day) data-science work — a self-contained repository with
the data, the data pipeline, and the model experiments, organised into three
top-level folders.

```
aegis/
├── data/            all datasets + acquisition scripts (EWS, weather, flights)
├── data_pipeline/   the Aegis self-healing data engine (the pipeline we built)
├── trial_models/    forecasting model experiments (foundation models, trials)
├── docs/            research, workflow, design docs
└── PROOFS.md        end-to-end proofs of the pipeline on two domains
```

## The three parts

### 📁 `data/` — [README](data/README.md)
All datasets in one place (committed for reproducibility), on the EWS timeline
**2025-04-01 → 2026-03-25**: EWS camera counts (`entry.csv`, `pesc.csv`), real
hourly weather (`hyderabad_weather.csv`), the joined table, and the HYD flight
route network (`hyderabad_routes.csv`) — plus the scripts that fetch/build each.

### 🔧 `data_pipeline/` — [README](data_pipeline/README.md)
**Aegis** — a general self-healing data engine. Point it at any file or database;
it learns the normal (median/MAD), detects `BLACKOUT/SPIKE/LOW/DRIFT`, repairs
scaled to the day's real activity, reconciles doubtful values from linked sources
(MICE-style), and iterates — confidence-gated — until the trust score converges.
Never fabricates: what it can't fix confidently is escalated. Built, tested, and
proven on two domains (see `PROOFS.md`).

### 🧪 `trial_models/` — [README](trial_models/README.md)
Forecasting experiments on the real EWS demand. Each model gets its own named
folder + a results README. So far: **Chronos** (Amazon foundation model) forecast
our demand at **89.8% zero-shot** — beating our trained RandomForest (88.3%).

## Honesty contract (applies throughout)
Every result is reported truthfully. The pipeline heals what it has confident
signal for and escalates the rest; the model trials report honest walk-forward
numbers, including where a fancy model is only *within noise* of a simple one.
