# P4-A — Market Implied Expectation Qualification Contract v0.2

## Purpose
P4-A defines when a model-specific reverse result may be represented as Market Implied Expectation (MIE), and when it must remain conditional or blocked.

## Qualification
DECISION_GRADE requires evidence sufficiency, SUFFICIENT candidate coverage, IDENTIFIABLE market interpretation, STABLE interpretation, a non-conditional representation, and complete semantic typing.
CONDITIONAL_ONLY is valid for an economically meaningful result that cannot be treated as one decision-grade market requirement, including AMBIGUOUS models and conditional inversions.
BLOCKED applies to unresolved identification, unstable interpretation, insufficient or unassessed candidate coverage, insufficient evidence, or incomplete semantic support.

## Representation
FULL_FEASIBLE_SET = complete supported feasible requirement set.
IMPLIED_POINT = point market-implied requirement.
IMPLIED_RANGE = bounded market-implied requirement range.
CONDITIONAL_IMPLIED_VARIABLE = a model-specific inverse variable conditional on explicit assumptions.
Conditional output cannot be labeled FULL_FEASIBLE_SET.

## Economic semantics
Every economic requirement carries variable, unit, basis, period, horizon, accounting basis, role and evidence IDs.
Generic market_implied_net_profit is forbidden.
Model semantics remain native: PE→forward EPS; PS→revenue; PB→book equity; EV/EBITDA→EBITDA plus EV bridge; DCF→FCF/assumptions; DDM→dividend/assumptions; SOTP→segment/residual; rNPV→pipeline value/probability/timing.

## Observation and PIT
Every MIE binds to a current price observation ID, observation date, cutoff, currency and adjustment semantics. Observation date must not exceed cutoff.

## Candidate coverage
P3 IDENTIFIABLE is candidate-set-conditional. Only SUFFICIENT coverage can qualify for decision-grade MIE. No component may invent a missing candidate model.

## Assumptions
Assumptions used to obtain implied requirements must be explicit, typed, period/horizon/accounting-basis aware and evidence-backed.

## Hard red-team requirements
Reject generic implied net profit; missing semantic fields; missing evidence IDs; invalid PIT; unstable interpretation; insufficient/unknown candidate coverage; AMBIGUOUS labeled DECISION_GRADE; conditional inversion labeled FULL_FEASIBLE_SET; and evidence insufficiency labeled DECISION_GRADE.

## Scope
P4-A defines qualification and typed representation. It does not calculate new MIE values, Expectation Gap, Expected Return, or decision actions.