# P3-A-RA — Market Model Identification / Historical Support & Regime Shift Semantic Contract v0.3

Date: 2026-10-05
Status: IMPLEMENTED IN PR #69 — merge pending final red-team acceptance

## Objective

Separate mathematical model feasibility from empirical historical-support status. A current observation outside the historical observed range is not, by itself, proof that the valuation model is mathematically infeasible or structurally broken.

## Frozen semantics

### Model fit

- FEASIBLE means the model-specific inverse is computable and evidence-backed; it does not require the current observation to remain inside the historical support envelope.
- INFEASIBLE is reserved for an actual model/equation/constraint contradiction.
- INSUFFICIENT_EVIDENCE means required PIT evidence or observations are missing/inadequate.
- CONTRADICTED remains available for explicit evidence contradiction.

Historical support is an orthogonal P3 diagnostic and admission attribute. Range exclusion MUST NOT be converted into model infeasibility.

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

A candidate outside historical support may remain FEASIBLE and IDENTIFIABLE at P3 because model computability and model uniqueness are distinct from empirical support. Outside-support status is therefore not allowed to create a false `INFEASIBLE` or `UNIDENTIFIABLE` result.

Historical support becomes a downstream Decision-Grade MIE support gate. P4-B must block decision-grade ratio MIE materialization whenever the identified model is outside the admitted support envelope.

## Stability boundary

The existing leave-one-out stability result is explicitly scoped to IDENTIFICATION_ONLY.

STABLE therefore means the identified-model state is invariant under the admissible perturbations tested. It does not establish model validity, regime stability, or stability of the historical support envelope.

## 300750 regression oracle

For RC-CN-A-300750-20261004:

- current EV/EBITDA = 8.3755367867x
- historical support = 13.6686920853x to 16.3854513730x
- support state = BELOW_HISTORICAL_RANGE
- fit status = FEASIBLE
- regime interpretation = POSSIBLE_REGIME_SHIFT
- identifiability = IDENTIFIABLE
- P4-B = BLOCKED by historical-support admission gate
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
