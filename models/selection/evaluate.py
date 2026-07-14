"""Evaluate — the ONE honest walk-forward ruler + accuracy metric.

Expanding-window walk-forward: for each test day, train on all prior days,
predict that day, score. This is the evaluation every modelling file now shares
(was duplicated in benchmark, backtest, eval_features, intervals).
"""
import time

import numpy as np
import pandas as pd

from modeling.dataset import FEATURES, TARGET

WARMUP, STEP = 60, 10


def acc(pred, actual):
    """Symmetric min/max accuracy (matches the project's holdout metric)."""
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    m = (actual > 0) & (pred > 0)
    if m.sum() == 0:
        return None
    return float((np.minimum(actual[m], pred[m]) / np.maximum(actual[m], pred[m])).mean()) * 100


def predict(spec, tr, te, features=FEATURES, target=TARGET):
    """Fit-and-predict one train/test split. `spec` is an estimator factory or a
    naive-baseline tag ('naive_seasonal' | 'naive_median')."""
    if spec == 'naive_seasonal':                       # same hour, 7 days earlier
        d0 = te['Date'].iloc[0]
        wk = tr[tr['Date'] == (d0 - pd.Timedelta(days=7))].set_index('Hour')[target]
        med = tr.groupby('Hour')[target].median()
        return te['Hour'].map(lambda h: wk.get(h, med.get(h, np.nan))).values
    if spec == 'naive_median':                         # median by (day-of-week, hour)
        med = tr.groupby(['DayOfWeek', 'Hour'])[target].median()
        return te.apply(lambda r: med.get((r['DayOfWeek'], r['Hour']), np.nan), axis=1).values
    model = spec()
    model.fit(tr[features], tr[target])
    return model.predict(te[features])


def walk_forward(frame, spec, features=FEATURES, target=TARGET, warmup=WARMUP, step=STEP):
    """Return (mean_acc, std_acc, n_days, seconds) for one model on one frame."""
    days = sorted(frame['Date'].unique())
    accs, t0 = [], time.time()
    for d in days[warmup::step]:
        tr, te = frame[frame['Date'] < d], frame[frame['Date'] == d]
        if len(te) == 0 or len(tr) < 50:
            continue
        a = acc(predict(spec, tr, te, features, target), te[target])
        if a is not None:
            accs.append(a)
    if not accs:
        return None, None, 0, 0.0
    return (round(float(np.mean(accs)), 1), round(float(np.std(accs)), 1),
            len(accs), round(time.time() - t0, 1))
