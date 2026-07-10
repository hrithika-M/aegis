"""Profile — learn what "normal" looks like for a source. Nothing configured;
everything measured.

For every (entity, weekday-vs-weekend, hour) bucket, the profile records:
  expected — the MEDIAN of history (robust central value)
  mad      — median absolute deviation (robust spread; std would be inflated by
             exactly the outages/spikes we are hunting)
  n        — how much history supports the judgement
plus each entity's p95 busy-scale (used by the dump-vs-open guard in detect).
"""
import numpy as np

from aegis.connectors import ENTITY, DATE, TIME, VALUE, WEEKEND


def aggregate(canon):
    """Collapse raw rows to one value per (date, hour, entity)."""
    g = canon.groupby([DATE, TIME, ENTITY], observed=True)[VALUE].sum().reset_index()
    wk = canon.groupby(DATE)[WEEKEND].first()
    g[WEEKEND] = g[DATE].map(wk).fillna(False)
    return g


def learn(agg):
    """Build the profile from an aggregated frame. Returns (profile_df, ent_p95)."""
    grp = agg.groupby([ENTITY, WEEKEND, TIME], observed=True)[VALUE]
    prof = grp.agg(expected='median', n='count')
    mad = grp.apply(lambda s: float(np.median(np.abs(s - np.median(s))))).rename('mad')
    prof = prof.join(mad).reset_index()
    ent_p95 = (agg[agg[VALUE] > 0].groupby(ENTITY, observed=True)[VALUE]
               .quantile(0.95).rename('ent_p95').reset_index())
    return prof, ent_p95
