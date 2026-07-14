"""Ad-hoc trial: does CatBoost beat our incumbent RandomForest?

CatBoost was the one major gradient-boosting library missing from the 20-model
benchmark. This runs it on the IDENTICAL footing — same trusted hourly data,
same 7 calendar features, same symmetric min/max metric, same expanding-window
walk-forward (warmup=60, step=10) — with RandomForest run alongside as the
reference anchor, so the comparison is apples-to-apples.

Run from DATA_POD:  python -m modeling.try_catboost
"""
import warnings
warnings.filterwarnings('ignore')

import numpy as np
from catboost import CatBoostRegressor
from sklearn.ensemble import RandomForestRegressor

from config import SHEET_NAMES, TOUCHPOINT_LABELS
from modeling.dataset import trusted_hourly
from modeling.evaluate import walk_forward
from training.common import get_clean_data


def make_catboost():
    # parallel to LightGBM/XGBoost in the zoo: 300 trees, lr 0.05
    return CatBoostRegressor(iterations=300, learning_rate=0.05, depth=6,
                             random_seed=42, verbose=False, allow_writing_files=False)


def make_rf():
    return RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)


if __name__ == '__main__':
    print("=" * 74)
    print("CATBOOST TRIAL — vs RandomForest, identical walk-forward footing")
    print("=" * 74)
    data = get_clean_data()
    cat_scores, rf_scores = [], []
    print(f"  {'Touchpoint':<22}{'CatBoost':>14}{'RandomForest':>16}{'gap':>8}")
    print("  " + "-" * 58)
    for tp in SHEET_NAMES:
        frame = trusted_hourly(data, tp)
        cm, cs, cn, _ = walk_forward(frame, make_catboost)
        rm, rs, rn, _ = walk_forward(frame, make_rf)
        cat_scores.append(cm)
        rf_scores.append(rm)
        gap = round((cm or 0) - (rm or 0), 1)
        label = TOUCHPOINT_LABELS.get(tp, tp)
        print(f"  {label:<22}{cm:>8}±{cs:<5}{rm:>10}±{rs:<5}{gap:>+8}")
    ca, ra = round(np.mean(cat_scores), 1), round(np.mean(rf_scores), 1)
    print("  " + "-" * 58)
    print(f"  {'AVERAGE':<22}{ca:>14}{ra:>16}{round(ca - ra, 1):>+8}")
    print()
    if ca > ra + 1.0:
        print(f"  => CatBoost wins by {round(ca - ra, 1)} pts (meaningful).")
    elif ca < ra - 1.0:
        print(f"  => RandomForest still better by {round(ra - ca, 1)} pts.")
    else:
        print(f"  => TIE (within +/-1.0 pt day noise). No reason to switch.")
