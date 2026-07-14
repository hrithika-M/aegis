"""Plan — the operational output: train the selected model on trusted data and
emit a Plan of the Day for any future date (thin; uses the shared core).

How POD works: a plan for a future date, produced ahead of time (T-n) and refined
day-by-day, final at T-1. Refinement is driven by fresh info arriving (updated
schedule, booking loads at T-7/T-3/T-1, recent actuals).

Today (calendar features only) the plan is the "typical day of this type" and is
horizon-invariant (same T-7 as T-1). The refinement hook is `extra_features` +
the `extra` argument to plan_of_day: when the real feeds arrive they join as
feature columns and the same code refines by lead time — no rewrite. Re-run
`modeling.benchmark` to re-select the algorithm on the new data.

Run:  python -m modeling.plan --date 2026-04-15 --algorithm lightgbm
"""
import argparse
from datetime import datetime

import pandas as pd

from config import SHEET_NAMES
from data_processor.prescription import prescribe_hour
from data_processor.features import add_date_feature_columns
from data_trust.integrate import median_pt
from modeling.dataset import FEATURES, TARGET, trusted_hourly
from modeling.estimators import make
from training.common import get_clean_data


class PODModel:
    def __init__(self, algorithm='randomforest', extra_features=None):
        """`algorithm` is either a single short name applied to every touchpoint,
        or a dict {touchpoint: short_name} to use the best model PER touchpoint
        (see modeling.select). Unlisted touchpoints fall back to RandomForest."""
        self.algorithm = algorithm
        self.features = list(FEATURES) + list(extra_features or [])
        self.models = {}
        self.pt = {}
        self.trained_on = None

    def _algo_for(self, tp):
        if isinstance(self.algorithm, dict):
            return self.algorithm.get(tp, 'randomforest')
        return self.algorithm

    def train(self, data=None, verbose=True):
        data = data or get_clean_data()
        for tp in SHEET_NAMES:
            g = trusted_hourly(data, tp)                 # trusted (cleaned) target
            feats = [f for f in self.features if f in g.columns]
            algo = self._algo_for(tp)
            self.models[tp] = make(algo).fit(g[feats], g[TARGET])
            self.pt[tp] = median_pt(data, tp)
            self.trained_on = (str(g['Date'].min()), str(g['Date'].max()))
            if verbose:
                print(f"  trained {tp:<12} on {len(g):,} trusted rows ({algo})")
        return self

    def _rows(self, target_date, extra=None):
        f = pd.DataFrame({'Date': [target_date] * 24, 'Hour': list(range(24))})
        f = add_date_feature_columns(f)
        if extra is not None:                            # refinement inputs, when available
            f = f.merge(extra, on='Hour', how='left')
        return f

    def plan_of_day(self, target_date, staffing=True, extra=None):
        """Plan of the Day: per touchpoint x hour predicted PAX (+ lanes)."""
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        rows = []
        for tp, model in self.models.items():
            fr = self._rows(target_date, extra)
            feats = [f for f in self.features if f in fr.columns]
            pax = model.predict(fr[feats]).clip(min=0).round()
            for h in range(24):
                rec = {'touchpoint': tp, 'hour': h, 'predicted_pax': int(pax[h])}
                if staffing:
                    rec['lanes'] = prescribe_hour(tp, pax[h], self.pt[tp])['lanes_needed']
                rows.append(rec)
        return pd.DataFrame(rows)


def summarise(plan):
    piv = plan.pivot_table(index='hour', columns='touchpoint',
                           values='predicted_pax', aggfunc='sum')
    piv = piv[[c for c in SHEET_NAMES if c in piv.columns]]
    piv['TOTAL'] = piv.sum(axis=1)
    return piv


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='2026-04-15')
    ap.add_argument('--algorithm', default='randomforest',
                    help='randomforest | lightgbm | xgboost')
    args = ap.parse_args()
    print("=" * 70)
    print(f"POD MODELLING LAYER — plan for {args.date}  (model: {args.algorithm})")
    print("=" * 70)
    m = PODModel(algorithm=args.algorithm).train()
    print(f"\ntrained on trusted actuals {m.trained_on[0]} .. {m.trained_on[1]}")
    piv = summarise(m.plan_of_day(args.date))
    print("\nPLAN OF THE DAY — hourly predicted passengers per touchpoint:")
    print(piv.to_string())
    print(f"\nDaily total: {int(piv['TOTAL'].sum()):,} pax   "
          f"Peak: {int(piv['TOTAL'].idxmax()):02d}:00 ({int(piv['TOTAL'].max()):,} pax)")
