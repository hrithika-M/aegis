# -*- coding: utf-8 -*-
"""Build the retail demo: a SQLite DATABASE of store footfall + till receipts
(simulated, clearly labelled as such) with realistic planted faults.

A totally different domain from airports — different entities (stores), different
rhythm (mall hours 09-21, weekend peaks), accessed through the DATABASE
connector. Same Aegis engine, zero code changes.

Faults planted:
  counter outage — Store_B footfall counter dark 2025-05-14 (whole day)
  double-count   — Store_A footfall x2 on 2025-06-02 10:00-13:00 (glitch)
  till feed gap  — receipts missing (0) for Store_C 2025-04-22 11:00-16:00

Links: footfall <-> receipts (people who enter, buy — strongly correlated),
so each feed can heal the other.

Run:  python make_data.py     -> retail.db
"""
import os

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

HERE = os.path.dirname(os.path.abspath(__file__))


def build():
    rng = np.random.default_rng(77)
    stores = {'Store_A': 1.0, 'Store_B': 1.5, 'Store_C': 0.7}
    foot, till = [], []
    for d in pd.date_range('2025-03-01', periods=150, freq='D'):
        wk = 1.35 if d.dayofweek >= 5 else 1.0
        for h in range(24):
            if 9 <= h <= 21:
                base = (120 + 90 * np.sin((h - 9) / 12 * np.pi)) * wk
            else:
                base = 0
            ts = d + pd.Timedelta(hours=h)
            for s, k in stores.items():
                if base == 0:                # mall CLOSED: genuinely zero, no noise
                    f = r = 0.0              # (noise here would teach the profile
                else:                        #  that 3AM visitors are normal)
                    f = max(0, base * k + rng.normal(0, 9))
                    r = max(0, f * 0.31 + rng.normal(0, 4))  # ~31% conversion
                foot.append({'ts': ts, 'store': s, 'visitors': round(f)})
                till.append({'ts': ts, 'store': s, 'receipts': round(r)})
    foot, till = pd.DataFrame(foot), pd.DataFrame(till)

    day = pd.Timestamp('2025-05-14')
    foot.loc[(foot['ts'].dt.date == day.date()) & (foot['store'] == 'Store_B'),
             'visitors'] = 0
    m = ((foot['ts'].dt.date == pd.Timestamp('2025-06-02').date())
         & foot['ts'].dt.hour.between(10, 13) & (foot['store'] == 'Store_A'))
    foot.loc[m, 'visitors'] = foot.loc[m, 'visitors'] * 2
    m2 = ((till['ts'].dt.date == pd.Timestamp('2025-04-22').date())
          & till['ts'].dt.hour.between(11, 16) & (till['store'] == 'Store_C'))
    till.loc[m2, 'receipts'] = 0

    db = os.path.join(HERE, 'retail.db')
    engine = create_engine(f"sqlite:///{db}")
    foot.to_sql('footfall', engine, index=False, if_exists='replace')
    till.to_sql('receipts', engine, index=False, if_exists='replace')
    print(f"retail.db built: {len(foot):,} footfall rows, {len(till):,} receipt rows")
    return db


if __name__ == '__main__':
    build()
