# -*- coding: utf-8 -*-
"""POD2 - Step 4: Entry show-up profile from the DIGITAL-TWIN data.

Goal: reproduce the SAME Entry analysis as Step 3 (the real HYD e-boarding), but on
the twin's generated data - so Step 5 can compare like-for-like.

COLUMN MATCH (this is the whole point of the step):
    Step 3 (real e-boarding)          Step 4 (twin)
    -------------------------------   ------------------------------------------
    FLIGHT_TIME                       departure_time / scheduled_time (DEP legs)
    TRML_ENT_SCAN_TIME                terminal show-up time = STD + DEP_ENTER offset
    minutes early = FLIGHT-SCAN       minutes early = STD - show-up  (the 40..150 offset)
    show-up % per bucket              triangular weight per bucket
    demand by entry-scan hour         entry demand by clock hour (DEP only)

The twin models terminal entry with a triangular show-up window (build_operations.py):
    DEP_ENTER = (-150, -40, -85)  -> pax enter 150..40 min before departure, peak 85.
We reconstruct that exact distribution here (same tri() weights, same 5-min slots) from
each DEP leg's reconciled passengers, then bucket it the SAME way as Step 3. DEP legs
only, because Step 3's "minutes before departure" is inherently a departure concept.

Outputs: twin_entry_showup_profile.csv, twin_entry_hourly.csv, twin_entry_dashboard.png
Run:     python analyze_twin_entry.py
"""
import csv, os
import datetime as dt
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAX = os.path.join(ROOT, os.pardir, 'bhogapuram_digital_twin', 'generated', 'passenger_estimates.csv')

# --- mirror the twin's Entry model exactly (build_operations.py) -------------------
DEP_ENTER = (-150, -40, -85)   # (win_start, win_end, peak) minutes before STD
STEP = 5
BUCKETS = ['<60', '60-90', '90-120', '120-150', '150-180', '>180']
COLORS = {'<60': '#e0201b', '60-90': '#16375e', '90-120': '#2f8fe0',
          '120-150': '#e08a2f', '150-180': '#7a3fb0', '>180': '#2ca02c'}


def tri(x, a, b, c):
    if x < a or x > b:
        return 0.0
    return (x - a) / (c - a) if x <= c else (b - x) / (b - c)


def bucket(m):                 # m = minutes early (positive), same thresholds as Step 3
    if m < 60: return '<60'
    if m < 90: return '60-90'
    if m < 120: return '90-120'
    if m < 150: return '120-150'
    if m < 180: return '150-180'
    return '>180'


def main():
    overall = defaultdict(float)
    hourly = defaultdict(lambda: defaultdict(float))   # clock hour -> bucket -> pax
    a, b, c = DEP_ENTER
    n_dep = 0
    tot_pax = 0.0

    for lg in csv.DictReader(open(PAX, encoding='utf-8')):
        if lg['movement_type'] != 'DEP':
            continue
        n_dep += 1
        P = float(lg['passengers'])
        tot_pax += P
        hh, mm = map(int, lg['scheduled_time'].split(':'))
        std_min = hh * 60 + mm                          # minutes-of-day of departure
        # same triangular spread the twin uses, over 5-min offsets in the window
        lo = int(round(a / STEP)); hi = int(round(b / STEP))
        weights = []
        for s in range(lo, hi + 1):
            rel = s * STEP                              # offset vs STD (negative = before)
            weights.append((rel, tri(rel, a, b, c)))
        tot = sum(w for _, w in weights)
        if tot <= 0:
            continue
        for rel, w in weights:
            pax = P * w / tot
            mins_early = -rel                           # 40..150 min before departure
            overall[bucket(mins_early)] += pax
            enter_hour = (int(std_min + rel) // 60) % 24
            hourly[enter_hour][bucket(mins_early)] += pax

    total = sum(overall.values())
    # 1) show-up profile
    with open(os.path.join(HERE, 'twin_entry_showup_profile.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['bucket', 'passengers', 'pct'])
        for bk in BUCKETS:
            w.writerow([bk, round(overall[bk]), round(100 * overall[bk] / total, 2)])
    # 2) hourly
    with open(os.path.join(HERE, 'twin_entry_hourly.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['hour'] + BUCKETS)
        for h in range(24):
            w.writerow([f"{h:02d}"] + [round(hourly[h][bk]) for bk in BUCKETS])

    # 3) dashboard (donut + hourly stacked bars) - same layout as Step 3
    fig, (axd, axb) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={'width_ratios': [1, 2.4]})
    fig.suptitle('POD2 - Step 4 - Entry show-up profile from the DIGITAL TWIN (generated, S26 season)',
                 fontsize=14, fontweight='bold', color='#16375e')
    order = sorted(BUCKETS, key=lambda bk: -overall[bk])
    axd.pie([overall[bk] for bk in order], labels=order,
            autopct=lambda p: f'{p:.1f}%', startangle=90, pctdistance=0.8,
            colors=[COLORS[bk] for bk in order], wedgeprops=dict(width=0.42, edgecolor='white'))
    axd.set_title('Arrival Pattern at Entry\n(minutes before departure)', fontweight='bold', color='#16375e')

    hours = list(range(24))
    bottom = [0.0] * 24
    for bk in BUCKETS:
        vals = [hourly[h][bk] for h in hours]
        axb.bar(hours, vals, bottom=bottom, label=bk, color=COLORS[bk])
        bottom = [bottom[i] + vals[i] for i in range(24)]
    axb.set_title('Passenger Show-Up Profile at Entry (by entry hour, DEP)', fontweight='bold', color='#16375e')
    axb.set_xlabel('Hour of day'); axb.set_ylabel('Passenger count (per season)')
    axb.set_xticks(hours); axb.legend(title='minutes early', frameon=False, ncol=2, fontsize=9)
    axb.spines[['top', 'right']].set_visible(False)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(HERE, 'twin_entry_dashboard.png'), dpi=120, bbox_inches='tight')

    print(f"twin DEP legs: {n_dep:,}   entry passengers (season): {total:,.0f}")
    print("Twin Entry show-up profile (% by minutes-early bucket):")
    for bk in BUCKETS:
        print(f"  {bk:<9} {overall[bk]:>10,.0f}  {100*overall[bk]/total:5.1f}%")
    pk = max(range(24), key=lambda h: sum(hourly[h].values()))
    print(f"peak entry hour: {pk:02d}:00  ({sum(hourly[pk].values()):,.0f} pax)")


if __name__ == '__main__':
    main()
