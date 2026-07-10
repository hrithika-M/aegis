# data — all datasets for the POD / Aegis work

Everything in one place, committed for reproducibility. Timeline anchor is the
**EWS window: 2025-04-01 → 2026-03-25**.

## Datasets

| File | What | Source | Rows |
|---|---|---|---|
| `entry.csv` | EWS Entry-gate camera counts (5-min, per zone) | POD project EWS export | ~986k |
| `pesc.csv` | EWS Security/PESC camera counts (5-min, per zone) | POD project EWS export | ~1.0M |
| `hyderabad_weather.csv` | Real hourly weather at RGIA (temp, humidity, precip, wind, gusts, pressure, weather_code) | Open-Meteo ERA5 archive | 8,616 |
| `ews_weather_hourly.csv` | EWS hourly demand joined with weather + calendar features | derived (`join_weather.py`) | ~8,611 |
| `hyderabad_routes.csv` | HYD flight route network (airline, origin/dest, direction) | OpenFlights | 147 routes |

## Acquisition scripts (reproducible)

| Script | Produces | Notes |
|---|---|---|
| `export_data.py` | `entry.csv`, `pesc.csv` | run from the POD project (`DATA_POD/`); needs its data layer |
| `fetch_weather.py` | `hyderabad_weather.csv` | Open-Meteo, free, no key — pulls the exact EWS window |
| `join_weather.py` | `ews_weather_hourly.csv` | joins EWS hourly demand + weather + calendar |
| `fetch_flights.py` | `hyderabad_routes.csv` | OpenFlights routes filtered to HYD |

## Honest notes on each stream
- **EWS (entry/pesc)** — real airport camera data; the core signal. Contains
  sensor faults (blackouts/spikes/drift) that the `data_pipeline` (Aegis) heals.
- **Weather** — real and correctly located, but analysis showed it has **no
  effect on passenger *demand* beyond the calendar** (seasonal confound; people
  fly on schedule). May matter for *disruption/timing* once flight-delay data
  exists. See `join_weather.py` output.
- **Flights (routes)** — the best FREE, no-credentials flight data available:
  the route *network* (which airlines fly HYD ↔ where). It is **reference data,
  not operations/delays**, and the OpenFlights snapshot is not recent. Real
  recent operations data needs a Kaggle token or OpenSky account.
- **NOT here (and unobtainable externally):** CUPPS, E-Boarding, LDM, PTM, PNR —
  proprietary GHIAL/airline passenger-processing data. These can only come from
  the airport, and are what the POD core models actually need to train on.
