# POD2 — Bhogapuram POD, rebuilt on the real product-owner data

A fresh, step-by-step build using **only the datasets Avra (product owner) shared**,
following the construct he walked us through. Each step is self-contained and
reviewed before moving on.

## The plan (8 steps)
1. **Isolate the clean June data** — of the two sheets in `JUN LOADS FOR AIRLINE`,
   use only the trusted **June** actuals (the other, labelled July, is calculated).
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
| 3 | Same on HYD e-boarding (EWS) | ⏳ next |
| 4 | Same on digital-twin data | pending |
| 5 | Cross-dataset pattern comparison + candidate formula columns | pending |
| 6 | Finalise dataset + confirm with Avra | pending |

## Folders
- `inputs/` — the source workbook (June+July; we use June only).
- `step1_june_data/` — `extract_june.py` → `june_load_daily.csv` (tidy, 180 rows).
- `step2_june_analysis/` — `analyze_june.py` → `june_dashboard.png`.

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
