"""Connectors — read any declared source and canonicalise it.

Supported kinds (config.SourceCfg.kind):
  csv / excel  — file path
  database     — SQLAlchemy URL + SQL query (Postgres, MySQL, SQLite, ...)
  dataframe    — an in-memory pandas DataFrame (programmatic use)

Canonical form every source is mapped into:
  entity (str) · date (date) · time_bucket (int hour) · value (float) · is_weekend

Validation is loud and accounted: bad timestamps, non-numeric values, negatives
and out-of-hour rows are COUNTED into the ingestion report and quarantined —
never silently dropped.
"""
import os

import pandas as pd

ENTITY, DATE, TIME, VALUE, WEEKEND = 'entity', 'date', 'time_bucket', 'value', 'is_weekend'
CANONICAL = [ENTITY, DATE, TIME, VALUE, WEEKEND]
_SINGLE = 'ALL'


def read_raw(src, dataframe=None):
    """Fetch the raw table for one SourceCfg."""
    if src.kind == 'dataframe':
        if dataframe is None:
            raise ValueError(f"source '{src.name}': kind=dataframe needs the frame "
                             "passed to run(..., frames={name: df})")
        return dataframe.copy()
    if src.kind == 'csv':
        return pd.read_csv(src.path)
    if src.kind == 'excel':
        return pd.read_excel(src.path)
    if src.kind == 'database':
        from sqlalchemy import create_engine, text
        engine = create_engine(src.url)
        with engine.connect() as conn:
            return pd.read_sql(text(src.query), conn)
    raise ValueError(f"source '{src.name}': unsupported kind '{src.kind}'")


def canonicalise(df, src):
    """Map raw columns -> canonical; validate; return (canon_df, ingestion_report)."""
    c = src.columns
    need = [v for v in (c.get('datetime'), c.get('date'), c.get('hour'),
                        c.get('entity'), c['value']) if v]
    missing = [col for col in need if col not in df.columns]
    if missing:
        raise KeyError(f"source '{src.name}': missing columns {missing}. "
                       f"Available: {list(df.columns)[:25]}")

    rep = {'rows_in': int(len(df))}
    if len(df) == 0:
        raise ValueError(f"source '{src.name}': no rows")

    out = pd.DataFrame(index=df.index)
    if c.get('datetime'):
        ts = pd.to_datetime(df[c['datetime']], errors='coerce')
        rep['rows_bad_timestamp'] = int(ts.isna().sum())
        out[DATE], out[TIME] = ts.dt.date, ts.dt.hour
        out[WEEKEND] = ts.dt.dayofweek.isin([5, 6])
    else:
        d = pd.to_datetime(df[c['date']], errors='coerce')
        h = pd.to_numeric(df[c['hour']], errors='coerce')
        rep['rows_bad_timestamp'] = int((d.isna() | h.isna()).sum())
        out[DATE], out[TIME] = d.dt.date, h
        out[WEEKEND] = d.dt.dayofweek.isin([5, 6])

    v = pd.to_numeric(df[c['value']], errors='coerce')
    rep['rows_nonnumeric_value'] = int(v.isna().sum())
    out[VALUE] = v
    out[ENTITY] = (df[c['entity']].astype(str).str.strip()
                   if c.get('entity') else _SINGLE)

    before = len(out)
    out = out.dropna(subset=[DATE, TIME, VALUE])
    rep['rows_negative_value'] = int((out[VALUE] < 0).sum())
    out = out[out[VALUE] >= 0]
    out[TIME] = out[TIME].astype(int)
    rep['rows_bad_hour'] = int(((out[TIME] < 0) | (out[TIME] > 23)).sum())
    out = out[(out[TIME] >= 0) & (out[TIME] <= 23)]
    rep['rows_dropped_total'] = before - len(out)
    rep['rows_used'] = int(len(out))
    if len(out) == 0:
        raise ValueError(f"source '{src.name}': no valid rows after validation ({rep})")
    rep['days'] = int(out[DATE].nunique())
    rep['entities'] = int(out[ENTITY].nunique())
    return out[CANONICAL].reset_index(drop=True), rep


def load_source(src, dataframe=None):
    """read_raw + canonicalise in one call -> (canon, ingestion_report)."""
    return canonicalise(read_raw(src, dataframe), src)
