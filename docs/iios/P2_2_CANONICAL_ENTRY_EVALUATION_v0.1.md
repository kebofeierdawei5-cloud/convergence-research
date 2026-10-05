# P2.2 Canonical Entry Evaluation + Decision Admission v0.1

P2.2 closes the structural gap between the P2.1 price-response engine and the IIOS investment decision.

## Canonical chain

P1.4 Decision State → P2.1 Canonical Price Response → P2.2 Canonical Entry Evaluation → P2.2 Decision Admission.

P1.4 remains authoritative for Trust, thesis, risk, portfolio and current-price expectation-gap precedence. P2.2 is a subsequent capital-admission layer and cannot weaken EXIT/REDUCE or other higher-protection outcomes.

## Canonical Entry Evaluation

P2.2 recomputes the effective target-entry boundary from the canonical return/risk target and the P2.1 response. It records the P2.1 response ID/hash, P4-F snapshot hash, model/expectation identity, constraint type, inclusive/strict semantics, current-price eligibility and binding components.

For normal cases with a canonical expectation_gap, the P2.1 target reference is derived from the same admitted market expectation and independent forecast references. This avoids a semantically divergent second reference.

## Decision Admission

BUY/ADD are the only actions constrained by the new price boundary.

- BUY + decision-grade current-price eligible → BUY.
- ADD + decision-grade current-price eligible → ADD.
- BUY + current price outside the canonical boundary → WATCH.
- ADD + current price outside the canonical boundary → HOLD.
- BUY/ADD + unresolved decision-grade entry evaluation → REVIEW_REQUIRED.
- CONDITIONAL_ONLY target-entry analysis is advisory and never becomes a capital gate.
- EXIT/REDUCE/HOLD/WATCH/NO-BUY are not overridden by P2.2.

The final decision exposes both the P1.4 pre-admission action and the P2.2 admission result.

## PIT and replay

P2.2 creates no new market evidence. It consumes the already PIT-bound P2.1 response. Canonical entry evaluation and decision admission have deterministic exact replay functions; tampering or input drift fails replay.
