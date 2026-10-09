# Changelog

## Unreleased

### 2026-10-09 — Route A Run #8 Partial Capture Retained + B2 Preflight (No Provider Credentials)

- Run #8 / `37938129274` completed SUCCESS using the canonical partial-capture final gate.
- Nine public/free sources were declared; eight objects were captured and their exact raw bytes independently verified; the Eastmoney K-line API failed with no bytes and remains explicitly failed in the receipt.
- Receipt status = `PARTIAL_CAPTURE_NOT_ADMITTED`; B2 preflight = `BLOCKED_NOT_ADMITTED`; independent integrity = `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`.
- Artifact ID `11620425220`, SHA-256 `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1`, 14-day retention. Run record: `docs/iios/ROUTE_A_CAPTURE_RC_CN_A_002001_20261009_RUN8.md`.
- No LLM/provider endpoint or API key was used. This green run means a partial artifact was preserved and verified; it does not mean complete URL coverage or any source's PIT/evidence admission.
- Next gate: create source-located fact-level Evidence Records from the raw reports/pages, review actual publication-vintage/licence evidence, and use the existing B2 validator. Until then, all seven required field groups remain uncovered by admitted facts.


### 2026-10-09 — Route A First Real Source Capture (Raw Intake Only)

- Captured five public source objects for the manually selected `002001.SZ` case through the no-secret GitHub Actions Route A workflow.
- Run #2 / `37918304170` = SUCCESS; all five HTTP fetches succeeded; independent verifier returned `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION` with `raw_bytes_verified=5` and `unknown_pit_sources=1`.
- Artifact ID `11610237261`; ZIP SHA-256 `71600859888d65d7bcdd67591f1029791910be744fe7e17dadedfcff804006d3`; 14-day GitHub retention. The evidence bundle is not embedded in Git.
- Preserved explicit non-claim: receipt remains `CAPTURED_NOT_ADMITTED`; the IR page is UNKNOWN, four exchange PDFs remain PIT candidates, and source authenticity/license/evidence admission have not passed.
- The next gate is the existing B2 Evidence/PIT admission for these actual bytes, followed by coverage of missing price, business-reality and capital-structure source groups.

### 2026-10-09 — Route A Free-First Company Evidence Intake

- Added company-level raw intake for public HTTPS source URLs and operator-supplied original files, without paid financial-data or LLM provider credentials.
- Retained exact raw bytes and manifest copies; recorded per-source SHA-256, byte size, retrieval time, source locator, time-basis claims and license/reuse declarations.
- Added a separate independent verifier for manifest binding, raw-byte hashes, source locator metadata, safe paths, unreferenced files and fail-closed PIT/UNKNOWN semantics.
- Kept capture outputs explicitly NOT_ADMITTED: hash verification does not establish source authenticity, PIT eligibility, completeness, or company-case admission.
- Merged PR #238 at `33ee2263683d346f7c6aec34a049b0bcd25e7dba`; dedicated Route A CI, State Hygiene, B2-F independent red-team, Investment Core, B1, B2, CORE-00, FM01 and C0 regression workflows passed on the validated PR head.

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
