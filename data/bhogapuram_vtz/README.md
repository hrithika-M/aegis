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

## Note
Different airport from the core POD work (which is GMR **Hyderabad / HYD**). Kept
in its own folder. Seat capacities in the schedule are web-verified per aircraft
type × operating airline (see that file's legend + header comment).
