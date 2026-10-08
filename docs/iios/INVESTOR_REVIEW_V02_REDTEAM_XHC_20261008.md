# Independent Red-team — Real Xinhecheng Publication against Investor Review v0.2

Date: 2026-10-08

## Input

- Case: RC-CN-A-002001-20261007
- Company: 浙江新和成股份有限公司
- Symbol: 002001
- Cutoff: 2026-10-07
- Decision Revision: r001
- Canonical clean-replay Publication SHA-256:
  7e9bc390c03e12ac3309754cdb65938aa928d9dea97a4145998e3ab9911a0ea0
- Source artifact: PILOT-04 clean replay
- Artifact SHA-256:
  40971d2f677254332aa421aec46a29265d8a90eb1c412451751b216d777b31b1

## Execution result

The real Publication was inspected with the v0.2 semantic-surface rules and an independent clean-room red-team.

The rendered v0.2 surface successfully exposes:

- Trust = REVALIDATION, with structured Trust content absent;
- Quality = CONDITIONAL, with canonical Quality Gate dimensions recovered from nested decision_upstream_admission;
- Reality = PASS, with economic structure visible;
- Thesis = INTACT;
- Value Drivers = PASS gate but only PARTIAL semantic content;
- Forecast = PASS;
- Valuation = PASS;
- MIE = NOT_PROVIDED;
- Expectation Gap = UNKNOWN;
- Risk = PASS;
- Positioning = BLOCKED;
- Decision = REVIEW_REQUIRED;
- Position = package present but constrained by Decision;
- Monitoring = PASS;
- Validation = PASS.

This is materially better than v0.1 and correctly demonstrates that missing modules must remain visible.

## Red-team findings

### P0 — RT-XHC-004
MIE is absent.

Expected human semantics:

NOT_PROVIDED

not NOT_IDENTIFIABLE, unless an upstream semantic artifact explicitly declares identifiability failure.

The report must not infer a stronger identifiability claim from absence alone.

### P0 — RT-XHC-005
required_return_pass = true while the numeric required_return is absent from the canonical published return metrics.

The report must not infer 10% from the pilot document or chat context.

Human consequence: the PASS condition is not independently auditable.

Required remediation: either publish the numeric Required Return canonically or downgrade the human audit status to UNKNOWN / INCOMPLETE.

### P0 — RT-XHC-006
Expected annualized return is present (~20.17%), but Bear/Base/Bull scenario probabilities are absent from the published forecast scenarios.

Human consequence: the expected return cannot be independently reconstructed from the visible scenario table.

Required remediation: expose canonical scenario weights or mark expected-return auditability incomplete.

### P0 — RT-XHC-007
Return/risk threshold price exists (26.60), while Decision.target_entry_price is absent because canonical entry evaluation is skipped.

Human consequence: a reader can still confuse 26.60, or the package entry zone 24.00–25.95, with an executable entry trigger.

Required remediation: the executive summary must explicitly state that no actionable target entry price exists and that 26.60 is a non-actionable return/risk threshold.

### P0 — RT-XHC-008
The Risk/Portfolio package contains can_add = true, while Decision has new_capital_allowed = false and positioning permission is NO_SIZING_PERMISSION.

The Decision precedence resolves this correctly, but the human surface must visibly show the override.

Required remediation:

Package can_add = TRUE → OVERRIDDEN BY DECISION: new capital FALSE

and position-package data must not be labeled simply PASS.

### P1 — RT-XHC-001
Quality is structurally present in the canonical Publication, but nested below decision_upstream_admission.quality_gate.

The v0.2 implementation initially missed this. The mapping has now been repaired.

Regression requirement: nested canonical admission paths must remain covered.

### P1 — RT-XHC-002
Trust has a decision-critical status (REVALIDATION) but no structured Trust artifact.

Human consequence: the report exposes the boundary but cannot show the reason/evidence structure behind Trust.

Required remediation: preserve status and explicit content-missing state; do not fabricate rationale.

### P1 — RT-XHC-003
Value Driver gate is PASS, but there is no full driver-ranking artifact at the expected top-level path.

The available key_driver_ids and VALUE_DRIVER admission reference support only PARTIAL semantics.

Required remediation: show semantic completeness separately from gate status.

### P1 — RT-XHC-009
Positioning is explicitly BLOCKED while a position package is populated.

Human consequence: package data can be mistaken for executable sizing.

Required remediation: separate package existence, sizing permission, and Decision capital authorization.

### P1 — RT-XHC-010
Lifecycle Validation = PASS is not equivalent to Forecast / Valuation / Decision / Thesis validation.

Required remediation: expose validation type/scope explicitly.

## Overall verdict

FAIL — not ready for Human Acceptance.

The v0.2 surface passes the narrower projection-integrity idea: it can preserve module states and expose missing modules.

It does not yet pass the stricter investor-usability requirement:

> the human reviewer must be able to understand not only what numbers exist, but which numbers are actually auditable, which are non-actionable thresholds, and which apparent permissions are overridden.

## Promotion boundary

Do not merge v0.2 yet.

Required next remediation set:

1. add explicit auditability flags for Required Return and Expected Return;
2. make threshold-vs-actionable-entry semantics prominent in the one-page summary;
3. explicitly show Decision override over portfolio.can_add;
4. retain MIE NOT_PROVIDED and Expectation Gap UNKNOWN unless upstream identifiability semantics are supplied;
5. distinguish gate status from semantic-content completeness and validation scope.

Independent red-team has not authorized canonical promotion.
