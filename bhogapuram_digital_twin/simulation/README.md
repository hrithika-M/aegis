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

---

# scenario_engine.py — what-if analysis with a queue model

The base twin says "you need N counters". Planners need the inverse: **given a FIXED
number of counters/lanes, what happens under stress?** This applies scenario levers
(demand multiplier, servers open/closed) to the busiest day and runs a deterministic
bucket queue to get queue length, wait time, and SLA breaches.

Run: `python scenario_engine.py` → `analytics/scenarios.csv`

## Queue model
`queue[t] = max(0, queue[t-1] + arrivals[t] − capacity[t])`, capacity = servers ×
service-rate (pax/5-min), `wait ≈ queue × 5 / capacity` minutes. SLA: check-in 20 min,
security 15 min. Scenarios are a config list — add rows freely.

## Result (busiest day)
| Scenario | Security wait | Verdict |
|---|---|---|
| baseline (6 lanes) | 0 min | OK |
| demand +20% | 0 min | OK |
| 2 lanes closed (→4) | 4.4 min | OK |
| surge +20% & 2 lanes closed | 12.7 min | OK |
| festival +40% | 2.3 min | OK |
| **3 lanes only** | **20.6 min** | **BREACH** |
| **major disruption +60%, 3 lanes** | **132.8 min** | **BREACH** |

## The planning insight
**Security is the binding constraint** — it breaches before check-in in every stress
case. VTZ can absorb +40% demand *or* the loss of 2 security lanes, but **not the loss
of a 3rd lane**, and a surge combined with understaffing is a meltdown (130+ min waits).
That's an actionable staffing rule, produced from the twin — exactly what a scenario
engine is for.

---

# event_engine.py — disruption propagation

Scenarios test static staffing; **events test dynamic shocks.** A weather window delays
the departures inside it; those passengers have already shown up, so they **dwell
longer** → terminal occupancy climbs. Measures the congestion that cascades.

Run: `python event_engine.py` → `analytics/events.csv`

## Result (design day, departures)
| Event | Peak occupancy | vs baseline | Extra dwell (pax-min) |
|---|---|---|---|
| baseline | 663 | — | — |
| morning fog (45 m, 06–09h) | 744 | +81 | 25,376 |
| evening storm (60 m, 18–21h) | 879 | **+216** | 50,721 |
| ground stop (90 m, all day) | 1,116 | **+453** | 346,693 |

## The planning insight
**Evening disruptions hurt more than morning** (the evening bank is busier: +216 vs
+81 peak occupancy), and a full ground stop **nearly doubles** peak occupancy — which
is the number the terminal's seating and holding areas must be sized for. Together with
the scenario engine, the twin now stress-tests both *staffing* (queues) and *shocks*
(congestion).
