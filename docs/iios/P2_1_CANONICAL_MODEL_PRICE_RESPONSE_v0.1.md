# P2.1 Canonical Model-Specific Price Response v0.1

P2.1 extends Target Entry Price 2.0 from a price-proportional vertical slice to a canonical model-native candidate-price response layer for the major valuation families used by IIOS.

## Scope

Supported families:

- EV/EBITDA
- DCF
- DDM
- SOTP
- rNPV

Under the currently frozen contemporaneous assumptions in P3/P4, all five supported relationships are affine in candidate price. No generic linear approximation is used.

### EV/EBITDA

The P4-B MIE may be an implied range. P2.1 preserves both endpoints.

Enterprise value = price × shares_outstanding + net_debt.
For each admitted historical-multiple endpoint m, implied EBITDA(price) = m × (price × shares_outstanding + net_debt) / reference_enterprise_value.
The endpoint functions are affine in price. The engine does not collapse a historical range into a point.

### DCF

With growth and discount rate frozen to the admitted P4-C conditional assumption slice:
FCF(price) = (discount_rate - growth) / (1 + growth) × (price × shares_outstanding + net_debt).
This is affine in price. The artifact remains CONDITIONAL_ONLY because current P4-C semantics do not promote DCF conditional inversions to decision-grade MIE.

### DDM

With growth and discount rate frozen:
Dividend(price) = (discount_rate - growth) / (1 + growth) × price.
This is affine/proportional in price.

### SOTP

With current admitted segment values frozen:
ResidualValue(price) = price × shares_outstanding - sum(segment_value).
This is affine in price. The artifact remains CONDITIONAL_ONLY under current P4-D semantics.

### rNPV

With observed pipeline composition, probabilities, timings, discount rate and base value frozen, the P4-D per-pipeline implied value is an affine function of enterprise value.

For pipeline i:
composition_i = pipeline_i / sum(pipeline_j).
weighted_average_risk_factor = sum(pipeline_j × probability_j / (1 + discount_rate)^timing_j) / sum(pipeline_j).
pipeline_i_implied_value(price) = composition_i × (price × shares_outstanding + net_debt - base_value) / weighted_average_risk_factor.

The weighted average risk factor is mandatory; dividing by only pipeline i's own probability/timing weight would not reproduce the P4-D admitted per-pipeline requirement.

## Canonical admission boundary

P2.1 never accepts caller-supplied price-response coefficients, net debt, shares, growth, discount rates, segment values or pipeline assumptions.

The engine only consumes an immutable admitted P4-F snapshot, its hash-bound provenance manifest, model assumptions already present in the materialized MIE, the canonical current-price binding, and a canonical independent-forecast admission.

Numeric shares outstanding and net debt required by the model response are represented by P4-F provenance records whose basis is model_context:<model_id>:<variable> and whose value is finite. Exactly one canonical record is required for each needed context variable. These records are included in the P2.1 response evidence set.

## PIT

P2.1 first validates the complete P4-F snapshot. Any provenance record with observation_date or known_at after the case cutoff fails closed before the model response is evaluated.

A hypothetical candidate price is never written back into the canonical current-price observation and is never treated as new market evidence.

## Reference consistency

The model-native relation is evaluated again at the canonical current price. The resulting point or range must exactly equal the MIE requirement contained in the immutable snapshot.

This prevents a response function from being derived from a formula that is merely plausible but inconsistent with the admitted reference MIE.

## Expectation-gap revalidation

For HIGHER_IS_BETTER variables, the conservative boundary is obtained from the high endpoint of an admitted MIE range.
For LOWER_IS_BETTER variables, the conservative boundary uses the low endpoint.

The result is exposed as an UPPER_BOUND_STRICT or LOWER_BOUND_STRICT price constraint and is combined with the existing return/risk target by the frozen P2 target-entry combiner.

P2.1 does not change P1.4 BUY/ADD precedence or upgrade CONDITIONAL_ONLY MIE into decision-grade MIE.

## Replay

Every response is content-addressed by response version, P4-F snapshot hash, model and expectation identity, candidate price, and canonical forecast identity.

replay_canonical_price_response() regenerates the response from the same immutable inputs and requires exact serialized equality.

Any response drift, snapshot tampering, PIT violation, provenance mismatch or formula/reference inconsistency fails closed.

## Nonlinear relation

The P2.1 contract deliberately does not approximate nonlinear relationships. A future nonlinear model requires a separately admitted formula version with explicit domain/provenance semantics and replay tests. Until then, unsupported nonlinear behavior is not silently linearized.
