# Aegis

**A general self-healing data engine.** Point it at any data source — a CSV/Excel
file or a database (Postgres, MySQL, SQLite…) — and it:

1. **learns** what "normal" looks like for that data (median + MAD bands — measured, never configured),
2. **detects** anomalies per cell: `BLACKOUT / SPIKE / LOW / DRIFT / OK`,
3. **repairs** them scaled to the day's real activity (not flat averages),
4. **reconciles** doubtful values from related tables + ground-truth references (MICE-style, bounded by physical limits),
5. **iterates** — confidence-gated — until the data-trust score converges,
6. **reports honestly**: healed data + audit trail of every change + an escalation list for what it could *not* confidently fix. It never fabricates.

Design lineage: HoloClean's signal unification · Soda's config/connector pattern ·
MICE cross-column imputation · the 2026 self-healing confidence-gate rule.
See [docs/RESEARCH_AND_PLAN.md](docs/RESEARCH_AND_PLAN.md) and
[docs/WORKFLOW.md](docs/WORKFLOW.md) (diagram: `docs/workflow.png`).

## Quick start

```yaml
# run.yaml
name: my_run
target_trust: 97
sources:
  - name: scans
    kind: csv                      # csv | excel | database
    path: data/scans.csv
    # kind: database
    # url: postgresql://user:pass@host:5432/mydb
    # query: SELECT * FROM scans
    columns: {datetime: scan_time, entity: gate, value: scan_count}
```

```bash
python -m aegis.scan run.yaml      # understand: profile + detect + trust score
python -m aegis.tests.test_phase1  # test suite
```

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 · Foundation | config · connectors (file+DB) · profile · detect · scan CLI | ✅ built, tests passing |
| 2 · Self-healing | repair · reconcile (MICE + refs) · confidence-gated heal loop · trust score | ⏳ next |
| 3 · Proof & polish | report/HTML · audit trail · proof on two unrelated real datasets | ⏳ |

## Honesty contract

Aegis heals what it has confident signal for and **escalates the rest**. The
target trust score (e.g. 97%) is an aim; the achieved score is always reported
truthfully, with the list of what needs a human or more data.
