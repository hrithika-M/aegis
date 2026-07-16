"""Day-wise / month-wise model competition — real HYD data.

Naveen's ask: don't collapse walk-forward into one aggregate accuracy number.
Show accuracy per TEST DAY and rolled up per MONTH, per touchpoint, per model —
so we can see which models actually compete well, and whether the winner is
consistent over time or just wins on average by offsetting good/bad days.

Same real trusted HYD data, same walk-forward (warmup=60, step=10), same
symmetric accuracy metric as the rest of modeling/ — this just keeps the
per-test-day results instead of discarding them.

Outputs:
  docs/daywise_accuracy.csv    one row per (touchpoint, model, test_date)
  docs/monthly_accuracy.csv    one row per (touchpoint, model, year_month)
  docs/monthly_winners.csv     one row per (touchpoint, year_month): best model,
                                its accuracy, and the gap to the runner-up

Run:  python -m modeling.eval_daywise
"""
import os
import time
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

from config import SHEET_NAMES, TOUCHPOINT_LABELS
from modeling.dataset import all_frames, FEATURES, TARGET
from modeling.estimators import zoo, zoo_extra, ALIASES
from modeling.evaluate import acc, predict, WARMUP, STEP

# competitive set — the same models select.py compares (floor models excluded;
# documented elsewhere as losing everywhere)
CANDIDATES = ['Naive-seasonal-7d', 'RandomForest [Naveen]', 'ExtraTrees',
              'HistGradientBoosting', 'LightGBM', 'XGBoost', 'Bagging(trees)']
NAME_TO_ALIAS = {v: k for k, v in ALIASES.items()}
DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')


def rmse(pred, actual):
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    m = actual > 0
    return float(np.sqrt(np.mean((pred[m] - actual[m]) ** 2))) if m.sum() else None


def mae(pred, actual):
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    m = actual > 0
    return float(np.mean(np.abs(pred[m] - actual[m]))) if m.sum() else None


def walk_forward_daywise(frame, spec, features=FEATURES, target=TARGET):
    """Like evaluate.walk_forward, but returns one row per test day instead of
    an aggregate."""
    days = sorted(frame['Date'].unique())
    rows = []
    for d in days[WARMUP::STEP]:
        tr, te = frame[frame['Date'] < d], frame[frame['Date'] == d]
        if len(te) == 0 or len(tr) < 50:
            continue
        p = predict(spec, tr, te, features, target)
        a = acc(p, te[target])
        if a is None:
            continue
        rows.append({'test_date': d, 'accuracy': round(a, 1),
                     'rmse': round(rmse(p, te[target]), 1),
                     'mae': round(mae(p, te[target]), 1), 'n_hours': len(te)})
    return rows


def main():
    print("=" * 78)
    print("DAY-WISE / MONTH-WISE MODEL COMPETITION — real trusted HYD EWS data")
    print("=" * 78)
    frames, _ = all_frames()
    allmodels = {**zoo(), **zoo_extra()}
    specs = {n: allmodels[n] for n in CANDIDATES}

    daily_rows = []
    t0 = time.time()
    for tp in SHEET_NAMES:
        frame = frames[tp]
        for name, spec in specs.items():
            for r in walk_forward_daywise(frame, spec):
                r2 = dict(r)
                r2['touchpoint'] = tp
                r2['model'] = name
                daily_rows.append(r2)
        print(f"  {TOUCHPOINT_LABELS.get(tp, tp):<22} done  ({time.time()-t0:.0f}s elapsed)")

    daily = pd.DataFrame(daily_rows)
    daily['year_month'] = pd.to_datetime(daily['test_date']).dt.strftime('%Y-%m')
    os.makedirs(DOC, exist_ok=True)
    daily.to_csv(os.path.join(DOC, 'daywise_accuracy.csv'), index=False)

    # monthly rollup
    monthly = (daily.groupby(['touchpoint', 'model', 'year_month'])
               .agg(mean_accuracy=('accuracy', 'mean'), std_accuracy=('accuracy', 'std'),
                    mean_rmse=('rmse', 'mean'), n_days=('accuracy', 'count'))
               .reset_index())
    monthly['mean_accuracy'] = monthly['mean_accuracy'].round(1)
    monthly['std_accuracy'] = monthly['std_accuracy'].round(1)
    monthly['mean_rmse'] = monthly['mean_rmse'].round(1)
    monthly.to_csv(os.path.join(DOC, 'monthly_accuracy.csv'), index=False)

    # monthly winner per touchpoint (who's actually competing well, and when)
    winners = []
    for (tp, ym), g in monthly.groupby(['touchpoint', 'year_month']):
        g = g.sort_values('mean_accuracy', ascending=False)
        best, second = g.iloc[0], g.iloc[1] if len(g) > 1 else g.iloc[0]
        winners.append({'touchpoint': tp, 'year_month': ym, 'winner': best['model'],
                         'winner_accuracy': best['mean_accuracy'],
                         'runner_up': second['model'], 'runner_up_accuracy': second['mean_accuracy'],
                         'gap': round(best['mean_accuracy'] - second['mean_accuracy'], 1)})
    win_df = pd.DataFrame(winners).sort_values(['touchpoint', 'year_month'])
    win_df.to_csv(os.path.join(DOC, 'monthly_winners.csv'), index=False)

    print("-" * 78)
    print(f"wrote docs/daywise_accuracy.csv    ({len(daily):,} rows)")
    print(f"wrote docs/monthly_accuracy.csv    ({len(monthly):,} rows)")
    print(f"wrote docs/monthly_winners.csv     ({len(win_df):,} rows)")
    print()
    print("=== overall winner-count per touchpoint (how many months each model won) ===")
    for tp in SHEET_NAMES:
        sub = win_df[win_df['touchpoint'] == tp]
        counts = sub['winner'].value_counts()
        label = TOUCHPOINT_LABELS.get(tp, tp)
        print(f"  {label:<22}" + "  ".join(f"{m}={c}" for m, c in counts.items()))
    print(f"\ntotal runtime: {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
