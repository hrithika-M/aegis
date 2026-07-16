# -*- coding: utf-8 -*-
"""POD on the day of COD — the Plan of the Day for Commercial Operations Date.

Meeting requirement (Bhogapuram, Jul-2026): "POD on the day of COD" and
"peak hours — no. of passengers, number of staff and lanes".

Produces the hour-by-hour operating plan for COD (2026-07-08, the announced
commercial-operations date) from the twin: expected passengers per touchpoint,
check-in counters, security lanes, and STAFF per hour.

STAFFING ASSUMPTIONS (flagged in QUESTIONNAIRE.md for validation with ops):
  check-in : 1.2 staff per open counter   (agents + supervision share)
  security : 4.0 staff per open lane      (typical Indian-airport lane crew:
                                           DFMD/frisking, x-ray operator, bag
                                           search, queue marshal)

Outputs:
  analytics/pod_cod.csv          hourly plan (pax, counters, lanes, staff)
  analytics/pod_cod_flights.csv  the COD flight list with expected pax
Run:  python build_pod_cod.py
"""
import csv, math, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COD = '2026-07-08'
FIVE = os.path.join(ROOT, 'generated', 'passenger_5min.csv')
PAX = os.path.join(ROOT, 'generated', 'passenger_estimates.csv')
OUT_H = os.path.join(ROOT, 'analytics', 'pod_cod.csv')
OUT_F = os.path.join(ROOT, 'analytics', 'pod_cod_flights.csv')

STAFF_PER_COUNTER = 1.2
STAFF_PER_LANE = 4.0


def main():
    # hourly plan from the 5-min dataset, COD only
    hour = defaultdict(lambda: defaultdict(float))
    for r in csv.DictReader(open(FIVE, encoding='utf-8')):
        if not r['timestamp'].startswith(COD):
            continue
        h = int(r['timestamp'][11:13])
        for k in ('checkin_demand', 'security_demand', 'boarding_demand', 'belt_demand',
                  'terminal_occupancy'):
            hour[h][k] += float(r[k]) if k != 'terminal_occupancy' else 0
        hour[h]['occ_max'] = max(hour[h]['occ_max'], float(r['terminal_occupancy']))
        hour[h]['counters'] = max(hour[h]['counters'], float(r['checkin_counters_req']))
        hour[h]['lanes'] = max(hour[h]['lanes'], float(r['security_lanes_req']))

    rows = []
    for h in sorted(hour):
        d = hour[h]
        counters, lanes = int(d['counters']), int(d['lanes'])
        rows.append([f"{h:02d}:00",
                     round(d['checkin_demand']), round(d['security_demand']),
                     round(d['boarding_demand']), round(d['belt_demand']),
                     round(d['occ_max']), counters, lanes,
                     math.ceil(counters * STAFF_PER_COUNTER),
                     math.ceil(lanes * STAFF_PER_LANE),
                     math.ceil(counters * STAFF_PER_COUNTER) + math.ceil(lanes * STAFF_PER_LANE)])
    with open(OUT_H, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['hour', 'checkin_pax', 'security_pax', 'boarding_pax', 'belt_pax',
                    'peak_occupancy', 'checkin_counters', 'security_lanes',
                    'checkin_staff', 'security_staff', 'total_staff'])
        w.writerows(rows)

    # flight list for COD with expected pax
    fl = [r for r in csv.DictReader(open(PAX, encoding='utf-8')) if r['date'] == COD]
    with open(OUT_F, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['movement', 'time', 'airline', 'route', 'aircraft', 'seats',
                    'expected_pax', 'load_factor'])
        for r in sorted(fl, key=lambda x: x['scheduled_time']):
            w.writerow([r['movement_type'], r['scheduled_time'], r['airline'],
                        r['route_city'] or r['route_code'], r['aircraft'],
                        r['seat_capacity'], r['passengers'], r['load_factor_effective']])

    tot_dep = sum(int(r['passengers']) for r in fl if r['movement_type'] == 'DEP')
    tot_arr = sum(int(r['passengers']) for r in fl if r['movement_type'] == 'ARR')
    peak = max(rows, key=lambda r: r[1] + r[2])
    print(f"POD for COD {COD} (Wed) — {len(fl)//2} rotations, "
          f"{tot_dep:,} departing + {tot_arr:,} arriving expected pax")
    print(f"  peak processing hour {peak[0]}: {peak[1]} check-in pax, {peak[2]} security pax "
          f"-> {peak[6]} counters + {peak[7]} lanes, {peak[10]} touchpoint staff")
    print(f"  wrote {os.path.relpath(OUT_H, ROOT)}, {os.path.relpath(OUT_F, ROOT)}")
    print("  staffing ratios are ASSUMPTIONS pending ops validation (QUESTIONNAIRE.md)")


if __name__ == '__main__':
    main()
