# P4-B Ratio-family Market Implied Expectation Acceptance Matrix v0.2

| ID | Case | Expected |
|---|---|---|
| B01 | Forward PE, P3 IDENTIFIABLE + STABLE + sufficient coverage/evidence | one DECISION_GRADE MIE |
| B02 | PS | one DECISION_GRADE MIE |
| B03 | PB | one DECISION_GRADE MIE |
| B04 | EV/EBITDA | one DECISION_GRADE MIE with EBITDA semantics |
| B05 | Multiple feasible ratio models | one MIE per feasible model, all CONDITIONAL_ONLY |
| B06 | P3 IDENTIFIABLE but P3 STABILITY=UNSTABLE | BLOCKED MIE |
| B07 | P3 IDENTIFIABILITY=INSUFFICIENT_EVIDENCE with one feasible candidate | BLOCKED MIE; no uniqueness promotion |
| B08 | Candidate coverage=INSUFFICIENT | BLOCKED MIE |
| B09 | Evidence sufficiency=INSUFFICIENT | BLOCKED MIE |
| B10 | Non-ratio candidate supplied to P4-B | reject |
| B11 | P3 solution variable differs from ratio-native variable | reject |
| B12 | P3 feasible solution lacks bounded range | reject |
| B13 | Coverage/evidence assessment references unknown manifest IDs | reject |
| B14 | Generic implied net profit appears in feasible solution | reject |
| B15 | P3 result method/status does not match accepted baseline | reject |
| B16 | Current observation/PIT invalid | reject via P3 input validation |

## Required semantic preservation

P4-B must copy, not reinterpret, the P3 ratio feasible requirement:

- forward PE → forward_eps
- PS → revenue
- PB → book_equity
- EV/EBITDA → ebitda

The P3 range is carried as IMPLIED_RANGE.

P4-B may not:
- recalculate a different inverse;
- convert any result into generic implied net profit;
- force a winner under ambiguity;
- promote unstable or insufficient interpretations;
- silently infer period, horizon or accounting basis.

Those semantic fields are explicit P4-B inputs.

## PASS gate

P4-B passes only when all four ratio families have a working vertical slice, P3 values/ranges are preserved exactly, P4-A qualification is enforced, ambiguity yields multiple conditional outputs without a winner, and P3/P4-A regression tests remain green.

No Expectation Gap, Expected Return or decision action is implemented in P4-B.