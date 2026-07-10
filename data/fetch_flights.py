# -*- coding: utf-8 -*-
"""Fetch the best FREE, no-credentials flight data for Hyderabad (HYD).

Reality check: recent flight OPERATIONS data (schedules, delays) is not
available free without credentials (OpenSky blocks anonymous; Kaggle needs a
token). The best real, no-auth flight data is the OpenFlights ROUTE NETWORK —
which airlines fly HYD to/from where. It is reference data (route structure),
not per-flight operations, and the OpenFlights routes snapshot is not recent —
but it is real. For recent operations, supply a Kaggle token or OpenSky account.

Source: OpenFlights (https://openflights.org/data.html), public domain-ish.

Run:  python fetch_flights.py   -> hyderabad_routes.csv
"""
import csv
import io
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTES = 'https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat'
COLS = ['airline', 'airline_id', 'source', 'source_id', 'dest', 'dest_id',
        'codeshare', 'stops', 'equipment']


def fetch(airport='HYD'):
    print(f"fetching OpenFlights routes and filtering to {airport} ...")
    req = urllib.request.Request(ROUTES, headers={'User-Agent': 'aegis'})
    raw = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    rows = []
    for r in csv.reader(io.StringIO(raw)):
        if len(r) != len(COLS):
            continue
        rec = dict(zip(COLS, r))
        if rec['source'] == airport or rec['dest'] == airport:
            rec['direction'] = 'departure' if rec['source'] == airport else 'arrival'
            rows.append(rec)
    path = os.path.join(HERE, 'hyderabad_routes.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS + ['direction'])
        w.writeheader()
        w.writerows(rows)
    airlines = sorted({r['airline'] for r in rows})
    dests = sorted({(r['dest'] if r['direction'] == 'departure' else r['source']) for r in rows})
    print(f"wrote {path}: {len(rows)} HYD routes, {len(airlines)} airlines, {len(dests)} connected airports")
    print("  sample airlines:", ', '.join(airlines[:12]))
    return path


if __name__ == '__main__':
    fetch()
