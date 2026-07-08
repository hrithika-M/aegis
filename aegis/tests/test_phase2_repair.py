# -*- coding: utf-8 -*-
"""Repair tests — planted faults must be FIXED to plausible values, with honest
confidence grades, and DRIFT must never be auto-corrected.

Run:  python -m aegis.tests.test_phase2_repair
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd

from aegis.connectors import canonicalise
from aegis.config import SourceCfg
from aegis.detect import detect
from aegis.repair import repair, summarize
from aegis.tests.test_phase1 import synthetic

CFG = SourceCfg(name='gates', kind='dataframe',
                columns={'datetime': 'ts', 'entity': 'gate', 'value': 'count'})


def _truth():
    """The clean values at the planted-fault spots (before injection)."""
    clean = synthetic()  # deterministic; then re-derive what WAS there pre-fault
    # synthetic() plants faults itself, so rebuild clean by regenerating pattern:
    rng = np.random.default_rng(21)
    rows = {}
    for d in pd.date_range('2025-01-01', periods=120, freq='D'):
        for h in range(24):
            for gate, k in (('Gate A', 1.0), ('Gate B', 1.2)):
                if 5 <= h <= 22:
                    v = max(0, (200 + 150 * np.sin((h - 5) / 17 * np.pi)) * k
                            + rng.normal(0, 12))
                else:
                    v = 0.0
                rows[(str(d.date()), h, gate)] = round(v)
    return rows


def _repaired():
    canon, _ = canonicalise(synthetic(), CFG)
    return repair(detect(canon))


def cell(t, d, h, e):
    r = t[(t['date'].astype(str) == d) & (t['time_bucket'] == h) & (t['entity'] == e)]
    assert len(r) == 1
    return r.iloc[0]


def test_blackout_filled_to_days_reality():
    t = _repaired()
    truth = _truth()
    for h in (8, 9, 10):
        r = cell(t, '2025-04-20', h, 'Gate A')
        true_v = truth[('2025-04-20', h, 'Gate A')]
        assert r['flag'] == 'BLACKOUT' and r['was_corrected']
        err = abs(r['value_adj'] - true_v) / true_v
        assert err < 0.25, f"h{h}: filled {r['value_adj']} vs true {true_v} ({err:.0%})"
        assert r['confidence'] == 'HIGH', r['confidence']  # day had >=6 healthy hours
    print("  PASS blackout filled near the TRUE values (day-scaled), HIGH confidence")


def test_spike_capped_and_low_restored():
    t = _repaired()
    s = cell(t, '2025-04-25', 2, 'Gate B')          # 5000 dumped into a silent hour
    assert s['flag'] == 'SPIKE' and s['value_adj'] <= 5, s['value_adj']
    lo = cell(t, '2025-04-25', 12, 'Gate B')        # sensor read 3, ~415 expected
    truth = _truth()[('2025-04-25', 12, 'Gate B')]
    assert lo['flag'] == 'LOW' and abs(lo['value_adj'] - truth) / truth < 0.25
    print("  PASS spike capped to silent-hour plausibility; LOW restored near truth")


def test_mostly_dark_day_gets_low_confidence():
    """If almost the whole day is dark, the activity factor is guesswork —
    fills must be graded LOW (handed to reconcile/escalation), never HIGH."""
    df = synthetic()
    day = pd.Timestamp('2025-03-05')
    mask = (df['ts'].dt.date == day.date()) & (df['gate'] == 'Gate A') & \
           (df['ts'].dt.hour.between(5, 21))       # kill 17 of 18 busy hours
    df.loc[mask, 'count'] = 0
    canon, _ = canonicalise(df, CFG)
    t = repair(detect(canon))
    fills = t[(t['date'].astype(str) == '2025-03-05') & (t['entity'] == 'Gate A')
              & t['was_corrected']]
    assert len(fills) >= 15
    assert (fills['confidence'] == 'LOW').all(), fills['confidence'].unique()
    print(f"  PASS mostly-dark day: {len(fills)} fills all graded LOW (not trusted blindly)")


def test_drift_never_autocorrected_and_physical_max():
    canon, _ = canonicalise(synthetic(), CFG)
    trust = detect(canon)
    t = repair(trust, physical_max=350)
    drift_rows = t[t['flag'] == 'DRIFT']
    if len(drift_rows):
        assert (drift_rows['value_adj'] == drift_rows['actual']).all()
    assert (t['value_adj'] <= 350).all(), "physical ceiling violated"
    s = summarize(t)
    assert s['corrected'] > 0 and 'HIGH' in s['by_confidence']
    print(f"  PASS drift untouched; physical ceiling enforced; summary={s['by_confidence']}")


if __name__ == '__main__':
    print("aegis phase-2 repair tests")
    print("-" * 52)
    test_blackout_filled_to_days_reality()
    test_spike_capped_and_low_restored()
    test_mostly_dark_day_gets_low_confidence()
    test_drift_never_autocorrected_and_physical_max()
    print("-" * 52)
    print("ALL TESTS PASSED")
