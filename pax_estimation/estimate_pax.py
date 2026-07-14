# -*- coding: utf-8 -*-
"""Estimate passenger (PAX) demand for Bhogapuram (VTZ) from the flight schedule.

Bhogapuram is a greenfield airport with NO historical passenger data. So we build
the demand bottom-up from the plan, cross-referencing the tables we have — exactly
the "inter-column relation" idea:

    aircraft type  --(seat map)-->   seats           (already in the schedule, col K)
    flight number  --(prefix)------> airline
    airline        --(DGCA/PLF)----> load factor
    seats x load factor            = PAX on that flight
    STA / STD                      = the HOUR it lands / departs
    FREQ (1..7)                    = the DAYS OF WEEK it operates

Departing flights -> boarding PAX (feed departure touchpoints: check-in, security,
emigration). Arriving flights -> deplaning PAX (feed arrival: immigration, belts).

Output: PAX per flight, and a typical-week demand grid by (day-of-week x hour),
plus season totals across the S26 window (2026-03-29 .. 2026-10-24).

Run:  python estimate_pax.py
"""
import csv
import datetime as dt
import os

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
SCHED = os.path.join(HERE, '..', 'data', 'bhogapuram_vtz', 'VTZ_schedule_S26.xlsx')

# IATA Summer 2026 season (last Sun of Mar .. last Sat of Oct)
SEASON_START, SEASON_END = dt.date(2026, 3, 29), dt.date(2026, 10, 24)

# airline (flight-no prefix) -> typical passenger load factor  (DGCA/airline FY26)
LOAD_FACTOR = {'6E': 0.86, 'IX': 0.87, 'AI': 0.83, 'TR': 0.85, 'I7': 0.75}
DEFAULT_LF = 0.80
DOW_NAME = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def airline_of(flt):
    f = str(flt).replace(' ', '')
    for code in ('6E', 'IX', 'AI', 'I7', 'TR'):
        if f.startswith(code):
            return code
    return '?'


def hour_of(t):
    return int(str(t).split(':')[0])


def freq_days(freq):
    """'1246' -> {0,1,3,5} (Mon=0..Sun=6). Digit d (1..7) -> weekday d-1."""
    return {int(ch) - 1 for ch in str(freq) if ch.isdigit() and ch != '0'}


def load_schedule():
    wb = openpyxl.load_workbook(SCHED, data_only=True)
    ws = wb.active
    flights = []
    for r in range(3, ws.max_row + 1):
        sl = ws.cell(r, 1).value
        if not isinstance(sl, int):
            break                                   # reached the legend rows
        seats = ws.cell(r, 11).value
        if not seats:
            continue
        arr_al = airline_of(ws.cell(r, 4).value)
        dep_al = airline_of(ws.cell(r, 7).value)
        flights.append({
            'sl': sl,
            'acft': ws.cell(r, 3).value,
            'seats': int(seats),
            'freq': freq_days(ws.cell(r, 2).value),
            'arr_flt': ws.cell(r, 4).value, 'org': ws.cell(r, 5).value,
            'arr_hour': hour_of(ws.cell(r, 6).value), 'arr_al': arr_al,
            'dep_flt': ws.cell(r, 7).value, 'dest': ws.cell(r, 8).value,
            'dep_hour': hour_of(ws.cell(r, 9).value), 'dep_al': dep_al,
            'intl': str(ws.cell(r, 10).value).strip().upper() == 'INTL',
            'arr_pax': round(int(seats) * LOAD_FACTOR.get(arr_al, DEFAULT_LF)),
            'dep_pax': round(int(seats) * LOAD_FACTOR.get(dep_al, DEFAULT_LF)),
        })
    return flights


def main():
    flights = load_schedule()

    # 1) per-flight PAX table
    with open(os.path.join(HERE, 'pax_per_flight.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['SL', 'Acft', 'Seats', 'ArrFlt', 'ORG', 'ArrHour', 'ArrAirline',
                    'ArrPAX(deplane)', 'DepFlt', 'DEST', 'DepHour', 'DepAirline',
                    'DepPAX(board)', 'INTL', 'DaysPerWeek'])
        for x in flights:
            w.writerow([x['sl'], x['acft'], x['seats'], x['arr_flt'], x['org'],
                        f"{x['arr_hour']:02d}:00", x['arr_al'], x['arr_pax'],
                        x['dep_flt'], x['dest'], f"{x['dep_hour']:02d}:00", x['dep_al'],
                        x['dep_pax'], 'Y' if x['intl'] else '', len(x['freq'])])

    # 2) typical-week demand grid: (dow, hour) -> dep/arr PAX  (one representative week)
    grid_dep = {(d, h): 0 for d in range(7) for h in range(24)}
    grid_arr = {(d, h): 0 for d in range(7) for h in range(24)}
    for x in flights:
        for d in x['freq']:
            grid_dep[(d, x['dep_hour'])] += x['dep_pax']
            grid_arr[(d, x['arr_hour'])] += x['arr_pax']
    with open(os.path.join(HERE, 'demand_by_hour_dow.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['DayOfWeek', 'Hour', 'DepPAX', 'ArrPAX', 'TotalPAX'])
        for d in range(7):
            for h in range(24):
                dep, arr = grid_dep[(d, h)], grid_arr[(d, h)]
                if dep or arr:
                    w.writerow([DOW_NAME[d], f"{h:02d}:00", dep, arr, dep + arr])

    # 3) season expansion + summary
    season_dep = season_arr = 0
    per_dow_dep = [0] * 7
    per_dow_arr = [0] * 7
    day = SEASON_START
    n_days = 0
    while day <= SEASON_END:
        d = day.weekday()
        dd = sum(x['dep_pax'] for x in flights if d in x['freq'])
        aa = sum(x['arr_pax'] for x in flights if d in x['freq'])
        season_dep += dd
        season_arr += aa
        per_dow_dep[d] += dd
        per_dow_arr[d] += aa
        n_days += 1
        day += dt.timedelta(days=1)

    # peak departure & arrival hour on a typical full day (all-7-day flights)
    typ = 2   # Wednesday, a representative weekday
    dep_by_h = [grid_dep[(typ, h)] for h in range(24)]
    arr_by_h = [grid_arr[(typ, h)] for h in range(24)]

    print("=" * 68)
    print("BHOGAPURAM (VTZ) — ESTIMATED PAX DEMAND from S26 schedule")
    print("=" * 68)
    print(f"flights in schedule: {len(flights)}   season: {SEASON_START} .. {SEASON_END} ({n_days} days)")
    print()
    print("Typical-day PAX by day of week (departing / arriving / total):")
    for d in range(7):
        dep = sum(x['dep_pax'] for x in flights if d in x['freq'])
        arr = sum(x['arr_pax'] for x in flights if d in x['freq'])
        nfl = sum(1 for x in flights if d in x['freq'])
        print(f"  {DOW_NAME[d]}  flights={nfl:>2}   dep={dep:>5,}  arr={arr:>5,}  total={dep+arr:>6,}")
    print()
    peak_dh = max(range(24), key=lambda h: dep_by_h[h])
    peak_ah = max(range(24), key=lambda h: arr_by_h[h])
    print(f"Peak DEPARTURE hour (Wed): {peak_dh:02d}:00  ->  {dep_by_h[peak_dh]:,} boarding PAX")
    print(f"Peak ARRIVAL   hour (Wed): {peak_ah:02d}:00  ->  {arr_by_h[peak_ah]:,} deplaning PAX")
    print()
    print(f"SEASON TOTAL  departing: {season_dep:,}   arriving: {season_arr:,}   "
          f"combined: {season_dep + season_arr:,}")
    print(f"  (~{(season_dep + season_arr) // n_days:,} PAX/day average through the terminal)")
    print()
    print("wrote: pax_per_flight.csv, demand_by_hour_dow.csv")


if __name__ == '__main__':
    main()
