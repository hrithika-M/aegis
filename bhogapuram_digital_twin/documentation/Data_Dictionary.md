# Data Dictionary — Bhogapuram Digital Twin (Sprint 1)

Every column tagged with **Source** (where the value comes from) and **Method**
(calculation or assumption). Real inputs vs generated data are kept separate.

## Provenance legend
- **schedule** = the real VTZ S26 flight schedule (`MAIN FILE` sheet), as provided.
- **reference** = public airport/aircraft reference data (coordinates, ICAO, specs).
- **derived** = computed deterministically from the schedule (no assumptions).

---

## master/Airport_Master.csv  (16 airports)
| Column | Description | Source | Method |
|---|---|---|---|
| airport_code | IATA code | schedule | as-is |
| airport_name | Airport name | reference | lookup |
| city / state_country | Location | reference | lookup |
| latitude / longitude | Coordinates (approx) | reference | lookup |
| scope | Domestic / International | reference | lookup |

## master/Aircraft_Master.csv  (6 types)
| Column | Description | Source | Method |
|---|---|---|---|
| aircraft | Canonical type | schedule | standardized from Acft Type |
| icao_code | ICAO type code | reference | lookup |
| nominal_seats | Typical seats | reference | lookup (config-dependent) |
| cruise_speed_kmh | Cruise speed | reference | lookup |
| typical_turnaround_min | Ground turnaround | reference | assumption (tunable) |
| body_type | Category | reference | lookup |
| schedule_labels | Raw label(s) seen | schedule | as-is (e.g. A320N/A32N -> A320neo) |

## master/Flight_Master.csv  (30 rotations)
The cleaned, standardized schedule. One row per aircraft **rotation** (an arrival
then its paired departure).
| Column | Description | Source | Method |
|---|---|---|---|
| flight_id | Stable twin id (BDT-Fnnn) | derived | assigned |
| airline | Operating carrier | schedule | mapped from flight-no prefix |
| arr_flight_no / origin / arrival_time | Inbound leg | schedule | cleaned (times zero-padded) |
| dep_flight_no / destination / departure_time | Outbound leg | schedule | cleaned |
| aircraft | Canonical type | schedule | standardized |
| seat_capacity | Seats (airline-specific) | schedule | as-is (web-verified col) |
| frequency / days_per_week | Weekly operating pattern | schedule | days_per_week derived from FREQ |
| traffic_type | Domestic / International | schedule | from Remarks (INTL) |
| valid_from / valid_to | S26 season window | reference | IATA S26 (2026-03-29..10-24) |

## generated/Daily_Flights.csv  (5,820 occurrences)  **[GENERATED]**
Schedule expanded to one row per dated flight occurrence.
| Column | Description | Source | Method |
|---|---|---|---|
| occurrence_id | Unique row id | derived | assigned |
| date / day_of_week | Calendar day | derived | expansion of FREQ across valid_from..valid_to |
| (all flight fields) | Carried from Flight_Master | schedule | join on flight_id |

**Method:** for each date in the season, a rotation appears iff its weekday is in
FREQ. Purely deterministic calendar expansion — no assumptions, no random numbers.

---

## Cleaning log (Module 1)
- row 22 (SL 20): ORG '881' unknown airport -> flagged UNK
