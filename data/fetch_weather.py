# -*- coding: utf-8 -*-
"""Fetch REAL hourly weather for Hyderabad airport (RGIA / VOHS) on the exact
EWS timeline, from the Open-Meteo Historical Archive (free, no API key, ERA5
reanalysis — real measured/modelled weather).

Why Open-Meteo over a Kaggle file: it delivers this *specific recent window*
(Apr 2025 - Mar 2026) for this *exact location*, hourly, aligned to local time —
which no static Kaggle dataset covers. Output is a clean CSV ready to drop into
the POD pipeline or as an Aegis source.

Airport: Rajiv Gandhi International, Hyderabad (HYD). lat 17.24, lon 78.43.
Timezone Asia/Kolkata so hourly stamps align with the EWS local time.

Run:  python fetch_weather.py         -> data/hyderabad_weather.csv
"""
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
START, END = '2025-04-01', '2026-03-25'          # EWS timeline
LAT, LON = 17.2403, 78.4294

# airport-disruption-relevant variables
# NB: 'visibility' is NOT in the free ERA5 archive (returns all-null), so it is
# omitted; weather_code carries the airport-critical fog (45/48) and thunderstorm
# (95-99) signals instead. For true reported visibility, METAR is the source.
HOURLY = ['temperature_2m', 'relative_humidity_2m', 'precipitation', 'rain',
          'weather_code', 'cloud_cover', 'wind_speed_10m',
          'wind_gusts_10m', 'surface_pressure']


def fetch():
    q = urllib.parse.urlencode({
        'latitude': LAT, 'longitude': LON,
        'start_date': START, 'end_date': END,
        'hourly': ','.join(HOURLY), 'timezone': 'Asia/Kolkata',
    })
    url = f'https://archive-api.open-meteo.com/v1/archive?{q}'
    print(f"fetching {START} .. {END} hourly weather for HYD ...")
    with urllib.request.urlopen(url, timeout=120) as r:
        data = json.load(r)
    h = data['hourly']
    import csv
    out = HERE
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'hyderabad_weather.csv')
    cols = ['time'] + HOURLY
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in range(len(h['time'])):
            w.writerow([h['time'][i]] + [h[c][i] for c in HOURLY])
    print(f"wrote {path}: {len(h['time']):,} hourly rows, {len(HOURLY)} variables")
    return path


if __name__ == '__main__':
    fetch()
