# -*- coding: utf-8 -*-
"""Scenario engine — what-if analysis with a queue model.

The base twin reports demand and "counters required". Planners need the inverse:
given a FIXED number of counters/lanes, what happens under stress? This applies
scenario levers (demand multiplier, servers open/closed) to the busiest day and runs
a deterministic bucket queue to get queue length, wait time, and SLA breaches.

Queue model (standard terminal cumulative-diagram / fluid approximation):
    queue[t] = max(0, queue[t-1] + arrivals[t] - capacity[t])
    capacity  = servers x service_rate (pax / 5 min)
    wait[t]   ~ queue[t] x 5 / capacity   (minutes; Little's-law style)

Scenarios are config below — add rows freely.

Run:  python scenario_engine.py  ->  analytics/scenarios.csv
"""
import csv, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIVE = os.path.join(ROOT, 'generated', 'passenger_5min.csv')
OUT = os.path.join(ROOT, 'analytics', 'scenarios.csv')

RATE = {'checkin': 6, 'security': 12}          # pax served / 5 min / server
SLA_MIN = {'checkin': 20, 'security': 15}      # acceptable max wait (minutes)

# scenario: (name, demand_multiplier, {touchpoint: servers_open})
SCENARIOS = [
    ('baseline',                      1.0, {'checkin': 10, 'security': 6}),
    ('demand +20%',                   1.2, {'checkin': 10, 'security': 6}),
    ('2 security lanes closed',       1.0, {'checkin': 10, 'security': 4}),
    ('surge +20% & 2 lanes closed',   1.2, {'checkin': 10, 'security': 4}),
    ('festival rush +40%',            1.4, {'checkin': 10, 'security': 6}),
    ('security down to 3 lanes',      1.0, {'checkin': 10, 'security': 3}),
    ('major disruption +60%, 3 lanes', 1.6, {'checkin': 8, 'security': 3}),
    ('worst case +80%, skeleton crew', 1.8, {'checkin': 6, 'security': 3}),
]


def busiest_day_demand():
    """Return {touchpoint: [demand per 5-min slot]} for the busiest day."""
    by_day = defaultdict(lambda: defaultdict(dict))
    day_tot = defaultdict(float)
    for r in csv.DictReader(open(FIVE, encoding='utf-8')):
        d, t = r['timestamp'][:10], r['timestamp'][11:16]
        for tp, col in (('checkin', 'checkin_demand'), ('security', 'security_demand')):
            by_day[d][tp][t] = float(r[col])
        day_tot[d] += float(r['checkin_demand']) + float(r['security_demand'])
    day = max(day_tot, key=day_tot.get)
    slots = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 5)]
    return day, {tp: [by_day[day][tp].get(s, 0.0) for s in slots] for tp in RATE}


def run_queue(arrivals, servers, rate, mult):
    cap = servers * rate
    q = 0.0
    peak_q, max_wait, slots_breach, sla = 0.0, 0.0, 0, None
    waits = []
    for a in arrivals:
        q = max(0.0, q + a * mult - cap)
        peak_q = max(peak_q, q)
        wait = (q * 5 / cap) if cap > 0 else float('inf')
        waits.append(wait)
        max_wait = max(max_wait, wait)
    return peak_q, max_wait, waits


def main():
    day, demand = busiest_day_demand()
    rows = []
    print("=" * 90)
    print(f"SCENARIO ENGINE — queue impact on the busiest day ({day})")
    print("=" * 90)
    print(f"  {'Scenario':<34}{'Touchpoint':<10}{'servers':>8}{'peakQ':>8}{'maxWait':>9}{'SLA':>8}")
    for name, mult, servers in SCENARIOS:
        for tp in ('checkin', 'security'):
            peak_q, max_wait, _ = run_queue(demand[tp], servers[tp], RATE[tp], mult)
            ok = 'OK' if max_wait <= SLA_MIN[tp] else 'BREACH'
            rows.append([name, tp, servers[tp], round(mult, 2), round(peak_q), round(max_wait, 1),
                         SLA_MIN[tp], ok])
            print(f"  {name:<34}{tp:<10}{servers[tp]:>8}{round(peak_q):>8}{round(max_wait, 1):>9}{ok:>8}")
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['scenario', 'touchpoint', 'servers_open', 'demand_multiplier',
                    'peak_queue_pax', 'max_wait_min', 'sla_min', 'verdict'])
        w.writerows(rows)
    print("-" * 90)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print("Read: BREACH = max wait exceeds the SLA -> that config understaffs under that scenario.")


if __name__ == '__main__':
    main()
