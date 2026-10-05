# P3-A-RA — Market Model Identification / Historical Support & Regime Shift Semantic Contract v0.3

Date: 2026-10-05
Status: EXECUTION DRAFT — merge candidate

## Objective

Separate mathematical model feasibility from empirical historical-support status. A current observation outside the historical observed range is not, by itself, proof that the valuation model is mathematically infeasible or structurally broken.

## Frozen semantics

### Model fit

- FEASIBLE means the model-specific inverse is computable, evidence-backed, and the current observation is inside the admitted historical support range.
- INFEASIBLE is reserved for actual model or constraint contradiction.
- OUTSIDE_HISTORICAL_SUPPORT means the model-specific inverse is computable from admitted evidence, but the current observation is below or above the observed historical support envelope.
- INSUFFICIENT_EVIDENCE means required PIT evidence or observations are missing/inadequate.
- CONTRADICTED remains available for explicit evidence contradiction.

OUTSIDE_HISTORICAL_SUPPORT MUST NOT be treated as INFEASIBLE.

## Historical support state

The current observation is classified as exactly one of:

- IN_RANGE
- BELOW_HISTORICAL_RANGE
- ABOVE_HISTORICAL_RANGE
- UNKNOWN
- INSUFFICIENT_EVIDENCE

The range is descriptive evidence support, not a statistical claim about the true market regime.

## Regime interpretation

P3-A-RA exposes, but does not automatically prove, regime change:

- NOT_ASSESSED
- POSSIBLE_REGIME_SHIFT
- VERIFIED_REGIME_SHIFT
- VERIFIED_MODEL_FAILURE

The production P3-A path may only emit POSSIBLE_REGIME_SHIFT from an outside-range observation. Verification of regime shift or model failure requires separate evidence and is not inferred from range exclusion.

## Identification boundary

A candidate outside historical support is not added to the P3 feasible model set. Therefore existing downstream P4-B remains fail-closed and cannot materialize a decision-grade MIE from an outside-support candidate.

UNIDENTIFIABLE in the aggregate result now means that no candidate remains inside the admitted empirical support boundary. It does not mean that every outside-support model has been proven mathematically invalid.

## Stability boundary

The existing leave-one-out stability result is explicitly scoped to IDENTIFICATION_ONLY.

STABLE therefore means the identified-model state is invariant under the admissible perturbations tested. It does not establish model validity, regime stability, or stability of the historical support envelope.

## 300750 regression oracle

For RC-CN-A-300750-20261004:

- current EV/EBITDA = 8.3755367867x
- historical support = 13.6686920853x to 16.3854513730x
- support state = BELOW_HISTORICAL_RANGE
- fit status = OUTSIDE_HISTORICAL_SUPPORT
- regime interpretation = POSSIBLE_REGIME_SHIFT
- identifiability = UNIDENTIFIABLE
- P4-B = BLOCKED
- no DECISION-GRADE MIE
- capital admitted = FALSE

This preserves the fail-closed investment boundary while eliminating the false claim that historical range exclusion proves model failure.

## Explicit non-goals

P3-A-RA does not:

- add a new valuation model;
- infer a BUY/ADD action;
- verify a regime shift from range exclusion alone;
- create a statistical regime-switching classifier;
- relax P4-B or downstream capital-admission gates.
