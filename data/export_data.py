# -*- coding: utf-8 -*-
"""Export ALL POD EWS camera data (every touchpoint) to CSVs.

The EWS data has six touchpoints: Entry, CheckIn, Emigration, Immigration,
PESC (Security), Transfers. This exports each to <tp>.csv (raw 5-min rows:
DateTime, Zone, Throughput) into this data/ folder.

Requires the POD project (its cached EWS data). Run from the DATA_POD folder:
    cd <...>/POD 1/DATA_POD
    python <...>/aegis/data/export_data.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.getcwd())                      # DATA_POD (run from there)
import data_trust                                    # noqa: F401  bootstraps POD_HOME

from config import SHEET_NAMES                        # noqa: E402  the 6 touchpoints
from training.common import get_clean_data           # noqa: E402  (POD data layer)

data = get_clean_data()
out = HERE
os.makedirs(out, exist_ok=True)
for tp in SHEET_NAMES:
    df = data[tp][['DateTime', 'Zone', 'Throughput']]
    fname = tp.lower() + '.csv'
    df.to_csv(os.path.join(out, fname), index=False)
    print(f"{fname:<16} {len(df):>10,} rows")
