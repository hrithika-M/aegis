# -*- coding: utf-8 -*-
"""Event engine — disruption propagation (departures AND arrivals).

Scenarios test static staffing; events test dynamic shocks. Departure delays make
passengers who already showed up DWELL longer (occupancy climbs); arrival delays
shift baggage-belt demand later and pile up meeters/greeters-side congestion.

Meeting-requested events (Bhogapuram, Jul-2026) included alongside the generic set:
  - "15 mins delay"            minor ATC/rotation slip, all day
  - "runway edge-lighting damaged (lightning)"  night arrivals+departures delayed —
      ASSUMPTION: damaged edge-line section -> increased spacing/inspection, avg
      40-min delay for movements 19:00-24:00 (flagged for validation with ops)
  - "wildlife strike on taxiway"  taxiway inspection/closure after a strike —
      ASSUMPTION: 30-min avg delay for ARRIVALS in a 2-hour window (14:00-16:00),
      single-taxiway ops while runway is inspected (flagged for validation)

Outputs one row per event with the OUTCOME quantified: peak occupancy delta,
extra dwell, arriving pax delayed, and peak belt-demand shift.

Run:  python event_engine.py  ->  analytics/events.csv
"""
import csv, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FM = os.path.join(ROOT, 'master', 'Flight_Master.csv')
ROUTEPROF = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz', 'vtz_route_profile.csv')
OUT = os.path.join(ROOT, 'analytics', 'events.csv')

STEP, SLOTS = 5, 24 * 12
DESIGN_DOW = 3                      # Wednesday
ENTER = (-150, -40, -85)            # dep show-up window (min before STD)
DEP_EXIT = -10                      # dep pax leave landside at boarding
BELT = (5, 35, 18)                  # arr belt demand window (min after STA)
ARR_EXIT = 45                       # arr pax clear the terminal
DEFAULT_MU = 0.80
CODE2CITY = {'HYD': 'Hyderabad', 'DEL': 'Delhi', 'BLR': 'Bengaluru', 'MAA': 'Chennai',
             'BOM': 'Mumbai', 'CCU': 'Kolkata', 'VGA': 'Vijayawada', 'TIR': 'Tirupati',
             'KJB': 'Kurnool', 'PYB': 'Jeypore', 'BBI': 'Bhubaneswar'}

# event: (name, delay_min, window_start_h, window_end_h, side: 'dep'|'arr'|'both')
EVENTS = [
    ('none (baseline)',                       0,  0, 24, 'both'),
    ('minor delay 15 min (all day)',         15,  0, 24, 'both'),
    ('morning fog (45m, 06-09h)',            45,  6,  9, 'both'),
    ('evening storm (60m, 18-21h)',          60, 18, 21, 'both'),
    ('runway edge-lighting damaged (40m, 19-24h)', 40, 19, 24, 'both'),
    ('wildlife strike on taxiway (30m, 14-16h, arrivals)', 30, 14, 16, 'arr'),
    ('ground stop (90m, all day)',           90,  0, 24, 'both'),
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


def spread(arr, base_min, P, win):
    a, b, c = win
    lo, hi = int(round((base_min + a) / STEP)), int(round((base_min + b) / STEP))
    ws = [(s, tri(s * STEP - base_min, a, b, c)) for s in range(lo, hi + 1)]
    tot = sum(w for _, w in ws)
    if tot <= 0:
        return
    for s, w in ws:
        if 0 <= s < SLOTS:
            arr[s] += P * w / tot


def load_legs():
    mus = route_mu()
    deps, arrs = [], []
    for r in csv.DictReader(open(FM, encoding='utf-8')):
        if str(DESIGN_DOW) not in r['frequency']:
            continue
        seats = int(r['seat_capacity'])
        dh, dm = map(int, r['departure_time'].split(':'))
        ah, am = map(int, r['arrival_time'].split(':'))
        deps.append((dh * 60 + dm, seats * mus.get(CODE2CITY.get(r['destination'], ''), DEFAULT_MU)))
        arrs.append((ah * 60 + am, seats * mus.get(CODE2CITY.get(r['origin'], ''), DEFAULT_MU)))
    return deps, arrs


def simulate(deps, arrs, delay, w0, w1, side):
    """Return occupancy curve, belt curve, arriving pax delayed."""
    en = [0.0] * SLOTS; ex = [0.0] * SLOTS; belt = [0.0] * SLOTS
    delayed_arr_pax = 0.0
    for std, P in deps:
        d = delay if (side in ('dep', 'both') and w0 * 60 <= std < w1 * 60) else 0
        spread(en, std, P, ENTER)                     # show-up follows ORIGINAL schedule
        xe = int(round((std + d + DEP_EXIT) / STEP))  # exit at the DELAYED boarding
        if 0 <= xe < SLOTS:
            ex[xe] += P
    for sta, P in arrs:
        d = delay if (side in ('arr', 'both') and w0 * 60 <= sta < w1 * 60) else 0
        if d:
            delayed_arr_pax += P
        s0 = int(round((sta + d) / STEP))             # arrivals land late
        if 0 <= s0 < SLOTS:
            en[s0] += P
        spread(belt, sta + d, P, BELT)
        xe = int(round((sta + d + ARR_EXIT) / STEP))
        if 0 <= xe < SLOTS:
            ex[xe] += P
    occ = [0.0] * SLOTS
    run = 0.0
    for i in range(SLOTS):
        run += en[i] - ex[i]
        occ[i] = max(0.0, run)
    return occ, belt, delayed_arr_pax


def main():
    deps, arrs = load_legs()
    base_occ, base_belt, _ = simulate(deps, arrs, 0, 0, 24, 'both')
    bpk, bbelt = max(base_occ), max(base_belt)
    rows = []
    print("=" * 96)
    print("EVENT ENGINE — disruption propagation on the design day (departures + arrivals)")
    print("=" * 96)
    print(f"  {'Event':<48}{'peak occ':>9}{'vs base':>9}{'arr pax delayed':>17}{'peak belt':>11}")
    for name, delay, w0, w1, side in EVENTS:
        occ, belt, dpax = simulate(deps, arrs, delay, w0, w1, side)
        peak, pbelt = max(occ), max(belt)
        extra = (sum(occ) - sum(base_occ)) * STEP
        rows.append([name, delay, f"{w0:02d}-{w1:02d}h", side, round(peak),
                     round(peak - bpk), round(extra), round(dpax), round(pbelt)])
        print(f"  {name:<48}{round(peak):>9}{round(peak - bpk):>+9}{round(dpax):>17,}{round(pbelt):>11}")
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['event', 'delay_min', 'window', 'side', 'peak_occupancy',
                    'delta_vs_baseline', 'extra_dwell_pax_min', 'arriving_pax_delayed',
                    'peak_belt_demand'])
        w.writerows(rows)
    print("-" * 96)
    print(f"wrote {os.path.relpath(OUT, ROOT)}   (baseline peak belt demand: {round(bbelt)})")
    print("OUTCOME reading: peak occupancy = crowding the terminal must absorb; arriving pax")
    print("delayed + belt shift = arrivals-hall congestion & belt scheduling impact.")
    print("NOTE: runway-lighting (40m) and wildlife-strike (30m) delay magnitudes are")
    print("ASSUMPTIONS pending validation with Bhogapuram ops (see QUESTIONNAIRE.md).")


if __name__ == '__main__':
    main()
