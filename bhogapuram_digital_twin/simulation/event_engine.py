# -*- coding: utf-8 -*-
"""Event engine — disruption propagation.

Scenarios test static staffing; events test dynamic shocks. A weather window delays
the departures inside it; those passengers have already shown up, so they DWELL
longer -> terminal occupancy climbs and later banks compress. This measures the
congestion that cascades from a disruption.

Model (design day, departures):
  passengers enter over the show-up window before the ORIGINAL departure and leave at
  boarding. Under an event, departures inside [start,end] get pushed by `delay_min`,
  so their passengers' exit shifts later -> extra dwell -> higher peak occupancy.

Events are a config list — add rows freely.

Run:  python event_engine.py  ->  analytics/events.csv
"""
import csv, os
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FM = os.path.join(ROOT, 'master', 'Flight_Master.csv')
ROUTEPROF = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz', 'vtz_route_profile.csv')
OUT = os.path.join(ROOT, 'analytics', 'events.csv')

STEP, SLOTS = 5, 24 * 12
DESIGN_DOW = 3
ENTER = (-150, -40, -85)          # terminal-entry show-up window (min before STD)
EXIT = -10                        # leave landside at boarding
DEFAULT_MU = 0.80
CODE2CITY = {'HYD': 'Hyderabad', 'DEL': 'Delhi', 'BLR': 'Bengaluru', 'MAA': 'Chennai',
             'BOM': 'Mumbai', 'CCU': 'Kolkata', 'VGA': 'Vijayawada', 'TIR': 'Tirupati',
             'KJB': 'Kurnool', 'PYB': 'Jeypore', 'BBI': 'Bhubaneswar'}

# event: (name, delay_min, window_start_hour, window_end_hour)
EVENTS = [
    ('none (baseline)',            0,  0, 24),
    ('morning fog (45m, 06-09h)', 45,  6,  9),
    ('evening storm (60m, 18-21h)', 60, 18, 21),
    ('ground stop (90m, all day)', 90,  0, 24),
]


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


def load_departures():
    mus = route_mu()
    deps = []
    for r in csv.DictReader(open(FM, encoding='utf-8')):
        if str(DESIGN_DOW) in r['frequency']:
            hh, mm = map(int, r['departure_time'].split(':'))
            std = hh * 60 + mm
            mu = mus.get(CODE2CITY.get(r['destination'], ''), DEFAULT_MU)
            deps.append((std, int(r['seat_capacity']) * mu))
    return deps


def occupancy(deps, delay, w0, w1):
    en = [0.0] * SLOTS; ex = [0.0] * SLOTS
    for std, P in deps:
        new_std = std + (delay if w0 * 60 <= std < w1 * 60 else 0)
        a, b, c = ENTER
        lo, hi = int(round((std + a) / STEP)), int(round((std + b) / STEP))   # entry on ORIGINAL schedule
        ws = [(s, tri(s * STEP - std, a, b, c)) for s in range(lo, hi + 1)]
        tot = sum(w for _, w in ws)
        for s, w in ws:
            if 0 <= s < SLOTS and tot > 0:
                en[s] += P * w / tot
        xe = int(round((new_std + EXIT) / STEP))                              # exit on NEW (delayed) schedule
        if 0 <= xe < SLOTS:
            ex[xe] += P
    occ = [0.0] * SLOTS
    run = 0.0
    for i in range(SLOTS):
        run += en[i] - ex[i]
        occ[i] = max(0.0, run)
    return occ


def main():
    deps = load_departures()
    base_occ = occupancy(deps, 0, 0, 24)
    base_peak = max(base_occ)
    rows = []
    print("=" * 78)
    print("EVENT ENGINE — disruption congestion on the design day (departures)")
    print("=" * 78)
    print(f"  {'Event':<30}{'peak occ':>10}{'vs base':>10}{'extra dwell (pax-min)':>22}")
    for name, delay, w0, w1 in EVENTS:
        occ = occupancy(deps, delay, w0, w1)
        peak = max(occ)
        extra_dwell = (sum(occ) - sum(base_occ)) * STEP        # pax-minutes of extra presence
        rows.append([name, delay, f"{w0:02d}-{w1:02d}h", round(peak),
                     round(peak - base_peak), round(extra_dwell)])
        print(f"  {name:<30}{round(peak):>10}{round(peak - base_peak):>+10}{round(extra_dwell):>22,}")
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['event', 'delay_min', 'window', 'peak_occupancy', 'delta_vs_baseline', 'extra_dwell_pax_min'])
        w.writerows(rows)
    print("-" * 78)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print("Higher peak occupancy + extra dwell = crowding the terminal/seating must absorb.")


if __name__ == '__main__':
    main()
