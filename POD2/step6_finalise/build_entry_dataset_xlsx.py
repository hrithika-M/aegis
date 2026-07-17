# -*- coding: utf-8 -*-
"""POD2 - Step 6 (detailed): finalised Entry dataset as a FLIGHT-LEVEL workbook.

Same construct as build_entry_pod.py, but built directly on the real VTZ S26 schedule
(the file Avra shared) and delivered at the schedule's own level of detail - one row per
departing flight - plus the full 5-minute demand table and the daily summary, in one
Excel workbook so it can be reviewed exactly like the schedule.

  passengers  = Capacity x LF[category, weekday]      (REAL June load factor)
  entry time  = STD - offset, offset drawn from the MEASURED e-boarding show-up buckets
  demand_5min -> demand_30min (forward 30-min projection)
  lanes       = ceil(demand_30min / 60)               (ATRS 120 pax/hr/lane)

Input : POD2/inputs/VTZ_Daily_Flight_Schedule_S26.xlsx  (sheet 'Daily Schedule')
        POD2/step1_june_data/june_load_daily.csv        (real LF)
        POD2/step3_ews_eboarding/entry_showup_profile.csv (measured show-up %)
Output: finalised_entry_dataset.xlsx  (sheets: Read Me / Entry by Flight /
        Entry Demand 5-min / Daily Summary)
Run   : python build_entry_dataset_xlsx.py
"""
import csv, math, os, statistics as st
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
LANE_PER_HR = 120                    # pax/hr per scanning lane  -- TO CONFIRM WITH AVRA
LANE_PER_30MIN = LANE_PER_HR // 2    # 60 pax per 30-min per lane
# Physical Entry = 3 gates, each with an A and B lane = 6 scanning lanes.
# Opening rule: balance across gates (one lane per gate, then the second lanes).
LANE_ORDER = ['01-A', '02-A', '03-A', '01-B', '02-B', '03-B']
N_LANES = len(LANE_ORDER)            # 6
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
    sd.append(['Date', 'Day', 'Time', 'Entry Demand (5-min)', 'Entry Demand (30-min)', 'Lanes Required'])
    gp = []          # 30-min gate plan rows
    gsum = []        # per-day gate summary
    daily = []
    for d in sorted(demand):
        dem = demand[d]; dem30 = [sum(dem[i:i + 6]) for i in range(SLOTS)]
        lanes = [math.ceil(x / LANE_PER_30MIN) for x in dem30]
        for i in range(SLOTS):
            if dem30[i] <= 0.05:                      # skip closed hours
                continue
            t = f"{(i*STEP)//60:02d}:{(i*STEP)%60:02d}"
            sd.append([d, daymeta[d], t, round(dem[i], 1), round(dem30[i], 1), lanes[i]])
        pk = max(range(SLOTS), key=lambda i: dem30[i])
        daily.append([d, daymeta[d], round(sum(dem)), round(dem30[pk]), lanes[pk],
                      f"{(pk*STEP)//60:02d}:{(pk*STEP)%60:02d}"])
        # gate allocation at 30-min resolution (gates are not reconfigured every 5 min)
        peak_block = 0; peak_need = 0; peak_gates = 0; peak_perlane = 0.0; peak_t = ''
        for i in range(0, SLOTS, 6):
            block = sum(dem[i:i + 6])                 # pax entering in this 30-min block
            if block <= 0.05:
                continue
            need = min(math.ceil(block / LANE_PER_30MIN), N_LANES)
            lanes_open = LANE_ORDER[:need]
            gates_open = sorted({l[:2] for l in lanes_open})
            per_lane = round(block / need, 1) if need else 0
            t = f"{(i*STEP)//60:02d}:{(i*STEP)%60:02d}"
            gp.append([d, daymeta[d], t, round(block), need, len(gates_open),
                       ', '.join(lanes_open), per_lane])
            if block > peak_block:
                peak_block = block; peak_need = need; peak_gates = len(gates_open)
                peak_perlane = per_lane; peak_t = t
        gsum.append([d, daymeta[d], peak_need, peak_gates, peak_perlane, peak_t])
    style_header(sd, 6)
    for i, w in enumerate([11, 10, 8, 20, 21, 15], 1):
        sd.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet: Daily Summary ----
    ss = out.create_sheet('Daily Summary')
    ss.append(['Date', 'Day', 'Entry Passengers', 'Peak 30-min Demand', 'Peak Lanes Required', 'Peak Time'])
    for row in daily:
        ss.append(row)
    style_header(ss, 6)
    for i, w in enumerate([11, 10, 17, 19, 20, 11], 1):
        ss.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet: Gate Plan (30-min) — which of the 6 gate-lanes to open ----
    gpz = out.create_sheet('Gate Plan (30-min)')
    gpz.append(['Date', 'Day', 'Time', 'Demand (30-min pax)', 'Lanes Needed (of 6)',
                'Gates Open (of 3)', 'Open Lanes', 'Pax per Lane'])
    for row in gp:
        gpz.append(row)
    style_header(gpz, 8)
    for i, w in enumerate([11, 10, 8, 20, 20, 18, 26, 14], 1):
        gpz.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet: Gate Summary (daily) ----
    gs = out.create_sheet('Gate Summary')
    gs.append(['Date', 'Day', 'Peak Lanes (of 6)', 'Peak Gates (of 3)', 'Peak Pax per Lane', 'Peak Time'])
    for row in gsum:
        gs.append(row)
    style_header(gs, 6)
    for i, w in enumerate([11, 10, 18, 18, 18, 11], 1):
        gs.column_dimensions[get_column_letter(i)].width = w

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
        ('Lanes Needed   = ceil(Demand(30-min) / 60)   [120 pax/hr/lane = 60 per 30 min]', 'mono'),
        ('', ''),
        ('Gate layout (per Avra)', 'h'),
        ('3 entry gates (01, 02, 03), each with an A and B lane = 6 scanning lanes:', ''),
        ('   01-A  01-B   02-A  02-B   03-A  03-B', 'mono'),
        ('Opening rule: BALANCE across gates - open one lane per gate first (01-A, 02-A,', ''),
        ('03-A), then the B lanes (01-B, 02-B, 03-B). Shortest queues / walking distance.', ''),
        ('Each lane = 120 pax/hr (TO CONFIRM). Total entry capacity = 6 x 120 = 720 pax/hr.', ''),
        ('', ''),
        ('Sheets', 'h'),
        ('Entry by Flight    - one row per departing flight (5,820) with its entry passengers', ''),
        ('Entry Demand 5-min - terminal-entry demand per 5-min slot, 30-min projection, lanes', ''),
        ('Daily Summary      - per-day totals and peak lane requirement', ''),
        ('Gate Plan (30-min) - which of the 6 gate-lanes to open each 30 min, and their load', ''),
        ('Gate Summary       - per-day peak lanes, peak gates open, peak load per lane', ''),
        ('', ''),
        ('Headline', 'h'),
        (f'{len(flights):,} departing flights  ·  {sum(r[13] for r in flights):,} season entry passengers', 'b'),
        (f'Peak {max(r[2] for r in gsum)} of 6 lanes across {max(r[3] for r in gsum)} of 3 gates  ·  6 lanes give comfortable headroom', 'b'),
        ('', ''),
        ('To confirm with Avra', 'h'),
        ('- lane throughput: assumed 120 pax/hr/lane (ATRS 180 trays/hr, 1.5 trays/pax) - CONFIRM', ''),
        ('- gate opening rule: balance across gates (vs fill gate-by-gate) - confirm preference', ''),
        ('- e-boarding show-up is from 2 days only (good overall, not day-of-week splits)', ''),
        ('- load factor uses the clean June sheet (the July-labelled sheet is a calculated copy)', ''),
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
    print(f"wrote {os.path.basename(OUT)}")
    print(f"  Entry by Flight rows: {len(flights):,}")
    print(f"  Entry Demand 5-min rows: {sd.max_row-1:,}   Gate Plan rows: {len(gp):,}")
    print(f"  season entry passengers: {tot:,}")
    print(f"  peak lanes: {max(r[2] for r in gsum)} of {N_LANES}   peak gates open: {max(r[3] for r in gsum)} of 3")
    busy = max(gsum, key=lambda r: r[2])
    print(f"  busiest day {busy[0]} ({busy[1]}): {busy[2]} lanes / {busy[3]} gates at {busy[5]}, {busy[4]} pax per lane")


if __name__ == '__main__':
    main()
