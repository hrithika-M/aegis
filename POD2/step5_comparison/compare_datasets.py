# -*- coding: utf-8 -*-
"""POD2 - Step 5: compare the three datasets on LIKE-FOR-LIKE dimensions.

Avra's construct has three layers; each of our datasets covers one, and the twin is
meant to reproduce two of them:

    LAYER              REAL SOURCE                TWIN (should match)
    ----------------   ------------------------   ------------------------------
    aircraft mix       June loads (Step 1/2)      Daily_Flights aircraft types
    load factor        June loads (Step 1/2)      passenger_estimates load_factor_effective
    show-up profile    HYD e-boarding (Step 3)    DEP_ENTER window (Step 4)

This script lines them up and writes:
  - comparison_dashboard.png  (mix | load factor | show-up profile, real vs twin)
  - comparison_summary.csv    (the numbers behind the panels)
Run: python compare_datasets.py
"""
import csv, os, statistics as st
import datetime as dt
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TWIN = os.path.join(ROOT, os.pardir, 'bhogapuram_digital_twin', 'generated')
JUNE = os.path.join(ROOT, 'step1_june_data', 'june_load_daily.csv')

# --- category map for the twin's aircraft types (Avra's A/B/C) ---------------------
def cat_of(ac):
    if ac.startswith('ATR'): return 'B'
    if 'Cessna' in ac or '208' in ac: return 'A'
    return 'C'                                     # A320/A321/B737 narrow-body

BLUE, AMBER, RED, DK, GREY = '#2f6bdd', '#f0a030', '#e0574f', '#16375e', '#9aa7b8'
BUCKETS = ['<60', '60-90', '90-120', '120-150', '150-180', '>180']

# --- REAL show-up profile (Step 3 output) and TWIN show-up (Step 4 output) ----------
def read_profile(path):
    d = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        d[r['bucket']] = float(r['pct'])
    return d

real_prof = read_profile(os.path.join(ROOT, 'step3_ews_eboarding', 'entry_showup_profile.csv'))
twin_prof = read_profile(os.path.join(ROOT, 'step4_twin_entry', 'twin_entry_showup_profile.csv'))
avra_prof = {'<60': 4.65, '60-90': 25.59, '90-120': 32.99, '120-150': 20.04, '150-180': 8.63, '>180': 8.11}


def june_layers():
    pax = defaultdict(float); lf = defaultdict(list); dow_lf = defaultdict(list)
    for r in csv.DictReader(open(JUNE, encoding='utf-8')):
        if r['direction'] != 'DEP':
            continue
        c = r['category']; pax[c] += float(r['pax'])
        if float(r['pax']) > 0:
            lf[c].append(float(r['load_factor']))
            if c == 'C':
                dow_lf[r['day_of_week']].append(float(r['load_factor']))
    tot = sum(pax.values())
    mix = {c: 100 * pax[c] / tot for c in pax}
    lf_c = 100 * st.mean(lf['C'])
    dow = {d: 100 * st.mean(v) for d, v in dow_lf.items()}
    return mix, lf_c, dow


def twin_layers():
    pax = defaultdict(float); lfC = []; dow_lf = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(TWIN, 'passenger_estimates.csv'), encoding='utf-8')):
        if r['movement_type'] != 'DEP':
            continue
        c = cat_of(r['aircraft']); p = float(r['passengers']); pax[c] += p
        if c == 'C':
            lfC.append(float(r['load_factor_effective']))
            d = dt.date.fromisoformat(r['date']).strftime('%A')
            dow_lf[d].append(float(r['load_factor_effective']))
    tot = sum(pax.values())
    mix = {c: 100 * pax[c] / tot for c in pax}
    lf_c = 100 * st.mean(lfC)
    dow = {d: 100 * st.mean(v) for d, v in dow_lf.items()}
    return mix, lf_c, dow


def main():
    jmix, jlfC, jdow = june_layers()
    tmix, tlfC, tdow = twin_layers()
    DOW = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    fig, ax = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle('POD2 - Step 5 - Real vs Twin, like-for-like (Entry)', fontsize=15, fontweight='bold', color=DK)

    # panel 1: aircraft mix (June real vs twin), categories C/B/A
    cats = ['C', 'B', 'A']; x = range(len(cats)); w = 0.38
    ax[0].bar([i - w/2 for i in x], [jmix.get(c, 0) for c in cats], w, label='June (real)', color=BLUE)
    ax[0].bar([i + w/2 for i in x], [tmix.get(c, 0) for c in cats], w, label='Twin', color=AMBER)
    ax[0].set_title('Departing pax mix by aircraft category', fontweight='bold', color=DK)
    ax[0].set_xticks(list(x)); ax[0].set_xticklabels(['C narrow-body', 'B ATR', 'A 9-seat'])
    ax[0].set_ylabel('% of departing pax'); ax[0].legend(frameon=False)
    for i, c in enumerate(cats):
        ax[0].text(i - w/2, jmix.get(c, 0) + 1, f"{jmix.get(c,0):.1f}", ha='center', fontsize=8)
        ax[0].text(i + w/2, tmix.get(c, 0) + 1, f"{tmix.get(c,0):.1f}", ha='center', fontsize=8)

    # panel 2: narrow-body load factor by day-of-week (June real vs twin)
    ax[1].plot(DOW, [jdow.get(d, 0) for d in DOW], marker='o', color=BLUE, label=f'June (real)  avg {jlfC:.0f}%')
    ax[1].plot(DOW, [tdow.get(d, 0) for d in DOW], marker='s', color=AMBER, label=f'Twin  avg {tlfC:.0f}%')
    ax[1].set_title('Narrow-body load factor by day-of-week', fontweight='bold', color=DK)
    ax[1].set_ylabel('Load factor (%)'); ax[1].set_ylim(60, 95)
    ax[1].set_xticklabels([d[:3] for d in DOW]); ax[1].legend(frameon=False)

    # panel 3: show-up profile (real e-boarding vs twin vs Avra)
    xb = range(len(BUCKETS)); w2 = 0.27
    ax[2].bar([i - w2 for i in xb], [real_prof[b] for b in BUCKETS], w2, label='Real e-boarding', color=BLUE)
    ax[2].bar([i for i in xb], [twin_prof[b] for b in BUCKETS], w2, label='Twin', color=AMBER)
    ax[2].bar([i + w2 for i in xb], [avra_prof[b] for b in BUCKETS], w2, label="Avra's dashboard", color=GREY)
    ax[2].set_title('Entry show-up profile (minutes early)', fontweight='bold', color=DK)
    ax[2].set_xticks(list(xb)); ax[2].set_xticklabels(BUCKETS, rotation=30); ax[2].set_ylabel('% of pax')
    ax[2].legend(frameon=False)

    for a in ax:
        a.spines[['top', 'right']].set_visible(False)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(os.path.join(HERE, 'comparison_dashboard.png'), dpi=120, bbox_inches='tight')

    # summary csv
    with open(os.path.join(HERE, 'comparison_summary.csv'), 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f)
        wr.writerow(['dimension', 'key', 'june_real', 'twin', 'match?'])
        for c in cats:
            wr.writerow(['aircraft_mix_%', c, round(jmix.get(c, 0), 1), round(tmix.get(c, 0), 1),
                         'Y' if abs(jmix.get(c, 0) - tmix.get(c, 0)) < 2 else 'N'])
        wr.writerow(['loadfactor_narrowbody_%', 'avg', round(jlfC, 1), round(tlfC, 1),
                     'Y' if abs(jlfC - tlfC) < 5 else 'close'])
        for b in BUCKETS:
            wr.writerow(['showup_%', b, real_prof[b], twin_prof[b],
                         'Y' if abs(real_prof[b] - twin_prof[b]) < 5 else 'N'])

    print("=== AIRCRAFT MIX (dep pax %) ===")
    for c in cats:
        print(f"  {c}: June {jmix.get(c,0):5.1f}%   Twin {tmix.get(c,0):5.1f}%")
    print(f"=== NARROW-BODY LOAD FACTOR ===\n  June {jlfC:.1f}%   Twin {tlfC:.1f}%  (gap {jlfC-tlfC:+.1f})")
    print("=== SHOW-UP PROFILE (real vs twin) ===")
    for b in BUCKETS:
        print(f"  {b:<9} real {real_prof[b]:5.1f}%   twin {twin_prof[b]:5.1f}%   diff {twin_prof[b]-real_prof[b]:+5.1f}")


if __name__ == '__main__':
    main()
