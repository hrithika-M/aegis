# -*- coding: utf-8 -*-
"""Automated invariant tests for the digital twin.

Runs with plain `python test_twin.py` (no pytest needed) or under pytest. Each test
asserts an invariant that must hold for the pipeline output to be trustworthy — so a
regression (like the occupancy-drift bug we already fixed) fails loudly next time.
"""
import csv, math, os
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
M = os.path.join(ROOT, 'master')
G = os.path.join(ROOT, 'generated')
DATADIR = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz')
SEASON = (dt.date(2026, 3, 29), dt.date(2026, 10, 24))


def rd(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


# ---------------- masters ----------------
def test_airport_master_complete():
    fm = rd(os.path.join(M, 'Flight_Master.csv'))
    airports = {r['airport_code'] for r in rd(os.path.join(M, 'Airport_Master.csv'))}
    used = {r['origin'] for r in fm} | {r['destination'] for r in fm}
    missing = used - airports
    assert not missing, f"airports in schedule but not in Airport_Master: {missing}"


def test_aircraft_master_complete_and_positive():
    fm = rd(os.path.join(M, 'Flight_Master.csv'))
    ac = {r['aircraft']: r for r in rd(os.path.join(M, 'Aircraft_Master.csv'))}
    for r in fm:
        assert r['aircraft'] in ac, f"aircraft {r['aircraft']} not in Aircraft_Master"
        assert int(ac[r['aircraft']]['nominal_seats']) > 0, f"{r['aircraft']} seats not positive"


def test_flight_master_times_and_seats():
    for r in rd(os.path.join(M, 'Flight_Master.csv')):
        for col in ('arrival_time', 'departure_time'):
            h, mm = r[col].split(':')
            assert 0 <= int(h) <= 23 and 0 <= int(mm) <= 59, f"bad time {r[col]}"
        assert int(r['seat_capacity']) > 0, "seat_capacity not positive"


# ---------------- daily flights ----------------
def test_daily_dates_in_season_and_dow_matches():
    for r in rd(os.path.join(G, 'Daily_Flights.csv')):
        d = dt.date.fromisoformat(r['date'])
        assert SEASON[0] <= d <= SEASON[1], f"date {d} outside S26 season"
        names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        assert names[d.weekday()] == r['day_of_week'], f"dow mismatch {d} {r['day_of_week']}"


def test_daily_respects_frequency():
    freq = {r['flight_id']: {int(c) - 1 for c in r['frequency'] if c.isdigit()}
            for r in rd(os.path.join(M, 'Flight_Master.csv'))}
    for r in rd(os.path.join(G, 'Daily_Flights.csv')):
        d = dt.date.fromisoformat(r['date'])
        assert d.weekday() in freq[r['flight_id']], \
            f"{r['flight_id']} on {d} ({d.weekday()}) not in its frequency"


# ---------------- passengers ----------------
def test_passengers_nonneg_le_seats_lf_range():
    for r in rd(os.path.join(G, 'passenger_estimates.csv')):
        pax, seats, lf = float(r['passengers']), int(r['seat_capacity']), float(r['load_factor_effective'])
        assert pax >= 0, f"negative passengers {pax}"
        assert pax <= seats, f"passengers {pax} exceed seats {seats}"
        assert 0 <= lf <= 0.99, f"load factor out of range {lf}"


def test_two_legs_per_occurrence():
    from collections import defaultdict
    legs = defaultdict(set)
    for r in rd(os.path.join(G, 'passenger_estimates.csv')):
        legs[r['occurrence_id']].add(r['movement_type'])
    bad = {k for k, v in legs.items() if v != {'ARR', 'DEP'}}
    assert not bad, f"occurrences without exactly ARR+DEP: {len(bad)}"


def test_reconciliation_scale_hyderabad():
    # loose sanity: simulated HYD departing pax for a month within 30% of real DGCA
    from collections import defaultdict
    sim = defaultdict(float)
    for r in rd(os.path.join(G, 'passenger_estimates.csv')):
        if r['route_city'] == 'Hyderabad' and r['movement_type'] == 'DEP':
            sim[int(r['month'])] += float(r['passengers'])
    real = defaultdict(float)
    for r in rd(os.path.join(DATADIR, 'vtz_citypair_monthly.csv')):
        if r['Route'] == 'Hyderabad' and int(r['Year']) == 2025:
            real[int(r['Month'])] += float(r['PaxDep_fromVTZ'] or 0)
    m = 5  # May
    ratio = sim[m] / real[m]
    assert 0.7 <= ratio <= 1.3, f"HYD May sim/real ratio {ratio:.2f} outside [0.7,1.3]"


# ---------------- 5-minute operations ----------------
def test_5min_nonneg_and_counter_consistency():
    for r in rd(os.path.join(G, 'passenger_5min.csv')):
        for c in ('checkin_demand', 'security_demand', 'boarding_demand', 'belt_demand', 'terminal_occupancy'):
            assert float(r[c]) >= 0, f"negative {c}"
        assert int(r['checkin_counters_req']) == math.ceil(float(r['checkin_demand']) / 6), "counter calc mismatch"
        assert int(r['security_lanes_req']) == math.ceil(float(r['security_demand']) / 12), "lane calc mismatch"


def test_occupancy_no_drift():
    # regression guard for the old cross-day drift bug (peaked at 11,912)
    rows = rd(os.path.join(G, 'passenger_5min.csv'))
    max_occ = max(float(r['terminal_occupancy']) for r in rows)
    # busiest single-day throughput is the hard ceiling for concurrent occupancy
    from collections import defaultdict
    day = defaultdict(float)
    for r in rd(os.path.join(G, 'passenger_estimates.csv')):
        day[r['date']] += float(r['passengers'])
    assert max_occ < max(day.values()), f"occupancy {max_occ:.0f} exceeds busiest-day throughput (drift?)"


# ---------------- provenance / versioning ----------------
def test_manifests_present_and_cover_outputs():
    import json
    for name in ('version.json', 'provenance.json'):
        assert os.path.exists(os.path.join(ROOT, name)), f"{name} missing (run build_provenance.py)"
    v = json.load(open(os.path.join(ROOT, 'version.json'), encoding='utf-8'))
    assert v['simulator_version'], "no simulator_version recorded"
    assert v['assumptions']['load_factor_model']['sigma'] > 0, "assumptions not captured"
    # every committed generated/master CSV should be fingerprinted
    for sub in ('master', 'generated'):
        for fn in os.listdir(os.path.join(ROOT, sub)):
            if fn.endswith('.csv'):
                rel = f"{sub}/{fn}"
                assert rel in v['outputs'], f"{rel} not tracked in version.json"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]

if __name__ == '__main__':
    passed = failed = 0
    print("=" * 66)
    print("DIGITAL TWIN — invariant tests")
    print("=" * 66)
    for t in TESTS:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print("-" * 66)
    print(f"  {passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
