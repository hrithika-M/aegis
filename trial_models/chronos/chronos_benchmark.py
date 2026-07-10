# -*- coding: utf-8 -*-
"""Foundation-model forecasting benchmark on EWS demand (zero-shot vs our ML).

Fair, walk-forward, apples-to-apples on ONE hourly passenger series:
  Chronos-Bolt   Amazon's pretrained model, ZERO-SHOT (no training on our data)
  RandomForest   our ML approach, calendar features, trained per test day
  Naive-7d       same hour last week (the floor)

For each held-out day we predict its 24 hours and score with the project's
symmetric min/max accuracy, then average over test days.

The ONLY thing trained here is the RandomForest baseline (its .fit). Chronos is
loaded pretrained (from_pretrained) and only reads recent history as context —
that is what "zero-shot" means.

Requires (not core aegis deps — install once):
    pip install chronos-forecasting torch scikit-learn
Data:  data/<tp>.csv exported by export_data.py (gitignored — real EWS data).

Run:   python forecast_benchmark.py            # Entry
       python forecast_benchmark.py --tp pesc  # Security/PESC
       python forecast_benchmark.py --model amazon/chronos-bolt-small
"""
import argparse
import os
import time
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
# data lives at <repo>/data (trial_models/chronos/ -> ../../data)
REPO_DATA = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'data')
WARMUP, STEP, HORIZON, CTX = 60, 10, 24, 2048        # walk-forward + context window


def hourly_series(tp):
    path = os.path.join(REPO_DATA, f'{tp}.csv')
    df = pd.read_csv(path, usecols=['DateTime', 'Throughput'])
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    s = df.groupby(df['DateTime'].dt.floor('h'))['Throughput'].sum()
    full = pd.date_range(s.index.min(), s.index.max(), freq='h')   # fill gaps with 0
    return s.reindex(full, fill_value=0.0)


def acc(pred, actual):
    """Project metric: symmetric min/max ratio, averaged over active hours."""
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    m = (actual > 0) & (pred > 0)
    if m.sum() == 0:
        return None
    return float((np.minimum(actual[m], pred[m]) / np.maximum(actual[m], pred[m])).mean()) * 100


def calendar(idx):
    return pd.DataFrame({'hour': idx.hour, 'dow': idx.dayofweek, 'month': idx.month,
                         'weekofyear': idx.isocalendar().week.astype(int),
                         'is_weekend': (idx.dayofweek >= 5).astype(int)}, index=idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tp', default='entry', help='touchpoint file stem (entry|pesc|...)')
    ap.add_argument('--model', default='amazon/chronos-bolt-base')
    args = ap.parse_args()

    import torch
    from chronos import BaseChronosPipeline
    from sklearn.ensemble import RandomForestRegressor

    s = hourly_series(args.tp)
    print(f"{args.tp} hourly series: {len(s):,} points, {s.index.min()} .. {s.index.max()}")
    days = pd.date_range(s.index.min().normalize(), s.index.max().normalize(), freq='D')
    test_days = days[WARMUP::STEP]

    print(f"loading {args.model} (pretrained — NO training on our data) ...")
    t0 = time.time()
    pipe = BaseChronosPipeline.from_pretrained(args.model, device_map='cpu',
                                               torch_dtype=torch.float32)
    print(f"  loaded in {time.time()-t0:.0f}s")

    Xcal = calendar(s.index)
    feats = ['hour', 'dow', 'month', 'weekofyear', 'is_weekend']
    ch, rf_, nv, n = [], [], [], 0
    tc = time.time()
    for d in test_days:
        start, end = d, d + pd.Timedelta(hours=HORIZON - 1)
        if end > s.index.max():
            break
        hist = s[s.index < start]
        actual = s[start:end].values
        if len(hist) < 200 or len(actual) < HORIZON:
            continue
        n += 1
        # Chronos — zero-shot: read recent history, forecast (no .fit)
        ctx = torch.tensor(hist.values[-CTX:], dtype=torch.float32)
        q, _ = pipe.predict_quantiles(ctx, prediction_length=HORIZON, quantile_levels=[0.5])
        ch.append(acc(q[0, :, 0].numpy(), actual))
        # Naive same-hour-last-week
        wk = s[(start - pd.Timedelta(days=7)):(end - pd.Timedelta(days=7))].values
        if len(wk) == HORIZON:
            nv.append(acc(wk, actual))
        # RandomForest — the ONLY training here (baseline)
        tr = s.index < start
        rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(Xcal[tr][feats], s[tr].values)
        rf_.append(acc(rf.predict(Xcal.loc[start:end][feats]), actual))

    def mean(x):
        v = [a for a in x if a is not None]
        return round(float(np.mean(v)), 1) if v else None

    print(f"\n  tested {n} held-out days in {time.time()-tc:.0f}s\n")
    print(f"  {'Chronos-Bolt (zero-shot)':<28} {mean(ch)}%")
    print(f"  {'RandomForest (our ML)':<28} {mean(rf_)}%")
    print(f"  {'Naive-7d (floor)':<28} {mean(nv)}%")


if __name__ == '__main__':
    main()
