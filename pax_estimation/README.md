# pax_estimation — passenger demand for Bhogapuram (VTZ) from the schedule

Bhogapuram is a **greenfield airport — no historical passenger data exists.** So
we estimate demand bottom-up from the flight plan, cross-referencing the tables we
have (the "inter-column relation" idea), keyed by **hour** and **day of week**:

```
aircraft type --(seat map)--> seats        (schedule col K, web-verified)
flight number --(prefix)-----> airline
airline       --(DGCA PLF)---> load factor
seats x load factor          = PAX on that flight
STA / STD                    = the hour it lands / departs
FREQ (1..7)                  = the days of week it flies
```

## Airline load factors used (DGCA / airline FY2026)
| Airline | Code | LF |
|---|---|---|
| IndiGo | 6E | 0.86 |
| Air India Express | IX | 0.87 |
| Air India | AI | 0.83 |
| Scoot | TR | 0.85 |
| Regional (Cessna/UDAN) | I7 | 0.75 |

## Outputs (regenerate with `python estimate_pax.py`)
- **`pax_per_flight.csv`** — every flight: seats, airline, arriving PAX (deplaning)
  and departing PAX (boarding), the hour each happens, INTL flag, days/week.
- **`demand_by_hour_dow.csv`** — the typical-week demand grid: for each
  `(day-of-week, hour)` the departing / arriving / total PAX. This is the
  hour-by-hour, day-by-day curve.

## Headline result (S26 season, 2026-03-29 .. 2026-10-24)
- ~**8,700 PAX/day** through the terminal (dep + arr), ~**1.83 M** for the season.
- Departures peak **~08:00** (morning bank); arrivals peak **~20:00** (evening bank).

## How this maps to touchpoints (the next layer)
- **Departing (boarding) PAX** flow through **Entry → Check-In → Security → (Emigration if INTL) → Gate.**
- **Arriving (deplaning) PAX** flow through **(Immigration if INTL) → Baggage Belts → Exit.**
- The `master_data_resources.xlsx` inventory (18 stands, 12 gates, 4 belts, CIC)
  is what this demand gets **sized against** — the POD prescription step.

## Honesty notes
- This is an **estimate from a plan**, not measured data. Two assumptions drive it:
  load factor (per airline, above) and that a flight fills evenly. Both are
  documented and easy to change in `estimate_pax.py`.
- PAX are placed in the **scheduled** hour. Real passengers arrive spread over a
  show-up window *before* departure — turning this into a check-in/security arrival
  curve needs a show-up profile (the POD "show-up" model), which is the next step.
- Row 7 (`C 2088`, regional Cessna) uses 9 seats — approximate; see the schedule's note.
