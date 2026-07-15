# -*- coding: utf-8 -*-
"""Phase 3 + 4 — Passenger behaviour -> 5-minute operational (EWS-style) dataset.

Phase 3 (behaviour): each flight's passengers don't appear at departure time; they
flow through the terminal over configurable windows before STD:
  check-in  -150..-45 min   security -95..-25 min   boarding -30..-8 min
Arrivals hit baggage belts +5..+35 min after STA. Windows are TUNABLE below.

Phase 4 (EWS): distribute each leg's reconciled passengers across those windows into
5-minute buckets for the whole S26 season, and add terminal occupancy, aircraft on
ground, and counters/lanes required from service-rate assumptions.

Input:  generated/passenger_estimates.csv, generated/Daily_Flights.csv
Output: generated/passenger_5min.csv, generated/gate_occupancy.csv

Clearly SIMULATED planning data — real passenger volumes (reconciled), modelled flow.
"""
import csv, datetime as dt, math, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAX = os.path.join(ROOT, 'generated', 'passenger_estimates.csv')
DAILY = os.path.join(ROOT, 'generated', 'Daily_Flights.csv')
OUT5 = os.path.join(ROOT, 'generated', 'passenger_5min.csv')
OUTGATE = os.path.join(ROOT, 'generated', 'gate_occupancy.csv')

SEASON_START = dt.datetime(2026, 3, 29)
SEASON_END = dt.datetime(2026, 10, 24, 23, 55)
STEP = 5
TOTAL = int((SEASON_END - SEASON_START).total_seconds() // 60 // STEP) + 1

# --- Phase 3 behaviour config (minutes relative to scheduled time; TUNABLE) -------
DEP_STAGES = {                       # stage: (win_start, win_end, peak)  [min before STD]
    'checkin':  (-150, -45, -90),
    'security': (-95, -25, -55),
    'boarding': (-30, -8, -18),
}
DEP_ENTER = (-150, -40, -85)         # when pax enter the terminal (landside)
DEP_EXIT = -10                       # when pax leave landside (boarded)
ARR_BELT = (5, 35, 18)               # baggage belt demand after STA
ARR_EXIT = 45                        # arrivals clear the terminal
# --- service-rate assumptions (pax handled per 5 min per unit; TUNABLE) -----------
CHECKIN_PER_5MIN = 6                  # ~72 pax/hr per check-in counter
SECURITY_PER_5MIN = 12               # ~144 pax/hr per security lane


def slot_of(day_offset_min):
    return int(round(day_offset_min / STEP))


def tri(x, a, b, c):
    if x < a or x > b:
        return 0.0
    return (x - a) / (c - a) if x <= c else (b - x) / (b - c)


def spread(arr, base_min, P, win, sign):
    """Add P passengers spread triangularly over a window into 5-min slots."""
    a, b, c = win
    s0 = slot_of(base_min + sign * (a if sign > 0 else b) if False else base_min + a * 1)
    lo = slot_of(base_min + a); hi = slot_of(base_min + b)
    weights = []
    for s in range(lo, hi + 1):
        rel = s * STEP - base_min
        weights.append((s, tri(rel, a, b, c)))
    tot = sum(w for _, w in weights)
    if tot <= 0:
        return
    for s, w in weights:
        if 0 <= s < TOTAL:
            arr[s] += P * w / tot


def main():
    checkin = [0.0] * TOTAL; security = [0.0] * TOTAL; boarding = [0.0] * TOTAL
    belt = [0.0] * TOTAL
    entry = [0.0] * TOTAL; exit_ = [0.0] * TOTAL
    dep_fl = [0] * TOTAL; arr_fl = [0] * TOTAL

    for lg in csv.DictReader(open(PAX, encoding='utf-8')):
        d = dt.date.fromisoformat(lg['date'])
        hh, mm = map(int, lg['scheduled_time'].split(':'))
        base_min = ((dt.datetime(d.year, d.month, d.day, hh, mm) - SEASON_START).total_seconds()) / 60
        P = float(lg['passengers'])
        s_sched = slot_of(base_min)
        if lg['movement_type'] == 'DEP':
            if 0 <= s_sched < TOTAL:
                dep_fl[s_sched] += 1
            spread(checkin, base_min, P, DEP_STAGES['checkin'], -1)
            spread(security, base_min, P, DEP_STAGES['security'], -1)
            spread(boarding, base_min, P, DEP_STAGES['boarding'], -1)
            spread(entry, base_min, P, DEP_ENTER, -1)
            se = slot_of(base_min + DEP_EXIT)
            if 0 <= se < TOTAL:
                exit_[se] += P
        else:  # ARR
            if 0 <= s_sched < TOTAL:
                arr_fl[s_sched] += 1
            spread(belt, base_min, P, ARR_BELT, 1)
            if 0 <= s_sched < TOTAL:
                entry[s_sched] += P
            se = slot_of(base_min + ARR_EXIT)
            if 0 <= se < TOTAL:
                exit_[se] += P

    # terminal occupancy = running (entries - exits), reset each day (terminal empties
    # overnight, so this avoids cross-day drift from boundary clipping)
    SLOTS_DAY = 288
    occ = [0.0] * TOTAL
    run = 0.0
    for i in range(TOTAL):
        if i % SLOTS_DAY == 0:
            run = 0.0
        run += entry[i] - exit_[i]
        occ[i] = max(0.0, run)

    # gate / stand occupancy: aircraft on ground = rotations with STA<=t<=STD (same day)
    onground = [0] * TOTAL
    for o in csv.DictReader(open(DAILY, encoding='utf-8')):
        d = dt.date.fromisoformat(o['date'])
        ah, am = map(int, o['arrival_time'].split(':'))
        dh, dm = map(int, o['departure_time'].split(':'))
        a0 = slot_of(((dt.datetime(d.year, d.month, d.day, ah, am) - SEASON_START).total_seconds()) / 60)
        d0 = slot_of(((dt.datetime(d.year, d.month, d.day, dh, dm) - SEASON_START).total_seconds()) / 60)
        if d0 < a0:  # overnight guard
            d0 = a0
        for s in range(max(0, a0), min(TOTAL, d0 + 1)):
            onground[s] += 1

    with open(OUT5, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['timestamp', 'dep_flights', 'arr_flights', 'checkin_demand', 'security_demand',
                    'boarding_demand', 'belt_demand', 'terminal_occupancy',
                    'checkin_counters_req', 'security_lanes_req'])
        for i in range(TOTAL):
            ci, se = checkin[i], security[i]
            # write only slots with any activity to keep the file lean
            if (ci or se or boarding[i] or belt[i] or occ[i] or dep_fl[i] or arr_fl[i]):
                ts = (SEASON_START + dt.timedelta(minutes=i * STEP)).strftime('%Y-%m-%d %H:%M')
                ci_r, se_r = round(ci), round(se)          # counters must derive from the SHOWN demand
                w.writerow([ts, dep_fl[i], arr_fl[i], ci_r, se_r, round(boarding[i]),
                            round(belt[i]), round(occ[i]), math.ceil(ci_r / CHECKIN_PER_5MIN),
                            math.ceil(se_r / SECURITY_PER_5MIN)])

    with open(OUTGATE, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['timestamp', 'aircraft_on_ground'])
        for i in range(TOTAL):
            if onground[i]:
                ts = (SEASON_START + dt.timedelta(minutes=i * STEP)).strftime('%Y-%m-%d %H:%M')
                w.writerow([ts, onground[i]])

    nz = sum(1 for i in range(TOTAL) if checkin[i] or security[i] or boarding[i] or belt[i] or occ[i])
    print(f"passenger_5min.csv: {nz:,} active 5-min slots over the S26 season")
    print(f"  peak check-in demand / 5min: {round(max(checkin)):,}  -> {math.ceil(max(checkin)/CHECKIN_PER_5MIN)} counters")
    print(f"  peak security demand / 5min: {round(max(security)):,}  -> {math.ceil(max(security)/SECURITY_PER_5MIN)} lanes")
    print(f"  peak terminal occupancy:     {round(max(occ)):,} passengers")
    print(f"  peak aircraft on ground:     {max(onground)}")


if __name__ == '__main__':
    main()
