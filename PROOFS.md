# Aegis — End-to-End Proofs

Two complete runs of the identical engine, zero code changes between them —
different domains, different connectors, different data shapes. This is the
generality claim, demonstrated. Committed reports: `data_pipeline/examples/*/report.html`.

---

## Proof 1 — Real airport camera data (CSV connector, 2M rows)

**Data:** GMR Hyderabad POD project — Entry gates (985,748 rows) + Security/PESC
(1,004,356 rows), real production sensor telemetry, Apr 2025 – Mar 2026.
**Links:** entry ↔ pesc (mutual healing).

| Result | Value |
|---|---|
| Cells healed (audited) | **9,351** (entry 3,256 · pesc 6,095) |
| Cross-healed from the linked source | **4,509**, provenance `pesc(r=0.73)` / `entry(...)` |
| Trust | entry **93.2% → 97.1%** · pesc **86.9% → 94.0%** |
| Iterations | 2 (converged — second pass found nothing more confident) |
| Verdict | **95.53% vs target 97% — TARGET NOT MET, reported honestly** |
| Escalations | 7,637 — of which **7,622 are DRIFT watchlist** |

**Why "target not met" is the RIGHT outcome here:** the remaining gap is almost
entirely DRIFT — sensors persistently over-counting their share for days. Aegis
deliberately refuses to auto-correct sustained bias (it needs a human camera
audit; silently "fixing" it would hide a real hardware problem). An engine that
reported 97%+ on this data would be lying. This is the honesty contract working
on production data.

**External validation:** Aegis learned the entry↔pesc relationship as r=0.73 —
independently matching r=0.718 measured months earlier in the POD project's own
correlation study. The engine rediscovered the airport's structure from scratch.

## Proof 2 — Retail store demo (SQL DATABASE connector, simulated)

**Data:** simulated mall footfall + till receipts (3 stores, 150 days, 21,600
rows) in a SQLite database — the exact code path Postgres uses. Faults planted:
a full-day counter outage, a 4-hour double-count glitch, a 6-hour till-feed gap.
**Links:** footfall ↔ receipts.

| Result | Value |
|---|---|
| Planted counter outage (Store_B, 13 open hours) | caught: BLACKOUT ×13, healed **from receipts** |
| Planted double-count (Store_A) | caught: SPIKE ×4, capped |
| Planted till gap (Store_C) | caught: BLACKOUT ×6, healed **from footfall** |
| False alarms | ~7 random LOWs = **0.03%** |
| Cross-healed | 13 cells, provenance `receipts(r=1.00)` etc. |
| Verdict | **99.66% — TARGET MET** |

**A lesson kept for the record:** the first demo generator put random noise in
closed-mall night hours, teaching the profile that "3 AM visitors are normal" —
the engine then (correctly) flagged genuine night zeros as blackouts. The engine
judged the data it was given; the data was wrong. Generator fixed (closed =
truly zero). The audit ledger made the cause obvious in seconds — which is the
point of having one.

---

## What the two proofs establish

1. **General:** same engine, same config shape — airports and retail, CSV and SQL.
2. **Scales:** 2M real rows end-to-end (scan → heal → report) in minutes.
3. **Heals across sources:** 4,509 real cells rebuilt from a linked feed with
   learned ratios and correlation-weighted confidence.
4. **Honest:** met the target where the data allowed (99.66%), and refused to
   fake it where it didn't (95.53% + a 7,622-row human watchlist).

Reproduce:
```bash
cd examples/retail_demo   && python make_data.py && python -m aegis.report config.yaml out
cd examples/pod_airport   && python export_data.py && python -m aegis.report config.yaml out
# (pod export requires the POD project's data; see export_data.py)
```
