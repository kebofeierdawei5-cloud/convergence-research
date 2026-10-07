# M1.2-FM03 Task Contract

Date: 2026-10-07
Status: **IMPLEMENTATION / REVIEW**

## Objective

Build a deterministic PIT-safe State Engine that transforms the frozen FM02 forecastability feature snapshot into an orthogonal Driver State vector for the frozen FM00 origin schedule.

The engine must preserve five hard boundaries carried forward from FM01/FM02:

1. PIT visibility;
2. explicit AVAILABLE / UNKNOWN semantics;
3. record-level / feature-level provenance;
4. immutable pre-scheduled origins;
5. capability isolation.

## User Value

Turn horizon-neutral forecastability features into an auditable state representation that later Conditional Backtest research can consume without allowing state construction to import future information, silently impute missing evidence, alter the frozen historical origins, or acquire downstream model-selection / production authority.

## Product Surface

- Frozen FM03 State Contract.
- Deterministic orthogonal state construction for DIRECTION, MOMENTUM, VOLATILITY, SEASONALITY, MEAN_REVERSION_PRESSURE, STRUCTURAL_STABILITY, and DATA_QUALITY.
- Exact binding to the admitted FM02 feature rows and frozen FM00 origin schedule.
- State-level provenance back to FM02 feature-row IDs and ultimately to DriverSeries record IDs.
- Explicit UNKNOWN propagation.
- Capability-gated research-only execution.
- Real CATL build/replay and independent PIT audit.

## State Semantics

FM03 intentionally uses deterministic, non-tuned mappings only.

Signed features use sign semantics:

- YOY_GROWTH: >0 = UP; =0 = FLAT; <0 = DOWN.
- GROWTH_ACCELERATION: >0 = ACCELERATING; =0 = FLAT; <0 = DECELERATING.
- SEASONAL_DEVIATION: >0 = POSITIVE; =0 = NEUTRAL; <0 = NEGATIVE.
- MEAN_REVERSION_GAP: >0 = DOWNWARD pressure; =0 = NEUTRAL; <0 = UPWARD pressure.

Non-signed rolling features use first-difference direction against the immediately prior scheduled origin for the same driver:

- ROLLING_GROWTH_VOL: higher = RISING, equal = FLAT, lower = FALLING.
- SLOPE_STABILITY: higher dispersion = DETERIORATING, equal = STABLE, lower dispersion = IMPROVING.

The first scheduled origin has UNKNOWN for comparison-only dimensions because no earlier frozen origin exists.

No empirical threshold, quantile, scaler, clustering, or result-driven calibration is introduced by FM03. Such learned state boundaries require a separately frozen research change and a new research epoch when result-driven.

## Test / Acceptance

The FM03 PR is acceptable only when exact-head remote CI demonstrates all of the following:

1. Frozen FM03 contract passes JSON Schema validation.
2. Real CATL FM02 input is accepted only when all 22 expected origin×driver rows are present and exactly bound to the frozen FM00 schedule.
3. Every accepted FM02 row remains PIT-valid: origin cutoff is authoritative, feature-as-of is before every scheduled 3M/6M/12M target, and FM02 provenance is retained.
4. State construction is deterministic and replay-stable.
5. UNKNOWN never becomes a value through imputation or fallback.
6. Missing/invalid provenance, duplicate rows, out-of-schedule origins, future feature-as-of, or malformed feature states fail closed.
7. Comparison-only state dimensions require the prior frozen origin and become UNKNOWN when that prerequisite is unavailable.
8. Capability isolation rejects contexts that grant Conditional Backtest, Model Selection, Production Router, or Automatic Execution authority.
9. Generated FM03 state snapshot passes the frozen output schema.
10. confirmatory_eligible = false and FM03 cannot authorize downstream capabilities.

## Out of Scope

FM03 does not authorize or implement:

- Conditional Backtest;
- Inner / Outer Model Selection;
- production forecast router;
- confirmatory evidence;
- current-price or market-data inputs;
- scheduler, alerts, automatic execution, or order placement;
- empirical threshold tuning;
- portfolio sizing or investment decisions.

The FM00 epoch remains exploratory / contaminated. FM03 outputs are research implementation material only and cannot be relabeled as clean confirmatory evidence.
