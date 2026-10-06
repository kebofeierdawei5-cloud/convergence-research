# TR-01 — Trigger Contract / Event Semantics v0.1

Date: 2026-10-06
Status: IMPLEMENTATION TARGET

## Objective

Turn the legacy Trigger persistence shell into a production contract that can support later Monitoring / Validation without making Trigger state a hidden decision engine.

TR-01 freezes only:
- declarative Trigger Contract semantics;
- immutable Trigger Event semantics;
- deterministic condition evaluation;
- strict provenance and PIT ordering.

It does not create a scheduler, notification service, portfolio optimizer, or automatic decision executor.

## Canonical Trigger Contract

A Trigger Contract is bound to an exact Decision Revision:
- decision_id;
- revision;
- decision_revision_hash;
- case_id;
- decision_cutoff_date.

It declares a role of THESIS_BREAK, MONITORING, or VALIDATION plus a canonical metric_id, narrow operator, scalar target where required, optional unit, optional evidence references, and enabled state.

No arbitrary expression string, callback, Python expression, or executable rule is accepted.

## Canonical Trigger Event

A Trigger Event is immutable and binds to the exact trigger_hash and Decision Revision identity.

It records evaluation cutoff, observed time, known-at time, source/evidence identity, observed value, optional previous value, validation state, and deterministic trigger state.

PIT rule:

observed_at <= known_at <= evaluation_cutoff_at

The evaluation cutoff is separate from the original decision cutoff because a monitoring event may occur after the decision while validating that decision retrospectively.

## Deterministic state

Every event evaluates to MATCHED, NOT_MATCHED, or UNKNOWN.

UNKNOWN is not equivalent to NOT_MATCHED. A malformed numeric observation is UNKNOWN rather than silently treated as false.

Disabled triggers remain auditable but cannot produce MATCHED.

## Boundary protection

Contract and Event both carry policy_effect = NO_DIRECT_DECISION_PRECEDENCE_CHANGE.

TR-01 cannot change Decision Precedence, upgrade Trust or Quality, authorize BUY / ADD, change valuation / forecast / MIE semantics, or execute trades.

Future Monitoring / Validation layers may consume Trigger Events as evidence, but capital-affecting decisions remain subject to the canonical Decision Kernel and Human Approval lifecycle.
