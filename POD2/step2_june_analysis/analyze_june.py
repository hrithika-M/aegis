# -*- coding: utf-8 -*-
"""POD2 · Step 2 — Avra-style analysis on the clean June load data (Entry focus).

Mirrors the kind of dashboard Avra shared, using what the June loads sheet actually
supports: daily passenger volume and load-factor patterns. (The passenger *show-up
profile* — the stacked hourly bars in Avra's image — needs per-passenger scan times,
which live in the e-boarding data; that is Step 3, not here.)

Panels:
  1. Passenger share by aircraft category (donut) — the June analog of Avra's donut
  2. Total passengers by date (Avra's 'Total pax by date' panel)
  3. Departure load factor by day-of-week (the weekly pattern Avra highlighted)
  4. Daily departure load factor across June (day-to-day variation / peaks)

Output: june_dashboard.png
Run:    python analyze_june.py
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(os.path.dirname(HERE), 'step1_june_data', 'june_load_daily.csv')
OUT = os.path.join(HERE, 'june_dashboard.png')

BLUE, AMBER, RED, DK = '#2f6bdd', '#f0a030', '#e0574f', '#16375e'
DOW_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def main():
    df = pd.read_csv(CSV, parse_dates=['date'])
    fig, ax = plt.subplots(2, 2, figsize=(15, 9))
    fig.suptitle('POD2 · Step 2 — June load actuals (Bhogapuram, real data)   ·   Entry-focus volume & load-factor patterns',
                 fontsize=14, fontweight='bold', color=DK)

    # 1) donut: passenger share by category (departures)
    dep = df[df.direction == 'DEP']
    share = dep.groupby('category')['pax'].sum().reindex(['C', 'B', 'A'])
    labels = ['C · Narrow-body\n(A320/A321/B737)', 'B · ATR-72', 'A · 9-seater']
    ax[0, 0].pie(share, labels=labels, autopct=lambda p: f'{p:.1f}%', startangle=90,
                 colors=[BLUE, AMBER, RED], pctdistance=0.78,
                 wedgeprops=dict(width=0.42, edgecolor='white'))
    ax[0, 0].set_title('Departing passenger share by aircraft category', fontweight='bold', color=DK)

    # 2) total pax by date (dep + arr stacked)
    piv = df.pivot_table(index='date', columns='direction', values='pax', aggfunc='sum')
    x = range(len(piv))
    ax[0, 1].bar(x, piv['DEP'], label='Departing', color=BLUE)
    ax[0, 1].bar(x, piv['ARR'], bottom=piv['DEP'], label='Arriving', color='#9fc0f0')
    ax[0, 1].set_title('Total passengers by date (June)', fontweight='bold', color=DK)
    ax[0, 1].set_xticks(list(x)[::3])
    ax[0, 1].set_xticklabels([d.strftime('%d') for d in piv.index[::3]])
    ax[0, 1].set_xlabel('June day'); ax[0, 1].set_ylabel('Passengers'); ax[0, 1].legend(frameon=False)

    # 3) departure load factor by day-of-week (category C = the bulk)
    depC = dep[dep.category == 'C'].copy()
    depC['dow'] = depC['date'].dt.day_name()
    lf_dow = depC.groupby('dow')['load_factor'].mean().reindex(DOW_ORDER) * 100
    bars = ax[1, 0].bar(DOW_ORDER, lf_dow, color=BLUE)
    ax[1, 0].axhline(lf_dow.mean(), ls='--', color=RED, lw=1, label=f'avg {lf_dow.mean():.0f}%')
    ax[1, 0].set_title('Departure load factor by day-of-week (narrow-body)', fontweight='bold', color=DK)
    ax[1, 0].set_ylabel('Load factor (%)'); ax[1, 0].set_ylim(60, 100); ax[1, 0].legend(frameon=False)
    ax[1, 0].set_xticklabels([d[:3] for d in DOW_ORDER])
    for b, v in zip(bars, lf_dow):
        ax[1, 0].text(b.get_x() + b.get_width() / 2, v + 0.5, f'{v:.0f}', ha='center', fontsize=9)

    # 4) daily departure load factor across June (category C)
    lf_day = depC.set_index('date')['load_factor'] * 100
    ax[1, 1].plot(lf_day.index, lf_day.values, marker='o', ms=4, color=BLUE)
    ax[1, 1].axhline(lf_day.mean(), ls='--', color=RED, lw=1, label=f'avg {lf_day.mean():.0f}%')
    ax[1, 1].set_title('Daily departure load factor across June (narrow-body)', fontweight='bold', color=DK)
    ax[1, 1].set_ylabel('Load factor (%)'); ax[1, 1].set_xlabel('Date'); ax[1, 1].legend(frameon=False)
    ax[1, 1].tick_params(axis='x', rotation=45)

    for a in ax.flat:
        a.spines[['top', 'right']].set_visible(False)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(OUT, dpi=120, bbox_inches='tight')
    print(f"wrote {os.path.relpath(OUT)}")
    # quick numbers for the report
    print(f"  narrow-body dep LF: overall {lf_day.mean():.1f}%  range {lf_day.min():.0f}-{lf_day.max():.0f}%")
    print(f"  busiest DOW: {lf_dow.idxmax()} ({lf_dow.max():.0f}%)  quietest: {lf_dow.idxmin()} ({lf_dow.min():.0f}%)")


if __name__ == '__main__':
    main()
