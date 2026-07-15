# Bhogapuram Airport Digital Twin

A reproducible **operational simulation** of Bhogapuram (new Visakhapatnam) airport,
built from the real VTZ reference schedule + real traffic statistics + explicit,
documented assumptions.

> **Why:** Bhogapuram opens 2026-07-08 with *no* historical operational data (no
> flight movements, no hourly passenger counts, no check-in/security/boarding
> demand). This project works backwards from the published schedule to *simulate*
> how the airport will behave — a planning tool for staffing, counters, gates and
> passenger flow before day one. It is **not** a prediction of a specific day and
> **not** historical data; it is a simulation model from real schedules + stats.

## Core principle: real vs generated stays separate
Every generated column records its **Source** (schedule / traffic sheet / route
profile / reference) and **Method** (calculation or assumption) — see
`documentation/Data_Dictionary.md`. Anyone can ask "where did this value come
from?" and get a straight answer.

## Phases
| Phase | What | Status |
|---|---|---|
| 1. Foundation | Master AODB, airport/aircraft masters, daily expansion | **done** |
| 2. Passenger engine | Seats × load factor, reconciled to real DGCA monthly totals | **done** |
| 3. Passenger behaviour | Show-up / check-in / security / boarding windows (tunable) | **done** |
| 4. EWS dataset | 5-minute operational demand + occupancy + counters | **done** |
| 5. Analytics + dashboard | KPIs, peak hours (CSV) + Power-BI-ready + HTML dashboard | **done** |

## Run the whole pipeline
```
python build/build_masters.py      # Phase 1  -> master/, generated/Daily_Flights.csv
python build/build_passengers.py   # Phase 2  -> generated/passenger_estimates.csv (stochastic LF)
python build/build_operations.py   # Phase 3+4-> generated/passenger_5min.csv, gate_occupancy.csv
python build/build_analytics.py    # Phase 5  -> analytics/kpis.csv, peak_hours.csv
python simulation/monte_carlo.py   # uncertainty -> analytics/confidence_intervals.csv (P95)
python simulation/scenario_engine.py  # what-if queues -> analytics/scenarios.csv (SLA breaches)
python validation/validate_synthetic.py   # twin vs real -> analytics/synthetic_validation.csv
python build/build_provenance.py   # audit -> version.json, provenance.json
python tests/test_twin.py          # 11 invariant tests (exits non-zero on failure)
```
Build masters validates the schedule first (bad input stops the build with a clear
message). `version.json` / `provenance.json` make every output auditable: simulator
version, input/output hashes, the exact assumptions used, and per-value Source/Method/
Confidence. Model selection: `python modeling/train_touchpoints.py`.

## Headline results (S26 season)
- **~7,942 passengers/day** simulated (real VTZ ~8,000 ✓), reconciled to DGCA route totals.
- Peak hour **07:00**; peak terminal occupancy **~1,350**; peak **10 check-in counters**, **6 security lanes**, **4 aircraft on ground**.

## Sprint 1 deliverables (built)
| File | Rows | What |
|---|---|---|
| `master/Airport_Master.csv` | 16 | every airport in the schedule + geo + scope |
| `master/Aircraft_Master.csv` | 6 | every aircraft type + ICAO, seats, cruise, turnaround |
| `master/Flight_Master.csv` | 30 | the cleaned, standardized schedule (one row/rotation) |
| `generated/Daily_Flights.csv` | 5,820 | schedule expanded to one row per dated occurrence |
| `documentation/Data_Dictionary.md` | — | every column's source + method + cleaning log |

Regenerate all of it: `python build/build_masters.py`

## Structure
```
bhogapuram_digital_twin/
├── input/          pointer to canonical real inputs (../data/bhogapuram_vtz/)
├── master/         Airport / Aircraft / Flight masters (cleaned real data)
├── generated/      simulated outputs (daily flights, later: passengers, 5-min EWS)
├── analytics/      KPIs, peak hours, reports (later)
├── dashboard/      Power BI (later)
├── documentation/  data dictionary
└── build/          the scripts that generate everything
```

## Honesty contract
Masters + Flight_Master = **cleaned real** schedule. Daily_Flights = **generated**
by deterministic calendar expansion (no assumptions). Later phases add passenger
and behaviour models — each with its assumptions documented and totals reconciled
back to the real DGCA traffic sheets, so the simulation stays internally consistent
and auditable.
