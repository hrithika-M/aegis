# -*- coding: utf-8 -*-
"""Reconcile tests — the cases single-source repair could NOT confidently fix
must be healed from a LINKED source, with provenance, and disagreements must be
arbitrated by the trust ladder.

Scenario: 'scans' (target) and 'camera' (helper) watch the same passenger flow
(scans ~ 85% of camera). We black out almost a whole scans-day: repair alone can
only grade those fills LOW (no evidence that day). Reconcile must then rebuild
them from the camera at HIGH confidence, close to the truth.

Run:  python -m aegis.tests.test_phase2_reconcile
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd

from aegis.config import SourceCfg
from aegis.connectors import canonicalise
from aegis.detect import detect
from aegis.repair import repair
from aegis.reconcile import reconcile, resolve

CFG = lambda n, e, v: SourceCfg(name=n, kind='dataframe',
                                columns={'datetime': 'ts', 'entity': e, 'value': v})


def make_pair(days=120):
    rng = np.random.default_rng(31)
    cam, scn, truth = [], [], {}
    for d in pd.date_range('2025-01-01', periods=days, freq='D'):
        for h in range(24):
            base = (400 + 260 * np.sin((h - 5) / 17 * np.pi)) if 5 <= h <= 22 else 0
            c = max(0, base + rng.normal(0, 18))
            s = max(0, base * 0.85 + rng.normal(0, 18))
            ts = d + pd.Timedelta(hours=h)
            cam.append({'ts': ts, 'zone': 'Z1', 'count': round(c)})
            scn.append({'ts': ts, 'gate': 'G1', 'scans': round(s)})
            truth[(str(d.date()), h)] = round(s)
    return pd.DataFrame(cam), pd.DataFrame(scn), truth


def build_tables(kill_day='2025-03-10'):
    cam, scn, truth = make_pair()
    day = pd.Timestamp(kill_day)
    mask = (scn['ts'].dt.date == day.date()) & scn['ts'].dt.hour.between(5, 21)
    scn.loc[mask, 'scans'] = 0                     # 17 of 18 busy hours dark
    canon_s, _ = canonicalise(scn, CFG('scans', 'gate', 'scans'))
    canon_c, _ = canonicalise(cam, CFG('camera', 'zone', 'count'))
    tables = {'scans': repair(detect(canon_s)),
              'camera': repair(detect(canon_c))}
    return tables, truth, kill_day


def test_low_confidence_fills_upgraded_from_helper():
    tables, truth, kill_day = build_tables()
    before = tables['scans']
    dark = before[(before['date'].astype(str) == kill_day) & before['was_corrected']]
    assert (dark['confidence'] == 'LOW').all() and len(dark) >= 15, \
        "precondition: repair alone must be LOW-confidence on the dark day"

    healed, rep = reconcile('scans', tables, links=['camera'])
    after = healed[(healed['date'].astype(str) == kill_day) & healed['was_corrected']]
    assert (after['confidence'] == 'HIGH').all(), after['confidence'].unique()
    assert after['healed_by'].str.startswith('camera(r=').all()
    assert rep['links_learned']['camera']['r'] > 0.95

    errs = []
    for _, r in after.iterrows():
        tv = truth[(kill_day, int(r['time_bucket']))]
        if tv > 0:
            errs.append(abs(r['value_adj'] - tv) / tv)
    mean_err = float(np.mean(errs))
    assert mean_err < 0.15, f"mean error {mean_err:.1%} (want <15%)"
    print(f"  PASS dark day rebuilt from camera: LOW->HIGH x{len(after)}, "
          f"mean error {mean_err:.1%}, provenance recorded")


def test_never_downgrades_and_unlinked_stays_low():
    tables, _, kill_day = build_tables()
    # no links -> nothing to learn -> nothing changes, LOW stays LOW (escalation)
    healed, rep = reconcile('scans', tables, links=[])
    after = healed[(healed['date'].astype(str) == kill_day) & healed['was_corrected']]
    assert (after['confidence'] == 'LOW').all() and rep['upgraded'] == 0
    assert rep['still_low'] >= 15
    print("  PASS without links nothing is invented: LOW fills stay LOW (escalated)")


def test_resolve_trust_ladder():
    r = resolve({'eboarding': 300, 'cupps': 2000, 'camera': 190},
                physical_max=220, reference='camera')
    assert r['chosen'] == 'camera' and 'eboarding' in r['rejected'] and 'cupps' in r['rejected']
    r2 = resolve({'ldm': 180, 'camera': 190, 'cupps': 2000},
                 physical_max=220, ranks={'ldm': 1, 'camera': 2, 'cupps': 3})
    assert r2['value'] == 180 and r2['chosen'] == 'ldm'
    r3 = resolve({'a': 500, 'b': 600}, physical_max=220)
    assert r3['value'] is None and 'ESCALATE' in r3['reason']
    print("  PASS trust ladder: ceiling rejects, reference wins, rank wins, escalates honestly")


if __name__ == '__main__':
    print("aegis phase-2 reconcile tests")
    print("-" * 52)
    test_low_confidence_fills_upgraded_from_helper()
    test_never_downgrades_and_unlinked_stays_low()
    test_resolve_trust_ladder()
    print("-" * 52)
    print("ALL TESTS PASSED")
