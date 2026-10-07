# M1.2-FM02 Acceptance — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

## Scope

M1.2-FM02 establishes the deterministic PIT Forecastability Feature Builder and its frozen feature contract for the admitted CATL FM01 dataset.

It does not authorize model selection, production forecasting, or investment execution.

## Canonical implementation

- PR: #144
- merge commit: `ade3541302eb6f3fa43ec8aac76540820000a727`
- base canonical main before FM02: `c0adb6a027837ca515faa1cd8838e275fa0a9d46`
- final pre-merge exact head: `617c9b8a3f091e76d5ea44a39e963ff255ffd99b`
- final remote CI: workflow `IIOS M1.2 FM01 Exact CATL Source Admission`, run #15
- final FM02 CI job: `verify-fm02-feature-builder`, conclusion SUCCESS
- FM01 admission job in the same run: SUCCESS

## Contract

Frozen contract:

`research/fm02/FM02_FEATURE_CONTRACT.json`

Schema:

`research/fm02/fm02_feature_contract.schema.json`

Output schema:

`research/fm02/fm02_feature_snapshot.schema.json`

Task contract:

`research/fm02/FM02_TASK_CONTRACT_20261007.md`

The contract explicitly fixes:

- confirmatory_eligible = false;
- PIT cutoff = origin quarter-end;
- visible input records require known_at <= cutoff;
- feature as-of period must precede every declared 3M / 6M / 12M target;
- no imputation;
- AVAILABLE / UNKNOWN are explicit states;
- downstream State Engine, Conditional Backtest, Model Selection, Production Router, and Automatic Execution remain disabled.

## Deterministic feature set

The accepted builder implements exactly six frozen features:

- YOY_GROWTH
- GROWTH_ACCELERATION
- ROLLING_GROWTH_VOL
- SEASONAL_DEVIATION
- MEAN_REVERSION_GAP
- SLOPE_STABILITY

The builder produces an origin × driver feature snapshot for the frozen 11-origin schedule and two admitted drivers, yielding **22 rows**.

## Remote CI evidence

Final run #15 passed:

- FM02 contract JSON Schema validation: PASS;
- 13 / 13 FM02 unit tests: PASS;
- real CATL feature snapshot build: PASS;
- generated snapshot schema validation: PASS;
- build receipt validation: PASS;
- independent PIT provenance audit: PASS;
- compileall: PASS;
- git diff --check: PASS.

The FM01 source-admission job also remained GREEN in the same run.

The generated FM02 canonical content hash was:

`3803be1404255652b831627fcd32acaf203f8984da33f70d3784e28dc449b9da`

This is the builder's canonical content hash of the feature rows, **not** a claim of a committed file-byte SHA.

Unknown outcomes in the final 22-row build:

- YOY_GROWTH: 0
- GROWTH_ACCELERATION: 0
- ROLLING_GROWTH_VOL: 4
- SEASONAL_DEVIATION: 6
- MEAN_REVERSION_GAP: 6
- SLOPE_STABILITY: 0

No unknown value was imputed.

## Fail-closed checks

The final test suite covers:

- FM01 DATA_READY bypass rejection;
- exact admitted dataset cardinality;
- extra-record rejection;
- frozen outer-origin lock enforcement;
- ambiguous visible revision rejection;
- future-known revision exclusion at the resolver boundary;
- target-period early visibility rejection;
- insufficient-history UNKNOWN behavior;
- downstream capability-boundary widening rejection;
- deterministic repeated builds;
- independent formula reference values.

## Acceptance boundary

FM02 is now canonical as a **feature-construction research capability only**.

It remains prohibited to:

- relabel FM00 exploratory evidence as clean confirmatory evidence;
- use FM02 output as model-selection PASS;
- invoke the State Engine as an FM02 capability;
- run Conditional Backtest authorization from FM02;
- authorize a production forecast router;
- introduce current-price leakage;
- introduce scheduler / alerts / automatic execution.

## Next boundary

The next M1.2 development boundary is:

**M1.2-FM03 State Engine / Forecastability State Construction**

FM03 must continue from this canonical main and retain the same PIT, UNKNOWN, provenance, and research-capability separation.
