# -*- coding: utf-8 -*-
"""POD2 · Step 3 — Entry show-up profile from the HYD e-boarding (EWS) data.

Reproduces Avra's ENTRY analysis (his 'Arrival Pattern At Entry' donut + 'Passenger
Show Up Profile At Entry' hourly bars) from the real passenger-level e-boarding data,
exactly as he described on the call:

    minutes early = FLIGHT_TIME - TRML_ENT_SCAN_TIME   (how long before departure the
                                                        passenger scanned in at entry)
    -> bucket into <60 / 60-90 / 90-120 / 120-150 / 150-180 / >180
    -> the % split IS the entry show-up profile (drives the forecast later)
    -> count by entry-scan hour, stacked by bucket = the entry demand curve

ENTRY ONLY (per current scope). Security/other touchpoints come after Avra confirms.

PRIVACY: the raw file has passenger PII (names, PNR, e-ticket). It is read from the
user's Downloads and is NOT committed. Only the aggregated, non-PII outputs below are
saved to the repo.

Inputs (not committed):  <Downloads>/AOCC_EBOARDING_STG_PAXDETAILSTAB_HIST (1).xlsx
Outputs: entry_showup_profile.csv, entry_hourly.csv, ews_entry_dashboard.png
Run:     python analyze_ews_entry.py
"""
import csv, os
import datetime as dt
from collections import defaultdict
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser('~/Downloads/AOCC_EBOARDING_STG_PAXDETAILSTAB_HIST (1).xlsx')
COL_FLIGHT_TIME, COL_ENTRY_SCAN = 16, 25
BUCKETS = ['<60', '60-90', '90-120', '120-150', '150-180', '>180']
COLORS = {'<60': '#e0201b', '60-90': '#16375e', '90-120': '#2f8fe0',
          '90-120 ': '#2f8fe0', '120-150': '#e08a2f', '150-180': '#7a3fb0', '>180': '#2ca02c'}
MAX_MIN = 600     # ignore > 10 h early as data artifacts


def bucket(m):
    if m < 60: return '<60'
    if m < 90: return '60-90'
    if m < 120: return '90-120'
    if m < 150: return '120-150'
    if m < 180: return '150-180'
    return '>180'


def main():
    overall = defaultdict(int)
    hourly = defaultdict(lambda: defaultdict(int))   # hour -> bucket -> count
    n_valid = n_null = n_out = 0
    wb = openpyxl.load_workbook(SRC, data_only=True, read_only=True)
    ws = wb['Sheet1']
    it = ws.iter_rows(values_only=True)
    next(it)                                          # header
    for row in it:
        ft, et = row[COL_FLIGHT_TIME], row[COL_ENTRY_SCAN]
        if not (isinstance(ft, dt.datetime) and isinstance(et, dt.datetime)):
            n_null += 1
            continue
        m = (ft - et).total_seconds() / 60
        if m < 0 or m > MAX_MIN:
            n_out += 1
            continue
        b = bucket(m)
        overall[b] += 1
        hourly[et.hour][b] += 1
        n_valid += 1
    wb.close()

    total = sum(overall.values())
    # 1) show-up profile csv (the % that feeds the forecast)
    with open(os.path.join(HERE, 'entry_showup_profile.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['bucket', 'passengers', 'pct'])
        for b in BUCKETS:
            w.writerow([b, overall[b], round(100 * overall[b] / total, 2)])
    # 2) hourly counts csv
    with open(os.path.join(HERE, 'entry_hourly.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['hour'] + BUCKETS)
        for h in range(24):
            w.writerow([f"{h:02d}"] + [hourly[h][b] for b in BUCKETS])

    # 3) dashboard (donut + hourly stacked bars), mirroring Avra
    fig, (axd, axb) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={'width_ratios': [1, 2.4]})
    fig.suptitle('POD2 · Step 3 — Entry show-up profile from HYD e-boarding (real, 12-13 Apr 2026)',
                 fontsize=14, fontweight='bold', color='#16375e')
    order_by_share = sorted(BUCKETS, key=lambda b: -overall[b])
    axd.pie([overall[b] for b in order_by_share], labels=order_by_share,
            autopct=lambda p: f'{p:.1f}%', startangle=90, pctdistance=0.8,
            colors=[COLORS[b] for b in order_by_share], wedgeprops=dict(width=0.42, edgecolor='white'))
    axd.set_title('Arrival Pattern at Entry\n(minutes before departure)', fontweight='bold', color='#16375e')

    hours = list(range(24))
    bottom = [0] * 24
    for b in BUCKETS:
        vals = [hourly[h][b] for h in hours]
        axb.bar(hours, vals, bottom=bottom, label=b, color=COLORS[b])
        bottom = [bottom[i] + vals[i] for i in range(24)]
    axb.set_title('Passenger Show-Up Profile at Entry (by entry-scan hour)', fontweight='bold', color='#16375e')
    axb.set_xlabel('Hour of day'); axb.set_ylabel('Passenger count')
    axb.set_xticks(hours); axb.legend(title='minutes early', frameon=False, ncol=2, fontsize=9)
    axb.spines[['top', 'right']].set_visible(False)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(HERE, 'ews_entry_dashboard.png'), dpi=120, bbox_inches='tight')

    print(f"valid entry records: {n_valid:,}  (null: {n_null:,}, outliers >{MAX_MIN}m or <0: {n_out:,})")
    print("Entry show-up profile (% of passengers by minutes-early bucket):")
    for b in BUCKETS:
        print(f"  {b:<9} {overall[b]:>6,}  {100*overall[b]/total:5.1f}%")
    pk = max(range(24), key=lambda h: sum(hourly[h].values()))
    print(f"peak entry hour: {pk:02d}:00  ({sum(hourly[pk].values()):,} pax)")


if __name__ == '__main__':
    main()
