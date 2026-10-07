# M1.2-FM02 Task Contract

Date: 2026-10-07
Status: PASS / MERGED / CANONICAL

## Objective

Build the deterministic PIT Feature Builder required to transform the admitted FM01 CATL DriverSeries history into an auditable, horizon-neutral feature snapshot.

## User Value

Create a reusable forecastability feature layer that can be independently replayed, audited, and later consumed by State / Conditional Backtest research without leaking future information or silently converting insufficient evidence into a value.

## Product Surface

- Frozen FM02 Forecastability Feature Contract.
- Deterministic feature builder for YOY_GROWTH, GROWTH_ACCELERATION, ROLLING_GROWTH_VOL, SEASONAL_DEVIATION, MEAN_REVERSION_GAP, and SLOPE_STABILITY.
- Record-level provenance and explicit AVAILABLE / UNKNOWN output semantics.
- Independent CI provenance and output-schema validation.

## Test / Acceptance

The FM02 PR is acceptable only when the remote CI gate demonstrates all of the following:

1. Frozen contract passes JSON Schema validation.
2. Real CATL FM01 input builds deterministically for the frozen 11-origin schedule and produces 22 origin×driver rows.
3. Every feature input record is PIT-visible at the origin cutoff and precedes every declared target horizon.
4. Ambiguous revisions and early target visibility fail closed.
5. Insufficient lookback produces UNKNOWN with no imputation.
6. Future-known records cannot alter prior-origin output.
7. Generated snapshot passes the frozen output schema.
8. confirmatory_eligible = false and downstream capabilities remain disabled.

## Out of Scope

FM02 does not authorize or implement:

- Driver State Engine;
- Conditional Backtest;
- Inner / Outer Model Selection;
- production forecast router;
- production confirmatory evidence;
- current-price or market-data inputs;
- scheduler, alerts, automatic execution, or order placement.

The existing FM00 epoch remains exploratory / contaminated. FM02 output is implementation research material and cannot be relabeled as clean confirmatory evidence.
