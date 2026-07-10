# -*- coding: utf-8 -*-
"""Export the REAL POD camera data (Entry + PESC) to CSVs for the Aegis proof.

Requires the POD project (its cached EWS data). Run from the DATA_POD folder:
    cd <...>/POD 1/DATA_POD
    python <...>/aegis/examples/pod_airport/export_data.py

Writes entry.csv / pesc.csv (raw 5-min rows: DateTime, Zone, Throughput) into
examples/pod_airport/data/ — NOT committed (real operational data).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.getcwd())                      # DATA_POD (run from there)
import data_trust                                    # noqa: F401  bootstraps POD_HOME

from training.common import get_clean_data          # noqa: E402  (POD data layer)

data = get_clean_data()
out = HERE
os.makedirs(out, exist_ok=True)
for tp, fname in (('Entry', 'entry.csv'), ('PESC', 'pesc.csv')):
    df = data[tp][['DateTime', 'Zone', 'Throughput']]
    df.to_csv(os.path.join(out, fname), index=False)
    print(f"{fname}: {len(df):,} rows")
