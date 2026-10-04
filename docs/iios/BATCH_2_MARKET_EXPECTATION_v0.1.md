# IIOS Batch 2｜Market Model Identification / Market Implied Expectation v0.1

## Boundary

Batch 2 starts from current market price and asks:

> What valuation model(s) and operating assumptions can feasibly explain this price?

It must not force a single market model when multiple models remain feasible.

## Chain

Current Price
→ Market Model Identification
→ Market Implied Expectation
→ Feasible Solution Set
→ Identifiability
→ Stability
→ Expectation Gap
→ Probability × Payoff
→ Edge
→ Position Size

## Minimum implementation

### Market Model Identification

Supported reverse-solvers:

- forward_pe → implied net profit / implied PE
- ps → implied revenue / implied PS
- pb → implied book equity / implied PB
- ev_ebitda → implied EBITDA / implied EV/EBITDA

Each candidate is evaluated against independently supplied operating ranges.

### Feasible Solution Set

Every model whose implied operating variable lies inside its supplied feasible range remains in the set.

No arbitrary winner is selected.

### Identifiability

- one feasible model → IDENTIFIABLE
- multiple feasible models → AMBIGUOUS
- zero feasible models → UNIDENTIFIABLE

This is deliberately conservative.

### Stability

The minimum version measures the relative width of the implied valuation-multiple interval.

- <=30% → STABLE
- >30% → UNSTABLE

This is not yet a full temporal or perturbation stability test.

### Expectation Gap

When a market model is identifiable, compare the market-implied value/expectation with independently estimated intrinsic value.

No market-model identification → no positive gap is allowed to pass the decision gate.

### Probability × Payoff

Bear/Base/Bull probabilities must:

- be in [0,1]
- sum exactly to 1

The engine calculates:

- scenario returns
- expected return
- win probability
- payoff ratio
- edge

### Position Size

Minimum implementation uses a 25% fractional-Kelly proxy, then caps the result by:

- portfolio maximum position
- explicit risk budget

This is a sizing primitive, not a claim that Kelly is the final IIOS sizing model.

## Hard boundary

Batch 2 v0.1 does NOT yet claim:

- automatic discovery of the market's actual valuation model from price/financial history
- temporal model-switch detection
- market-model confidence calibrated from historical observations
- multi-variable reverse DCF
- SOTP market decomposition
- identifiability across correlated assumptions
- stability under time-series / perturbation / regime changes

Those are subsequent Batch 2 increments.

## Fail-closed rules

Missing market-model inputs block the investment decision.

No feasible market model blocks positive expectation-gap approval.

Ambiguous model identification cannot be silently converted into a single market expectation.

## Gate

Batch 2 Core Gate requires deterministic tests for:

1. multiple feasible models → AMBIGUOUS;
2. one feasible model → IDENTIFIABLE;
3. zero feasible models → BLOCKED;
4. exact probability sum;
5. positive/negative edge;
6. position cap;
7. decision engine receives market-model status;
8. missing market-model evidence fails closed.
