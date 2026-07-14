"""Benchmark — the model-selection experiment (thin; uses the shared core).

Runs every algorithm in estimators.zoo() (or zoo_extra) through the shared
walk-forward ruler on the shared trusted dataset, ranks them, and appends the
result to docs/model_trials.md. See docs/MODEL_SELECTION.md for the write-up.

Run:  python -m modeling.benchmark            # batch 1 (10 models)
      python -m modeling.benchmark --extra    # batch 2 (10 more)
      python -m modeling.benchmark --tp PESC  # single touchpoint (fast)
"""
import argparse
import os
import time
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

import numpy as np

from config import SHEET_NAMES, TOUCHPOINT_LABELS
from modeling.dataset import all_frames, trusted_hourly
from modeling.estimators import zoo, zoo_extra
from modeling.evaluate import walk_forward, WARMUP, STEP
from training.common import get_clean_data

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'docs', 'model_trials.md')


def run(touchpoints, extra=False, verbose=True):
    data = get_clean_data()
    frames = {tp: trusted_hourly(data, tp) for tp in touchpoints}
    models = zoo_extra() if extra else zoo()
    results = {name: {} for name in models}
    for name, spec in models.items():
        for tp in touchpoints:
            mean, _std, _n, _s = walk_forward(frames[tp], spec)
            results[name][tp] = mean
        vals = [v for v in results[name].values() if v is not None]
        results[name]['AVG'] = round(float(np.mean(vals)), 1) if vals else None
        if verbose:
            print(f"  {name:<24} avg={results[name]['AVG']:>5}   "
                  + '  '.join(f'{tp[:4]}={results[name][tp]}' for tp in touchpoints))
    return results


def write_log(results, touchpoints):
    ranked = sorted(results.items(), key=lambda kv: -(kv[1]['AVG'] or 0))
    lines = [f"\n## Trial run — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"Task: hourly PAX per touchpoint · trusted actuals · walk-forward "
             f"(warmup={WARMUP}, step={STEP}) · symmetric accuracy.\n",
             "| Rank | Model | AVG | " + " | ".join(TOUCHPOINT_LABELS.get(t, t) for t in touchpoints) + " |",
             "|---|---|---|" + "---|" * len(touchpoints)]
    for i, (name, r) in enumerate(ranked, 1):
        lines.append(f"| {i} | {name} | **{r['AVG']}** | "
                     + " | ".join(str(r[t]) for t in touchpoints) + " |")
    header = ""
    if not os.path.exists(LOG):
        header = ("# POD Model Trials — Record\n\nEvery algorithm benchmarked for the "
                  "POD demand model, on the honest walk-forward ruler over the trusted "
                  "actuals. Higher = better. RandomForest is Naveen's incumbent.\n")
    with open(LOG, 'a', encoding='utf-8') as f:
        if header:
            f.write(header)
        f.write("\n".join(lines) + "\n")
    print(f"\nlogged {len(ranked)} models to {LOG}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tp', default=None, help='single touchpoint (default: all 6)')
    ap.add_argument('--extra', action='store_true', help='run the second batch')
    args = ap.parse_args()
    tps = [args.tp] if args.tp else list(SHEET_NAMES)
    print("=" * 92)
    print(f"MODEL BENCHMARK{' [extra]' if args.extra else ''} — {len(tps)} touchpoint(s), "
          "walk-forward, trusted actuals")
    print("=" * 92)
    t0 = time.time()
    res = run(tps, extra=args.extra)
    print("-" * 92)
    print("RANKING (by average accuracy):")
    for i, (name, r) in enumerate(sorted(res.items(), key=lambda kv: -(kv[1]['AVG'] or 0)), 1):
        tag = '  <-- incumbent' if 'Naveen' in name else ''
        print(f"  {i:>2}. {name:<24} {r['AVG']}%{tag}")
    write_log(res, tps)
    print(f"total {time.time()-t0:.0f}s")
