"""Train and save the BEST model per touchpoint.

The walk-forward selection study (docs/MODEL_SELECTION.md) identified the highest-
accuracy algorithm for each touchpoint. This fits that winner on the full trusted
history and saves one compact artifact per touchpoint, plus a manifest recording
the algorithm, walk-forward accuracy, features, and target for each.

These are the models worth keeping — one per touchpoint — instead of the full 4GB
zoo. Honesty note: every winner is within ~1 pt of RandomForest (day-to-day noise),
so in production RF-for-all is equally defensible; these are the *nominal* winners.

Run from DATA_POD:  python -m modeling.train_best
"""
import json
import os
import warnings
warnings.filterwarnings('ignore')

import joblib

from modeling.dataset import trusted_hourly, FEATURES, TARGET
from modeling.estimators import zoo, zoo_extra
from training.common import get_clean_data

# touchpoint -> (zoo name, walk-forward accuracy from MODEL_SELECTION.md)
BEST = {
    'Entry':       ('RandomForest [Naveen]', 87.6),
    'CheckIn':     ('LightGBM',              88.3),
    'Emigration':  ('LightGBM',              80.1),
    'Immigration': ('XGBoost',               67.1),
    'PESC':        ('LightGBM',              90.9),
    'Transfers':   ('LightGBM',              77.8),
}

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'modeling', 'best_per_touchpoint')


def main():
    allmodels = {**zoo(), **zoo_extra()}
    os.makedirs(OUT, exist_ok=True)
    data = get_clean_data()
    manifest = {}
    print("=" * 66)
    print("TRAIN BEST MODEL PER TOUCHPOINT")
    print("=" * 66)
    for tp, (model_name, wf_acc) in BEST.items():
        frame = trusted_hourly(data, tp)
        frame = frame.dropna(subset=[TARGET])
        est = allmodels[model_name]()               # fresh estimator
        est.fit(frame[FEATURES], frame[TARGET])
        algo = model_name.split(' [')[0]            # strip "[Naveen]"
        fname = f"{tp.lower()}_{algo.lower()}.pkl"
        path = os.path.join(OUT, fname)
        joblib.dump(est, path, compress=3)          # compress -> small artifact
        size_mb = os.path.getsize(path) / 1048576
        manifest[tp] = {
            'algorithm': algo,
            'artifact': fname,
            'walk_forward_accuracy': wf_acc,
            'features': FEATURES,
            'target': TARGET,
            'trained_on_rows': int(len(frame)),
            'size_mb': round(size_mb, 2),
        }
        print(f"  {tp:<12} {algo:<14} acc={wf_acc:<5} "
              f"rows={len(frame):>6,}  ->  {fname} ({size_mb:.2f} MB)")
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    total = sum(m['size_mb'] for m in manifest.values())
    print("-" * 66)
    print(f"  saved {len(manifest)} models + manifest.json to {OUT}  ({total:.1f} MB total)")


if __name__ == '__main__':
    main()
