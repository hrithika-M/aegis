"""Detect — judge every (date, hour, entity) bucket against its learned profile.

Flags (validated on 3.5M rows of real airport sensor data in the POD project):
  BLACKOUT — reads 0 in a bucket where history says it should be busy
  SPIKE    — implausibly far above the band (phantom dump / double-count);
             on dead-flat history buckets an extra busy-scale guard prevents
             flagging usually-closed entities that legitimately open
  LOW      — non-zero but far below the band (dying sensor)
  DRIFT    — an entity persistently over-counting its share across days
             (watchlist: reported, never auto-corrected)
  OK       — inside the plausible band

All thresholds are per-source overridable (SourceCfg.params); the DEFAULTS are
the POD-validated ones. The bands themselves are always learned, never set.
"""
import numpy as np
import pandas as pd

from aegis.connectors import ENTITY, DATE, TIME, VALUE, WEEKEND
from aegis.profile import aggregate, learn

DEFAULTS = dict(
    operating_min_median=1.0,   # bucket is "operating" if its median >= this
    z_spike=4.0,                # robust-z above which -> spike
    z_low=3.5,                  # robust-z below which a non-zero bucket -> low
    spike_min_abs=15,           # spike must also exceed expected by this much
    drift_share_dev=0.30,       # sustained over-share vs the entity's own history
    drift_min_days=3,
    drift_min_share=0.02,
    min_history=20,             # samples required before judging a bucket
    dump_scale_frac=0.5,        # mad==0 spike also needs value >= frac * ent p95
)


def detect(canon, params=None):
    """Return the trust table: one row per (date, hour, entity) with
    actual, expected, mad, robust_z, flag, severity."""
    p = {**DEFAULTS, **(params or {})}
    agg = aggregate(canon)
    prof, ent_p95 = learn(agg)
    m = agg.merge(prof, on=[ENTITY, WEEKEND, TIME], how='left')
    m = m.merge(ent_p95, on=ENTITY, how='left')

    # MAD floor: dead-flat buckets (mad=0) would null the z-score and hide dumps
    safe_mad = m['mad'].where(m['mad'] > 0,
                              np.maximum(1.0, 0.05 * m['expected'].fillna(0)))
    m['robust_z'] = (0.6745 * (m[VALUE] - m['expected']) / safe_mad).fillna(0.0)

    operating = m['expected'] >= p['operating_min_median']
    enough = m['n'] >= p['min_history']
    dump_scale = m[VALUE] >= p['dump_scale_frac'] * m['ent_p95'].fillna(np.inf)

    flag = np.full(len(m), 'OK', dtype=object)
    flag[(m[VALUE] == 0) & operating & enough] = 'BLACKOUT'
    spike = ((m['robust_z'] >= p['z_spike'])
             & ((m[VALUE] - m['expected']) >= p['spike_min_abs'])
             & enough & ((m['mad'] > 0) | dump_scale))
    flag[spike] = 'SPIKE'
    flag[(m[VALUE] > 0) & (m['robust_z'] <= -p['z_low']) & operating & enough] = 'LOW'
    m['flag'] = flag

    # DRIFT: share-based, sustained, material, over-count only (watchlist)
    dz = m.groupby([DATE, ENTITY], observed=True)[VALUE].sum().reset_index()
    dz['tot'] = dz.groupby(DATE, observed=True)[VALUE].transform('sum')
    dz['share'] = dz[VALUE] / dz['tot'].replace(0, np.nan)
    med = dz.groupby(ENTITY, observed=True)['share'].median().rename('med_share')
    dz = dz.merge(med, on=ENTITY, how='left')
    dz['dev'] = (dz['share'] - dz['med_share']) / dz['med_share'].replace(0, np.nan)
    dz = dz.sort_values([ENTITY, DATE])
    dz['roll'] = (dz.groupby(ENTITY, observed=True)['dev']
                    .transform(lambda s: s.rolling(p['drift_min_days'],
                                                   min_periods=p['drift_min_days']).mean()))
    drift = dz[(dz['roll'] >= p['drift_share_dev']) & (dz['med_share'] >= p['drift_min_share'])]
    key = set(zip(drift[ENTITY], drift[DATE]))
    is_drift = pd.MultiIndex.from_frame(m[[ENTITY, DATE]]).isin(key)
    m.loc[is_drift & (m['flag'] == 'OK'), 'flag'] = 'DRIFT'

    m['severity'] = np.where(m['flag'] == 'OK', 0.0, m['robust_z'].abs().round(2))
    m = m.rename(columns={VALUE: 'actual'})
    return m[[DATE, TIME, ENTITY, WEEKEND, 'actual', 'expected', 'mad', 'n',
              'ent_p95', 'robust_z', 'flag', 'severity']]


def trust_score(trust):
    """Initial data-trust score: % of buckets judged OK (0-100)."""
    if len(trust) == 0:
        return 0.0
    return round(float((trust['flag'] == 'OK').mean()) * 100, 2)
