# IIOS C4 — Expectation Gap Production Integration v0.1

Date: 2026-10-06
Status: IMPLEMENTATION CANDIDATE — pending dedicated CI and canonical acceptance
Parent boundary: Stage C3 Second Company
Scope: production Expectation Gap evaluation and Decision integration

## 1. Objective

C4 reconnects the existing Market Implied Expectation substrate to the canonical IIOS investment-decision path as a first-class, auditable Expectation Gap evaluation.

Canonical chain:

Independent Fundamental Expectation
→ Market Implied Expectation
→ semantic compatibility
→ Expectation Gap
→ Existing Return / Decision Policy

C4 does not create a new P3/P4 model family.

## 2. Production boundary

The C4 production object is "expectation_gap_evaluation".

It binds:

- case identity and PIT cutoff;
- exact current-price observation identity;
- exact P4-F MIE snapshot hash, MIE-set hash and provenance hash;
- exact market expectation identity;
- exact canonical independent-forecast reference and admitted forecast metadata;
- variable, unit, basis, horizon and comparison direction;
- scalar independent / market-required values only when a valid point comparison exists;
- gap absolute and relative values only when the comparison is decision-grade and uniquely resolved;
- explicit resolution and qualification states;
- deterministic evaluation hash and replay identity.

## 3. Semantic compatibility

A scalar expectation gap is permitted only when the independent expectation and market expectation share:

- the same economic variable;
- the same unit;
- the same basis;
- the same horizon;
- an explicit comparison direction.

A range-valued market requirement does not become a scalar by selecting an arbitrary endpoint.

A non-unique market interpretation does not become a market truth merely because an inverse equation is algebraically solvable.

## 4. Failure states

C4 distinguishes:

- PASS: uniquely resolved, decision-grade, semantically compatible, point-comparable gap;
- INCOMPATIBLE: semantic identity mismatch or non-point requirement; no scalar gap;
- AMBIGUOUS: multiple materialized market interpretations prevent unique identification; no scalar gap;
- NO_FEASIBLE_SOLUTION: no feasible market model exists; no scalar gap;
- BLOCKED: insufficient evidence or non-decision-grade MIE prevents evaluation.

Malformed or unverifiable evidence remains fail-closed through the existing validation boundary.

## 5. Decision-policy boundary

C4 does not add a new return hurdle and does not make MIE mandatory for BUY/ADD.

The existing B1 / CORE-04 rule remains authoritative:

MIE_POLICY = OPTIONAL_EXPLANATORY

Therefore:

- a positive gap may inform the canonical proposal;
- a zero or negative but otherwise valid gap is retained as an explicit advisory calculation;
- MIE absence or unresolved state does not itself veto a company-side opportunity;
- no additive 15% threshold is introduced;
- no hidden contradiction threshold is introduced;
- any future material-contradiction veto requires a separate versioned policy.

policy_effect = ADVISORY_ONLY_NO_ADDITIVE_RETURN_THRESHOLD.

## 6. Canonical persistence / replay

The C4 evaluation is embedded in the v0.3 Decision payload so it flows into:

Decision Revision
→ Machine Publication
→ Human Report
→ Monitoring / Validation references

The evaluation itself is content-addressed and deterministic. Replay recomputes the same hash basis and must pass before C4 acceptance.

## 7. Explicit non-goals

C4 does not add:

- new P3/P4 market-model families;
- positioning or sizing;
- scheduler or alerts;
- automatic execution;
- order placement;
- portfolio optimization;
- changes to Trust / Quality semantics;
- changes to Decision precedence;
- Forecast Research productionization.

## 8. Acceptance target

Dedicated C4 CI must prove:

1. a valid comparable pair produces a deterministic scalar gap;
2. a non-positive valid gap remains an explicit calculation and does not become a hidden BUY veto under OPTIONAL_EXPLANATORY;
3. incompatible expectations never produce a scalar gap;
4. ambiguous market interpretation never produces a scalar gap;
5. no-feasible market model never produces a scalar gap;
6. the detailed evaluation is bound into the canonical v0.3 Decision output;
7. standalone schema validation passes;
8. replay is deterministic;
9. existing semantic expectation-gap and v0.3 Investment Core tests remain green for the C4 path.

C4 acceptance does not claim that a specific market-side MIE is true; it only verifies the controlled production semantics for qualifying one.
