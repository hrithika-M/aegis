# POD2 · Step 5 — Cross-dataset comparison (Entry) & the formula-column plan

The comparison is strictly between the three POD datasets: **June loads ↔ HYD
e-boarding ↔ digital twin** (see `comparison_dashboard.png`, numbers in
`comparison_summary.csv`).

> **Note:** Avra's dashboard is only a **style template** for how the analysis should
> *look* — it is not a POD dataset, so it is **not** used as a comparison series
> anywhere here.

## First, which dataset can even speak to each Entry dimension?
Not every dataset has the columns for every dimension. For **Entry** specifically:

| Dimension | June loads | HYD e-boarding | Digital twin |
|---|---|---|---|
| Passenger volume | ✅ real (daily) | ⚠️ real, 2 days only | ✅ modelled |
| Load factor | ✅ real | ❌ no seat/LF field | ✅ modelled |
| Aircraft mix | ✅ real | ~ per-flight | ✅ modelled |
| **Entry show-up profile** (minutes early) | ❌ **none** | ✅ real | ✅ modelled |
| **Entry hourly demand** | ❌ **none** | ✅ real | ✅ modelled |

**June loads has no terminal-entry scans, no per-passenger rows and no time-of-day** —
only daily `load_factor` + `pax` by aircraft category. So June **cannot** participate in
the Entry show-up/timing comparison at all; its only role at Entry is as the upstream
*volume + load-factor input*. The **Entry show-up comparison is therefore two-way:
HYD e-boarding (real) vs digital twin (modelled).**

## What matches, what doesn't

| Dimension | Datasets compared | Result | Verdict |
|---|---|---|---|
| **Aircraft mix** | June ↔ Twin | C 95.3 vs 95.5, B 4.6 vs 4.4, A 0.1 vs 0.1 | ✅ **Matches** (≤0.2 pt) |
| **Load factor (level)** | June ↔ Twin | 82.1% vs **77.8%** | ⚠️ Twin ~4 pt low |
| **Load factor (day-of-week)** | June ↔ Twin | June Mon 78 → **Sun 88%** vs twin flat ~78% | ⚠️ Twin misses the weekly shape |
| **Show-up profile** | HYD ↔ Twin *(June absent — no data)* | HYD tail 20% >150 min vs twin **0%** past 150 | ⚠️ Twin mis-calibrated |

**Takeaway:** the twin gets the *fleet/volume* structure right, but two behavioural
layers — how full flights are through the week, and how early people show up — are
modelled with flat/narrow assumptions that the real data contradicts. These are the
two things to recalibrate before Avra sign-off.

## Two concrete recalibrations (fold into Step 6)

1. **Show-up window (`DEP_ENTER` in `build_operations.py`).**
   Current `(-150, -40, -85)` caps at 150 min and can't produce the real 20% tail past
   150. **Fix:** drive terminal entry from the *measured* e-boarding buckets
   (`step3_ews_eboarding/entry_showup_profile.csv`) instead of a triangle — this is
   exactly how Avra does it (measured show-up %, not an assumed curve). If a triangle
   must stay, widen to roughly `(-210, -30, -105)` so the tail and earlier peak appear.

2. **Load factor.** Lift the narrow-body base ~82% and add the day-of-week curve from
   June (quietest Monday 78%, busiest Sunday 88%) rather than a flat draw.

## The formula-derived columns (Avra's construct, Entry)

All of these are **simple, auditable formulas** on data we already have — no ML:

| Column | Formula | Source |
|---|---|---|
| `passengers` | `seat_capacity × load_factor[category, day_of_week]` | June LF + schedule |
| `minutes_early` | `departure_time − entry_scan_time` | e-boarding (real) / show-up curve (twin) |
| `showup_bucket` | bucket(`minutes_early`) into <60 … >180 | Step 3 thresholds |
| `entry_demand[t]` | `Σ passengers × showup_pct(bucket → t before STD)` | passengers × profile |
| `entry_demand_30min[t]` | rolling 30-min sum of `entry_demand` | Avra's 30-min projection |
| `lanes_required[t]` | `ceil(entry_demand_30min / throughput_30min)` | ATRS 120 pax/hr/lane ⇒ 60 pax/30min/lane |
| `queue[t]`, `wait[t]` | `max(0, queue[t-1]+arrivals−capacity)`; `wait≈queue×5/capacity` | queue model |

## Data caveats to raise with Avra (for the questionnaire)
- E-boarding file is only **2 days** (12–13 Apr) → good for the overall show-up %, but
  **not** enough for day-of-week show-up splits. Ask for a full month.
- June load sheet has the July-labelled copy ambiguity — using June only (confirmed).
- Confirm the throughput assumption (ATRS 180 trays/hr, 1.5 trays/pax ⇒ 120 pax/hr/lane).

## Status
Entry layer fully mapped across all three datasets. Ready for **Step 6**: apply the two
recalibrations, materialise the formula columns into a single finalised Entry dataset,
and take it to Avra for confirmation before any modelling.
