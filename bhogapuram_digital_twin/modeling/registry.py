# -*- coding: utf-8 -*-
"""Model registry — lightweight MLflow-style governance.

Every model-selection run is recorded with what it was trained on, its metrics, and
the champion + runner-up per touchpoint — so any deployed model is traceable to the
exact data and run that produced it. One entry per data version (re-running the same
data updates in place).

Reads:  analytics/model_selection_twin.csv, generated/passenger_5min.csv
Writes: modeling/model_registry.json

Run:  python registry.py
"""
import csv, hashlib, json, os
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEL = os.path.join(ROOT, 'analytics', 'model_selection_twin.csv')
DATA = os.path.join(ROOT, 'generated', 'passenger_5min.csv')
REG = os.path.join(HERE, 'model_registry.json')

try:
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'build'))
    from twin_version import SIMULATOR_VERSION
except Exception:
    SIMULATOR_VERSION = 'unknown'


def sha(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()[:16]


def num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def main():
    rows = list(csv.DictReader(open(SEL, encoding='utf-8')))
    by_tp = {}
    for r in rows:
        by_tp.setdefault(r['Touchpoint'], []).append(r)

    touchpoints = {}
    for tp, models in by_tp.items():
        ranked = sorted((m for m in models if num(m['Accuracy']) is not None),
                        key=lambda m: num(m['Accuracy']), reverse=True)
        real = [m for m in ranked if m['Model'] != 'Naive-7d']
        naive = next((m for m in ranked if m['Model'] == 'Naive-7d'), None)
        champ = real[0] if real else ranked[0]
        runner = real[1] if len(real) > 1 else None

        def pack(m):
            return {'model': m['Model'], 'accuracy': num(m['Accuracy']), 'rmse': num(m['RMSE']),
                    'mae': num(m['MAE']), 'r2': num(m['R2']),
                    'peak_recall': num(m.get('PeakRecall')), 'peak_f1': num(m.get('PeakF1'))}
        touchpoints[tp] = {
            'champion': pack(champ),
            'runner_up': pack(runner) if runner else None,
            'naive_baseline_accuracy': num(naive['Accuracy']) if naive else None,
            'beats_naive_baseline': (num(champ['Accuracy']) > num(naive['Accuracy'])) if naive else None,
        }

    run = {
        'run_id': dt.datetime.now().strftime('%Y%m%dT%H%M%S'),
        'timestamp': dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + 'Z',
        'data_source': 'twin (SIMULATED — pipeline test, not real accuracy)',
        'data_version_sha16': sha(DATA),
        'simulator_version': SIMULATOR_VERSION,
        'metric_primary': 'accuracy (symmetric min/max), full panel recorded',
        'touchpoints': touchpoints,
    }

    registry = {'runs': []}
    if os.path.exists(REG):
        registry = json.load(open(REG, encoding='utf-8'))
    # one entry per data version — replace if re-run on the same data
    registry['runs'] = [r for r in registry['runs'] if r.get('data_version_sha16') != run['data_version_sha16']]
    registry['runs'].append(run)
    registry['runs'].sort(key=lambda r: r['timestamp'])
    with open(REG, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2)

    print(f"model_registry.json — {len(registry['runs'])} run(s) recorded")
    print(f"  latest run {run['run_id']}  data {run['data_version_sha16']}  sim {SIMULATOR_VERSION}")
    for tp, d in touchpoints.items():
        c = d['champion']
        beat = 'beats naive' if d['beats_naive_baseline'] else 'ties/below naive'
        print(f"  {tp:<10} champion {c['model']:<14} acc={c['accuracy']} rmse={c['rmse']} recall={c['peak_recall']}  ({beat})")


if __name__ == '__main__':
    main()
