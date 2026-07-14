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
- `vtz_monthly_traffic.csv` — the months with published figures (Jan-2025 with
  dom/intl + arr/dep split, Jan-2026, Feb-2026, Jan–Nov-2025 cumulative). Only
  actually-published months are listed; no months were fabricated.

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
