# simulation — Monte Carlo uncertainty

The deterministic twin gives one number ("10 check-in counters"). Real operations
planning needs a **distribution** — you staff for the P95, not the average, or you
understaff on any heavier-than-typical day. This runs the design day many times with
per-flight load factors drawn from their distributions and reports percentiles.

Run: `python monte_carlo.py`  →  `analytics/confidence_intervals.csv`

## Model
- `load_factor ~ Normal(mu_route, 0.07)`, clipped [0.45, 0.98] — the same per-flight
  LF model the passenger engine uses (`build_passengers.py`), so the twin and its
  uncertainty band are consistent.
- Design day = a representative Wednesday (all flights whose frequency includes Wed).
- `N = 1000` runs (seeded, reproducible). Each run builds a 5-minute departure-demand
  curve (check-in / security / boarding via the show-up windows) and extracts the peaks.

## Result (current build)
| Metric | mean | P5 | P50 | **P95 (plan for this)** |
|---|---|---|---|---|
| Daily departing pax | 3,897 | 3,785 | 3,898 | **4,009** |
| Peak check-in demand /5min | 43.6 | 40.7 | 43.5 | **46.5** |
| Peak security demand /5min | 54.6 | 51.6 | 54.5 | **58.0** |
| Peak check-in counters | 7.8 | 7 | 8 | **8** |
| Peak security lanes | 5.0 | 5 | 5 | **5** |
| Peak terminal occupancy | 672 | 633 | 670 | **714** |

**How to read it:** size check-in for **8 counters** and security for **5 lanes** —
those hold at the P95, so a busier-than-average Wednesday won't blow the plan. The
bands are fairly tight because a 5-minute peak sums many flights, so individual
load-factor noise partly averages out — itself a realistic finding.

## Why this matters for production
A single deterministic peak is a point estimate that will be wrong on ~half of days.
Percentiles turn the twin from "here's a number" into "here's the number and the risk
around it" — which is what an airport actually staffs against.
