# M1.2-FM04 Acceptance — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

## Scope

M1.2-FM04 establishes the first PIT-safe Conditional Backtest capability on the canonical FM03 State Engine path.

It evaluates whether forecast-model performance can be compared conditional on the seven frozen FM03 State dimensions without allowing outer outcomes, future observations, or production authority to leak into model selection.

## Canonical implementation

- PR: #150
- accepted pre-merge head: `PENDING`
- merge commit: `PENDING`
- base canonical main: `ddf7034e7422d91f1f7f0135470fef6907b94272`
- dedicated workflow: `IIOS M1.2 FM04 Conditional Backtest`
- accepted CI run: #2
- accepted run id: `37564860982`
- accepted job: `verify-fm04-conditional-backtest`
- accepted job id: `112610137700`
- accepted job conclusion: SUCCESS

## Frozen upstream bindings

FM04 is bound to:

- FM03 state snapshot canonical content SHA-256:
  `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`
- FM03 state contract Git blob:
  `1ede6cfd87476e466010a229599c52f984b24de6`
- FM01 DriverSeries Git blob:
  `8fbdafaa941587d843ab2509bb732620f5f66b4d`
- FM00 outer-universe lock Git blob:
  `abe9c575ea4a194249a419bbb145b5ddf7dd05de`
- FM00 research plan Git blob:
  `a440223d2b61b786434c9d63b00ca1d525fb4a79`
- FM00 candidate-space Git blob:
  `70778aa3bbeccccc87c856c7d4645ea366de3ac0`
- FM00 evaluation-purity boundary Git blob:
  `b7e7810bd383e893a328e2ed738d825423e98eda`

The frozen outer schedule remains 11 origins with:

- 3M: 11
- 6M: 10
- 12M: 8

The four admitted model candidates are:

- SEASONAL_NAIVE
- PERSISTENCE_YOY
- TREND_LOG_LINEAR_8Q
- MEAN_REVERSION_YOY_8

No additional model family or parameterization is enabled by FM04.

## Conditional selection semantics

A selection unit is:

`security × driver × horizon × state_dimension × state_value × outer_origin`

Inner selection is valid only from strictly earlier frozen origins, with the same state condition and the same target/horizon. The target actual must already be known at or before the outer-origin cutoff.

All four candidate models must be forecastable on the same inner-origin universe. The minimum common inner sample is 3. Otherwise the result is `NO_SELECTION`.

Selection uses mean inner MAE with the frozen deterministic model-order tie-break.

Outer actuals are used only after selection for OOS scoring.

## CI acceptance evidence

The accepted FM04 workflow passed:

1. exact upstream Git blob anchor checks;
2. frozen FM04 contract and schema validation;
3. exact FM02 feature reconstruction;
4. exact FM03 state reconstruction and pinned state-snapshot hash;
5. FM04 unit tests;
6. real CATL Conditional Backtest build;
7. FM04 result schema and structural invariant validation;
8. independent PIT / nested-selection / scoring audit;
9. compileall;
10. git diff-check.

The dedicated run reported:

- outer selection units: **406**
- selected units: **0**
- outer evaluated units: **0**
- `NO_SELECTION` units: **406**
- conditional descriptive groups: **79**

The result is therefore a **valid sufficiency boundary**, not a predictive finding.

With the current 11-origin frozen schedule and seven-dimensional state conditioning, no state-conditioned outer unit obtained the preregistered minimum common inner sample of 3. FM04 consequently authorizes no state-conditioned model selection.

## Interpretation boundary

This acceptance does **not** establish:

- that any FM03 State predicts future outcomes;
- that any model is superior in production;
- that a State should route production forecasting;
- statistical significance;
- confirmatory evidence;
- an investment decision.

The 79 conditional descriptive groups are research diagnostics only. Any observed difference among model metrics remains exploratory and cannot be promoted to production or confirmatory evidence.

## Five retained hard boundaries

### PIT

Forecast inputs are restricted to records visible at the relevant origin cutoff. Inner target actuals must be known by the outer cutoff; outer actuals are not available to model selection.

### UNKNOWN

FM03 UNKNOWN remains UNKNOWN. An UNKNOWN state forces `NO_SELECTION`; there is no imputation or fallback state.

### Provenance

State-row provenance, FM03 feature-row lineage, DriverSeries record identity, inner actual identity, and model input record identity are carried into the research result and independently audited.

### Frozen origin schedule

Only the hash-bound FM00 scheduled origins and horizons are admitted. Origins are not added, removed, or retrospectively excluded from FM04.

### Capability isolation

FM04 grants only:

`principal=iios_research`
`grant=m1.2.fm04.conditional_backtest`

Production Router, production Model Selection, Automatic Execution, and Investment Decision authority remain forbidden.

## Research posture

The FM00 epoch remains:

- EXPLORATORY
- CONTAMINATED
- DEVELOPMENT_ONLY
- confirmatory_eligible = false

Outer results cannot flow back into same-epoch tuning. Any result-driven model/state/threshold change requires a new research epoch.

## Acceptance boundary

FM04 is canonical as a **Conditional Backtest Research Capability**.

It demonstrates that the system can perform PIT-safe conditional comparison and correctly fail closed when the frozen sample is insufficient.

It does **not** demonstrate predictive validity.

## Next boundary

**M1.2-FM05 Scope Freeze / Data Sufficiency Adjudication**

Before any threshold relaxation, state regrouping, model-family expansion, or result-driven tuning, the research scope and sample-sufficiency policy must be explicitly adjudicated and frozen in a new controlled boundary.
