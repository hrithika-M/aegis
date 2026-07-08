# -*- coding: utf-8 -*-
"""Report tests — the deliverables must be complete, consistent and honest.

Run:  python -m aegis.tests.test_phase3_report
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd

from aegis.heal import heal
from aegis.report import write_outputs, audit_trail
from aegis.tests.test_phase2_heal import CONFIG, make_frames


def test_outputs_complete_and_consistent():
    res = heal(CONFIG, frames=make_frames(), verbose=False)
    out = tempfile.mkdtemp(prefix='aegis_rep_')
    path = write_outputs(res, out)

    # all artifacts exist and are non-empty
    for f in ('scans_healed.csv', 'camera_healed.csv', 'audit.csv',
              'report.json', 'report.html'):
        p = os.path.join(out, f)
        assert os.path.exists(p) and os.path.getsize(p) > 0, f

    # audit ledger rows == corrected cells across sources
    audit = pd.read_csv(os.path.join(out, 'audit.csv'))
    n_corrected = sum(int(t['was_corrected'].sum()) for t in res['tables'].values())
    assert len(audit) == n_corrected

    # healed CSVs: value_adj complete, no NaNs
    healed = pd.read_csv(os.path.join(out, 'scans_healed.csv'))
    assert 'value_adj' in healed.columns and healed['value_adj'].notna().all()

    # json summary matches the result
    js = json.load(open(os.path.join(out, 'report.json'), encoding='utf-8'))
    assert js['overall_trust'] == res['overall_trust'] and js['target_met'] is True

    # html contains the verdict, provenance and the honesty line
    html = open(path, encoding='utf-8').read()
    assert 'TARGET MET' in html and 'camera(r=' in html
    assert 'never fabricates' in html
    print(f"  PASS artifacts complete & consistent ({len(audit)} audited cells)")


def test_honest_report_when_target_missed():
    cfg = {**CONFIG, 'target_trust': 99.9,
           'sources': [dict(s, links=[]) for s in CONFIG['sources']]}
    res = heal(cfg, frames=make_frames(), verbose=False)
    out = tempfile.mkdtemp(prefix='aegis_rep2_')
    path = write_outputs(res, out)
    html = open(path, encoding='utf-8').read()
    assert 'TARGET NOT MET' in html and 'reported honestly' in html
    assert os.path.exists(os.path.join(out, 'escalations.csv'))
    esc = pd.read_csv(os.path.join(out, 'escalations.csv'))
    assert len(esc) == res['n_escalations'] >= 30
    print(f"  PASS missed target reported honestly ({len(esc)} escalations in CSV)")


if __name__ == '__main__':
    print("aegis phase-3 report tests")
    print("-" * 52)
    test_outputs_complete_and_consistent()
    test_honest_report_when_target_missed()
    print("-" * 52)
    print("ALL TESTS PASSED")
