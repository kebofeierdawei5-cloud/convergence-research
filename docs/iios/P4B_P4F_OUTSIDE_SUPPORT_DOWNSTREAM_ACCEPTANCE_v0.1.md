# P4-B / P4-F Downstream Semantic Acceptance — Outside Historical Support

Date: 2026-10-05
Status: Acceptance Candidate

## Negative oracle

Given a P3 candidate with:

- model fit = FEASIBLE
- identifiability = IDENTIFIABLE
- stability = STABLE or INSUFFICIENT_EVIDENCE
- historical_support = BELOW_HISTORICAL_RANGE or ABOVE_HISTORICAL_RANGE
- regime_interpretation = POSSIBLE_REGIME_SHIFT

the downstream system MUST NOT produce DECISION_GRADE admission.

## Acceptance matrix

| Layer | Required result |
| --- | --- |
| P4-B ratio MIE | BLOCK / no materialized MIE when historical support is outside range |
| P4-C DCF/DDM | CONDITIONAL_ONLY or BLOCKED, never DECISION_GRADE |
| P4-D SOTP/rNPV | CONDITIONAL_ONLY or BLOCKED, never DECISION_GRADE |
| P4-E Multi-model set | NO_DECISION_GRADE_MODEL + BLOCKED whenever any admitted model is explicitly outside-support |
| P4-F Snapshot | Persist/replay NO_DECISION_GRADE_MODEL + BLOCKED |
| P4-F mixed model set | Outside-support state overrides any materialized decision-grade alternative |
| 300750 real case | FEASIBLE + IDENTIFIABLE + BELOW_HISTORICAL_RANGE → P4-B/P4-F blocked → capital admitted FALSE |

## Decision-grade invariant

MIEQualification.DECISION_GRADE is only reachable downstream when every applicable admission gate is satisfied. Historical support is a hard support gate for ratio decision-grade MIE.

Conditional DCF/DDM and SOTP/rNPV representations remain structurally non-decision-grade regardless of support state.

## Replay invariant

P4-F replay MUST recompute set semantics from the serialized evaluation states. A serialized outside-support evaluation MUST resolve to NO_DECISION_GRADE_MODEL and BLOCKED, not UNIQUE_MODEL or DECISION_GRADE.

## Anti-bypass cases

1. An outside-support evaluation plus a decision-grade materialized alternative MUST remain NO_DECISION_GRADE_MODEL and BLOCKED.
2. A tampered snapshot changing the resolution/qualification without changing the underlying evaluation states MUST fail semantic validation.
3. A conditional P4-C/P4-D output MUST never become DECISION_GRADE through the generic qualification layer.
