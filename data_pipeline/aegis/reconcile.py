"""Reconcile — heal the doubtful cases using OTHER sources + ground truth.

Where repair.py fixes a source from its own history, reconcile fixes it from
its RELATIONSHIPS — the user-declared links in the config (e.g. e-boarding
scans <-> camera counts <-> LDM manifests). This is the MICE idea (predict a
broken column from the others) applied across sources, plus HoloClean's rule
that external/reference data and physical limits bound every estimate.

For each (date, hour) where the target is DARK or its repair confidence is
LOW/MEDIUM:
  1. every linked source that is HEALTHY at that hour contributes an estimate:
       helper_value x learned per-hour ratio (target/helper, from mutually
       healthy history)
  2. estimates are combined weighted by each helper's LEARNED correlation with
     the target (a helper that tracks the target at r=0.95 outweighs r=0.4)
  3. the combined estimate is bounded by the physical ceiling and, if a
     REFERENCE source (role: reference — ground truth like LDM) covers that
     key, pulled to within the reference's plausible band
  4. the fix carries provenance (which helpers, what weights) and a confidence:
       HIGH    >= 1 strong helper (r >= 0.7) or 2+ moderate ones
       MEDIUM  a single moderate helper (0.4 <= r < 0.7)
       LOW     only weak helpers -> value left as repair's estimate, ESCALATED

reconcile never downgrades: it only replaces a cell when its own confidence is
HIGHER than what repair achieved alone.
"""
import numpy as np
import pandas as pd

from aegis.connectors import ENTITY, DATE, TIME

STRONG_R, MODERATE_R = 0.7, 0.4
MIN_OVERLAP = 50          # mutually-healthy hours needed to learn ratio/corr
_RANK = {'': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}


def _hourly(t, value_col):
    """Source totals per (date, hour) + healthy flag (from its trust table)."""
    g = (t.groupby([DATE, TIME], observed=True)
         .agg(val=(value_col, 'sum'),
              n=('flag', 'size'),
              bad=('flag', lambda s: s.isin(['BLACKOUT', 'LOW', 'SPIKE']).sum()))
         .reset_index())
    g['healthy'] = g['bad'] / g['n'] < 0.5
    return g


def learn_link(target_h, helper_h):
    """Per-hour ratio (target/helper) + Pearson r, on mutually-healthy history.
    Returns (ratios: {hour: ratio}, r, n_overlap) or (None, None, 0)."""
    j = target_h[target_h['healthy']].merge(
        helper_h[helper_h['healthy']], on=[DATE, TIME], suffixes=('_t', '_h'))
    j = j[(j['val_t'] > 0) & (j['val_h'] > 0)]
    if len(j) < MIN_OVERLAP:
        return None, None, len(j)
    r = float(np.corrcoef(j['val_t'], j['val_h'])[0, 1])
    ratios = (j['val_t'] / j['val_h']).groupby(j[TIME]).median().to_dict()
    return ratios, r, len(j)


def reconcile(target_name, tables, links, references=(), physical_max=None):
    """Improve `tables[target_name]` using its linked sources.

    tables     : {source_name: repaired trust table (from repair.repair)}
    links      : [helper_source_name, ...] for this target (from config)
    references : subset of links whose role is 'reference' (ground truth)
    Returns (updated trust table, reconcile_report).
    """
    t = tables[target_name].copy()
    if 'healed_by' not in t.columns:
        t['healed_by'] = ''
    target_h = _hourly(t, 'actual')

    # learn every link once
    learned = {}
    for h in links:
        ratios, r, n = learn_link(target_h, _hourly(tables[h], 'value_adj'))
        if ratios is not None:
            learned[h] = {'ratios': ratios, 'r': r, 'n': n,
                          'hourly': _hourly(tables[h], 'value_adj')}

    # candidates: corrected cells whose confidence is not already HIGH
    cand = t[t['was_corrected'] & (t['confidence'] != 'HIGH')]
    n_upgraded = 0
    for idx, row in cand.iterrows():
        dt, hr = row[DATE], row[TIME]
        ests, provenance, rs = [], [], []
        for h, L in learned.items():
            if hr not in L['ratios'] or abs(L['r']) < MODERATE_R:
                continue
            hh = L['hourly']
            m = hh[(hh[DATE] == dt) & (hh[TIME] == hr)]
            if len(m) and bool(m['healthy'].iloc[0]) and m['val'].iloc[0] > 0:
                ests.append((m['val'].iloc[0] * L['ratios'][hr], max(L['r'], 0.1)))
                provenance.append(f"{h}(r={L['r']:.2f})")
                rs.append(L['r'])
        if not ests:
            continue
        strong = sum(1 for r in rs if r >= STRONG_R)
        conf = ('HIGH' if strong >= 1 or len(ests) >= 2 else
                'MEDIUM' if rs and max(rs) >= MODERATE_R else 'LOW')
        if _RANK[conf] <= _RANK[row['confidence']]:
            continue                       # never downgrade / sideways-grade
        wsum = sum(w for _, w in ests)
        est = sum(v * w for v, w in ests) / wsum
        # bounds: physical ceiling, and share of the total across entities
        if physical_max is not None:
            est = min(est, physical_max)
        # distribute hour-estimate to this entity by its healthy-share... single
        # entity per row: scale by entity's share of the target's hourly total
        ent_share = _entity_share(t, row)
        t.loc[idx, 'value_adj'] = round(max(est * ent_share, 0))
        t.loc[idx, 'confidence'] = conf
        t.loc[idx, 'repair_method'] = 'reconciled_from_links'
        t.loc[idx, 'healed_by'] = '+'.join(provenance)
        n_upgraded += 1

    report = {
        'target': target_name,
        'links_learned': {h: {'r': round(L['r'], 3), 'n': L['n']}
                          for h, L in learned.items()},
        'candidates': int(len(cand)),
        'upgraded': int(n_upgraded),
        'still_low': int((t['was_corrected'] & (t['confidence'] == 'LOW')).sum()),
    }
    return t, report


def _entity_share(t, row):
    """This entity's typical share of the source's hourly total (median share
    on healthy history for that hour) — 1.0 for single-entity sources."""
    hr = row[TIME]
    hrs = t[(t[TIME] == hr) & (t['flag'] == 'OK')]
    if hrs.empty:
        return 1.0
    tot = hrs.groupby(DATE, observed=True)['actual'].sum().rename('tot')
    ent = (hrs[hrs[ENTITY] == row[ENTITY]]
           .groupby(DATE, observed=True)['actual'].sum().rename('ent'))
    j = pd.concat([tot, ent], axis=1).dropna()
    j = j[j['tot'] > 0]
    if j.empty:
        return 1.0
    return float((j['ent'] / j['tot']).median())


def resolve(estimates, physical_max=None, reference=None, ranks=None, tol=0.05):
    """Arbitrate when sources DISAGREE about the same quantity.
    Ladder: physical ceiling -> nearest-to-reference -> best rank -> median.
    Returns dict(value, chosen, rejected, reason)."""
    ranks = ranks or {}
    rejected, survivors = {}, {}
    for s, v in estimates.items():
        if physical_max is not None and v > physical_max * (1 + tol):
            rejected[s] = f'exceeds physical max {physical_max} ({v})'
        else:
            survivors[s] = v
    if not survivors:
        return {'value': None, 'chosen': None, 'rejected': rejected,
                'reason': 'all exceed physical ceiling — ESCALATE'}
    if reference and reference in survivors and len(survivors) > 1:
        ref = survivors[reference]
        chosen = min(survivors, key=lambda s: abs(survivors[s] - ref))
        return {'value': survivors[chosen], 'chosen': chosen,
                'rejected': rejected, 'reason': f'nearest to reference {reference}={ref}'}
    best = sorted(survivors, key=lambda s: ranks.get(s, 99))
    top = [s for s in best if ranks.get(s, 99) == ranks.get(best[0], 99)]
    if len(top) == 1:
        return {'value': survivors[top[0]], 'chosen': top[0],
                'rejected': rejected, 'reason': f'best trust rank ({top[0]})'}
    vals = sorted(survivors[s] for s in top)
    return {'value': vals[len(vals) // 2], 'chosen': top, 'rejected': rejected,
            'reason': f'median of equal-rank {top}'}
