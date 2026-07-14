"""Dataset — the ONE source of truth for the trusted feature frame.

Every model in this layer trains on this: the corrected (trusted) hourly actuals
from the data-trust engine, with calendar features. This replaces the identical
frame-build that used to be copy-pasted into benchmark, plan, intervals, backtest.

Feature interface for the future: `FEATURES` is calendar-only today. When the
real feeds arrive (booking load, aircraft type, updated schedule, scans...),
join them onto the frame and extend the feature list — same downstream code.
"""
from config import SHEET_NAMES
from data_processor.features import FEATURES_HOURLY, add_date_feature_columns
from data_trust.adapter import camera_to_canonical
from data_trust.single_source import corrected_hourly
from data_trust.schema import DATE, TIME
from training.common import get_clean_data, drop_dump_days

FEATURES = list(FEATURES_HOURLY)   # calendar features (extend when real data lands)
TARGET = 'adj'                     # trusted (corrected) hourly passengers


def trusted_hourly(data, tp):
    """Trusted hourly frame for one touchpoint: columns Date, Hour, raw, adj +
    calendar features. `adj` is the target (cleaned actuals)."""
    g, _ = corrected_hourly(camera_to_canonical(drop_dump_days(data[tp])))
    g = g.rename(columns={DATE: 'Date', TIME: 'Hour'})
    return add_date_feature_columns(g)


def all_frames(data=None):
    """{touchpoint: trusted_hourly frame} for every touchpoint (+ the raw data)."""
    data = data or get_clean_data()
    return {tp: trusted_hourly(data, tp) for tp in SHEET_NAMES}, data
