# tests — invariant + input-validation suite

Production basics: the pipeline must (1) reject bad input loudly and (2) guarantee
its output obeys hard invariants, so a regression fails immediately instead of
shipping quietly-wrong numbers.

## Run
```
python test_twin.py          # no pytest needed; exits non-zero on any failure
# or:  pytest test_twin.py
```

## Input validation — `build/validators.py`
`build_masters.py` validates the schedule before building. **Errors stop the build**
(missing/zero seats, unparseable STA/STD, bad FREQ, missing MAIN FILE sheet, duplicate
SL NO); **warnings fall back and log** (unknown airport → UNK, unknown aircraft, empty
flight number). Proven to reject a crafted bad row rather than guess.

## Invariants tested (10, all passing)
| Test | Guarantees |
|---|---|
| airport / aircraft master complete | every code in the schedule is in the masters, seats > 0 |
| flight master times & seats | times are valid HH:MM, seats positive |
| daily dates in season & dow matches | occurrences land in S26, weekday label is correct |
| daily respects frequency | a flight appears only on days its FREQ allows |
| passengers non-neg ≤ seats, LF in range | no negative/over-capacity passengers |
| two legs per occurrence | every rotation splits into exactly ARR + DEP |
| reconciliation scale (Hyderabad) | simulated route total stays within 30% of real DGCA |
| 5-min non-neg & counter consistency | demands ≥ 0; counters/lanes derive from the shown demand |
| **occupancy no drift** | regression guard for the old cross-day drift bug (peaked 11,912) |

The counter-consistency test already caught a real bug (counters were computed from
raw demand but the rounded demand was shown) — now fixed at the source.

## CI-ready
`test_twin.py` exits non-zero on any failure, so it drops straight into a CI step
(`python bhogapuram_digital_twin/tests/test_twin.py`) once a CI runner is set up.
