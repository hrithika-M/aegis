# -*- coding: utf-8 -*-
"""POD2 - Step 6 (detailed): finalised Entry dataset as a FLIGHT-LEVEL workbook.

Same construct as build_entry_pod.py, but built directly on the real VTZ S26 schedule
(the file Avra shared) and delivered at the schedule's own level of detail - one row per
departing flight - plus the full 5-minute demand table and the daily summary, in one
Excel workbook so it can be reviewed exactly like the schedule.

  passengers  = Capacity x LF[category, weekday]      (REAL June load factor)
  entry time  = STD - offset, offset drawn from the MEASURED e-boarding show-up buckets
  demand_5min -> demand_30min (forward 30-min rolling)  -> demand_60min (hourly)

DEMAND ONLY: lane / gate / capacity numbers are intentionally left out until Avra
confirms the ENTRY processing rate (120 pax/hr from ATRS trays is the SECURITY rate,
not Entry). They will be added back once the rate is given.

Input : POD2/inputs/VTZ_Daily_Flight_Schedule_S26.xlsx  (sheet 'Daily Schedule')
        POD2/step1_june_data/june_load_daily.csv        (real LF)
        POD2/step3_ews_eboarding/entry_showup_profile.csv (measured show-up %)
Output: finalised_entry_dataset.xlsx  (sheets: Read Me / Entry by Flight /
        Entry Demand 5-min / Entry Demand 60-min / Daily Summary)
Run   : python build_entry_dataset_xlsx.py
"""
import csv, os, statistics as st
import datetime as dt
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCHED = os.path.join(ROOT, 'inputs', 'VTZ_Daily_Flight_Schedule_S26.xlsx')
JUNE = os.path.join(ROOT, 'step1_june_data', 'june_load_daily.csv')
SHOWUP = os.path.join(ROOT, 'step3_ews_eboarding', 'entry_showup_profile.csv')
OUT = os.path.join(HERE, 'finalised_entry_dataset.xlsx')

STEP = 5
SLOTS = 24 * 60 // STEP
# NOTE: this deliverable is DEMAND ONLY. Lane/capacity numbers are deliberately left out
# because the Entry processing rate is not yet confirmed (Avra clarified 120 pax/hr from
# ATRS trays is the SECURITY rate, not Entry). Once Avra gives the Entry rate we add the
# lane/gate sizing back. Physical layout for reference: 3 gates (01/02/03) x A/B = 6 lanes.
BUCKET_RANGE = {'<60': (30, 60), '60-90': (60, 90), '90-120': (90, 120),
                '120-150': (120, 150), '150-180': (150, 180), '>180': (180, 240)}
CATLABEL = {'C': 'C - Narrow-body', 'B': 'B - ATR-72', 'A': 'A - 9-seater'}


def cat_of(ac):
    ac = (ac or '').upper()
    if ac.startswith('ATR'): return 'B'
    if ac.startswith('C '): return 'A'          # 'C 2088' (Cessna 208)
    return 'C'


def load_lf():
    by = defaultdict(list); byc = defaultdict(list)
    for r in csv.DictReader(open(JUNE, encoding='utf-8')):
        if r['direction'] != 'DEP' or float(r['pax']) <= 0:
            continue
        lf = float(r['load_factor'])
        by[(r['category'], r['day_of_week'])].append(lf); byc[r['category']].append(lf)
    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    lf = {}
    for c in byc:
        for d in dows:
            v = by.get((c, d)); lf[(c, d)] = st.mean(v) if v else st.mean(byc[c])
    return lf


def load_weights():
    pct = {r['bucket']: float(r['pct']) for r in csv.DictReader(open(SHOWUP, encoding='utf-8'))}
    w = defaultdict(float)
    for b, (lo, hi) in BUCKET_RANGE.items():
        offs = list(range(lo, hi, STEP)); share = (pct.get(b, 0) / 100.0) / len(offs)
        for o in offs: w[o] += share
    tot = sum(w.values())
    return {o: v / tot for o, v in w.items()}


def tmin(v):
    if isinstance(v, dt.time): return v.hour * 60 + v.minute
    if isinstance(v, dt.datetime): return v.hour * 60 + v.minute
    if isinstance(v, str) and ':' in v:
        hh, mm = v.split(':')[:2]; return int(hh) * 60 + int(mm)
    return None


# ---------- styling ----------
HDR_FILL = PatternFill('solid', fgColor='16375E')
HDR_FONT = Font(bold=True, color='FFFFFF', size=11)
TITLE_FONT = Font(bold=True, color='16375E', size=14)
THIN = Side(style='thin', color='D5DEE5')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, ncol, row=1):
    for c in range(1, ncol + 1):
        cell = ws.cell(row, c); cell.fill = HDR_FILL; cell.font = HDR_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center'); cell.border = BORDER
    ws.freeze_panes = ws.cell(row + 1, 1)
    ws.auto_filter.ref = f"A{row}:{get_column_letter(ncol)}{row}"


def main():
    lf = load_lf(); weights = load_weights()
    wb = openpyxl.load_workbook(SCHED, read_only=True, data_only=True)
    ws = wb['Daily Schedule']
    it = ws.iter_rows(values_only=True); hdr = next(it)

    flights = []
    demand = defaultdict(lambda: [0.0] * SLOTS)
    daymeta = {}
    for r in it:
        if r[0] is None:
            continue
        date = r[0].date() if isinstance(r[0], dt.datetime) else r[0]
        day = r[2]                                   # 'Sunday'
        sl = r[4]; depfl = r[9]; dest = r[10]; std = r[11]
        ac = r[12]; cap = r[13]; ttype = r[14]; band = r[15]
        c = cat_of(ac); L = lf.get((c, day), st.mean([v for (cc, _), v in lf.items() if cc == c]))
        pax = cap * L
        stdm = tmin(std)
        stdstr = f"{stdm//60:02d}:{stdm%60:02d}" if stdm is not None else ''
        flights.append([date.isoformat(), day, sl, depfl, dest, stdstr, ac, cap, ttype, band,
                        stdm // 60 if stdm is not None else None, CATLABEL[c], round(L * 100, 1), round(pax)])
        daymeta[date.isoformat()] = day
        if stdm is not None:
            for off, wgt in weights.items():
                ent = max(0, stdm - off); demand[date.isoformat()][ent // STEP] += pax * wgt

    # ---- Sheet: Entry by Flight ----
    del wb                                            # (read-only source; build fresh workbook)
    out = openpyxl.Workbook()
    sf = out.active; sf.title = 'Entry by Flight'
    cols = ['Date', 'Day', 'SL No', 'Departure Flight', 'Destination', 'STD', 'Aircraft Type',
            'Capacity', 'Traffic Type', 'Time Band', 'STD Hour', 'Category',
            'Load Factor %', 'Entry Passengers']
    sf.append(cols)
    for row in flights:
        sf.append(row)
    style_header(sf, len(cols))
    widths = [11, 10, 7, 15, 11, 8, 13, 9, 12, 11, 9, 16, 13, 15]
    for i, w in enumerate(widths, 1):
        sf.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet: Entry Demand 5-min (operating slots only) ----
    sd = out.create_sheet('Entry Demand 5-min')
    sd.append(['Date', 'Day', 'Time', 'Entry Demand (5-min)', 'Entry Demand (30-min)'])
    h60 = []         # 60-min (hourly) demand rows
    daily = []
    for d in sorted(demand):
        dem = demand[d]; dem30 = [sum(dem[i:i + 6]) for i in range(SLOTS)]
        for i in range(SLOTS):
            if dem30[i] <= 0.05:                      # skip closed hours
                continue
            t = f"{(i*STEP)//60:02d}:{(i*STEP)%60:02d}"
            sd.append([d, daymeta[d], t, round(dem[i], 1), round(dem30[i], 1)])
        # 60-min (hourly) demand
        for h in range(24):
            d60 = sum(dem[h * 12:(h + 1) * 12])       # pax entering in the clock hour
            if d60 <= 0.05:
                continue
            h60.append([d, daymeta[d], f"{h:02d}:00-{(h+1)%24:02d}:00", round(d60)])
        pk = max(range(SLOTS), key=lambda i: dem30[i])
        daily.append([d, daymeta[d], round(sum(dem)), round(dem30[pk]),
                      f"{(pk*STEP)//60:02d}:{(pk*STEP)%60:02d}"])
    style_header(sd, 5)
    for i, w in enumerate([11, 10, 8, 20, 21], 1):
        sd.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet: Entry Demand 60-min (hourly, for benchmark comparison) ----
    sh60 = out.create_sheet('Entry Demand 60-min')
    sh60.append(['Date', 'Day', 'Hour', 'Entry Demand (pax/hr)'])
    for row in h60:
        sh60.append(row)
    style_header(sh60, 4)
    for i, w in enumerate([11, 10, 14, 20], 1):
        sh60.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet: Daily Summary ----
    ss = out.create_sheet('Daily Summary')
    ss.append(['Date', 'Day', 'Entry Passengers', 'Peak 30-min Demand', 'Peak Time'])
    for row in daily:
        ss.append(row)
    style_header(ss, 5)
    for i, w in enumerate([11, 10, 17, 19, 11], 1):
        ss.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet: Read Me (put first) ----
    rm = out.create_sheet('Read Me', 0)
    lines = [
        ('POD2 - Finalised Entry Dataset (Bhogapuram / VTZ, S26)', 'title'),
        ('', ''),
        ('What this is', 'h'),
        ('A pure, auditable calculation of terminal-ENTRY passenger demand for every departing', ''),
        ('flight in the real VTZ S26 schedule. No machine learning. Entry = departing pax.', ''),
        ('', ''),
        ('Formulas (Avra\'s construct)', 'h'),
        ('Entry Passengers = Capacity x Load Factor[category, weekday]', 'mono'),
        ('   Load Factor = REAL June actuals by aircraft category and day-of-week', ''),
        ('Entry time     = STD - offset;  offset from the MEASURED HYD e-boarding show-up profile', 'mono'),
        ('Demand (30-min)= forward 30-minute sum of 5-minute entry demand', 'mono'),
        ('', ''),
        ('This version is DEMAND ONLY', 'h'),
        ('Lane / gate / capacity numbers are intentionally left out until Avra confirms the', ''),
        ('ENTRY processing rate. (120 pax/hr from ATRS trays is the SECURITY rate, not Entry.)', ''),
        ('Physical layout for reference: 3 gates (01/02/03), each with an A and B lane = 6 lanes', ''),
        ('   01-A  01-B   02-A  02-B   03-A  03-B', 'mono'),
        ('Lane / gate sizing will be added once the Entry rate is given.', ''),
        ('', ''),
        ('Sheets', 'h'),
        ('Entry by Flight    - one row per departing flight (5,820) with its entry passengers', ''),
        ('Entry Demand 5-min - terminal-entry demand per 5-min slot + 30-min rolling', ''),
        ('Entry Demand 60-min- hourly demand (to compare against the benchmark)', ''),
        ('Daily Summary      - per-day total entry pax + peak 30-min demand', ''),
        ('', ''),
        ('Headline', 'h'),
        (f'{len(flights):,} departing flights  ·  {sum(r[13] for r in flights):,} season entry passengers'
         f'  ·  ~{round(sum(r[13] for r in flights)/len(daily)):,}/day', 'b'),
        ('', ''),
        ('To confirm with Avra', 'h'),
        ('- ENTRY processing rate: PENDING (needed before any lane / gate / capacity sizing)', ''),
        ('- e-boarding show-up is from 2 days only (good overall, not day-of-week splits)', ''),
        ('', ''),
        ('Confirmed by Avra', 'h'),
        ('- load data is JUNE (both sheets are June; the July label was wrong) - using June actuals', ''),
    ]
    for i, (txt, kind) in enumerate(lines, 1):
        cell = rm.cell(i, 1, txt)
        if kind == 'title': cell.font = Font(bold=True, color='16375E', size=16)
        elif kind == 'h': cell.font = Font(bold=True, color='0B6E99', size=12)
        elif kind == 'b': cell.font = Font(bold=True, color='2E8B57', size=12)
        elif kind == 'mono': cell.font = Font(name='Consolas', size=10, color='1E2B37')
    rm.column_dimensions['A'].width = 95
    rm.sheet_view.showGridLines = False

    out.save(OUT)
    tot = sum(r[13] for r in flights)
    print(f"wrote {os.path.basename(OUT)}  (DEMAND ONLY - lane/gate sizing pending Entry rate)")
    print(f"  Entry by Flight rows: {len(flights):,}")
    print(f"  Entry Demand 5-min rows: {sd.max_row-1:,}   60-min rows: {sh60.max_row-1:,}")
    print(f"  season entry passengers: {tot:,}   (~{round(tot/len(daily)):,}/day)")


if __name__ == '__main__':
    main()
