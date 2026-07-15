# validation — does the twin resemble the real data?

Before trusting a digital twin in production, validate the **simulator itself**, not
just the models. This compares generated data against real DGCA data with standard
distribution tests (KS, Wasserstein/EMD, PSI — numpy only, no scipy).

Run: `python validate_synthetic.py`  →  `analytics/synthetic_validation.csv`

## Thresholds (PSI)
`< 0.10` PASS (stable) · `0.10–0.25` WARN (moderate shift) · `> 0.25` FAIL (significant shift)

## Results (current build)
| Check | Type | Result | Verdict |
|---|---|---|---|
| Route passenger shares (twin vs real DGCA) | integrity | PSI 0.046 | **PASS** |
| Day-of-week demand shape (twin vs real national daily) | realism | PSI 0.001, KS 0.009 | **PASS** |
| Load-factor distribution (twin per-flight vs real airline PLF) | realism | PSI 2.85, KS 0.545, EMD 0.125 | **FAIL** |

## Honest interpretation
**What passed — the twin's structure is sound.**
- Route mix matches reality (reconciliation works).
- The weekly rhythm matches real national daily traffic *almost exactly* — the
  schedule-driven day-of-week shape is realistic.

**What failed — and why it's useful, not fatal.** Twin per-flight load factor:
mean 0.758 vs real 0.881, std 0.163 vs 0.063 (2.5× too spread). Two causes:
1. **Partly apples-to-oranges (expected):** we compare *per-flight* LF (naturally
   high variance) to airline *daily-average* PLF (smoothed). Per-flight always
   varies more, so some extra spread is inherent to the comparison.
2. **Partly a real modelling weakness:** reconciling a base 0.85 LF to real DGCA
   route totals over a *sparse* schedule inflates under-served routes (pinned at the
   0.95 cap) and deflates over-served ones — producing a bimodal, over-spread LF
   distribution that real operations don't have. VTZ regional routes also genuinely
   run below the national-average PLF, explaining part of the lower mean.

**The fix (next Tier-1 item):** model per-flight load factor as a proper
distribution per airline/route (μ, σ) instead of base-then-reconcile-then-cap — i.e.
the uncertainty / behavioural-distribution work. **This validation directly
motivates and prioritises that step**, and gives an objective metric (PSI 2.85 → aim
< 0.25) to measure the improvement against.

## Data-quality note
The validator also surfaced a malformed source value (`84..1`) in
`national_daily_reference.csv` — now corrected to `84.1`. Catching such things is a
side benefit of running distribution checks.
