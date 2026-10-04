# P4-A Final Acceptance — Market Implied Expectation Qualification v0.2

Date: 2026-10-04

## Acceptance Status

**P4-A = FINAL PASS / MERGED**

## Evidence Chain

- PR #9: merged
- PR #9 merge commit: b347df63270b0389c8bfc531ed05eed5a14c843e
- PR #9 Investment Core CI run #120 / 37187273721: SUCCESS
- PR #9 FM00 CI run #88 / 37187273688: SUCCESS
- PR #10: merged
- PR #10 merge commit: ff46b1ed30e8521041d30eb5d1cebd2e4d6ccad0
- PR #10 final Investment Core CI run #125 / 37187410083: SUCCESS
- PR #10 final test result: 101 passed
- post-merge main Investment Core CI run #126 / 37187434857: SUCCESS
- post-merge main SHA: ff46b1ed30e8521041d30eb5d1cebd2e4d6ccad0

## Implemented Boundary

P4-A establishes a typed and executable qualification boundary between P3 deterministic inverse results and decision-grade Market Implied Expectation.

The boundary distinguishes:

- FULL_FEASIBLE_SET
- IMPLIED_POINT
- IMPLIED_RANGE
- CONDITIONAL_IMPLIED_VARIABLE

Qualification states:

- DECISION_GRADE
- CONDITIONAL_ONLY
- BLOCKED

Candidate coverage is typed through an explicit assessment with scope, candidate model IDs, evidence IDs and rationale.

Evidence sufficiency is typed and participates in qualification.

Every economic requirement carries:

- economic variable
- unit
- basis
- period
- horizon
- accounting basis
- role
- evidence IDs

MIE binds to current price observation ID, observation date, PIT cutoff, currency and adjustment semantics.

Generic market_implied_net_profit is rejected.

Qualification is recomputed from semantic states rather than trusted from a caller-declared qualification field.

Model ID must appear in admitted candidate coverage.

Top-level evidence IDs must cover nested requirement / assumption / coverage evidence.

## Cross-field Schema Hardening

JSON Schema now enforces qualification consistency:

- DECISION_GRADE requires IDENTIFIABLE + STABLE + SUFFICIENT coverage + SUFFICIENT evidence + non-conditional representation;
- unresolved identification / instability / insufficient coverage / insufficient evidence require BLOCKED;
- CONDITIONAL_IMPLIED_VARIABLE requires CONDITIONAL_ONLY;
- AMBIGUOUS cannot be DECISION_GRADE.

The schema also rejects unknown top-level fields.

## Red-Team Findings and Resolutions

### RT-01 — Caller-forced qualification

Rejected: qualification field is recomputed and validated.

### RT-02 — Candidate coverage self-report without structure

Rejected: coverage is represented as an auditable typed assessment rather than a bare boolean/enum.

### RT-03 — Provenance leakage

Rejected: nested evidence must be covered by top-level evidence_ids.

### RT-04 — Ambiguous model mislabeled as decision-grade

Rejected by executable validation and JSON Schema.

### RT-05 — Conditional inverse mislabeled as full feasible set

Rejected by executable validation and JSON Schema.

### RT-06 — Generic implied net profit

Rejected at the economic-variable boundary.

### RT-07 — PIT violation

Observation basis rejects observation_date after cutoff.

## Explicit Non-Goals

P4-A does not:

- calculate new market-implied values;
- implement ratio/DCF/DDM/SOTP/rNPV extraction;
- calculate Expectation Gap;
- calculate Expected Return;
- make portfolio decisions;
- choose the human Primary Model;
- perform automatic market-model selection.

## Capability Interpretation

P4-A does not upgrade P3 into unconditional market-model truth.

A decision-grade MIE still requires sufficient candidate coverage, identifiable interpretation, stable interpretation and sufficient evidence.

P4-A is a qualification boundary, not a calibrated market-behavior classifier.

## Next Gate

**P4-B — Ratio-family Market Implied Expectation vertical slice**

Scope:

- forward PE
- PS
- PB
- EV/EBITDA

P4-B must consume P4-A qualified typed outputs and preserve model-native economic variables, PIT, provenance and candidate-coverage semantics.
