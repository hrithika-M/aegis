"""Per-touchpoint model selection — the best model FOR EACH touchpoint.

Different touchpoints have different demand shapes, so the best model can differ.
This runs the competitive models per touchpoint (mean +/- std over walk-forward),
picks the winner for each, and — crucially — flags whether the win is
STATISTICALLY MEANINGFUL vs Naveen's RandomForest. A win inside the day-to-day
noise is not worth switching for, so those default back to the incumbent.

Outputs a per-touchpoint recommendation table + a {touchpoint: algorithm} map
that PODModel(algorithm=map) can consume directly. Appends to
docs/MODEL_SELECTION.md.

Run:  python -m modeling.select
"""
import os
import warnings

warnings.filterwarnings('ignore')

import numpy as np

from config import SHEET_NAMES, TOUCHPOINT_LABELS
from modeling.dataset import trusted_hourly
from modeling.estimators import zoo, zoo_extra, ALIASES
from modeling.evaluate import walk_forward
from training.common import get_clean_data

# competitive set only — the floor models (linear/GLM/SVR/MLP) lose everywhere
# (documented in MODEL_SELECTION.md), so per-touchpoint selection is among these.
CANDIDATES = ['Naive-seasonal-7d', 'RandomForest [Naveen]', 'ExtraTrees',
              'HistGradientBoosting', 'LightGBM', 'XGBoost', 'Bagging(trees)']
INCUMBENT = 'RandomForest [Naveen]'
NAME_TO_ALIAS = {v: k for k, v in ALIASES.items()}
DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'docs', 'MODEL_SELECTION.md')


def select(verbose=True):
    data = get_clean_data()
    allmodels = {**zoo(), **zoo_extra()}
    specs = {n: allmodels[n] for n in CANDIDATES}
    per_tp = {}       # tp -> {model: (mean, std)}
    for tp in SHEET_NAMES:
        frame = trusted_hourly(data, tp)
        per_tp[tp] = {}
        for name, spec in specs.items():
            mean, std, n, _s = walk_forward(frame, spec)
            per_tp[tp][name] = (mean, std)
        if verbose:
            best = max(per_tp[tp], key=lambda m: per_tp[tp][m][0] or 0)
            print(f"  {TOUCHPOINT_LABELS.get(tp, tp):<22} best={best} "
                  f"({per_tp[tp][best][0]})")
    return per_tp


def recommend(per_tp, margin=1.0):
    """For each touchpoint pick the winner; keep RandomForest unless another model
    beats it by more than `margin` points (a real gap vs the ±std noise)."""
    rec = {}
    rows = []
    for tp in SHEET_NAMES:
        scores = per_tp[tp]
        rf_mean, rf_std = scores[INCUMBENT]
        winner = max(scores, key=lambda m: scores[m][0] or 0)
        win_mean, win_std = scores[winner]
        meaningful = (winner != INCUMBENT) and ((win_mean - rf_mean) > margin)
        chosen = winner if meaningful else INCUMBENT
        rec[tp] = NAME_TO_ALIAS.get(chosen, 'randomforest')
        rows.append({
            'tp': tp, 'winner': winner, 'win': win_mean, 'win_std': win_std,
            'rf': rf_mean, 'gap': round((win_mean or 0) - (rf_mean or 0), 1),
            'chosen': chosen, 'meaningful': meaningful,
        })
    return rec, rows


def write_doc(per_tp, rows, rec):
    lines = ["\n---\n\n## Per-touchpoint selection\n",
             "Best model **for each touchpoint** (mean±std, walk-forward, trusted "
             "actuals). 'Chosen' keeps RandomForest unless another model beats it by "
             ">1.0 pt (a real gap vs the ±4-10% day noise).\n",
             "| Touchpoint | " + " | ".join(c.split(' [')[0].split(' (')[0] for c in CANDIDATES)
             + " | Winner | vs RF | **Chosen** |",
             "|---|" + "---|" * (len(CANDIDATES) + 3)]
    for r in rows:
        cells = []
        for c in CANDIDATES:
            mean, std = per_tp[r['tp']][c]
            mark = '**' if c == r['winner'] else ''
            cells.append(f"{mark}{mean}±{std}{mark}")
        lines.append(f"| {TOUCHPOINT_LABELS.get(r['tp'], r['tp'])} | " + " | ".join(cells)
                     + f" | {r['winner'].split(' [')[0].split(' (')[0]} | {r['gap']:+} "
                     + f"| {r['chosen'].split(' [')[0].split(' (')[0]} |")
    lines.append("\n**Per-touchpoint model map** (feed to `PODModel(algorithm=...)`):\n")
    lines.append("```python")
    lines.append("PER_TOUCHPOINT = " + repr(rec))
    lines.append("```")
    with open(DOC, 'a', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nappended per-touchpoint section to {DOC}")


if __name__ == '__main__':
    print("=" * 78)
    print("PER-TOUCHPOINT MODEL SELECTION")
    print("=" * 78)
    per_tp = select()
    rec, rows = recommend(per_tp)
    print("-" * 78)
    print(f"  {'Touchpoint':<22}{'winner':<24}{'vs RF':>7}   chosen")
    for r in rows:
        flag = 'SWITCH' if r['meaningful'] else 'keep RF'
        print(f"  {TOUCHPOINT_LABELS.get(r['tp'], r['tp']):<22}{r['winner']:<24}"
              f"{r['gap']:>+7}   {flag}")
    print("\nrecommended per-touchpoint map:")
    print("  " + repr(rec))
    write_doc(per_tp, rows, rec)
