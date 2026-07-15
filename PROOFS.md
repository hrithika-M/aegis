# Proofs — evidence across the whole platform

Concrete, reproducible evidence for **each** subsystem, not just the data engine:
Aegis healing (Proofs 1–2), the forecasting models (Proof 3), and the digital-twin
reconciliation (Proof 4). See [`ARCHITECTURE.md`](ARCHITECTURE.md) for how they fit.

---

## Proofs 1–2 — Aegis self-healing engine
Two runs of the identical engine, zero code changes — different domains, connectors,
data shapes: the generality claim, demonstrated. Reports: `data_pipeline/examples/*/report.html`.

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

## Proof 3 — Forecasting models (real HYD data)

Per-touchpoint model selection on **real** Hyderabad EWS demand — expanding-window
walk-forward, full metric panel (not a single number). The finalized winners:

| Touchpoint | Best model | Accuracy (walk-forward) |
|---|---|---|
| PESC / Security | LightGBM | **90.9%** |
| Check-In | LightGBM | 88.3% |
| Entry | RandomForest | 87.6% |
| Emigration | LightGBM | 80.1% |
| Transfers | LightGBM | 77.8% |
| Immigration | XGBoost | 67.1% |

**Honest findings:** all capable tree/boosting models tie within ~1 pt (RF chosen as
the robust default); a foundation model (Amazon **Chronos**) reached **89.8%
zero-shot** on Entry, beating the trained RandomForest (88.3%). Immigration's ~67%
ceiling is a *data* limit (arrivals need flight-arrival signal a calendar can't
supply), not an algorithm limit. Artifacts: `models/`, `trial_models/`.

## Proof 4 — Digital-twin reconciliation (Bhogapuram/VTZ)

The twin generates simulated operations for a greenfield airport — but its
passenger *volumes* are pinned to reality:

| Check | Twin | Real (DGCA/AAI) | Match |
|---|---|---|---|
| Daily passengers | ~7,942/day | ~8,000/day | ✓ |
| Jan-2026 monthly | 270,258 | 271,302 | **99.6%** |
| Per-route totals | reconciled per route × month × direction | DGCA city-pair | exact (95%-capped) |

The twin is honest about what it is: real volumes, *modelled* flow (documented
show-up/service assumptions). Artifacts: `bhogapuram_digital_twin/`.

---

## What the proofs establish

1. **Aegis is general & honest:** same engine on airports and retail, CSV and SQL;
   2M real rows end-to-end; 4,509 cells cross-healed; met the target where the data
   allowed (99.66%) and refused to fake it where it didn't (95.53% + watchlist).
2. **The models are validated on real data:** per-touchpoint winners at 67–91%
   walk-forward, judged on a full metric panel, with honest ceilings called out.
3. **The twin is anchored to reality:** simulated operations that reconcile to real
   DGCA passenger counts within ~4%, with real/simulated kept strictly separate.

Reproduce:
```bash
cd examples/retail_demo   && python make_data.py && python -m aegis.report config.yaml out
cd examples/pod_airport   && python export_data.py && python -m aegis.report config.yaml out
# (pod export requires the POD project's data; see export_data.py)
```
