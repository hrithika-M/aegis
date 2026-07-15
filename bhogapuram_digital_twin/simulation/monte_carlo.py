# -*- coding: utf-8 -*-
"""Monte Carlo — confidence intervals for peak resource demand.

The deterministic twin gives ONE number ("10 check-in counters"). Real planning
needs a distribution: you staff for the P95, not the average. This runs the design
day many times, each with per-flight load factors drawn from their distributions,
and reports P5 / P50 / P95 for the peak metrics.

  load_factor ~ Normal(mu_route, sigma)   (same model as the passenger engine)
  each run  -> a design-day 5-min demand curve -> peak check-in / security / occupancy
  N runs    -> percentiles

Design day = a representative Wednesday (all flights whose frequency includes Wed).

Output: analytics/confidence_intervals.csv
Run:    python monte_carlo.py
"""
import csv, os
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FM = os.path.join(ROOT, 'master', 'Flight_Master.csv')
ROUTEPROF = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz', 'vtz_route_profile.csv')
OUT = os.path.join(ROOT, 'analytics', 'confidence_intervals.csv')

N_RUNS = 1000
SEED = 42
LF_SIGMA, DEFAULT_MU = 0.07, 0.80
LF_MIN, LF_MAX = 0.45, 0.98
DESIGN_DOW = 3                        # Wednesday (1=Mon..7=Sun)
STEP, SLOTS = 5, 24 * 12
CHECKIN_PER_5MIN, SECURITY_PER_5MIN = 6, 12
STAGES = {'checkin': (-150, -45, -90), 'security': (-95, -25, -55), 'boarding': (-30, -8, -18)}
ENTER, EXIT = (-150, -40, -85), -10
CODE2CITY = {'HYD': 'Hyderabad', 'DEL': 'Delhi', 'BLR': 'Bengaluru', 'MAA': 'Chennai',
             'BOM': 'Mumbai', 'CCU': 'Kolkata', 'VGA': 'Vijayawada', 'TIR': 'Tirupati',
             'KJB': 'Kurnool', 'PYB': 'Jeypore', 'BBI': 'Bhubaneswar'}


def route_mu():
    mu = {}
    if os.path.exists(ROUTEPROF):
        for r in csv.DictReader(open(ROUTEPROF, encoding='utf-8')):
            try:
                lf = float(r['ImpliedLoadFactor_pct']) / 100.0
            except (ValueError, KeyError):
                continue
            if 0.50 <= lf <= 0.95:
                mu[r['Route']] = lf
    return mu


def tri(x, a, b, c):
    if x < a or x > b:
        return 0.0
    return (x - a) / (c - a) if x <= c else (b - x) / (b - c)


def spread(arr, base_slot, P, win):
    a, b, c = win
    lo, hi = int(round((base_slot * STEP + a) / STEP)), int(round((base_slot * STEP + b) / STEP))
    ws = [(s, tri(s * STEP - base_slot * STEP, a, b, c)) for s in range(lo, hi + 1)]
    tot = sum(w for _, w in ws)
    if tot <= 0:
        return
    for s, w in ws:
        if 0 <= s < SLOTS:
            arr[s] += P * w / tot


def main():
    mus = route_mu()
    rng = np.random.default_rng(SEED)
    # design-day departures: dest city, dep slot, seats
    deps = []
    for r in csv.DictReader(open(FM, encoding='utf-8')):
        if str(DESIGN_DOW) in r['frequency']:
            hh, mm = map(int, r['departure_time'].split(':'))
            deps.append((CODE2CITY.get(r['destination'], ''), (hh * 60 + mm) // STEP, int(r['seat_capacity'])))

    peaks = defaultdict(list)
    for _ in range(N_RUNS):
        ci = [0.0] * SLOTS; se = [0.0] * SLOTS; en = [0.0] * SLOTS; ex = [0.0] * SLOTS
        total = 0.0
        for city, slot, seats in deps:
            mu = mus.get(city, DEFAULT_MU)
            lf = float(np.clip(rng.normal(mu, LF_SIGMA), LF_MIN, LF_MAX))
            P = seats * lf
            total += P
            spread(ci, slot, P, STAGES['checkin'])
            spread(se, slot, P, STAGES['security'])
            spread(en, slot, P, ENTER)
            xe = int(round((slot * STEP + EXIT) / STEP))
            if 0 <= xe < SLOTS:
                ex[xe] += P
        occ, run = 0.0, 0.0
        for i in range(SLOTS):
            run += en[i] - ex[i]
            occ = max(occ, run)
        peaks['daily_departing_pax'].append(total)
        peaks['peak_checkin_demand_5min'].append(max(ci))
        peaks['peak_security_demand_5min'].append(max(se))
        peaks['peak_checkin_counters'].append(np.ceil(max(ci) / CHECKIN_PER_5MIN))
        peaks['peak_security_lanes'].append(np.ceil(max(se) / SECURITY_PER_5MIN))
        peaks['peak_terminal_occupancy'].append(occ)

    rows = []
    print("=" * 74)
    print(f"MONTE CARLO — {N_RUNS} runs, design day (Wed).  Plan for the P95, not the mean.")
    print("=" * 74)
    print(f"  {'Metric':<30}{'mean':>8}{'P5':>8}{'P50':>8}{'P95':>8}")
    for k, v in peaks.items():
        v = np.array(v)
        m, p5, p50, p95 = v.mean(), np.percentile(v, 5), np.percentile(v, 50), np.percentile(v, 95)
        rows.append([k, round(m, 1), round(p5, 1), round(p50, 1), round(p95, 1)])
        print(f"  {k:<30}{m:>8.1f}{p5:>8.1f}{p50:>8.1f}{p95:>8.1f}")
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['metric', 'mean', 'P5', 'P50', 'P95']); w.writerows(rows)
    print("-" * 74)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print("Staffing example: size check-in counters for the P95, not the average, so")
    print("you don't understaff on a heavier-than-typical day.")


if __name__ == '__main__':
    main()
