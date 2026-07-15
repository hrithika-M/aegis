# -*- coding: utf-8 -*-
"""Provenance + versioning — make every generated value auditable.

Writes two machine-readable manifests at the twin root:

  version.json     the BUILD fingerprint: simulator version, input files + hashes,
                   output files + hashes + row counts, the exact assumptions used
                   (read live from the build modules, so they can't drift), and KPIs.
  provenance.json  per-artifact + per-column Source / Method / Confidence, so anyone
                   can answer "where did this value come from?" without reading code.

Run LAST in the pipeline:  python build_provenance.py
"""
import csv, hashlib, json, os
import datetime as dt

import twin_version
import build_passengers as bp
import build_operations as bo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATADIR = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz')


def sha(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()[:16]


def nrows(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return max(0, sum(1 for _ in f) - 1)


def fingerprint(rel):
    p = os.path.join(ROOT, rel) if not os.path.isabs(rel) else rel
    return {'sha256_16': sha(p), 'rows': nrows(p)}


def main():
    inputs = {
        'VTZ_schedule_S26.xlsx': os.path.join(DATADIR, 'VTZ_schedule_S26.xlsx'),
        'vtz_citypair_monthly.csv': os.path.join(DATADIR, 'vtz_citypair_monthly.csv'),
        'vtz_route_profile.csv': os.path.join(DATADIR, 'vtz_route_profile.csv'),
        'national_daily_reference.csv': os.path.join(DATADIR, 'national_daily_reference.csv'),
    }
    outputs = ['master/Airport_Master.csv', 'master/Aircraft_Master.csv', 'master/Flight_Master.csv',
               'generated/Daily_Flights.csv', 'generated/passenger_estimates.csv',
               'generated/passenger_5min.csv', 'generated/gate_occupancy.csv',
               'analytics/kpis.csv', 'analytics/peak_hours.csv',
               'analytics/confidence_intervals.csv', 'analytics/synthetic_validation.csv',
               'analytics/model_selection_twin.csv', 'analytics/scenarios.csv',
               'analytics/events.csv']

    kpis = {}
    kp = os.path.join(ROOT, 'analytics', 'kpis.csv')
    if os.path.exists(kp):
        for r in csv.DictReader(open(kp, encoding='utf-8')):
            kpis[r['metric']] = r['value']

    version = {
        'simulator_version': twin_version.SIMULATOR_VERSION,
        'built_at_utc': dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + 'Z',
        'inputs': {name: {'sha256_16': sha(path), 'exists': os.path.exists(path)}
                   for name, path in inputs.items()},
        'outputs': {rel: fingerprint(rel) for rel in outputs},
        'assumptions': {
            'load_factor_model': {
                'distribution': 'Normal(mu_route, sigma)', 'sigma': bp.LF_SIGMA,
                'default_mu': bp.DEFAULT_MU, 'clip': [bp.LF_MIN, bp.LF_MAX],
                'reconcile_factor_bounds': [bp.RECON_LO, bp.RECON_HI], 'seed': bp.SEED},
            'behaviour_windows_min_before_STD': {k: list(v) for k, v in bo.DEP_STAGES.items()},
            'arrival_belt_min_after_STA': list(bo.ARR_BELT),
            'service_rates_pax_per_5min': {'checkin': bo.CHECKIN_PER_5MIN, 'security': bo.SECURITY_PER_5MIN},
            'season': [bo.SEASON_START.date().isoformat(), bo.SEASON_END.date().isoformat()],
        },
        'kpis': kpis,
    }
    with open(os.path.join(ROOT, 'version.json'), 'w', encoding='utf-8') as f:
        json.dump(version, f, indent=2)

    H, M, L = 'HIGH', 'MEDIUM', 'LOW'
    provenance = {
        'simulator_version': twin_version.SIMULATOR_VERSION,
        'confidence_legend': {
            'HIGH': 'real, reconciled-to-real, or deterministic derivation',
            'MEDIUM': 'simulated with documented assumptions',
            'LOW': 'depends on soft service-rate assumptions'},
        'artifacts': [
            {'file': 'master/Flight_Master.csv', 'source': 'schedule',
             'method': 'cleaned + standardized', 'confidence': H},
            {'file': 'master/Airport_Master.csv', 'source': 'reference',
             'method': 'lookup (geo/scope)', 'confidence': H},
            {'file': 'master/Aircraft_Master.csv', 'source': 'reference',
             'method': 'lookup (ICAO/seats/specs)', 'confidence': H},
            {'file': 'generated/Daily_Flights.csv', 'source': 'schedule',
             'method': 'deterministic FREQ expansion', 'confidence': H},
            {'file': 'generated/passenger_estimates.csv', 'source': 'schedule + DGCA',
             'method': 'seats x Normal(route_LF, sigma), lightly reconciled to DGCA totals',
             'confidence': M,
             'columns': {'passengers': {'source': 'schedule+DGCA', 'method': 'reconciled', 'confidence': H},
                         'load_factor_effective': {'source': 'drawn', 'method': 'Normal(mu,sigma)', 'confidence': M}}},
            {'file': 'generated/passenger_5min.csv', 'source': 'passenger_estimates',
             'method': 'show-up/service behaviour windows -> 5-min buckets', 'confidence': M,
             'columns': {'terminal_occupancy': {'source': 'derived', 'method': 'entries-exits (daily reset)', 'confidence': M},
                         'checkin_counters_req': {'source': 'derived', 'method': 'ceil(demand / service_rate)', 'confidence': L}}},
            {'file': 'generated/gate_occupancy.csv', 'source': 'Daily_Flights',
             'method': 'rotations on stand (STA..STD)', 'confidence': M},
            {'file': 'analytics/confidence_intervals.csv', 'source': 'Monte Carlo',
             'method': '1000-run design day, P5/P50/P95', 'confidence': M},
            {'file': 'analytics/synthetic_validation.csv', 'source': 'twin vs real DGCA',
             'method': 'KS / Wasserstein / PSI', 'confidence': H},
            {'file': 'analytics/scenarios.csv', 'source': 'passenger_5min + scenario levers',
             'method': 'deterministic bucket queue, busiest day', 'confidence': M},
            {'file': 'analytics/events.csv', 'source': 'Flight_Master + disruption events',
             'method': 'delay propagation -> occupancy delta, design day', 'confidence': M},
        ],
    }
    with open(os.path.join(ROOT, 'provenance.json'), 'w', encoding='utf-8') as f:
        json.dump(provenance, f, indent=2)

    print(f"wrote version.json (simulator {twin_version.SIMULATOR_VERSION}) + provenance.json")
    print(f"  inputs fingerprinted: {len(inputs)}   outputs: {len(outputs)}   KPIs: {len(kpis)}")


if __name__ == '__main__':
    main()
