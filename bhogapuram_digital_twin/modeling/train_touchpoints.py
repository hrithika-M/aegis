# -*- coding: utf-8 -*-
"""Per-touchpoint model selection for Bhogapuram (VTZ) — READY FOR REAL DATA.

Same methodology as the HYD POD work: a model zoo compared with expanding-window
walk-forward backtesting on the project's symmetric min/max accuracy metric, one
winner picked per touchpoint.

>>> THE ONE THING THAT CHANGES WHEN REAL DATA ARRIVES <<<
Only `load_touchpoint_hourly()` below. Today it reads the SIMULATED twin
(generated/passenger_5min.csv). When Bhogapuram opens (2026-07-08) and real sensor
counts start flowing, point that function at the real EWS export instead — the
model zoo, features, metric, walk-forward and selection all stay identical, and the
accuracies it prints become REAL accuracies.

HONEST NOTE: run on the twin, the numbers will be optimistically high (~95%+) — the
data is model-generated, so the models partly relearn our own assumptions. Treat
today's output as a pipeline/template check, not a real accuracy claim.

VTZ touchpoints (what a domestic point-to-point airport actually has):
  CheckIn, Security, Boarding (departures) + Belt (arrivals).
(HYD's Emigration/Immigration/Transfers don't meaningfully exist at VTZ.)

Run:  python train_touchpoints.py
"""
import csv, os, warnings
warnings.simplefilter('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIVE = os.path.join(ROOT, 'generated', 'passenger_5min.csv')
OUT = os.path.join(ROOT, 'analytics', 'model_selection_twin.csv')

# touchpoint -> column in the 5-min dataset (swap the SOURCE, keep the mapping)
TOUCHPOINTS = {'CheckIn': 'checkin_demand', 'Security': 'security_demand',
               'Boarding': 'boarding_demand', 'Belt': 'belt_demand'}
FEATURES = ['DayOfWeek', 'Month', 'IsWeekend', 'WeekOfYear', 'Hour']
WARMUP, STEP = 45, 7


# ------------------------------------------------------------------ DATA SOURCE
def load_touchpoint_hourly(touchpoint):
    """Return list of dict rows {Date, Hour, + features, demand} for one touchpoint.

    *** SWAP THIS FUNCTION FOR REAL SENSOR DATA LATER — nothing else changes. ***
    Today: aggregates the simulated 5-min twin to hourly demand.
    """
    import datetime as dt
    col = TOUCHPOINTS[touchpoint]
    agg = defaultdict(float)
    with open(FIVE, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            ts = r['timestamp']
            d = dt.date.fromisoformat(ts[:10]); h = int(ts[11:13])
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
    z = {
        'RandomForest': lambda: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'ExtraTrees': lambda: ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'HistGradientBoosting': lambda: HistGradientBoostingRegressor(random_state=42),
    }
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


def acc(pred, actual):
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    m = (actual > 0) & (pred > 0)
    if m.sum() == 0:
        return None
    return float((np.minimum(actual[m], pred[m]) / np.maximum(actual[m], pred[m])).mean()) * 100


def walk_forward(rows, make):
    days = sorted({r['Date'] for r in rows})
    test_days = days[WARMUP::STEP]
    scores = []
    for td in test_days:
        tr = [r for r in rows if r['Date'] < td]
        te = [r for r in rows if r['Date'] == td]
        if len(tr) < 100 or not te:
            continue
        Xtr = np.array([[r[f] for f in FEATURES] for r in tr]); ytr = [r['demand'] for r in tr]
        Xte = np.array([[r[f] for f in FEATURES] for r in te]); yte = [r['demand'] for r in te]
        m = make().fit(Xtr, ytr)
        a = acc(m.predict(Xte), yte)
        if a is not None:
            scores.append(a)
    if not scores:
        return None, None
    return round(float(np.mean(scores)), 1), round(float(np.std(scores)), 1)


def naive_seasonal(rows):
    """7-day seasonal naive baseline, walk-forward."""
    days = sorted({r['Date'] for r in rows})
    idx = {(r['Date'], r['Hour']): r['demand'] for r in rows}
    import datetime as dt
    scores = []
    for td in days[WARMUP::STEP]:
        te = [r for r in rows if r['Date'] == td]
        p, a = [], []
        for r in te:
            prev = idx.get((td - dt.timedelta(days=7), r['Hour']))
            if prev is not None:
                p.append(prev); a.append(r['demand'])
        s = acc(p, a) if p else None
        if s is not None:
            scores.append(s)
    return (round(float(np.mean(scores)), 1), round(float(np.std(scores)), 1)) if scores else (None, None)


def main():
    models = zoo()
    print("=" * 74)
    print("VTZ PER-TOUCHPOINT MODEL SELECTION  [pipeline test on SIMULATED twin data]")
    print("=" * 74)
    header = ['Touchpoint'] + list(models.keys()) + ['Naive-7d', 'BEST']
    results = {}
    rows_out = []
    for tp in TOUCHPOINTS:
        data = load_touchpoint_hourly(tp)
        per = {}
        for name, make in models.items():
            mean, std = walk_forward(data, make)
            per[name] = mean
        nm, _ = naive_seasonal(data)
        per['Naive-7d'] = nm
        best = max((k for k in per if per[k] is not None), key=lambda k: per[k])
        results[tp] = (per, best)
        cells = [tp] + [f"{per[k]}" if per[k] is not None else "-" for k in list(models.keys()) + ['Naive-7d']] + [best]
        rows_out.append(cells)
        print(f"  {tp:<10} " + "  ".join(f"{k}={per[k]}" for k in models if per[k] is not None)
              + f"  Naive={nm}  -> BEST: {best} ({per[best]})")

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows_out)
    print("-" * 74)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print("NOTE: simulated-data numbers are optimistic. Swap load_touchpoint_hourly()")
    print("      for real EWS data (post-2026-07-08) to get REAL per-touchpoint accuracies.")


if __name__ == '__main__':
    main()
