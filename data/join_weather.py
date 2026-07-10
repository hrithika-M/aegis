# -*- coding: utf-8 -*-
"""Join EWS passenger flow with weather -> one modelling-ready hourly table.

For each (date, hour): total passengers per touchpoint (summed across zones and
the twelve 5-min rows in the hour) + that hour's weather + calendar features.
This is what a weather-aware demand model trains on.

Also prints an HONEST check: does weather actually relate to demand? (Airlines
fly on schedule regardless of drizzle, so weather tends to move TIMING/delays
more than total volume — we report what the data says, not what we hope.)

Run:  python join_weather.py     -> data/ews_weather_hourly.csv
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = HERE


def hourly_pax(fname, label):
    df = pd.read_csv(os.path.join(DATA, fname), usecols=['DateTime', 'Throughput'])
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    df['hour'] = df['DateTime'].dt.floor('h')
    return df.groupby('hour')['Throughput'].sum().rename(label)


def build():
    entry = hourly_pax('entry.csv', 'entry_pax')
    pesc = hourly_pax('pesc.csv', 'pesc_pax')
    wx = pd.read_csv(os.path.join(DATA, 'hyderabad_weather.csv'), parse_dates=['time'])
    wx = wx.rename(columns={'time': 'hour'})

    # join weather onto every EWS hour (left join keeps all operating hours)
    df = pd.concat([entry, pesc], axis=1).reset_index()
    df = df.merge(wx, on='hour', how='left')

    # calendar features a model would use
    df['dow'] = df['hour'].dt.dayofweek
    df['month'] = df['hour'].dt.month
    df['hour_of_day'] = df['hour'].dt.hour
    df['is_weekend'] = (df['dow'] >= 5).astype(int)

    out = os.path.join(DATA, 'ews_weather_hourly.csv')
    df.to_csv(out, index=False)
    print(f"wrote {out}: {len(df):,} hourly rows, {df.shape[1]} columns")
    print("columns:", list(df.columns))

    # ── honest signal check ──
    print("\nDoes weather relate to demand? (Pearson r on daily totals)")
    daily = df.set_index('hour').resample('D').agg(
        entry=('entry_pax', 'sum'), pesc=('pesc_pax', 'sum'),
        rain=('precipitation', 'sum'), max_gust=('wind_gusts_10m', 'max'),
        avg_temp=('temperature_2m', 'mean')).dropna()
    for w in ('rain', 'max_gust', 'avg_temp'):
        re = daily['entry'].corr(daily[w]); rp = daily['pesc'].corr(daily[w])
        print(f"  daily {w:9} vs entry r={re:+.3f} | vs pesc r={rp:+.3f}")
    wet = daily[daily['rain'] > 5]; dry = daily[daily['rain'] == 0]
    if len(wet) and len(dry):
        print(f"\n  avg entry pax — rainy days (>5mm, n={len(wet)}): {wet['entry'].mean():,.0f}"
              f"  vs dry days (n={len(dry)}): {dry['entry'].mean():,.0f}")
    return out


if __name__ == '__main__':
    build()
