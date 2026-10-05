# RP-01 — Risk / Portfolio Production Contract v0.1

Date: 2026-10-05
Status: ACCEPTED / CANONICAL

## Objective

Turn the existing Risk and Portfolio decision inputs into one explicit production contract.

This batch does not create a new risk model, portfolio optimizer, sizing algorithm, or Decision Precedence rule.

## Production contract

Risk requires explicit:
- status: PASS / FAIL / UNKNOWN;
- max_loss_pct;
- thesis_breaks;
- evidence_ids.

Portfolio requires explicit:
- position_pct;
- constraint_status: PASS / BLOCKED / UNKNOWN;
- can_add.

The existing BUY/ADD package is validated when supplied. An absent package is represented as ABSENT and package_ready=false.

No implicit can_add=true default is allowed by the production contract.

## Fail-closed rules

- invalid numeric ranges fail;
- missing risk budget fields fail;
- missing portfolio capacity fields fail;
- duplicate evidence or trigger IDs fail;
- invalid entry-zone order fails;
- initial position > target position > max position fails;
- tampered contract hash fails;
- UNKNOWN remains a valid state but is not ready;
- BLOCKED portfolio constraints are not softened.

## Decision boundary

The contract is an upstream input-validation and normalization layer.

policy_effect = NO_DIRECT_DECISION_PRECEDENCE_CHANGE.

The existing Decision State Machine / Decision Kernel remains the sole authority for BUY / ADD / HOLD / REDUCE / EXIT / NO-BUY / WATCH / REVIEW_REQUIRED.

RP-01 does not modify P3, P4, MIE, valuation, or forecast semantics.

## Acceptance

RP-01 is accepted when the dedicated contract tests and Investment Core regression pass, the v0.3 Validator consumes the contract, and the canonical Decision Precedence remains unchanged.
