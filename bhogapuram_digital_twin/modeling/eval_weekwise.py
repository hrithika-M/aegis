# -*- coding: utf-8 -*-
"""Week-wise rollup of the day-wise walk-forward results — Bhogapuram TWIN.

Reads analytics/twin_daywise_accuracy.csv (from eval_daywise.py) and rolls it up
by ISO week instead of by month. Same simulated-data caveat as everywhere else in
this folder: pipeline test, not real accuracy, until the data source is swapped
for real Bhogapuram EWS data.

Outputs:
  analytics/twin_weekwise_accuracy.csv
  analytics/twin_weekwise_winners.csv

Run:  python eval_weekwise.py   (after eval_daywise.py has run)
"""
import csv, os
import datetime as dt
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DAILY = os.path.join(ROOT, 'analytics', 'twin_daywise_accuracy.csv')
OUT_WK = os.path.join(ROOT, 'analytics', 'twin_weekwise_accuracy.csv')
OUT_WIN = os.path.join(ROOT, 'analytics', 'twin_weekwise_winners.csv')


def iso_week(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def main():
    rows = list(csv.DictReader(open(DAILY, encoding='utf-8')))
    grouped = defaultdict(list)
    for r in rows:
        d = dt.date.fromisoformat(r['test_date'])
        key = (r['touchpoint'], r['model'], iso_week(d))
        grouped[key].append(r)

    weekly = []
    for (tp, model, wk), rs in grouped.items():
        accs = [float(x['accuracy']) for x in rs]
        rms = [float(x['rmse']) for x in rs]
        mean_acc = sum(accs) / len(accs)
        std_acc = (sum((a - mean_acc) ** 2 for a in accs) / len(accs)) ** 0.5 if len(accs) > 1 else 0.0
        weekly.append({'touchpoint': tp, 'model': model, 'iso_year_week': wk,
                       'mean_accuracy': round(mean_acc, 1), 'std_accuracy': round(std_acc, 1),
                       'mean_rmse': round(sum(rms) / len(rms), 1), 'n_days': len(rs)})
    with open(OUT_WK, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['touchpoint', 'model', 'iso_year_week',
                                          'mean_accuracy', 'std_accuracy', 'mean_rmse', 'n_days'])
        w.writeheader(); w.writerows(weekly)

    by_tp_wk = defaultdict(list)
    for r in weekly:
        by_tp_wk[(r['touchpoint'], r['iso_year_week'])].append(r)
    win_rows = []
    for (tp, wk), rs in sorted(by_tp_wk.items()):
        rs.sort(key=lambda x: -x['mean_accuracy'])
        best, second = rs[0], rs[1] if len(rs) > 1 else rs[0]
        win_rows.append({'touchpoint': tp, 'iso_year_week': wk, 'winner': best['model'],
                         'winner_accuracy': best['mean_accuracy'], 'runner_up': second['model'],
                         'runner_up_accuracy': second['mean_accuracy'],
                         'gap': round(best['mean_accuracy'] - second['mean_accuracy'], 1)})
    with open(OUT_WIN, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['touchpoint', 'iso_year_week', 'winner', 'winner_accuracy',
                                          'runner_up', 'runner_up_accuracy', 'gap'])
        w.writeheader(); w.writerows(win_rows)

    print(f"wrote {os.path.relpath(OUT_WK, ROOT)}  ({len(weekly)} rows)")
    print(f"wrote {os.path.relpath(OUT_WIN, ROOT)}  ({len(win_rows)} rows)")
    print()
    print("=== winner-count per touchpoint (how many weeks each model won) ===")
    tps = sorted({r['touchpoint'] for r in win_rows})
    for tp in tps:
        counts = defaultdict(int)
        for r in win_rows:
            if r['touchpoint'] == tp:
                counts[r['winner']] += 1
        print(f"  {tp:<10} " + "  ".join(f"{m}={c}" for m, c in sorted(counts.items(), key=lambda x: -x[1])))
    print("\nREMINDER: simulated twin data -> pipeline test, NOT real accuracy.")


if __name__ == '__main__':
    main()
