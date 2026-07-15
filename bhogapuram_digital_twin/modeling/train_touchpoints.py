# -*- coding: utf-8 -*-
"""Per-touchpoint model selection for Bhogapuram (VTZ) — READY FOR REAL DATA.

Same methodology as the HYD POD work: a model zoo compared with expanding-window
walk-forward backtesting, one winner per touchpoint. Reports a FULL metric panel,
not a single number:

  Regression:      Accuracy (symmetric min/max), RMSE, MAE, MAPE, R2
  Classification:  Peak-hour detection precision / recall / F1
                   (peak = actual demand >= 80th percentile -> the busy hours you
                    must staff for; recall = share of real peaks the model caught)

>>> THE ONE THING THAT CHANGES WHEN REAL DATA ARRIVES <<<
Only `load_touchpoint_hourly()`. Today it reads the SIMULATED twin
(generated/passenger_5min.csv). Point it at the real EWS export when Bhogapuram
opens (2026-07-08) — the zoo, features, metrics, walk-forward and selection stay
identical, and the numbers become REAL.

HONEST NOTE: on the twin the data is deterministic, so scores are optimistic and the
naive baseline ties the ML models. Treat today's output as a pipeline/template check.

VTZ touchpoints: CheckIn, Security, Boarding (departures) + Belt (arrivals).

Run:  python train_touchpoints.py
"""
import csv, os, warnings
warnings.simplefilter('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'
from collections import defaultdict
import datetime as dt
import numpy as np
from sklearn.metrics import r2_score, precision_score, recall_score, f1_score

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIVE = os.path.join(ROOT, 'generated', 'passenger_5min.csv')
OUT = os.path.join(ROOT, 'analytics', 'model_selection_twin.csv')

TOUCHPOINTS = {'CheckIn': 'checkin_demand', 'Security': 'security_demand',
               'Boarding': 'boarding_demand', 'Belt': 'belt_demand'}
FEATURES = ['DayOfWeek', 'Month', 'IsWeekend', 'WeekOfYear', 'Hour']
WARMUP, STEP = 45, 7
PEAK_PCTL = 80          # "peak hour" = demand at/above this percentile


# ------------------------------------------------------------------ DATA SOURCE
def load_touchpoint_hourly(touchpoint):
    """{Date,Hour,features,demand} rows for one touchpoint.
    *** SWAP THIS FUNCTION FOR REAL SENSOR DATA — nothing else changes. ***"""
    col = TOUCHPOINTS[touchpoint]
    agg = defaultdict(float)
    with open(FIVE, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            d = dt.date.fromisoformat(r['timestamp'][:10]); h = int(r['timestamp'][11:13])
            agg[(d, h)] += float(r[col])
    rows = []
    for (d, h), v in sorted(agg.items()):
        rows.append({'Date': d, 'Hour': h, 'DayOfWeek': d.weekday(), 'Month': d.month,
                     'IsWeekend': int(d.weekday() >= 5), 'WeekOfYear': int(d.strftime('%W')),
                     'demand': v})
    return rows
# -----------------------------------------------------------------------------


def zoo():
    from sklearn.ensemble import (RandomForestRegressor, ExtraTreesRegressor,
                                  HistGradientBoostingRegressor)
    z = {'RandomForest': lambda: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
         'ExtraTrees': lambda: ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1),
         'HistGradientBoosting': lambda: HistGradientBoostingRegressor(random_state=42)}
    try:
        from lightgbm import LGBMRegressor
        z['LightGBM'] = lambda: LGBMRegressor(n_estimators=300, learning_rate=0.05, random_state=42, verbose=-1)
    except Exception:
        pass
    try:
        from xgboost import XGBRegressor
        z['XGBoost'] = lambda: XGBRegressor(n_estimators=300, learning_rate=0.05, random_state=42, verbosity=0)
    except Exception:
        pass
    return z


def walk_forward_pool(rows, make):
    """Return pooled (pred, actual) over all walk-forward test days."""
    days = sorted({r['Date'] for r in rows})
    P, A = [], []
    for td in days[WARMUP::STEP]:
        tr = [r for r in rows if r['Date'] < td]
        te = [r for r in rows if r['Date'] == td]
        if len(tr) < 100 or not te:
            continue
        Xtr = np.array([[r[f] for f in FEATURES] for r in tr]); ytr = [r['demand'] for r in tr]
        Xte = np.array([[r[f] for f in FEATURES] for r in te])
        m = make().fit(Xtr, ytr)
        P.extend(m.predict(Xte)); A.extend([r['demand'] for r in te])
    return np.array(P, float), np.array(A, float)


def naive_pool(rows):
    idx = {(r['Date'], r['Hour']): r['demand'] for r in rows}
    days = sorted({r['Date'] for r in rows})
    P, A = [], []
    for td in days[WARMUP::STEP]:
        for r in [x for x in rows if x['Date'] == td]:
            prev = idx.get((td - dt.timedelta(days=7), r['Hour']))
            if prev is not None:
                P.append(prev); A.append(r['demand'])
    return np.array(P, float), np.array(A, float)


def metrics(P, A):
    if len(A) == 0:
        return None
    m = (A > 0) & (P > 0)
    acc = float((np.minimum(A[m], P[m]) / np.maximum(A[m], P[m])).mean()) * 100 if m.sum() else 0
    rmse = float(np.sqrt(np.mean((P - A) ** 2)))
    mae = float(np.mean(np.abs(P - A)))
    ma = A > 0
    mape = float(np.mean(np.abs(P[ma] - A[ma]) / A[ma]) * 100) if ma.sum() else 0
    r2 = float(r2_score(A, P))
    thr = np.percentile(A[A > 0], PEAK_PCTL) if (A > 0).sum() else 0
    yt, yp = (A >= thr).astype(int), (P >= thr).astype(int)
    prec = float(precision_score(yt, yp, zero_division=0))
    rec = float(recall_score(yt, yp, zero_division=0))
    f1 = float(f1_score(yt, yp, zero_division=0))
    return {'Accuracy': round(acc, 1), 'RMSE': round(rmse, 1), 'MAE': round(mae, 1),
            'MAPE': round(mape, 1), 'R2': round(r2, 3),
            'PeakPrecision': round(prec, 3), 'PeakRecall': round(rec, 3), 'PeakF1': round(f1, 3)}


def main():
    models = zoo()
    cols = ['Accuracy', 'RMSE', 'MAE', 'MAPE', 'R2', 'PeakPrecision', 'PeakRecall', 'PeakF1']
    print("=" * 92)
    print("VTZ PER-TOUCHPOINT MODEL SELECTION  [pipeline test on SIMULATED twin data]")
    print("Accuracy/MAPE in %, higher acc better, lower RMSE/MAE/MAPE better, R2->1, Peak* -> 1")
    print("=" * 92)
    out_rows = []
    for tp in TOUCHPOINTS:
        data = load_touchpoint_hourly(tp)
        runs = {name: metrics(*walk_forward_pool(data, make)) for name, make in models.items()}
        runs['Naive-7d'] = metrics(*naive_pool(data))
        best = max(runs, key=lambda k: runs[k]['Accuracy'])
        print(f"\n### {tp}   (best by accuracy: {best})")
        print(f"  {'Model':<20}" + "".join(f"{c:>15}" for c in cols))
        for name, mt in runs.items():
            star = '  <=' if name == best else ''
            print(f"  {name:<20}" + "".join(f"{str(mt[c]):>15}" for c in cols) + star)
            out_rows.append([tp, name] + [mt[c] for c in cols] + ['BEST' if name == best else ''])

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Touchpoint', 'Model'] + cols + ['Selected'])
        w.writerows(out_rows)
    print("\n" + "-" * 92)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print("Peak = demand >= 80th percentile (the busy hours to staff for);")
    print("PeakRecall = share of real peaks the model caught. Swap load_touchpoint_hourly()")
    print("for real EWS data (post-2026-07-08) to get REAL metrics.")


if __name__ == '__main__':
    main()
