# M1.2-FM04 Task Contract

Date: 2026-10-07
Status: IMPLEMENTATION / REVIEW

## Objective

Implement the first Conditional Backtest research capability on the canonical FM03 State Engine output.

FM04 answers the narrower research question:

Conditional on a PIT-safe forecastability state observed at an outer origin, does the relative performance of the pre-registered forecast model set differ in a reproducible way?

FM04 must distinguish:

- state construction from predictive validity;
- inner model selection from outer evaluation;
- development / contaminated research evidence from confirmatory evidence.

## Frozen research boundaries

FM04 inherits and re-enforces:

1. PIT-only forecast inputs;
2. explicit AVAILABLE / UNKNOWN state semantics;
3. record-level provenance;
4. frozen FM00 origin schedule;
5. frozen candidate model universe;
6. inner-selection / outer-evaluation separation;
7. result-exposure firewall;
8. capability isolation;
9. insufficiency => NO_SELECTION;
10. no statistical significance claim from the exploratory sample.

## Pre-registered model universe

The four frozen model candidates are:

- SEASONAL_NAIVE
- PERSISTENCE_YOY
- TREND_LOG_LINEAR_8Q
- MEAN_REVERSION_YOY_8

No additional model family or parameterization may enter FM04.

## Conditional selection unit

A selection unit is:

security × driver × horizon × state_dimension × state_value × outer_origin

The state is taken from the FM03 row for the same driver and outer origin.

Inner observations for an outer origin must satisfy all of:

- earlier frozen origin only;
- same security, driver, horizon, state dimension, and state value;
- target actual is already known at or before the outer origin cutoff;
- all four model candidates are forecastable from PIT-visible inputs at that inner origin;
- the same inner-origin universe is used for all four model comparisons.

Minimum common inner sample size:

n >= 3

Selection criterion:

- primary metric: MAE;
- choose the lowest mean inner MAE;
- deterministic tie-break order follows the frozen model order.

No outer result, outer actual, or future information may influence inner selection.

## Outer evaluation

After selection, the selected model is evaluated once at the outer origin against the target actual.

Outer actuals are permitted only in the scoring phase and must never appear in model inputs or inner-selection evidence.

FM04 also produces a descriptive conditional performance matrix for every state dimension / state value using a common outer universe across all four models. This descriptive matrix is not a model-selection authorization.

## Statistical interpretation

FM04 is explicitly exploratory / contaminated.

It may report:

- common sample size;
- MAE;
- RMSE;
- sMAPE;
- selected-model frequency;
- paired outer error observations.

It may not report:

- confirmatory significance;
- production routing authorization;
- evidence that a state is predictive merely because model performance differs conditionally.

Rolling origins are not assumed iid.

## Out of scope

FM04 does not authorize:

- production model router;
- clean confirmatory research;
- current price;
- scheduler / alerts;
- automatic execution;
- portfolio sizing;
- investment decisions;
- post-hoc state threshold tuning.
