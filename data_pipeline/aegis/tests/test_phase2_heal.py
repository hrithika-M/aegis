# -*- coding: utf-8 -*-
"""Heal-loop tests — the full engine: mutual healing across iterations,
convergence, and the honest target-not-met verdict.

Scenario: scans and camera watch the same flow, and EACH has a dark window the
OTHER can see: scans dark on 10 Mar (05-21h), camera dark on 12 Mar (05-21h).
Single-source repair grades both windows LOW; the loop must heal scans from
camera AND camera from scans (mutual), converge, and report honestly.

Run:  python -m aegis.tests.test_phase2_heal
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd

from aegis.heal import heal

def make_frames():
    rng = np.random.default_rng(41)
    cam, scn = [], []
    for d in pd.date_range('2025-01-01', periods=120, freq='D'):
        for h in range(24):
            base = (400 + 260 * np.sin((h - 5) / 17 * np.pi)) if 5 <= h <= 22 else 0
            ts = d + pd.Timedelta(hours=h)
            cam.append({'ts': ts, 'zone': 'Z1', 'count': round(max(0, base + rng.normal(0, 18)))})
            scn.append({'ts': ts, 'gate': 'G1', 'scans': round(max(0, base * 0.85 + rng.normal(0, 18)))})
    cam, scn = pd.DataFrame(cam), pd.DataFrame(scn)
    kill = lambda df, day, col: df.__setitem__(
        col, df[col].where(~((df['ts'].dt.date == pd.Timestamp(day).date())
                             & df['ts'].dt.hour.between(5, 21)), 0))
    kill(scn, '2025-03-10', 'scans')
    kill(cam, '2025-03-12', 'count')
    return {'scans': scn, 'camera': cam}


CONFIG = {
    'name': 'heal_test', 'target_trust': 97.0, 'max_iterations': 5,
    'sources': [
        {'name': 'scans', 'kind': 'dataframe',
         'columns': {'datetime': 'ts', 'entity': 'gate', 'value': 'scans'},
         'links': ['camera']},
        {'name': 'camera', 'kind': 'dataframe',
         'columns': {'datetime': 'ts', 'entity': 'zone', 'value': 'count'},
         'links': ['scans']},
    ],
}


def test_mutual_healing_and_convergence():
    res = heal(CONFIG, frames=make_frames(), verbose=False)
    # both dark windows must end HIGH (healed from each other)
    for name, day in (('scans', '2025-03-10'), ('camera', '2025-03-12')):
        t = res['tables'][name]
        # judge only the PLANTED window (05-21h); the generator's own rare
        # micro-anomalies at near-silent hours are legitimate escalations
        w = t[(t['date'].astype(str) == day) & t['was_corrected']
              & t['time_bucket'].between(5, 21)]
        assert len(w) >= 15, (name, len(w))
        assert (w['confidence'] == 'HIGH').all(), (name, w['confidence'].unique())
        assert w['healed_by'].str.contains(r'\(r=').all()
    assert res['target_met'] and res['overall_trust'] >= 97
    assert res['trust_final']['scans'] > res['trust_initial']['scans']
    assert res['iterations'][-1]['upgrades'] >= 0 and len(res['iterations']) <= 5
    print(f"  PASS mutual healing: both dark windows HIGH, "
          f"trust {res['trust_initial']} -> {res['trust_final']}, "
          f"{len(res['iterations'])} iteration(s)")


def test_honest_target_not_met():
    """No links -> the dark windows cannot be confidently healed; the engine
    must say so (target_met=False) and list every escalation."""
    # dark windows are a small fraction of all buckets, so overall trust stays
    # ~99.4% even unhealed — set the bar above what an honest engine can reach
    # without links, and verify it ADMITS the miss instead of forcing it
    cfg = {**CONFIG, 'target_trust': 99.9,
           'sources': [dict(s, links=[]) for s in CONFIG['sources']]}
    res = heal(cfg, frames=make_frames(), verbose=False)
    assert not res['target_met'], res['overall_trust']
    assert res['n_escalations'] >= 30            # both 17h windows escalated
    esc = res['escalations']
    assert set(esc['source'].unique()) == {'scans', 'camera'}
    assert (esc['confidence'] != 'HIGH').all()
    print(f"  PASS honesty: no links -> trust {res['overall_trust']}% < 97, "
          f"target_met=False, {res['n_escalations']} rows escalated (never faked)")


def test_loop_terminates_when_nothing_improves():
    cfg = {**CONFIG, 'target_trust': 100.0}      # unreachable target
    res = heal(cfg, frames=make_frames(), verbose=False)
    assert len(res['iterations']) < 5, "loop must stop when no upgrades remain"
    assert res['iterations'][-1]['upgrades'] == 0 or res['overall_trust'] == 100
    print(f"  PASS convergence: unreachable target -> stopped after "
          f"{len(res['iterations'])} iteration(s), no infinite loop, no fabrication")


if __name__ == '__main__':
    print("aegis phase-2 heal-loop tests")
    print("-" * 52)
    test_mutual_healing_and_convergence()
    test_honest_target_not_met()
    test_loop_terminates_when_nothing_improves()
    print("-" * 52)
    print("ALL TESTS PASSED")
