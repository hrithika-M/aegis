"""Repair — fix what detect flagged, scaled to the day's REAL activity.

The core idea (validated on real airport data): when a sensor was dark for an
hour, don't fill the gap with a flat historical average — measure how busy THAT
DAY actually was from the same entity's healthy hours, and scale the expected
value by that factor. A genuinely busy day stays busy; a quiet day stays quiet.

Actions per flag:
  BLACKOUT / LOW — fill with  expected × day_activity_factor
  SPIKE          — cap at     expected × factor + 3×MAD   (never below 0)
  DRIFT          — untouched (watchlist: sustained bias needs a human/audit,
                   auto-"correcting" it would hide a real sensor problem)
  OK             — untouched, always

Every repair carries a CONFIDENCE, based on how much healthy evidence that
day/entity offered for the activity factor:
  HIGH    >= 6 healthy hours that day  -> safe to auto-apply
  MEDIUM  3-5 healthy hours            -> apply, but report prominently
  LOW     < 3 healthy hours            -> factor is guesswork; the fill is
          computed but flagged for the reconcile stage (Push 6) to improve
          using OTHER sources — or for escalation. Never silently trusted.

An optional physical ceiling (SourceCfg.physical_max) clamps every repaired
value to what is physically possible.
"""
import numpy as np
import pandas as pd

from aegis.connectors import ENTITY, DATE, TIME

FACTOR_CLIP = (0.3, 3.0)      # day-activity factor bounds (guards tiny samples)
HIGH_MIN_HEALTHY = 6          # healthy hours/day for HIGH confidence
MED_MIN_HEALTHY = 3           # ... for MEDIUM confidence


def repair(trust, physical_max=None):
    """Take detect()'s trust table; return it with:
    value_adj (the repaired series), was_corrected, repair_method, confidence.
    """
    t = trust.copy()
    healthy = t['flag'] == 'OK'
    # INFORMATIVE healthy hours only: a silent night hour (expected ~ 0) is
    # trivially 'OK' but says nothing about how busy the day was — it must not
    # inflate the factor's evidence count (confidence would lie).
    informative = healthy & (t['expected'] >= 1.0)

    # day-activity factor per (date, entity), from that day's informative
    # healthy hours: how busy was today vs what history expected for them?
    day = (t[informative].groupby([DATE, ENTITY], observed=True)
           .agg(a=('actual', 'sum'), e=('expected', 'sum'), n_healthy=('actual', 'size'))
           .reset_index())
    day['factor'] = (day['a'] / day['e'].replace(0, np.nan)).clip(*FACTOR_CLIP).fillna(1.0)
    t = t.merge(day[[DATE, ENTITY, 'factor', 'n_healthy']], on=[DATE, ENTITY], how='left')
    t['factor'] = t['factor'].fillna(1.0)
    t['n_healthy'] = t['n_healthy'].fillna(0).astype(int)

    adj = t['actual'].astype(float).copy()
    method = np.full(len(t), '', dtype=object)
    conf = np.full(len(t), '', dtype=object)

    # BLACKOUT / LOW -> fill with expected scaled to today's activity
    fill = t['flag'].isin(['BLACKOUT', 'LOW'])
    adj[fill] = (t.loc[fill, 'expected'] * t.loc[fill, 'factor']).round()
    method[fill] = 'fill_expected_x_day_factor'

    # SPIKE -> cap to the plausible ceiling for today
    cap = t['flag'] == 'SPIKE'
    ceiling = (t['expected'] * t['factor'] + 3.0 * t['mad'].fillna(0)).clip(lower=0)
    adj[cap] = np.minimum(t.loc[cap, 'actual'], ceiling[cap]).round()
    method[cap] = 'cap_to_plausible_ceiling'

    # confidence from the healthy-evidence the factor rests on
    fixed = fill | cap
    conf[fixed & (t['n_healthy'] >= HIGH_MIN_HEALTHY)] = 'HIGH'
    conf[fixed & (t['n_healthy'] >= MED_MIN_HEALTHY)
         & (t['n_healthy'] < HIGH_MIN_HEALTHY)] = 'MEDIUM'
    conf[fixed & (t['n_healthy'] < MED_MIN_HEALTHY)] = 'LOW'

    # DRIFT: watchlist — report, never auto-correct
    drift = t['flag'] == 'DRIFT'
    method[drift] = 'watchlist_no_autocorrect'

    if physical_max is not None:
        over = adj > physical_max
        adj[over] = physical_max
        method[over & fixed] = method[over & fixed] + '+clamped_physical_max'

    t['value_adj'] = adj
    t['was_corrected'] = fixed
    t['repair_method'] = method
    t['confidence'] = conf
    return t


def summarize(t):
    """Machine-readable repair summary for the report/heal stages."""
    fixed = t[t['was_corrected']]
    moved = float((t['value_adj'] - t['actual']).abs().sum())
    total = float(t['actual'].sum())
    return {
        'buckets': int(len(t)),
        'corrected': int(len(fixed)),
        'by_confidence': fixed['confidence'].value_counts().to_dict(),
        'volume_shift_pct': round(moved / total * 100, 2) if total else 0.0,
        'drift_watchlist': int((t['flag'] == 'DRIFT').sum()),
    }
