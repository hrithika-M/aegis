# -*- coding: utf-8 -*-
"""POD2 - Step 6: build the FINALISED Entry dataset (Bhogapuram / VTZ).

This is the deliverable to take to Avra. It is a pure, auditable CALCULATION - no ML -
using Avra's construct and the two recalibrations we found in Step 5:

  RECAL 1 (load factor):  passengers = seat_capacity x LF[category, day_of_week]
                          LF is the REAL June actual by category & day-of-week
                          (fixes the twin's flat ~78%; now Mon 78% .. Sun 88% for C).
  RECAL 2 (show-up):      passengers are distributed to terminal-entry time using the
                          MEASURED e-boarding show-up buckets (Step 3), not a triangle
                          (fixes the missing >150-min tail).

Then the Avra-style touchpoint columns:
  entry_demand_5min[t]   pax entering the terminal in each 5-min slot
  entry_demand_30min[t]  forward 30-min projection (Avra's 30-min touchpoint view)
  lanes_required[t]      ceil(entry_demand_30min / 60)   [ATRS 120 pax/hr/lane = 60/30min]

Basis: the VTZ S26 schedule (Daily_Flights.csv). Entry = DEParting pax (landside entry).

Inputs : POD2/step1_june_data/june_load_daily.csv          (real LF)
         POD2/step3_ews_eboarding/entry_showup_profile.csv (measured show-up %)
         bhogapuram_digital_twin/generated/Daily_Flights.csv (VTZ schedule)
Outputs: finalised_entry_daily_summary.csv, finalised_entry_sample_day.csv
Run    : python build_entry_pod.py
"""
import csv, math, os, statistics as st
import datetime as dt
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
JUNE = os.path.join(ROOT, 'step1_june_data', 'june_load_daily.csv')
SHOWUP = os.path.join(ROOT, 'step3_ews_eboarding', 'entry_showup_profile.csv')
SCHED = os.path.join(ROOT, os.pardir, 'bhogapuram_digital_twin', 'generated', 'Daily_Flights.csv')

STEP = 5
SLOTS = 24 * 60 // STEP                      # 288 slots per day
LANE_PER_30MIN = 60                          # 120 pax/hr/lane -> 60 pax/30min/lane (Avra)
# show-up bucket -> minute range it is spread across (uniform), min before departure
BUCKET_RANGE = {'<60': (30, 60), '60-90': (60, 90), '90-120': (90, 120),
                '120-150': (120, 150), '150-180': (150, 180), '>180': (180, 240)}


def cat_of(ac):
    if ac.startswith('ATR'): return 'B'
    if 'Cessna' in ac or '208' in ac: return 'A'
    return 'C'


def load_lf():
    """Real June DEP load factor by (category, day_of_week); fall back to category mean."""
    by = defaultdict(list); byc = defaultdict(list)
    for r in csv.DictReader(open(JUNE, encoding='utf-8')):
        if r['direction'] != 'DEP' or float(r['pax']) <= 0:
            continue
        lf = float(r['load_factor'])
        by[(r['category'], r['day_of_week'])].append(lf); byc[r['category']].append(lf)
    lf = {}
    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for c in byc:
        for d in dows:
            v = by.get((c, d))
            lf[(c, d)] = st.mean(v) if v else st.mean(byc[c])
    return lf


def load_showup_weights():
    """Measured show-up %, spread uniformly over each bucket's minute range into 5-min
    offsets. Returns {offset_min: weight} normalised to sum 1."""
    pct = {}
    for r in csv.DictReader(open(SHOWUP, encoding='utf-8')):
        pct[r['bucket']] = float(r['pct'])
    w = defaultdict(float)
    for b, (lo, hi) in BUCKET_RANGE.items():
        offs = list(range(lo, hi, STEP))
        share = (pct.get(b, 0) / 100.0) / len(offs)
        for o in offs:
            w[o] += share
    tot = sum(w.values())
    return {o: v / tot for o, v in w.items()}


def main():
    lf = load_lf()
    weights = load_showup_weights()

    demand = defaultdict(lambda: [0.0] * SLOTS)      # date -> 5-min entry demand
    pax_by_date = defaultdict(float)
    n_flights = 0
    for r in csv.DictReader(open(SCHED, encoding='utf-8')):
        dep = r.get('departure_time', '').strip()
        if not dep or ':' not in dep:                # skip arrival-only rotations
            continue
        n_flights += 1
        c = cat_of(r['aircraft']); dow = r['day_of_week']
        dowfull = {'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday', 'Thu': 'Thursday',
                   'Fri': 'Friday', 'Sat': 'Saturday', 'Sun': 'Sunday'}.get(dow, dow)
        seats = float(r['seat_capacity'])
        P = seats * lf.get((c, dowfull), st.mean([v for (cc, _), v in lf.items() if cc == c]))
        pax_by_date[r['date']] += P
        hh, mm = map(int, dep.split(':'))
        dep_min = hh * 60 + mm
        for off, wgt in weights.items():
            ent = dep_min - off
            if ent < 0:                              # entry before midnight -> clamp to day start
                ent = 0
            demand[r['date']][ent // STEP] += P * wgt

    # per-day summary: total pax, peak 30-min demand, peak lanes, peak time
    daily = []
    sample = None; sample_peak = -1
    for d in sorted(demand):
        dem = demand[d]
        dem30 = [sum(dem[i:i + 6]) for i in range(SLOTS)]        # forward 30-min projection
        lanes = [math.ceil(x / LANE_PER_30MIN) for x in dem30]
        pk = max(range(SLOTS), key=lambda i: dem30[i])
        daily.append({'date': d, 'day_of_week': None,
                      'entry_pax': round(pax_by_date[d]),
                      'peak_30min_demand': round(dem30[pk]),
                      'peak_lanes_required': lanes[pk],
                      'peak_time': f"{(pk*STEP)//60:02d}:{(pk*STEP)%60:02d}"})
        if dem30[pk] > sample_peak:
            sample_peak = dem30[pk]; sample = (d, dem, dem30, lanes)

    with open(os.path.join(HERE, 'finalised_entry_daily_summary.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'entry_pax', 'peak_30min_demand',
                                          'peak_lanes_required', 'peak_time'])
        w.writeheader()
        for row in daily:
            row.pop('day_of_week')
            w.writerow(row)

    # busiest-day 5-min profile so Avra can see the shape
    d, dem, dem30, lanes = sample
    with open(os.path.join(HERE, 'finalised_entry_sample_day.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['date', 'time', 'entry_demand_5min', 'entry_demand_30min', 'lanes_required'])
        for i in range(SLOTS):
            t = f"{(i*STEP)//60:02d}:{(i*STEP)%60:02d}"
            w.writerow([d, t, round(dem[i], 1), round(dem30[i], 1), lanes[i]])

    tot_pax = sum(pax_by_date.values())
    print(f"flights (DEP): {n_flights:,}   season entry pax: {tot_pax:,.0f}   days: {len(daily)}")
    print(f"LF applied: real June by (category, day-of-week); show-up: measured e-boarding buckets")
    pk_lanes = max(r['peak_lanes_required'] for r in daily)
    busy = max(daily, key=lambda r: r['peak_30min_demand'])
    print(f"season peak lanes required (any day): {pk_lanes}")
    print(f"busiest day {busy['date']}: {busy['entry_pax']:,} entry pax, "
          f"peak 30-min demand {busy['peak_30min_demand']:,} at {busy['peak_time']}, "
          f"{busy['peak_lanes_required']} lanes")


if __name__ == '__main__':
    main()
