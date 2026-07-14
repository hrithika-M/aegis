# Bhogapuram (VTZ) — new airport planning data

Everything GHIAL/Bhogapuram has given us so far for the **new Visakhapatnam
(Bhogapuram) airport**. This is a **greenfield airport** — not yet operating —
so there is **no historical passenger/sensor data**. What exists is the *plan*:

| File | Sheet(s) | What it is | Nature |
|---|---|---|---|
| `VTZ_schedule_S26.xlsx` | MAIN FILE | Summer-2026 flight timetable — ~30 aircraft rotations/day (arr+dep), aircraft type, ORG/DEST, scheduled times, weekly frequency, **+ Seat Capacity** (added by us) | **plan** (repeating daily) |
| `master_data_resources.xlsx` | Stands (18), Gates (12), Belts (4), CIC | Physical infrastructure inventory — parking stands (apron, ICAO compat, contact/remote), boarding gates, baggage belts, check-in counter areas | **fixed resources** |
| `nature_codes_VTZ.xlsx` | Codes (17 DOM + INTL) | Flight category & kind code dictionary (e.g. "Domestic Schedule Pax" = 51) | **reference taxonomy** |

## Important: what this data is and isn't
- **It is a forecast/plan, not measured history.** A schedule + an inventory + a
  code list. There are **no passenger counts and no sensor streams** here.
- **The seat-capacity column** (added to the schedule) is the bridge to passengers:
  `flights × seats × load factor → estimated PAX`, expanded across the season by
  each flight's weekly frequency. That is a **demand-estimation build**, not the
  self-healing data pipeline (which needs a measured time series with faults to
  heal — see `../../data_pipeline/`). Nothing here has anomalies to heal yet.
- The **resource inventory** (stands/gates/belts/CIC) is what estimated demand
  gets sized *against* — the POD prescription layer's target once demand exists.

## Real traffic counts (measured — the only real PAX numbers available)
VTZ is an **operating** airport, so official passenger counts exist — but only at
**monthly** granularity (no daily/hourly/passenger-level anywhere on the public web;
that is proprietary and, for Bhogapuram, starts only when it opens 2026-07-08).

- `vtz_annual_traffic.csv` — full financial-year series 2014-15 → 2025-26 (AAI/DGCA).
- `vtz_monthly_traffic.csv` — airport monthly totals (news/AAI-sourced anchors).
- **`vtz_citypair_monthly.csv`** — the granular one: **DGCA route-level monthly
  passengers, directional (arrivals to VTZ / departures from VTZ), 126 months
  Apr-2015 → Dec-2025, 42 routes.** Sourced from DGCA city-pair statistics (via
  the open `Vonter/india-aviation-traffic` compilation). Columns: `Year, Month,
  Route, PaxArr_toVTZ, PaxDep_fromVTZ, PaxTotal`. 2026 rows were still provisional
  (empty) at fetch time, so Dec-2025 is the latest complete month.

Real seasonal shape from this file (monthly totals): summer peak May-2025 262,049;
monsoon low Jul-2025 215,442; festive peak Nov-2025 265,082. Top routes (Dec-2025):
Hyderabad 74,060, Delhi 40,366, Bengaluru 38,896, Chennai 30,491.

This is the finest **real passenger** granularity that exists publicly — **route ×
month × direction.** It lets us compute a **real per-route load factor** (real pax
÷ scheduled seats) instead of a flat assumption. Still not hourly (hourly PAX is
not public for any airport), but it's real counts, per route, per direction.

- **`vtz_route_profile.csv`** — the join: each current route + **airline(s) + aircraft
  type(s)** (from the schedule) + real Dec-2025 passengers (DGCA) + **real implied load
  factor**. Built by `../../pax_estimation/route_profile.py`. Most routes land at a
  believable **65–86%** LF (independent validation of the seat capacities). Two flags:
  *Bhubaneswar shows LF>100% (impossible)* — the schedule under-captures that route
  (its arrival leg had a bad origin code `881`); *Kurnool 23%* is a genuinely thin ATR
  route. Note: per-route-per-**airline** passenger counts are NOT public (DGCA carrier
  data is national totals), so the airline/aircraft here come from the schedule, not
  from measured per-airline pax.

**These validate the schedule-derived estimate against reality:**
| Month | Estimate (8,718/day × days) | Actual | Match |
|---|---|---|---|
| Jan 2026 | 270,258 | 271,302 | **99.6%** |
| Jan 2025 | 270,258 | 272,743 | **99.1%** |
| Feb 2026 | 244,104 | 230,117 | 106% (Feb is a seasonally low month) |

Granularity ceiling: **monthly is the finest real count obtainable.** For the
intra-day curve we combine real monthly totals × the schedule-derived hourly
*shape* (`../../pax_estimation/`) — real volume, modelled distribution.

## Note
Different airport from the core POD work (which is GMR **Hyderabad / HYD**). Kept
in its own folder. Seat capacities in the schedule are web-verified per aircraft
type × operating airline (see that file's legend + header comment). Traffic counts
in `vtz_*_traffic.csv` are official AAI/DGCA figures (sources in each row).
