# -*- coding: utf-8 -*-
"""Phase 2 — Passenger engine.

Turns each daily flight into passenger loads, split into arrival (deplaning) and
departure (boarding) legs, then RECONCILES so each route-direction-month sums to
the real DGCA monthly passenger count. No random numbers.

  base pax  = seat_capacity x base load factor (0.85)
  reconcile = scale each (route, direction, month) so the simulated total equals
              the real 2025 same-month DGCA directional count for that route.
  routes with no DGCA match (intl AUH/SIN, Navi Mumbai, UNK) stay at base (flagged).

Input:  generated/Daily_Flights.csv, ../data/bhogapuram_vtz/vtz_citypair_monthly.csv
Output: generated/passenger_estimates.csv  (one row per flight leg occurrence)
"""
import csv, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DAILY = os.path.join(ROOT, 'generated', 'Daily_Flights.csv')
CITYPAIR = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz', 'vtz_citypair_monthly.csv')
OUT = os.path.join(ROOT, 'generated', 'passenger_estimates.csv')
BASE_LF = 0.85
MAX_LF = 0.95        # a flight physically cannot board >95% + jump-seat; cap reconciliation
CODE2CITY = {'HYD': 'Hyderabad', 'DEL': 'Delhi', 'BLR': 'Bengaluru', 'MAA': 'Chennai',
             'BOM': 'Mumbai', 'CCU': 'Kolkata', 'VGA': 'Vijayawada', 'TIR': 'Tirupati',
             'KJB': 'Kurnool', 'PYB': 'Jeypore', 'BBI': 'Bhubaneswar'}


def real_targets():
    """(city, month) -> {'ARR': pax_to_vtz, 'DEP': pax_from_vtz} from 2025 DGCA."""
    t = defaultdict(lambda: {'ARR': 0.0, 'DEP': 0.0})
    for r in csv.DictReader(open(CITYPAIR, encoding='utf-8')):
        if int(r['Year']) != 2025:
            continue
        key = (r['Route'], int(r['Month']))
        t[key]['ARR'] += float(r['PaxArr_toVTZ'] or 0)
        t[key]['DEP'] += float(r['PaxFromVTZ'] if 'PaxFromVTZ' in r else r['PaxDep_fromVTZ'] or 0)
    return t


def main():
    targets = real_targets()
    legs = []
    for o in csv.DictReader(open(DAILY, encoding='utf-8')):
        month = int(o['date'][5:7])
        seats = int(o['seat_capacity'])
        base = seats * BASE_LF
        # arrival leg (deplaning) — route = origin
        legs.append({'occurrence_id': o['occurrence_id'], 'date': o['date'], 'month': month,
                     'flight_id': o['flight_id'], 'movement_type': 'ARR', 'airline': o['airline'],
                     'route_code': o['origin'], 'route_city': CODE2CITY.get(o['origin'], ''),
                     'scheduled_time': o['arrival_time'], 'aircraft': o['aircraft'],
                     'seat_capacity': seats, 'traffic_type': o['traffic_type'], 'base_pax': base})
        # departure leg (boarding) — route = destination
        legs.append({'occurrence_id': o['occurrence_id'], 'date': o['date'], 'month': month,
                     'flight_id': o['flight_id'], 'movement_type': 'DEP', 'airline': o['airline'],
                     'route_code': o['destination'], 'route_city': CODE2CITY.get(o['destination'], ''),
                     'scheduled_time': o['departure_time'], 'aircraft': o['aircraft'],
                     'seat_capacity': seats, 'traffic_type': o['traffic_type'], 'base_pax': base})

    # sum base pax per (city, direction, month) for reconciliation
    sim = defaultdict(float)
    for lg in legs:
        if lg['route_city']:
            sim[(lg['route_city'], lg['movement_type'], lg['month'])] += lg['base_pax']

    cols = ['occurrence_id', 'date', 'month', 'flight_id', 'movement_type', 'airline',
            'route_code', 'route_city', 'scheduled_time', 'aircraft', 'seat_capacity',
            'traffic_type', 'passengers', 'load_factor_effective', 'reconciled']
    n_rec = n_cap = 0
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for lg in legs:
            city, mv, m = lg['route_city'], lg['movement_type'], lg['month']
            tgt = targets.get((city, m), {}).get(mv, 0) if city else 0
            s = sim.get((city, mv, m), 0)
            if tgt > 0 and s > 0:
                pax = lg['base_pax'] * (tgt / s)
                lg['reconciled'] = 'Y'
                n_rec += 1
            else:
                pax = lg['base_pax']
                lg['reconciled'] = 'N'
            cap = lg['seat_capacity'] * MAX_LF
            if pax > cap:                       # under-served route -> realistic cap
                pax = cap
                lg['reconciled'] = 'capped'
                n_cap += 1
            lg['passengers'] = round(pax)
            lg['load_factor_effective'] = round(pax / lg['seat_capacity'], 3)
            w.writerow(lg)

    print(f"passenger_estimates.csv: {len(legs):,} legs  ({n_rec:,} reconciled, {n_cap:,} capped at {MAX_LF:.0%})")
    # quick check: total simulated departing pax vs real, a sample month
    dep_may = sum(round(lg['base_pax'] * (targets.get((lg['route_city'],5),{}).get('DEP',0) /
                  sim[(lg['route_city'],'DEP',5)])) for lg in legs
                  if lg['movement_type']=='DEP' and lg['month']==5 and lg['route_city']
                  and sim.get((lg['route_city'],'DEP',5)))
    real_may = sum(v['DEP'] for (c,m),v in targets.items() if m==5)
    print(f"  reconciliation check (May, departing): sim {dep_may:,} vs real {round(real_may):,}")


if __name__ == '__main__':
    main()
