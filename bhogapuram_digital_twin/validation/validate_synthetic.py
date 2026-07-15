# -*- coding: utf-8 -*-
"""Synthetic-data validation — does the TWIN resemble the REAL data?

For a digital twin headed to production, the first thing to establish is not model
accuracy — it's whether the generated data statistically matches reality. We test
three distributions with standard tests (all implemented in numpy, no scipy dep):

  KS statistic (D)      max gap between empirical CDFs        (0 = identical)
  Wasserstein / EMD     average "work" to morph one into other (units of the axis)
  PSI                   population stability index             (<0.1 stable, >0.25 shift)

Comparisons:
  1. Route passenger shares : twin vs real DGCA        [reconciliation integrity — should PASS]
  2. Load-factor distribution: twin per-flight vs real airline PLF   [realism test]
  3. Day-of-week demand shape: twin vs real national daily          [realism test]

Verdicts use documented thresholds. Reports honestly — a WARN/FAIL is a real finding,
not a failure of the exercise.

Run:  python validate_synthetic.py
"""
import csv, os
import datetime as dt
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAX = os.path.join(ROOT, 'generated', 'passenger_estimates.csv')
CITYPAIR = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz', 'vtz_citypair_monthly.csv')
NATDAILY = os.path.join(ROOT, '..', 'data', 'bhogapuram_vtz', 'national_daily_reference.csv')
OUT = os.path.join(ROOT, 'analytics', 'synthetic_validation.csv')
DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


# ---- stat helpers (numpy only) ----------------------------------------------
def ks_2samp(a, b):
    a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
    grid = np.concatenate([a, b])
    ca = np.searchsorted(a, grid, side='right') / len(a)
    cb = np.searchsorted(b, grid, side='right') / len(b)
    return float(np.max(np.abs(ca - cb)))


def wasserstein_1d(a, b):
    qs = np.linspace(0, 1, 101)
    return float(np.mean(np.abs(np.quantile(a, qs) - np.quantile(b, qs))))


def psi_continuous(expected, actual, bins=10):
    edges = np.quantile(expected, np.linspace(0, 1, bins + 1))
    edges = np.unique(edges)
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.clip(np.histogram(expected, edges)[0] / len(expected), 1e-6, None)
    a = np.clip(np.histogram(actual, edges)[0] / len(actual), 1e-6, None)
    return float(np.sum((a - e) * np.log(a / e)))


def psi_categorical(e_share, a_share):
    e = np.clip(np.asarray(e_share, float), 1e-6, None)
    a = np.clip(np.asarray(a_share, float), 1e-6, None)
    return float(np.sum((a - e) * np.log(a / e)))


def verdict(psi):
    return 'PASS' if psi < 0.1 else ('WARN' if psi < 0.25 else 'FAIL')


# ---- load ------------------------------------------------------------------
def load_twin():
    legs = list(csv.DictReader(open(PAX, encoding='utf-8')))
    lf = [float(r['load_factor_effective']) for r in legs if float(r['load_factor_effective']) > 0]
    route_pax = defaultdict(float)
    dow_pax = defaultdict(float)
    for r in legs:
        if r['route_city']:
            route_pax[r['route_city']] += float(r['passengers'])
        d = dt.date.fromisoformat(r['date'])
        dow_pax[d.weekday()] += float(r['passengers'])
    return np.array(lf), route_pax, dow_pax


def load_real_routes():
    rp = defaultdict(float)
    for r in csv.DictReader(open(CITYPAIR, encoding='utf-8')):
        if int(r['Year']) == 2025:
            rp[r['Route']] += float(r['PaxTotal'] or 0)
    return rp


def load_real_plf_and_dow():
    plf, dow = [], defaultdict(list)
    def num(s):
        try:
            return float(s)
        except (ValueError, TypeError):
            return None                      # skip malformed source values (e.g. '84..1')
    for r in csv.DictReader(open(NATDAILY, encoding='utf-8')):
        for c in ('LF_IndiGo_pct', 'LF_AirIndia_pct', 'LF_Akasa_pct', 'LF_SpiceJet_pct'):
            v = num(r[c])
            if v is not None and 0 < v <= 100:
                plf.append(v / 100.0)
        d = dt.date.fromisoformat(r['Date'])
        dp = num(r['DomesticPax'])
        if dp is not None:
            dow[d.weekday()].append(dp)
    dow_mean = {k: np.mean(v) for k, v in dow.items()}
    return np.array(plf), dow_mean


def shares(d, keys):
    tot = sum(d.get(k, 0) for k in keys)
    return [d.get(k, 0) / tot if tot else 0 for k in keys]


def main():
    twin_lf, twin_route, twin_dow = load_twin()
    real_route = load_real_routes()
    real_plf, real_dow = load_real_plf_and_dow()

    rows = []

    # 1. route shares (integrity) — only routes the schedule actually flies
    keys = sorted(set(twin_route) & set(real_route))
    tsh, rsh = shares(twin_route, keys), shares(real_route, keys)
    p1 = psi_categorical(rsh, tsh)
    rows.append(['Route passenger shares (twin vs real DGCA)', 'integrity',
                 f'PSI={p1:.3f}', '', '', verdict(p1)])

    # 2. load-factor distribution (realism)
    ks2 = ks_2samp(real_plf, twin_lf)
    w2 = wasserstein_1d(real_plf, twin_lf)
    p2 = psi_continuous(real_plf, twin_lf)
    rows.append(['Load-factor distribution (twin per-flight vs real airline PLF)', 'realism',
                 f'PSI={p2:.3f}', f'KS={ks2:.3f}', f'EMD={w2:.3f}', verdict(p2)])

    # 3. day-of-week demand shape (realism)
    tdow = shares(twin_dow, range(7))
    rdow = shares(real_dow, range(7))
    p3 = psi_categorical(rdow, tdow)
    ks3 = ks_2samp(np.repeat(range(7), (np.array(rdow) * 1000).astype(int)),
                   np.repeat(range(7), (np.array(tdow) * 1000).astype(int)))
    rows.append(['Day-of-week demand shape (twin vs real national daily)', 'realism',
                 f'PSI={p3:.3f}', f'KS={ks3:.3f}', '', verdict(p3)])

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['comparison', 'type', 'stat1', 'stat2', 'stat3', 'verdict'])
        w.writerows(rows)

    print("=" * 84)
    print("SYNTHETIC-DATA VALIDATION — twin vs real  (PSI <0.1 PASS, 0.1-0.25 WARN, >0.25 FAIL)")
    print("=" * 84)
    for r in rows:
        stats = "  ".join(s for s in r[2:5] if s)
        print(f"  [{r[5]:<4}] {r[0]}\n           {stats}")
    print("-" * 84)
    print(f"  twin mean load factor {twin_lf.mean():.3f} vs real airline PLF mean {real_plf.mean():.3f}")
    print(f"  twin LF spread (std)  {twin_lf.std():.3f} vs real {real_plf.std():.3f}")
    print(f"wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == '__main__':
    main()
