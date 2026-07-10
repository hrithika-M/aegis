# -*- coding: utf-8 -*-
"""Build a richer holiday/festival calendar for Hyderabad (India + Telangana).

The POD project ships a basic national holiday list; this adds Telangana
state-specific festivals (Bonalu, Bathukamma, Ugadi, Telangana Formation Day)
that drive real local travel patterns a national list misses — mapping to the
POD requirement for a "RGIA-specific event calendar."

Free, no key (the `holidays` Python package). Run:
    pip install holidays
    python fetch_holidays.py   -> hyderabad_holidays.csv
"""
import csv
import datetime as dt
import os

import holidays

HERE = os.path.dirname(os.path.abspath(__file__))
START, END = dt.date(2025, 4, 1), dt.date(2026, 3, 25)   # EWS window


def build():
    national = holidays.India(years=[2025, 2026])
    telangana = holidays.India(subdiv='TS', years=[2025, 2026])
    rows = []
    for d, name in sorted(telangana.items()):
        if START <= d <= END:
            rows.append({'date': d.isoformat(), 'holiday_name': name,
                         'scope': 'national' if d in national else 'telangana'})
    path = os.path.join(HERE, 'hyderabad_holidays.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'holiday_name', 'scope'])
        w.writeheader()
        w.writerows(rows)
    n_tel = sum(1 for r in rows if r['scope'] == 'telangana')
    print(f"wrote {path}: {len(rows)} holidays ({n_tel} Telangana-specific)")
    return path


if __name__ == '__main__':
    build()
