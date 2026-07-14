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
| 1. Foundation | Master AODB, airport/aircraft masters, daily expansion | **Sprint 1 — done** |
| 2. Passenger engine | Seats × load factor, reconciled to real monthly totals | backbone built* |
| 3. Passenger behaviour | Show-up / check-in / security / boarding windows | next |
| 4. EWS dataset | 5-minute operational demand (check-in/security/boarding/occupancy) | next |
| 5. Dashboard | Power BI ops dashboard (peak hour, gates, flow, utilisation) | later |

\* Phase-2 real inputs already exist in `../data/bhogapuram_vtz/` (route load factors,
monthly/daily reals) and `../pax_estimation/` (hourly demand). Phase 2 here will wire
them onto the daily flights and reconcile to the real DGCA monthly totals.

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
