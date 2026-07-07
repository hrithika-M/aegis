# Aegis — Workflow Pipeline

The concrete data flow, derived from the research (see AEGIS_RESEARCH_AND_PLAN.md).
Diagram: `docs/aegis_workflow.png`.

**One line:** point Aegis at any source → it learns what "normal" is → heals the
errors it can fix confidently → escalates the rest → reports honestly.

---

## Stage-by-stage (inputs → what happens → outputs)

**0 · CONFIGURE** *(config.py)*
- IN: a config declaring each source (name, connector, file-path OR DB
  credentials, column mapping, role = data | reference | constraint), the
  ground-truth references (e.g. LDM), physical limits (e.g. value ≤ seat_capacity),
  cross-source links, the confidence gate, and the trust target.
- OUT: a validated run configuration.

**1 · CONNECT & CANONICALISE** *(connectors.py — Soda pattern)*
- Read each source: file (csv/xlsx) OR SQL query over Postgres (SQLAlchemy).
- Map raw columns → canonical form (`source, entity, time, value, dims`).
- Validate: bad timestamps, non-numeric, negatives, out-of-range → **counted and
  quarantined, never silently dropped.**
- OUT: canonical frame per source + an ingestion report.

**2 · PROFILE — learn "normal"** *(profile.py — Deequ/GX + our median/MAD)*
- Per source, per (entity × time-bucket): robust band = **median + MAD**, valid
  range, operating/sparsity pattern.
- OUT: a profile store (the learned notion of normal). *Nothing hard-coded — it is
  measured from the data, so it works on any dataset.*

**3 · DETECT — per cell** *(detect.py — our single_source)*
- Compare each cell to its learned band via robust-z → flag **OK / BLACKOUT /
  SPIKE / LOW / DRIFT**.
- OUT: flag table + an initial **trust score** (% cells OK, redundancy-weighted).

**4 · SELF-HEALING LOOP** — repeat until `trust ≥ target` OR no new confident fix
OR max iterations:
- **4a · REPAIR (single-source)** *(repair.py)* — BLACKOUT/SPIKE/LOW →
  `expected × that-day's activity-factor` (scaled to the day's real busyness, not a
  flat average). High confidence when the source's own band is strong.
- **4b · RECONCILE (cross-source)** *(reconcile.py — HoloClean + MICE)* — for
  still-low-confidence cells: predict the suspect value from **related
  columns/tables** (MICE chained equations + learned correlations), **bounded by
  physical limits** and **anchored to ground-truth references (LDM)**. Combine
  estimates weighted by correlation strength → best estimate + confidence +
  provenance (which sources were used).
- **4c · CONFIDENCE GATE** *(heal.py — the 2026 self-heal rule)* — apply only
  **HIGH-confidence** fixes; **LOW-confidence → escalation list** (never forced).
- **4d · RE-SCORE + CONVERGE?** — recompute the trust score on the healed data;
  if still improving, re-profile on the healed data and loop.

**5 · REPORT & OUTPUT** *(report.py)*
- Healed dataset(s) written back (file or DB).
- Trust score **before → after**, per source.
- **Full audit trail:** every change (cell, old → new, method, confidence, sources
  used).
- **Escalation list:** low-confidence cells needing a human or more data.
- HTML report.

---

## The three gates (decision points)

1. **Ingestion validation** — quarantine unparseable/impossible rows (counted).
2. **Confidence gate** — auto-fix HIGH only; escalate the rest. This is what makes
   "self-healing" safe and honest.
3. **Convergence** — stop when the target is met, or no more confident fixes are
   found, or max iters. The achieved trust score is reported truthfully; the target
   (97%) is an aim, not a fabricated guarantee.

## Why this is general (not POD-specific)

Every stage learns from the data (profiles, correlations, ratios) or reads from
config (sources, references, limits). Nothing is hard-coded to POD. Hand it a
different dataset + config and the same pipeline runs — POD is just the first
tenant.
