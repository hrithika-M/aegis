# POD2 — Bhogapuram POD, rebuilt on the real product-owner data

A fresh, step-by-step build using **only the datasets Avra (product owner) shared**,
following the construct he walked us through. Each step is self-contained and
reviewed before moving on.

## The plan (8 steps)
1. **Isolate the clean June data** — of the two sheets in `JUN LOADS FOR AIRLINE`,
   use the **June** actuals. (Avra later confirmed both sheets are June — the July label was wrong.)
2. **Avra-style analysis on the June data** — per touchpoint, starting with **Entry**.
3. Same analysis on the **HYD e-boarding (EWS)** data for Entry.
4. Same analysis on the **digital-twin** data for Entry.
5. **Compare patterns** across the three → see what matches the Bhogapuram data,
   then work out which columns can be built with simple formulas (as Avra did).
6. **Finalise the dataset**, confirm with Avra, then move to modelling.
7. (this folder)
8. Report after every step before continuing.

## Status
| Step | What | State |
|---|---|---|
| 1 | Isolate clean June data | ✅ done |
| 2 | Avra-style analysis on June data (Entry) | ✅ done |
| 3 | Entry show-up profile from HYD e-boarding (EWS) | ✅ done |
| 4 | Same (Entry) on digital-twin data | ✅ done |
| 5 | Cross-dataset pattern comparison + candidate formula columns | ✅ done |
| 6 | Finalise Entry dataset (build done; Avra confirm pending) | ✅ built |

## Folders
- `inputs/` — the source workbooks (June loads — both sheets confirmed June; VTZ schedule).
- `step1_june_data/` — `extract_june.py` → `june_load_daily.csv` (tidy, 180 rows).
- `step2_june_analysis/` — `analyze_june.py` → `june_dashboard.png`.
- `step3_ews_eboarding/` — `analyze_ews_entry.py` → `entry_showup_profile.csv`,
  `entry_hourly.csv`, `ews_entry_dashboard.png`. **Raw e-boarding file is NOT
  committed** (passenger PII); only aggregated outputs are.
- `step4_twin_entry/` — `analyze_twin_entry.py` → `twin_entry_showup_profile.csv`,
  `twin_entry_hourly.csv`, `twin_entry_dashboard.png`. Reconstructs the twin's Entry
  minutes-early distribution from its `DEP_ENTER` show-up window, bucketed the **same
  way as Step 3** for a like-for-like comparison.
- `step5_comparison/` — `compare_datasets.py` → `comparison_dashboard.png`,
  `comparison_summary.csv`, and **`COMPARISON.md`** (what matches, the two
  recalibrations, and the formula-column plan for Step 6).
- `step6_finalise/` — `build_entry_pod.py` → `finalised_entry_daily_summary.csv`,
  `finalised_entry_sample_day.csv`. The finalised Entry POD: pure calculation
  (no ML) with both recalibrations applied (real LF-by-day-of-week + measured show-up
  buckets) and Avra's formula columns (entry demand, 30-min projection, lanes required).

## Step 6 result — finalised Entry dataset (Bhogapuram / VTZ)
`passengers = seat_capacity × LF[category, day_of_week]` (real June LF) → distributed to
terminal entry by the **measured** e-boarding show-up buckets → `entry_demand_5min` →
`entry_demand_30min` (Avra's 30-min projection) → `lanes_required = ceil(demand_30min/60)`.
- 5,820 departures, **873,509 season entry pax** (real ~82% LF vs the twin's flat ~78%).
- **Peak = 4 entry lanes**; busiest day 30-min demand 229 pax.
- Avra sign-off is the gate before any modelling (Entry-only until then).

## Step 5 result — the twin matches on fleet, misses on two behaviours
Comparison is strictly June loads ↔ HYD e-boarding ↔ twin. (Avra's dashboard is a
*style template only*, not a dataset — not compared against.) **June has no scan times,
so it cannot join the Entry show-up comparison — that one is two-way, HYD ↔ twin.**
| Dimension | Compared | Result | Verdict |
|---|---|---|---|
| Aircraft mix (C/B/A) | June ↔ twin | 95.3/4.6/0.1 vs 95.5/4.4/0.1 | ✅ matches |
| Load factor (level) | June ↔ twin | 82.1% vs 77.8% | ⚠️ ~4 pt low |
| Load factor (day-of-week) | June ↔ twin | Mon 78→Sun 88% vs flat ~78% | ⚠️ misses weekly shape |
| Show-up profile | HYD ↔ twin *(June: no data)* | 20% >150 min vs 0% past 150 | ⚠️ mis-calibrated |

Two recalibrations to fold into Step 6: (1) drive Entry from the **measured** e-boarding
show-up buckets instead of the triangular `DEP_ENTER`; (2) lift load factor to ~82% with
June's day-of-week curve. See `step5_comparison/COMPARISON.md` for the full write-up and
the Avra-style formula columns (`passengers = seats × LF`, `minutes_early`, 30-min
projection, `lanes_required`, queue/wait).

## Step 4 result — the twin's Entry window is mis-calibrated vs reality
Same buckets, three datasets (share of Entry passengers):
| minutes early | Twin (generated) | Real e-boarding | Avra |
|---|---|---|---|
| <60 | 6.1% | 4.3% | 4.65% |
| 60–90 | **39.4%** | 23.2% | 25.59% |
| 90–120 | 39.9% | 32.0% | 32.99% |
| 120–150 | 14.7% | 20.5% | 20.04% |
| 150–180 | **0.0%** | 9.5% | 8.63% |
| >180 | **0.0%** | 10.5% | 8.11% |

The twin's `DEP_ENTER = (-150, -40, -85)` window **caps at 150 min and peaks at 85**,
so it puts **0%** in the 150–180 and >180 buckets — but ~20% of real passengers show
up that early. The twin over-concentrates in 60–120 (79% vs real 55%). **Fix for
Step 5/6:** recalibrate `DEP_ENTER` to the real profile — widen the tail past 180 min
and shift the peak earlier (real peak bucket is 90–120). The hourly *shape* differs too
(twin peaks 19:00 on season totals vs real 08:00) because the twin is a full S26 season
while the e-boarding is 2 April days — compare shapes, not absolute counts.

## Step 3 result — our profile matches Avra's
Entry show-up % from the real e-boarding data (our 2-day sample vs Avra's full-month dashboard):
| minutes early | Ours (12–13 Apr) | Avra (full April) |
|---|---|---|
| 90–120 | 32.0% | 32.99% |
| 60–90 | 23.2% | 25.59% |
| 120–150 | 20.5% | 20.04% |
| 150–180 | 9.5% | 8.63% |
| >180 | 10.5% | 8.11% |
| <60 | 4.3% | 4.65% |

Same method, same shape — validates the construct. Data caveat: the file we have is
only **2 days** (12–13 Apr, 20,079 valid entry records), not the full month Avra used.

## What the June data can and can't show
The June loads sheet has **daily passenger volume and load factor** per aircraft
category — so it supports volume/load-factor patterns (total pax by date, load
factor by day-of-week, etc.). It has **no per-passenger scan times**, so the
passenger **show-up profile** (Avra's stacked hourly bars) is *not* derivable here —
that needs the e-boarding data (Step 3).

## Key June facts (real actuals, Jun 2026)
- 30 days · **220,886 total passengers** (108,487 departing + 112,399 arriving).
- Aircraft mix: **Category C (narrow-body) = 95.3%** of departing pax, B (ATR) ~4.6%, A (9-seater) ~0.1%.
- Narrow-body departure load factor: **82% average**, ranging 68–94% day to day.
- Day-of-week: quietest **Monday (78%)**, busiest **Sunday (88%)**.
