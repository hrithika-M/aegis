# -*- coding: utf-8 -*-
"""Aegis Phase-1 tests — the same planted faults must be found through EVERY
connector (CSV file, SQL database, in-memory frame), and config errors must be
loud.

Run:  python -m aegis.tests.test_phase1
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd

from aegis.config import load
from aegis.scan import scan

TMP = tempfile.mkdtemp(prefix='aegis_p1_')


def synthetic(days=120):
    """Two gates, busy 05-22h, silent nights; three planted faults on known spots:
    a 3h blackout (Gate A, 2025-04-20 08-10h), a midnight dump (Gate B, 5000 at
    02h), a dying-sensor LOW (Gate B reads 3 at noon).
    DETERMINISTIC: fresh fixed-seed RNG per call, so every connector test sees
    byte-identical data (that's the point — same data, same results, any door)."""
    RNG = np.random.default_rng(21)
    rows = []
    for d in pd.date_range('2025-01-01', periods=days, freq='D'):
        for h in range(24):
            for gate, k in (('Gate A', 1.0), ('Gate B', 1.2)):
                if 5 <= h <= 22:
                    v = max(0, (200 + 150 * np.sin((h - 5) / 17 * np.pi)) * k
                            + RNG.normal(0, 12))
                else:
                    v = 0.0
                rows.append({'ts': d + pd.Timedelta(hours=h), 'gate': gate,
                             'count': round(v)})
    df = pd.DataFrame(rows)
    day = pd.Timestamp('2025-04-20')
    for h in (8, 9, 10):
        df.loc[(df['ts'] == day + pd.Timedelta(hours=h)) & (df['gate'] == 'Gate A'),
               'count'] = 0
    df.loc[(df['ts'] == pd.Timestamp('2025-04-25 02:00')) & (df['gate'] == 'Gate B'),
           'count'] = 5000
    df.loc[(df['ts'] == pd.Timestamp('2025-04-25 12:00')) & (df['gate'] == 'Gate B'),
           'count'] = 3
    return df


def assert_faults_found(res, label):
    """All planted faults must be found AT THE RIGHT PLACES, and the false-alarm
    rate must stay below 0.1% (a z-threshold detector legitimately fires on rare
    genuine tail events in random noise — zero false positives is not honest)."""
    t = res['sources']['gates']['trust']
    key = lambda r: (str(r['date']), int(r['time_bucket']), r['entity'])
    flagged = {key(r): r['flag'] for _, r in t[t['flag'] != 'OK'].iterrows()}

    planted = {('2025-04-20', 8, 'Gate A'): 'BLACKOUT',
               ('2025-04-20', 9, 'Gate A'): 'BLACKOUT',
               ('2025-04-20', 10, 'Gate A'): 'BLACKOUT',
               ('2025-04-25', 2, 'Gate B'): 'SPIKE',
               ('2025-04-25', 12, 'Gate B'): 'LOW'}
    for k, expect in planted.items():
        assert flagged.get(k) == expect, f"{label}: {k} should be {expect}, got {flagged.get(k)}"

    extras = {k: v for k, v in flagged.items() if k not in planted}
    fa_rate = len(extras) / len(t) * 100
    assert fa_rate < 0.1, f"{label}: false-alarm rate {fa_rate:.3f}% too high ({extras})"
    assert res['sources']['gates']['score'] > 99.5
    print(f"  PASS {label}: all 5 planted faults found at the right spots "
          f"(false-alarm {fa_rate:.3f}%, trust={res['sources']['gates']['score']}%)")


def test_csv_connector():
    path = os.path.join(TMP, 'gates.csv')
    synthetic().to_csv(path, index=False)
    cfg = {'name': 'p1', 'sources': [{
        'name': 'gates', 'kind': 'csv', 'path': path,
        'columns': {'datetime': 'ts', 'entity': 'gate', 'value': 'count'}}]}
    assert_faults_found(scan(cfg, verbose=False), 'CSV file connector')


def test_database_connector():
    """Same data through a REAL SQL database (SQLite via SQLAlchemy — the exact
    code path Postgres uses; only the URL differs)."""
    from sqlalchemy import create_engine
    db = os.path.join(TMP, 'aegis.db').replace('\\', '/')
    engine = create_engine(f'sqlite:///{db}')
    synthetic().to_sql('gate_counts', engine, index=False, if_exists='replace')
    cfg = {'name': 'p1db', 'sources': [{
        'name': 'gates', 'kind': 'database', 'url': f'sqlite:///{db}',
        'query': 'SELECT ts, gate, count FROM gate_counts',
        'columns': {'datetime': 'ts', 'entity': 'gate', 'value': 'count'}}]}
    assert_faults_found(scan(cfg, verbose=False), 'SQL database connector')


def test_yaml_config_and_dirty_rows():
    """YAML config file end-to-end + dirty rows counted (not silently eaten)."""
    df = synthetic(days=60)
    df['count'] = df['count'].astype(object)
    df.loc[:39, 'count'] = 'garbage'
    path = os.path.join(TMP, 'dirty.csv')
    df.to_csv(path, index=False)
    ycfg = os.path.join(TMP, 'run.yaml')
    with open(ycfg, 'w', encoding='utf-8') as f:
        f.write(f"""name: yaml_run
target_trust: 97
sources:
  - name: gates
    kind: csv
    path: {path.replace(os.sep, '/')}
    columns: {{datetime: ts, entity: gate, value: count}}
""")
    res = scan(ycfg, verbose=False)
    ing = res['report']['sources']['gates']['ingestion']
    assert ing['rows_nonnumeric_value'] == 40 and ing['rows_dropped_total'] == 40
    print("  PASS yaml config + dirty-row accounting (40 counted, none silent)")


def test_config_validation_is_loud():
    for bad, msg in [
        ({'name': 'x', 'sources': []}, 'at least one source'),
        ({'name': 'x', 'sources': [{'name': 's', 'kind': 'csv', 'path': 'p.csv',
                                    'columns': {'value': 'v'}}]}, 'datetime'),
        ({'name': 'x', 'sources': [{'name': 's', 'kind': 'database', 'url': 'u',
                                    'columns': {'datetime': 't', 'value': 'v'}}]}, 'query'),
        ({'name': 'x', 'sources': [
            {'name': 'a', 'kind': 'csv', 'path': 'p',
             'columns': {'datetime': 't', 'value': 'v'}, 'links': ['nope']}]}, 'unknown source'),
    ]:
        try:
            load(bad)
            raise AssertionError(f"config should have failed: {msg}")
        except (ValueError, KeyError) as e:
            assert msg.split()[0] in str(e), (msg, str(e))
    print("  PASS config validation fails loudly on bad configs")


if __name__ == '__main__':
    print("aegis phase-1 tests")
    print("-" * 52)
    test_csv_connector()
    test_database_connector()
    test_yaml_config_and_dirty_rows()
    test_config_validation_is_loud()
    print("-" * 52)
    print("ALL TESTS PASSED")
