# Aegis — Research & Plan (a general self-healing data engine)

**Status:** RESEARCH + PLAN (not yet implemented). Approved architecture goes here
before code. This is the systematic record of *why* we build it the way we do.

**Goal:** generalize our POD `data_trust` engine into a **dataset-agnostic,
config-driven, self-healing** data-quality system: point it at any source (file
path OR Postgres credentials), it profiles the data, detects anomalies
(blackout/spike/low/drift), repairs them scaled to the day's real activity, then
uses cross-table dependencies + ground-truth references to fix the low-confidence
cases — iterating until the data-trust score converges. Works for POD and any
other dataset.

---

## 1. Prior art (what exists, how it works)

| System | What it does | Take-away for us |
|---|---|---|
| **HoloClean** (VLDB) — arxiv.org/abs/1702.00820 | Repairs data by unifying 3 weak signals: statistical profiles + integrity constraints + **external/cross-table data**, via probabilistic inference | The theoretical blueprint for our exact idea. But heavy, academic, not time-series. We build a practical, time-series version. |
| **Great Expectations / Soda / Deequ / Pandera** | Detect / validate data quality; Soda connects to any DB via credentials + YAML | They **detect but do NOT repair** — that is our differentiator. Adopt Soda's config+connector pattern. |
| **MICE** (Multiple Imputation by Chained Equations) | Impute each broken column by predicting it from all the others, iteratively | The gold standard for cross-column-dependency filling = our "inter-table dependency" reconcile step. |
| **Self-healing pipelines (2026 trend)** | Detect → diagnose → remediate autonomously | Key rule: **confidence-gated repair** — auto-fix only HIGH-confidence + LOW blast-radius; escalate the rest. This is how we make "self-healing" safe. |

**Sources:** HoloClean (arxiv.org/abs/1702.00820); GX/Soda/Deequ comparison
(branchboston.com); 2026 OSS data-quality landscape (datakitchen.io); MICE
(medium.com/@saraswatp); imputation comparison (PMC10870437); self-healing 2026
(analyticsweek.com, medium.com/ai-analytics-diaries).

## 2. The gap (nobody combines all six)

Connect any source · detect · **repair** · cross-table/ground-truth reconcile ·
time-series aware · **iterate + confidence-gate**. Detectors don't repair;
HoloClean repairs but is heavy & not time-series; MICE imputes but ignores
ground-truth/physical limits. Our `data_trust` already does the time-series
repair + cross-source reconciliation — Aegis generalizes it and adds config/DB
connectors, MICE cross-column imputation, and the confidence-gated self-heal loop.

## 3. Architecture

```
config.yaml  (paths OR Postgres creds + ground-truth refs + limits + target)
   ① CONNECT     file / Postgres(SQLAlchemy) -> canonical frame        [Soda]
   ② PROFILE     learn normal band per column: median, MAD, range      [Deequ/GX + ours]
   ③ DETECT      flag each cell: OK/BLACKOUT/SPIKE/LOW/DRIFT            [ours]
   ┌─ SELF-HEALING LOOP (until converged or target) ──────────────────────────┐
   │ ④ REPAIR (single-source)   expected x that-day's activity-factor          │
   │ ⑤ RECONCILE (cross-source) MICE chained-eqns + trust policy:              │
   │    predict low-confidence cells from related columns/tables, anchored     │
   │    to ground-truth refs (LDM) & physical limits (seat cap), correlation-  │
   │    weighted. Each fix carries a CONFIDENCE.                    [HoloClean+MICE]
   │ ⑥ SCORE   data-trust score; auto-apply HIGH-confidence only    [2026 self-heal]
   └───────────────────────────────────────────────────────────────────────────┘
   ⑦ REPORT   healed data + trust score + audit trail + ESCALATION list
```

## 4. Honest note on the "97%" target

Achievable quality is bounded by **redundancy**. If a value is missing and its
related sources/columns have signal, we fill it with high confidence; if *all*
related signal is also dark, no iteration invents the truth — the engine reports
"could not confidently repair -> escalated," never fabricates. So the target is:
**iterate until the trust score converges, auto-fix every high-confidence error,
aim for 97%, and honestly report the achieved score + escalation list.** On
redundant data (like POD's) it will get very high; the guarantee is honesty, not
a magic number. (This matches the industry confidence-gate rule.)

## 5. Build plan — package `aegis/`

| # | File | Role | Reuse/New |
|---|---|---|---|
| 1 | `config.py` | declarative config (sources, DB creds, refs, constraints, gate, target) | new |
| 2 | `connectors.py` | file + Postgres (SQLAlchemy) -> canonical frame | new |
| 3 | `profile.py` | learn normal band per column | generalize ours |
| 4 | `detect.py` | per-cell anomaly flags | generalize single_source |
| 5 | `repair.py` | single-source day-scaled reconstruction | ours |
| 6 | `reconcile.py` | MICE cross-column + trust policy + ground-truth refs | ours + new |
| 7 | `heal.py` | confidence-gated iterative self-heal loop + trust score | new |
| 8 | `report.py` | audit trail + trust score + HTML + escalation list | generalize ours |
| 9 | `cli.py` | `python -m aegis run config.yaml` | new |

**Phasing:**
- **Phase 1** — config + connectors (file+Postgres) + profile + detect → runs on any source, *reports* quality (proves generality).
- **Phase 2** — repair + reconcile (MICE+refs) + self-heal loop → actually heals + trust score.
- **Phase 3** — report/HTML + escalation; prove on POD *and* a second unrelated dataset.

## 6. Open decisions
1. "97%" reframe (converge + confidence-gate + honest residual) — agreed?
2. Postgres test target — real DB, or SQLite + synthetic tables for now?
3. Name — "Aegis" (a shield) or other?
