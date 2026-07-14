# -*- coding: utf-8 -*-
"""Route profile: attach airline + aircraft (from the schedule) to each VTZ route,
join the REAL DGCA monthly passengers, and derive the real load factor.

  airline + aircraft + scheduled seats  ← VTZ_schedule_S26.xlsx (who flies the route)
  real monthly passengers               ← vtz_citypair_monthly.csv (DGCA, Dec-2025)
  load factor = real pax / scheduled monthly seats

Run from this folder:  python route_profile.py  -> ../data/bhogapuram_vtz/vtz_route_profile.csv
"""
import csv, os
from collections import defaultdict
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data', 'bhogapuram_vtz')
SCHED = os.path.join(DATA, 'VTZ_schedule_S26.xlsx')
CITYPAIR = os.path.join(DATA, 'vtz_citypair_monthly.csv')
OUT = os.path.join(DATA, 'vtz_route_profile.csv')
YEAR, MONTH = 2025, 12                      # latest complete DGCA month

CODE2CITY = {'HYD': 'Hyderabad', 'DEL': 'Delhi', 'BLR': 'Bengaluru', 'MAA': 'Chennai',
             'BOM': 'Mumbai', 'NMI': 'Mumbai', 'CCU': 'Kolkata', 'VGA': 'Vijayawada',
             'TIR': 'Tirupati', 'KJB': 'Kurnool', 'PYB': 'Jeypore', 'BBI': 'Bhubaneswar'}
AIRLINE = {'6E': 'IndiGo (6E)', 'IX': 'Air India Express (IX)', 'AI': 'Air India (AI)',
           'TR': 'Scoot (TR)', 'I7': 'Alliance/regional (I7)'}


def al(f):
    f = str(f).replace(' ', '')
    for c in ('6E', 'IX', 'AI', 'I7', 'TR'):
        if f.startswith(c):
            return c
    return '?'


def days(fr):
    return sum(1 for c in str(fr) if c.isdigit() and c != '0')


def main():
    ws = openpyxl.load_workbook(SCHED, data_only=True).active
    prof = defaultdict(lambda: {'airlines': set(), 'acft': set(), 'mv': 0, 'seats': 0})
    for r in range(3, ws.max_row + 1):
        sl = ws.cell(r, 1).value
        if not isinstance(sl, int):
            break
        seats = ws.cell(r, 11).value
        if not seats:
            continue
        seats = int(seats); acft = str(ws.cell(r, 3).value).strip(); fr = days(ws.cell(r, 2).value)
        for code, alcol in [(ws.cell(r, 5).value, ws.cell(r, 4).value),
                            (ws.cell(r, 8).value, ws.cell(r, 7).value)]:
            city = CODE2CITY.get(str(code).strip().upper())
            if not city:
                continue
            p = prof[city]
            p['airlines'].add(AIRLINE.get(al(alcol), al(alcol)))
            p['acft'].add(acft)
            p['mv'] += fr
            p['seats'] += seats * fr

    realpax = defaultdict(float)
    for r in csv.DictReader(open(CITYPAIR, encoding='utf-8')):
        if int(r['Year']) == YEAR and int(r['Month']) == MONTH:
            realpax[r['Route']] += float(r['PaxTotal'] or 0)

    out = []
    for city, p in prof.items():
        mo_seats = p['seats'] * 4.345
        rp = realpax.get(city, 0)
        lf = round(rp / mo_seats * 100, 1) if mo_seats else 0
        note = 'schedule under-captures this route (LF>100 impossible)' if lf > 100 else ''
        out.append([city, ', '.join(sorted(p['airlines'])), ', '.join(sorted(p['acft'])),
                    p['mv'], int(p['seats']), int(mo_seats), int(rp), lf, note])
    out.sort(key=lambda x: -x[6])
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Route', 'Airlines', 'AircraftTypes', 'WeeklyMovements', 'WeeklySeats',
                    'MonthlySeats_est', 'RealPax_Dec2025', 'ImpliedLoadFactor_pct', 'Note'])
        w.writerows(out)
    print(f"wrote {OUT}  ({len(out)} routes)")
    for x in out:
        print(f"  {x[0]:<13}{x[1]:<36}{x[2]:<22}{x[6]:>9,} pax  LF={x[7]}%")


if __name__ == '__main__':
    main()
