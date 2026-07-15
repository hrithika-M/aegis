# Architecture — the end-to-end workflow

This repository is **not** a single thing. It is a set of subsystems that together
take an airport from *"we have flight schedules and some statistics"* to *"we have a
live, self-correcting passenger-demand forecast driving operational decisions."*

This document describes the **whole workflow** and — importantly — draws the line
between the parts that **generate** data, the parts that **clean** data, and the
parts that **forecast**. They are often confused; they are not the same.

---

## 1. The two regimes it has to serve

| | Hyderabad (HYD) — live airport | Bhogapuram (VTZ) — opens 2026-07-08 |
|---|---|---|
| Real operational data? | **Yes** — EWS camera counts | **No** — greenfield, nothing yet |
| So the job is… | *clean* the real feed, then forecast | *simulate* a plausible feed, then forecast |
| Which subsystem leads | **Aegis** (self-healing) | **Digital Twin** (simulation) |

The design goal is that **both regimes feed the same forecasting models and
dashboards through the same interfaces** — so when Bhogapuram switches on real
sensors, we swap the data source, not the architecture.

---

## 2. The end-to-end flow

```
                         REAL WORLD DATA                         PLANNING DATA
                    (measured, has faults)                  (no real data yet)

   data/  ────────────────┐                        ┌──────  data/bhogapuram_vtz/
   EWS camera counts,      │                        │        VTZ schedule, DGCA route
   weather, flights        │                        │        traffic, master resources
                           ▼                        ▼
              ┌────────────────────────┐   ┌────────────────────────────┐
   STEP A     │  AEGIS  (data_pipeline)│   │  DIGITAL TWIN              │
   clean /    │  heals REAL sensor data │   │  (bhogapuram_digital_twin)│
   generate   │  BLACKOUT/SPIKE/DRIFT   │   │  schedule → daily flights │
              │  → trusted actuals      │   │  → passengers (reconciled │
              │  NEVER fabricates       │   │  to real DGCA totals)     │
              │  DOES NOT create data   │   │  → 5-min operational data │
              └───────────┬─────────────┘   │  GENERATES simulated data │
                          │                 └───────────┬────────────────┘
                          │                             │
                          ▼                             ▼
                   ┌───────────────────────────────────────────┐
   STEP B          │   CLEAN / SIMULATED "ACTUALS" (same shape) │
   common          │   Date · Hour · touchpoint demand         │
   interface       └───────────────────┬───────────────────────┘
                                        ▼
                          ┌──────────────────────────────┐
   STEP C                 │  FORECASTING MODELS            │
   forecast               │  models/ · trial_models/ ·     │
                          │  bhogapuram_digital_twin/modeling
                          │  per-touchpoint model selection │
                          │  (walk-forward, full metrics)   │
                          └───────────────┬─────────────────┘
                                          ▼
                          ┌──────────────────────────────┐
   STEP D                 │  PLAN / DASHBOARDS / KPIs      │
   act                    │  dashboard/ · analytics/       │
                          │  peak hours, counters, gates   │
                          └──────────────────────────────┘
```

**The one sentence that matters:** *Aegis cleans real measured data; the Digital
Twin generates simulated data. They occupy the same slot in the pipeline (the
"clean actuals" that models forecast on) — one for a live airport, one for a
greenfield one.*

---

## 3. Subsystems (what each does, and its real↔simulated status)

### A. Data & acquisition — `data/`
Real inputs. HYD EWS camera counts, weather, flight routes; for VTZ the schedule,
**real DGCA route/monthly/daily traffic**, master resources. *Real.*

### B. Aegis self-healing pipeline — `data_pipeline/`
A general engine that **heals a stream of real measurements that contains faults**
(sensor blackouts, spikes, drift), cross-healing from linked sources, confidence-
gated, never fabricating. **It is a data-quality engine, not a data generator.**
On HYD it healed 9,351 real cells (see `PROOFS.md`). For Bhogapuram it does nothing
useful *yet* — there is no real feed to heal until the airport opens. *Operates on real data.*

### C. Digital Twin — `bhogapuram_digital_twin/`
Because Bhogapuram has no history, this **generates** a plausible operational dataset
from the schedule: masters → daily flights → passengers (reconciled to real DGCA
totals, 95%-capped) → 5-minute check-in/security/boarding/belt demand + occupancy +
resource need. *Generates simulated data (real volumes, modelled flow).*

### D. Demand estimation — `pax_estimation/`
Lighter-weight schedule→demand estimators (hourly/daily curves), reconciled to real
DGCA counts. Feeds and cross-checks the twin. *Derived from real totals.*

### E. Forecasting models — `models/`, `trial_models/`, `bhogapuram_digital_twin/modeling/`
Per-touchpoint model selection (walk-forward, full metric panel: accuracy, RMSE,
MAE, MAPE, R², peak precision/recall/F1). On **real HYD data** these produced
validated winners (RF/LightGBM/XGBoost, 67–91%). On the **twin** they run as a
pipeline test (optimistic; swap in real data post-opening for real numbers). *Model
choices validated on real data; ready to retrain on real Bhogapuram data.*

### F. Dashboards & KPIs — `dashboard/`, `*/analytics/`
Operational views: peak hour, terminal occupancy, counters/lanes, gate/stand use.
*Presentation of the above.*

---

## 4. The design principle (why this is a platform, not a script)
Every subsystem has a **defined input/output contract**, so any one is replaceable
without touching the others:
- The twin fills the exact slot real sensor data will fill (`Date, Hour, demand`).
- The model pipeline's **only** data-source dependency is one function
  (`load_touchpoint_hourly`) — swap it, everything else is untouched.
- Aegis is config-driven and domain-agnostic (proven on airports *and* retail).

So the transition **Simulation → Production** at Bhogapuram is a data-source swap,
not a rewrite.

---

## 5. Real vs generated — the honesty map
| Artifact | Real / Generated | Anchor |
|---|---|---|
| HYD EWS counts, DGCA/AAI traffic | **Real** | measured |
| Aegis healed actuals (HYD) | Real, corrected | healed from real, escalates the rest |
| Twin daily flights | Generated (deterministic) | expansion of real schedule |
| Twin passengers | Generated | **reconciled to real DGCA route totals** |
| Twin 5-min flow | Generated (simulated) | modelled show-up/service windows |
| HYD model accuracies | **Real** | walk-forward on measured data |
| Twin model accuracies | Pipeline test (optimistic) | on simulated data |

Every generated column records **Source + Method** (see the data dictionaries).
Nothing real and nothing simulated is ever presented as the other.
