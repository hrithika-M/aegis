# data_pipeline — the Aegis self-healing data engine

The data-quality / self-healing pipeline we built. Point it at any source (file
or database); it learns the normal, detects anomalies (blackout/spike/low/drift),
repairs them, reconciles doubtful values from linked sources, and iterates —
confidence-gated — until the trust score converges. Honest by design: what it
cannot fix confidently is escalated, never fabricated.

Full engine docs: [`aegis/README.md`](aegis/README.md).

## Run it (from THIS folder, so the `aegis` package resolves)
```bash
cd data_pipeline
python -m aegis.tests.test_phase1        # engine tests
python -m aegis.tests.test_phase2_heal   # self-healing loop tests
python -m aegis.report <config.yaml> out # heal a run -> healed data + HTML report
```

## Layout
```
data_pipeline/
  aegis/        the engine package (schema, connectors, detect, repair,
                reconcile, heal, report + tests)
  examples/
    retail_demo/    SQL-database demo (make_data.py + config.yaml)
    pod_airport/    Aegis run on the real EWS camera data (config + report.html)
```

Proof runs and results: see the top-level `../PROOFS.md`.
