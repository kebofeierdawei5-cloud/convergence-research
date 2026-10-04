# P3-B Complex Model Identification Acceptance — 2026-10-04

## Acceptance Status

**P3-B Complex Model-Specific Market Model Identification = FINAL PASS / MERGED**

Scope: implement evidence-backed Feasible Solution Set → Identifiability → Stability for DCF / DDM / SOTP / rNPV directly on the frozen P2-B typed domain.

## Evidence Chain

- PR: #8
- PR URL: https://github.com/kebofeierdawei5-cloud/convergence-research/pull/8
- pre-merge HEAD: `ee295b59c4ce59110da6496991b51dee9ec487a5`
- CI run #112: `37186090902`
- CI conclusion: **SUCCESS**
- CI coverage: **80 tests passed**, compileall PASS, schema validation PASS, MVP run PASS, replay PASS
- merge commit: `77022db416f5b1d32c306f5d644e3642c0f5936b`

## Implemented

- `iios_mvp/market_model_identification.py`
- `schemas/market_model_identification_v0.2.schema.json`
- `tests/test_market_model_identification.py`

No new market-model domain layer was introduced. The existing P2-B typed objects remain canonical.

## Model-Specific Inversion

### DCF

Deterministic one-stage FCFF perpetuity baseline:

- requires FCF, growth, margin, reinvestment, terminal value and discount rate evidence;
- enforces model-domain constraints including positive FCF / terminal value and discount rate > growth;
- derives current implied FCF from market enterprise value under the model;
- uses historical implied FCF range as the admissible consistency constraint.

This is deliberately a conservative baseline, not a general multi-period DCF inference engine.

### DDM

Deterministic Gordon-growth baseline:

- requires dividend, payout, growth and discount rate evidence;
- enforces payout and discount-rate constraints;
- derives current implied dividend under the model;
- uses historical implied dividend range as the admissible consistency constraint.

### SOTP

Model-specific segment/residual inversion:

- requires explicit segment observations using `segment:<id>` basis;
- duplicate segment identifiers are rejected;
- segment values must have consistent units and positive values;
- current market capitalization minus observed segment construction yields implied residual value;
- historical implied residual range constrains current consistency.

### rNPV

Pipeline-specific probability/timing inversion:

- requires pipeline value, probability, timing, discount rate and base-value evidence;
- requires aligned `pipeline:<id>` basis identifiers across value / probability / timing;
- validates probability, timing and discount constraints;
- preserves multi-pipeline composition when inverting the current residual value;
- does not collapse pipeline economics into generic implied net profit.

## Identifiability

P3-B reuses the canonical P2-B / P3-A conservative identification semantics:

- one feasible explanation and no unresolved competitor → **IDENTIFIABLE**;
- multiple materially feasible explanations → **AMBIGUOUS**;
- no supported explanation → **UNIDENTIFIABLE**;
- unresolved evidence insufficiency → **INSUFFICIENT_EVIDENCE**;
- no forced winner.

## Stability

For complex models, the perturbation unit is the **complete historical observation date**, because one date contains multiple model variables.

Leave-one-date-out perturbations are used when enough historical dates exist.

- interpretation invariant across full and admissible date-level perturbations → **STABLE**;
- interpretation changes under a valid perturbation → **UNSTABLE**;
- insufficient historical dates → **INSUFFICIENT_EVIDENCE**.

A dedicated regression test proves that deleting one historical date can change a DCF interpretation to infeasible, yielding UNSTABLE.

## Evidence / PIT Boundary

P3-B preserves the existing evidence boundary and adds observation-level provenance binding:

- every referenced observation evidence ID must exist;
- evidence variable must match the observation economic variable;
- evidence unit must match the observation unit;
- existing PIT validation remains mandatory;
- candidate admission still requires explicit evidence IDs.

The implementation therefore fails closed instead of silently accepting semantically incompatible evidence.

## Red-Team Findings Resolved Before Merge

The implementation was not accepted on the first CI pass. The following defects were found and fixed through successive CI/red-team iterations:

1. DCF terminal-value unit access bug.
2. Internal solver context contaminating market-context checks.
3. Multi-pipeline rNPV inversion incorrectly using probability-weight sum instead of observed composition scaling.
4. Complex-model stability dropping individual variable rows instead of whole historical dates.
5. Observation evidence variable / unit mismatches not being bound.
6. Test fixtures containing incorrect rNPV timing units.

The final canonical CI run #112 is green after these corrections.

## Explicit Non-Goals / Current Limits

P3-B does not:

- implement P4 Market Implied Expectation;
- compute semantic Expectation Gap;
- compute the >15% Expected Return gate;
- modify the human-authoritative company valuation model;
- claim universal statistical identification of investor behavior;
- prove candidate-set completeness;
- implement calibrated regime classifiers;
- turn the simplified DCF / DDM / SOTP / rNPV baselines into production-grade forecasting models.

These remain subsequent engineering / research gates.

## Batch 2 v0.1 Boundary

**PR #3 remains OPEN / RED-TEAM BLOCKED / NOT MERGED and was not extended or used as the P3-B implementation path.**

## Next Gate

**P4 — Market Implied Expectation Engine**

P4 may begin only from the now-validated model-specific market interpretations. P3-B itself is complete and merged.
