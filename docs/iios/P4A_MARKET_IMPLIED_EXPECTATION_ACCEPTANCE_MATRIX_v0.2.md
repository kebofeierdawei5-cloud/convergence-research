# P4-A Market Implied Expectation Acceptance Matrix v0.2

| ID | Case | Expected result |
|---|---|---|
| A01 | IDENTIFIABLE + STABLE + SUFFICIENT + IMPLIED_RANGE | DECISION_GRADE |
| A02 | IDENTIFIABLE + STABLE + SUFFICIENT + CONDITIONAL_IMPLIED_VARIABLE | CONDITIONAL_ONLY |
| A03 | AMBIGUOUS + STABLE + SUFFICIENT | CONDITIONAL_ONLY |
| A04 | UNIDENTIFIABLE | BLOCKED |
| A05 | INSUFFICIENT_EVIDENCE | BLOCKED |
| A06 | UNSTABLE | BLOCKED |
| A07 | candidate coverage INSUFFICIENT | BLOCKED |
| A08 | candidate coverage UNASSESSED | BLOCKED |
| A09 | generic market_implied_net_profit | reject |
| A10 | missing period/horizon/accounting basis | reject |
| A11 | missing evidence IDs | reject |
| A12 | observation date after cutoff | reject |
| A13 | CONDITIONAL_IMPLIED_VARIABLE mislabeled FULL_FEASIBLE_SET | reject |
| A14 | unsupported extra top-level field | reject by schema |
| A15 | stable ambiguity with selected winner | CONDITIONAL_ONLY; no forced winner |
| A16 | evidence_sufficiency=false + DECISION_GRADE | reject |

## PASS gate
P4-A passes only when executable validation and JSON schema agree, qualification is recomputed rather than trusted from caller input, conditionality is explicit, candidate coverage is explicit, semantic basis is mandatory, generic implied net profit is impossible, PIT binding is represented, and existing P2/P3 tests remain green.

## Non-goals
No P4-B extraction, Expectation Gap, Expected Return or action selection.