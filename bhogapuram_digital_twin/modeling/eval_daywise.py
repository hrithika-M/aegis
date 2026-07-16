# -*- coding: utf-8 -*-
"""Day-wise / month-wise model competition — Bhogapuram (VTZ) twin.

Same idea as the real-HYD version (models/selection/eval_daywise.py in the aegis
repo): don't collapse walk-forward into one aggregate number, keep every
per-test-day result and roll it up by month, per touchpoint, per model.

*** THIS RUNS ON THE SIMULATED TWIN — NOT REAL DATA ***
Bhogapuram has no real operational history (opens 2026-07-08). The twin's demand
is generated from the schedule + a stochastic load-factor model, so this is a
PIPELINE TEST — it proves the day-wise/month-wise machinery works and gives a
template, but the numbers are optimistic and not a claim about real accuracy.
Swap `load_touchpoint_hourly()` (same swap point as train_touchpoints.py) for the
real EWS export once Bhogapuram is live, and these numbers become real.

Outputs:
  analytics/twin_daywise_accuracy.csv
  analytics/twin_monthly_accuracy.csv
  analytics/twin_monthly_winners.csv

Run:  python eval_daywise.py
"""
import csv, os, warnings
warnings.simplefilter('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'
from collections import defaultdict
import datetime as dt
import numpy as np

from train_touchpoints import (load_touchpoint_hourly, zoo, TOUCHPOINTS, FEATURES,
                               WARMUP, STEP)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DAY = os.path.join(ROOT, 'analytics', 'twin_daywise_accuracy.csv')
OUT_MON = os.path.join(ROOT, 'analytics', 'twin_monthly_accuracy.csv')
OUT_WIN = os.path.join(ROOT, 'analytics', 'twin_monthly_winners.csv')


def acc(pred, actual):
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    m = (actual > 0) & (pred > 0)
    return float((np.minimum(actual[m], pred[m]) / np.maximum(actual[m], pred[m])).mean()) * 100 if m.sum() else None


def rmse(pred, actual):
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    m = actual > 0
    return float(np.sqrt(np.mean((pred[m] - actual[m]) ** 2))) if m.sum() else None


def naive_predict(rows_train, rows_test):
    idx = {(r['Date'], r['Hour']): r['demand'] for r in rows_train}
    out = []
    for r in rows_test:
        prev = idx.get((r['Date'] - dt.timedelta(days=7), r['Hour']))
        out.append(prev if prev is not None else np.nan)
    return np.array(out, float)


def walk_forward_daywise(rows, make, is_naive=False):
    days = sorted({r['Date'] for r in rows})
    out = []
    for td in days[WARMUP::STEP]:
        tr = [r for r in rows if r['Date'] < td]
        te = [r for r in rows if r['Date'] == td]
        if len(tr) < 100 or not te:
            continue
        yte = np.array([r['demand'] for r in te])
        if is_naive:
            p = naive_predict(tr, te)
            mask = ~np.isnan(p)
            if mask.sum() == 0:
                continue
            p, yt = p[mask], yte[mask]
        else:
            Xtr = np.array([[r[f] for f in FEATURES] for r in tr]); ytr = [r['demand'] for r in tr]
            Xte = np.array([[r[f] for f in FEATURES] for r in te])
            m = make().fit(Xtr, ytr)
            p, yt = m.predict(Xte), yte
        a = acc(p, yt)
        if a is None:
            continue
        out.append({'test_date': td, 'accuracy': round(a, 1), 'rmse': round(rmse(p, yt), 1)})
    return out


def main():
    models = zoo()
    print("=" * 82)
    print("DAY-WISE / MONTH-WISE MODEL COMPETITION — Bhogapuram TWIN (simulated, pipeline test)")
    print("=" * 82)
    daily_rows = []
    for tp in TOUCHPOINTS:
        rows = load_touchpoint_hourly(tp)
        for name, make in models.items():
            for r in walk_forward_daywise(rows, make):
                r2 = dict(r); r2['touchpoint'] = tp; r2['model'] = name
                daily_rows.append(r2)
        for r in walk_forward_daywise(rows, None, is_naive=True):
            r2 = dict(r); r2['touchpoint'] = tp; r2['model'] = 'Naive-7d'
            daily_rows.append(r2)
        print(f"  {tp:<10} done")

    import csv as csvmod
    os.makedirs(os.path.dirname(OUT_DAY), exist_ok=True)
    with open(OUT_DAY, 'w', newline='', encoding='utf-8') as f:
        w = csvmod.DictWriter(f, fieldnames=['touchpoint', 'model', 'test_date', 'accuracy', 'rmse'])
        w.writeheader()
        for r in daily_rows:
            w.writerow({'touchpoint': r['touchpoint'], 'model': r['model'],
                        'test_date': r['test_date'], 'accuracy': r['accuracy'], 'rmse': r['rmse']})

    # monthly rollup
    monthly = defaultdict(list)
    for r in daily_rows:
        ym = r['test_date'].strftime('%Y-%m')
        monthly[(r['touchpoint'], r['model'], ym)].append(r)
    mon_rows = []
    for (tp, model, ym), rs in monthly.items():
        accs = [x['accuracy'] for x in rs]
        rms = [x['rmse'] for x in rs]
        mon_rows.append({'touchpoint': tp, 'model': model, 'year_month': ym,
                         'mean_accuracy': round(float(np.mean(accs)), 1),
                         'std_accuracy': round(float(np.std(accs)), 1) if len(accs) > 1 else 0.0,
                         'mean_rmse': round(float(np.mean(rms)), 1), 'n_days': len(rs)})
    with open(OUT_MON, 'w', newline='', encoding='utf-8') as f:
        w = csvmod.DictWriter(f, fieldnames=['touchpoint', 'model', 'year_month',
                                             'mean_accuracy', 'std_accuracy', 'mean_rmse', 'n_days'])
        w.writeheader(); w.writerows(mon_rows)

    # monthly winner per touchpoint
    by_tp_ym = defaultdict(list)
    for r in mon_rows:
        by_tp_ym[(r['touchpoint'], r['year_month'])].append(r)
    win_rows = []
    for (tp, ym), rs in sorted(by_tp_ym.items()):
        rs.sort(key=lambda x: -x['mean_accuracy'])
        best, second = rs[0], rs[1] if len(rs) > 1 else rs[0]
        win_rows.append({'touchpoint': tp, 'year_month': ym, 'winner': best['model'],
                         'winner_accuracy': best['mean_accuracy'], 'runner_up': second['model'],
                         'runner_up_accuracy': second['mean_accuracy'],
                         'gap': round(best['mean_accuracy'] - second['mean_accuracy'], 1)})
    with open(OUT_WIN, 'w', newline='', encoding='utf-8') as f:
        w = csvmod.DictWriter(f, fieldnames=['touchpoint', 'year_month', 'winner', 'winner_accuracy',
                                             'runner_up', 'runner_up_accuracy', 'gap'])
        w.writeheader(); w.writerows(win_rows)

    print("-" * 82)
    print(f"wrote {os.path.relpath(OUT_DAY, ROOT)}  ({len(daily_rows)} rows)")
    print(f"wrote {os.path.relpath(OUT_MON, ROOT)}  ({len(mon_rows)} rows)")
    print(f"wrote {os.path.relpath(OUT_WIN, ROOT)}  ({len(win_rows)} rows)")
    print()
    print("=== winner-count per touchpoint (how many months each model won) ===")
    for tp in TOUCHPOINTS:
        sub = [r for r in win_rows if r['touchpoint'] == tp]
        counts = defaultdict(int)
        for r in sub:
            counts[r['winner']] += 1
        print(f"  {tp:<10} " + "  ".join(f"{m}={c}" for m, c in sorted(counts.items(), key=lambda x: -x[1])))
    print("\nREMINDER: simulated twin data -> pipeline test, NOT real accuracy.")


if __name__ == '__main__':
    main()
