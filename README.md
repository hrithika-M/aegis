# Airport Operations Intelligence Platform

Passenger-demand forecasting and operations planning for GMR airports — **Hyderabad
(live)** and **Bhogapuram / Visakhapatnam (opens 2026-07-08)**. This is not one
model or one dataset; it is an end-to-end platform that goes from raw flight
schedules + traffic statistics to a live, self-correcting operational forecast.

> **Read [`ARCHITECTURE.md`](ARCHITECTURE.md) first** — it draws the full workflow
> and the critical distinction between the parts that *generate* data, *clean* data,
> and *forecast*.

## The workflow in one line
```
real/known inputs → clean (Aegis) OR simulate (Digital Twin) → forecast (models) → plan (dashboards)
```
- **Live airport (HYD):** real sensor data exists → **Aegis heals it** → models forecast.
- **Greenfield airport (Bhogapuram):** no data yet → **Digital Twin simulates it** →
  same models forecast → swap in real data the day sensors go live.

Both paths feed the **same** models and dashboards through the **same interfaces**,
so Simulation → Production is a data-source swap, not a rewrite.

## The subsystems
| Folder | What it is | Real or generated |
|---|---|---|
| [`data/`](data/) | All datasets + acquisition (EWS, weather, flights, DGCA traffic) | **real** |
| [`data_pipeline/`](data_pipeline/) | **Aegis** — self-healing engine for real sensor data (heals faults, never fabricates). *Cleans data; does not create it.* | operates on **real** |
| [`bhogapuram_digital_twin/`](bhogapuram_digital_twin/) | The **Digital Twin** — schedule → daily flights → passengers → 5-min operations, reconciled to real DGCA totals | **generates** simulation |
| [`pax_estimation/`](pax_estimation/) | Schedule → demand estimators (hourly/daily), reconciled to real counts | derived |
| [`models/`](models/) · [`trial_models/`](trial_models/) | Per-touchpoint forecasting model selection (walk-forward, full metric panel) | validated on **real** |
| [`dashboard/`](dashboard/) · `*/analytics/` | Operational dashboards + KPIs | presentation |
| [`PROOFS.md`](PROOFS.md) | Evidence: pipeline healing, forecasting accuracy, twin reconciliation | — |

## What's been established (the honest scorecard)
- **Aegis** healed **9,351 real cells** of HYD sensor data; refused to fake the rest
  (target-not-met reported honestly — see `PROOFS.md`).
- **Forecasting** on real HYD data: per-touchpoint winners RF/LightGBM/XGBoost at
  **67–91%** (walk-forward); Chronos foundation model reached **89.8%** zero-shot.
- **Digital Twin** reproduces VTZ's real throughput to within **~4%** of DGCA
  monthly counts (~7,942 pax/day vs real ~8,000), fully reconciled per route.
- Every forecast is judged on a **full metric panel** (accuracy, RMSE, MAE, MAPE,
  R², peak precision/recall/F1) — never a single flattering number.

## Honesty contract (applies throughout)
Real data and generated data are kept strictly separate and labelled. The pipeline
heals what it has confident signal for and escalates the rest; the twin's passenger
*volumes* are real (reconciled to DGCA) while its *flow* is simulated with documented
assumptions; model results are honest walk-forward numbers, including where a fancy
model only ties a simple one. Every generated value records its **Source + Method**.
