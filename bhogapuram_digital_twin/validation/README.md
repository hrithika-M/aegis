# validation — does the twin resemble the real data?

Before trusting a digital twin in production, validate the **simulator itself**, not
just the models. This compares generated data against real DGCA data with standard
distribution tests (KS, Wasserstein/EMD, PSI — numpy only, no scipy).

Run: `python validate_synthetic.py`  →  `analytics/synthetic_validation.csv`

## Thresholds (PSI)
`< 0.10` PASS (stable) · `0.10–0.25` WARN (moderate shift) · `> 0.25` FAIL (significant shift)

## Results (after stochastic-LF engine)
| Check | Type | Result | Verdict |
|---|---|---|---|
| Route passenger shares (twin vs real DGCA) | integrity | PSI 0.051 | **PASS** |
| Day-of-week demand shape (twin vs real national daily) | realism | PSI 0.001, KS 0.009 | **PASS** |
| Load-factor distribution (twin per-flight vs real airline PLF) | realism | PSI 1.81 (was 2.85) | still flagged — read below |

## Honest interpretation
**What passed — the twin's structure is sound.** Route mix matches reality
(reconciliation works); the weekly rhythm matches real national traffic almost
exactly.

**Load factor — improved, and the residual is real signal, not a bug.** Switching
from "flat 0.85 → hard-reconcile → cap" to **per-flight load factor drawn from a
distribution around each route's real mean** (`build_passengers.py`) cut the spread
in half (std 0.163 → 0.115) and PSI from 2.85 → 1.81. It still doesn't "PASS"
against national PLF, and we do **not** contort the test to force green — here's the
honest reason it shouldn't:
1. **VTZ genuinely runs below the national average.** Real VTZ system load factor is
   ~0.76 (2.97 M real DGCA pax ÷ its scheduled seat supply) vs the ~0.88 *national*
   airline PLF. The twin's mean (0.764) matches VTZ reality; the gap to national is
   a real level difference, not a modelling error.
2. **Granularity mismatch.** We compare *per-flight* LF (naturally variable) to
   airline *daily-average* PLF (smoothed). Per-flight legitimately varies more.

So the national PLF is partly the wrong yardstick for a regional airport. We report
this openly rather than swap in a circular reference — the same "target not met,
reported honestly" ethos as the rest of the repo.

**Remaining fixable slice** (tracked): tighten the per-flight σ and use route-level
σ from real data when it becomes available, to trim the last of the excess spread.

## Data-quality note
The validator also surfaced a malformed source value (`84..1`) in
`national_daily_reference.csv` — corrected to `84.1`. Catching such things is a side
benefit of running distribution checks.
