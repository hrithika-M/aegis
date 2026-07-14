# Data Dictionary — Operations layer (Phases 2–5)  **[GENERATED / SIMULATED]**

All outputs below are **simulated planning data** — real passenger *volumes*
(reconciled to DGCA), modelled *flow*. Every assumption is listed and tunable in
the build scripts.

## generated/passenger_estimates.csv  (Phase 2 — passenger engine)
One row per flight **leg** (each rotation → an ARR and a DEP leg).
| Column | Description | Source | Method |
|---|---|---|---|
| occurrence_id / flight_id / date | Links to Daily_Flights | derived | join |
| movement_type | ARR (deplaning) or DEP (boarding) | derived | leg split |
| route_city / route_code | The other endpoint | schedule | code→city map |
| seat_capacity | Seats | schedule | as-is |
| passengers | Estimated passengers on the leg | **derived** | seats × 0.85, then **reconciled** so each (route,direction,month) sums to the real 2025 DGCA count; **capped at 95%** load |
| load_factor_effective | passengers ÷ seats | derived | computed |
| reconciled | Y / capped / N | derived | Y=matched to DGCA; capped=route under-served by schedule; N=no DGCA match (intl/UNK) |

**Assumptions:** base load factor 0.85; max load factor 0.95 (physical cap).
**Reconciliation target:** real 2025 same-month DGCA directional route pax.

## generated/passenger_5min.csv  (Phases 3–4 — behaviour → EWS)
5-minute operational demand across the S26 season (active slots only).
| Column | Description | Method |
|---|---|---|
| timestamp | 5-min bucket | grid |
| dep_flights / arr_flights | Movements in the bucket | count |
| checkin_demand / security_demand / boarding_demand | Departing pax in each stage | each flight's pax spread triangularly over its stage window |
| belt_demand | Arriving pax at baggage | spread over STA+5..+35 |
| terminal_occupancy | Passengers in terminal | running(entries − exits), reset daily |
| checkin_counters_req | Counters needed | ceil(checkin_demand / 6 pax·5min⁻¹) |
| security_lanes_req | Lanes needed | ceil(security_demand / 12 pax·5min⁻¹) |

**Behaviour windows (min before departure, TUNABLE in build_operations.py):**
check-in −150…−45 (peak −90) · security −95…−25 (peak −55) · boarding −30…−8 (peak −18) ·
terminal entry −150…−40, exit −10 · arrivals: belt +5…+35, clear +45.
**Service rates (assumption):** check-in 6 pax/5min/counter (~72/hr); security 12 pax/5min/lane (~144/hr).

## generated/gate_occupancy.csv
| Column | Description | Method |
|---|---|---|
| timestamp | 5-min bucket | grid |
| aircraft_on_ground | Concurrent rotations on stand | count of rotations with STA ≤ t ≤ STD |

## analytics/kpis.csv  (Phase 5)
`metric, value, unit, when, method` — headline peaks (check-in, security, boarding,
occupancy, counters, lanes, aircraft on ground), busiest day, avg daily pax, peak hour.

## analytics/peak_hours.csv  (Phase 5)
Typical-day hourly profile (mean across all season days) per touchpoint +
counters/lanes. Drives the dashboard.
