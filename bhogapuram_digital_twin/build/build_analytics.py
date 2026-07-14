# -*- coding: utf-8 -*-
"""Phase 5 (data) — KPIs + peak-hour profile from the 5-minute operational dataset.

Outputs (Power BI-ready):
  analytics/kpis.csv        headline metrics + how each was derived
  analytics/peak_hours.csv  typical-day hourly profile per touchpoint (mean across days)
"""
import csv, math, os
from collections import defaultdict
from statistics import mean

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIVE = os.path.join(ROOT, 'generated', 'passenger_5min.csv')
GATE = os.path.join(ROOT, 'generated', 'gate_occupancy.csv')
KPIS = os.path.join(ROOT, 'analytics', 'kpis.csv')
PEAK = os.path.join(ROOT, 'analytics', 'peak_hours.csv')


def main():
    rows = list(csv.DictReader(open(FIVE, encoding='utf-8')))
    def col(c): return [float(r[c]) for r in rows]
    checkin, security, boarding = col('checkin_demand'), col('security_demand'), col('boarding_demand')
    belt, occ = col('belt_demand'), col('terminal_occupancy')
    cc, sl = col('checkin_counters_req'), col('security_lanes_req')
    dep, arr = col('dep_flights'), col('arr_flights')

    # per-day totals (throughput) and per-hour profile
    day_pax = defaultdict(float)
    hour = defaultdict(lambda: defaultdict(list))
    for r in rows:
        ts = r['timestamp']; d = ts[:10]; h = int(ts[11:13])
        thru = float(r['checkin_demand']) + float(r['belt_demand'])   # proxy throughput
        day_pax[d] += float(r['boarding_demand']) + float(r['belt_demand'])
        for k in ('checkin_demand', 'security_demand', 'boarding_demand', 'belt_demand',
                  'terminal_occupancy', 'checkin_counters_req', 'security_lanes_req'):
            hour[h][k].append(float(r[k]))

    onground = [int(r['aircraft_on_ground']) for r in csv.DictReader(open(GATE, encoding='utf-8'))]
    busiest_day = max(day_pax, key=day_pax.get)

    def peak_at(vals):
        i = max(range(len(vals)), key=lambda k: vals[k])
        return round(vals[i]), rows[i]['timestamp']

    kpis = []
    pc, tc = peak_at(checkin); kpis.append(('Peak check-in demand', pc, 'pax / 5 min', tc, 'max of checkin_demand'))
    ps, tsx = peak_at(security); kpis.append(('Peak security demand', ps, 'pax / 5 min', tsx, 'max of security_demand'))
    pb, tb = peak_at(boarding); kpis.append(('Peak boarding demand', pb, 'pax / 5 min', tb, 'max of boarding_demand'))
    po, to = peak_at(occ); kpis.append(('Peak terminal occupancy', po, 'passengers', to, 'max of terminal_occupancy'))
    kpis.append(('Peak check-in counters required', int(max(cc)), 'counters', '', 'ceil(demand / 6 pax per 5min)'))
    kpis.append(('Peak security lanes required', int(max(sl)), 'lanes', '', 'ceil(demand / 12 pax per 5min)'))
    kpis.append(('Peak aircraft on ground', max(onground), 'aircraft', '', 'max concurrent rotations on stand'))
    kpis.append(('Busiest day', busiest_day, 'date', '', 'max daily boarding+belt pax'))
    kpis.append(('Avg daily passengers (dep+arr)', round(mean(day_pax.values())), 'pax / day', '', 'mean of daily throughput'))
    # peak clock hour by total processing demand
    hour_tot = {h: mean(hour[h]['checkin_demand']) + mean(hour[h]['security_demand']) for h in hour}
    ph = max(hour_tot, key=hour_tot.get)
    kpis.append(('Peak hour of day', f"{ph:02d}:00", 'clock hour', '', 'hour with max mean check-in+security demand'))

    with open(KPIS, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['metric', 'value', 'unit', 'when', 'method'])
        w.writerows(kpis)

    with open(PEAK, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['hour', 'checkin_demand', 'security_demand', 'boarding_demand',
                    'belt_demand', 'terminal_occupancy', 'checkin_counters', 'security_lanes'])
        for h in range(24):
            if h in hour:
                m = lambda k: round(mean(hour[h][k]), 1)
                w.writerow([f"{h:02d}:00", m('checkin_demand'), m('security_demand'), m('boarding_demand'),
                            m('belt_demand'), m('terminal_occupancy'),
                            math.ceil(mean(hour[h]['checkin_counters_req'])), math.ceil(mean(hour[h]['security_lanes_req']))])

    print("analytics built:")
    for k in kpis:
        print(f"  {k[0]:<34} {k[1]} {k[2]}" + (f"  @ {k[3]}" if k[3] else ""))


if __name__ == '__main__':
    main()
