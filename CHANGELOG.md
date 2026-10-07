# Changelog

## Unreleased

### 2026-10-07 — M1.2-FM04 Conditional Backtest

- Added frozen Conditional Backtest contract and result schema over the canonical FM03 state path.
- Added PIT-safe evaluation for the four preregistered model candidates with strict inner/outer separation.
- Added explicit UNKNOWN → `NO_SELECTION`, common-inner-universe, deterministic MAE selection/tie-break, and provenance controls.
- Added independent PIT/nested-selection/scoring audit and dedicated CI.
- Accepted CATL run #2 with 12 tests passing, 406 outer selection units, 0 selected, 406 `NO_SELECTION`, and 79 conditional descriptive groups.
- FM04 remains exploratory/contaminated/development-only and does not authorize production model routing, confirmatory inference, automatic execution, or investment decisions.

### 2026-10-07 — M1.2-FM03 Deterministic PIT State Engine

- Added frozen FM03 State Contract and output schema for the seven orthogonal Forecastability State dimensions.
- Added deterministic PIT state construction from the admitted FM02 CATL feature snapshot with explicit AVAILABLE / UNKNOWN semantics and no imputation.
- Added provenance closure to FM02 feature rows and upstream DriverSeries record IDs, frozen FM00 origin-lock hash binding, and fail-closed capability isolation for `iios_research` / `m1.2.fm03.state_engine`.
- Added dedicated CI with 14 / 14 tests, real CATL 22-row state build, output schema validation, independent PIT/provenance audit, compileall, and diff-check.
- FM03 remains DEVELOPMENT_ONLY / contaminated and non-confirmatory; Conditional Backtest, Model Selection, Production Router, current-price inputs, scheduler, and automatic execution remain out of scope.

### 2026-10-07 — M1.2-FM02 PIT Feature Builder / Forecastability Feature Contract

- Added the frozen FM02 forecastability feature contract and output schema.
- Added deterministic PIT feature construction for six forecastability features over the admitted CATL 22-quarter FM01 history.
- Added explicit AVAILABLE / UNKNOWN semantics, record-level provenance, exact FM01 admission cardinality gates, frozen outer-origin lock checks, and fail-closed adversarial tests.
- Final remote CI run #15 passed with 13 / 13 FM02 tests, generated snapshot schema validation, independent PIT provenance audit, compileall, and diff-check.
- FM02 remains research-only and non-confirmatory; State Engine, Conditional Backtest, Model Selection, Production Router, current-price inputs, scheduler, and automatic execution remain out of scope.

### 2026-10-04 — B2 Data / Evidence / PIT Foundation

- Added frozen Evidence Contract v0.1 and machine-readable Evidence Record schema.
- Added frozen Source Registry v0.1 with free-first and non-mandatory paid-data policy.
- Added frozen PIT Temporal Semantics v0.1 separating published_at, known_at, retrieved_at and effective intervals.
- Added executable fail-closed A02 exact-admission preflight and negative-control tests.
- Recorded the current A02 real-data state as BLOCKED because exact 000906cons.xls bytes and the PIT Security Master raw bundle are not independently materialized.
- No A02 downstream parameterization or model selection is enabled by this change.
## [Unreleased]

### 2026-10-04 — State Reconciliation

- Reconciled current Git state against stale status/index documentation.
- Recorded current `main` and merged investment-core history.
- Recorded Batch 2 v0.1 as OPEN / RED-TEAM BLOCKED and not a current capability.
- Confirmed Human-authoritative company valuation model selection is merged.
- Corrected the investment return hurdle semantics: positive return >15%; no fixed 1–3 year holding period and no annualized-return core gate.
- Separated Investment Decision Core from M1.2 Forecast Research state.

### 2026-09-30

- M1.2-FM-01 implementation foundation is PASS; CATL exact historical source ingress remains BLOCKED until an exact M1.1 snapshot is available.
- Next active research task after data admission: M1.2-FM-02 PIT Feature Builder.

## [0.1.0] — 2026-09-30

- Established first Git engineering baseline for M1.2 Forecast Validation.
- Added G2 R10 frozen-reference identity/evidence layer without changing frozen governance artifacts.
- Added FM-00 Exploratory Research Epoch, Research Plan, Candidate Space, horizon-specific Outer Universe, Evaluation Purity Boundary, schemas, validator, tests, and validation evidence.
- Added Agent Engineering Constitution and long-term project continuity state.
