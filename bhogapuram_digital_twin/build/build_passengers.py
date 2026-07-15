# -*- coding: utf-8 -*-
"""Phase 2 — Passenger engine (stochastic load factors).

Each flight leg gets passengers = seats x load_factor, where load_factor is DRAWN
from a realistic distribution per route:

    load_factor ~ Normal(mu_route, sigma),   clipped to [0.45, 0.98]
    mu_route    = real implied load factor for that route (vtz_route_profile), else 0.80
    sigma       = 0.07  (per-flight spread; real airline daily PLF std ~0.06)

Then a LIGHT reconciliation nudges each (route, direction, month) toward the real
2025 DGCA total — factor clipped to [0.9, 1.1] so we DON'T reintroduce the extreme
per-flight load factors that failed synthetic validation. Reproducible (seed=42).

Why this replaces "base 0.85 -> hard reconcile -> cap": that produced per-flight load
factors 2.5x too spread (validation PSI 2.85). Drawing around real route means fixes
the distribution while keeping totals within a few percent of real.

Input:  generated/Daily_Flights.csv, ../data/bhogapuram_vtz/{vtz_citypair_monthly,vtz_route_profile}.csv
Output: generated/passenger_estimates.csv
"""
import csv, os
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DAILY = os.path.join(ROOT, 'generated', 'Daily_Flights.csv')
DATADIR = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz')
CITYPAIR = os.path.join(DATADIR, 'vtz_citypair_monthly.csv')
ROUTEPROF = os.path.join(DATADIR, 'vtz_route_profile.csv')
OUT = os.path.join(ROOT, 'generated', 'passenger_estimates.csv')

SEED = 42
LF_SIGMA = 0.07
DEFAULT_MU = 0.80
LF_MIN, LF_MAX = 0.45, 0.98
RECON_LO, RECON_HI = 0.9, 1.1
CODE2CITY = {'HYD': 'Hyderabad', 'DEL': 'Delhi', 'BLR': 'Bengaluru', 'MAA': 'Chennai',
             'BOM': 'Mumbai', 'CCU': 'Kolkata', 'VGA': 'Vijayawada', 'TIR': 'Tirupati',
             'KJB': 'Kurnool', 'PYB': 'Jeypore', 'BBI': 'Bhubaneswar'}


def route_mu():
    """city -> real implied load factor (from route profile), sane values only."""
    mu = {}
    if os.path.exists(ROUTEPROF):
        for r in csv.DictReader(open(ROUTEPROF, encoding='utf-8')):
            try:
                lf = float(r['ImpliedLoadFactor_pct']) / 100.0
            except (ValueError, KeyError):
                continue
            if 0.50 <= lf <= 0.95:                 # skip anomalies (BBI 322%, Kurnool 23%)
                mu[r['Route']] = lf
    return mu


def real_targets():
    t = defaultdict(lambda: {'ARR': 0.0, 'DEP': 0.0})
    for r in csv.DictReader(open(CITYPAIR, encoding='utf-8')):
        if int(r['Year']) != 2025:
            continue
        key = (r['Route'], int(r['Month']))
        t[key]['ARR'] += float(r['PaxArr_toVTZ'] or 0)
        t[key]['DEP'] += float(r['PaxDep_fromVTZ'] or 0)
    return t


def main():
    rng = np.random.default_rng(SEED)
    mus = route_mu()
    targets = real_targets()
    legs = []
    for o in csv.DictReader(open(DAILY, encoding='utf-8')):
        month = int(o['date'][5:7])
        seats = int(o['seat_capacity'])
        for mv, code, tcol in [('ARR', o['origin'], o['arrival_time']),
                               ('DEP', o['destination'], o['departure_time'])]:
            city = CODE2CITY.get(code, '')
            mu = mus.get(city, DEFAULT_MU)
            lf = float(np.clip(rng.normal(mu, LF_SIGMA), LF_MIN, LF_MAX))
            legs.append({'occurrence_id': o['occurrence_id'], 'date': o['date'], 'month': month,
                         'flight_id': o['flight_id'], 'movement_type': mv, 'airline': o['airline'],
                         'route_code': code, 'route_city': city,
                         'scheduled_time': tcol, 'aircraft': o['aircraft'],
                         'seat_capacity': seats, 'traffic_type': o['traffic_type'],
                         'base_pax': seats * lf})

    sim = defaultdict(float)
    for lg in legs:
        if lg['route_city']:
            sim[(lg['route_city'], lg['movement_type'], lg['month'])] += lg['base_pax']

    cols = ['occurrence_id', 'date', 'month', 'flight_id', 'movement_type', 'airline',
            'route_code', 'route_city', 'scheduled_time', 'aircraft', 'seat_capacity',
            'traffic_type', 'passengers', 'load_factor_effective', 'reconciled']
    n_rec = 0
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for lg in legs:
            key = (lg['route_city'], lg['movement_type'], lg['month'])
            tgt = targets.get((lg['route_city'], lg['month']), {}).get(lg['movement_type'], 0) if lg['route_city'] else 0
            s = sim.get(key, 0)
            if tgt > 0 and s > 0:
                factor = float(np.clip(tgt / s, RECON_LO, RECON_HI))     # LIGHT nudge only
                lg['reconciled'] = 'Y'
                n_rec += 1
            else:
                factor = 1.0
                lg['reconciled'] = 'N'
            pax = min(lg['base_pax'] * factor, lg['seat_capacity'] * LF_MAX)
            lg['passengers'] = round(pax)
            lg['load_factor_effective'] = round(pax / lg['seat_capacity'], 3)
            w.writerow(lg)

    lfs = np.array([min(l['base_pax'], l['seat_capacity'] * LF_MAX) / l['seat_capacity'] for l in legs])
    print(f"passenger_estimates.csv: {len(legs):,} legs  ({n_rec:,} lightly reconciled to DGCA)")
    print(f"  per-flight load factor: mean {lfs.mean():.3f}  std {lfs.std():.3f}  (real airline PLF ~0.88 / 0.06)")


if __name__ == '__main__':
    main()
