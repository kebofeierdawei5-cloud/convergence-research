# M1.2-FM03 Acceptance — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

## Scope

M1.2-FM03 establishes the deterministic PIT Forecastability State Engine for the admitted CATL FM01/FM02 research path.

FM03 converts the frozen horizon-neutral FM02 feature snapshot into an orthogonal seven-dimension state vector:

- DIRECTION
- MOMENTUM
- VOLATILITY
- SEASONALITY
- MEAN_REVERSION_PRESSURE
- STRUCTURAL_STABILITY
- DATA_QUALITY

FM03 does not authorize Conditional Backtest, Model Selection, Production Router, confirmatory evidence, current-price inputs, scheduler, alerts, automatic execution, portfolio sizing, or investment decisions.

## Canonical implementation

- PR: #147
- accepted pre-merge head: `276d37111c0866ef7a0e69b7ab38aa1e4e1d2788`
- merge commit: `007ac477f7e45664c6eb7d4681de5d92c3a16b11`
- base canonical main: `bc5ca3f2166d946d69b47da27f2213f6e1758a7a`
- dedicated workflow: `IIOS M1.2 FM03 State Engine`
- accepted CI run: #2
- accepted CI run id: `37563313542`
- accepted job: `verify-fm03-state-engine`
- accepted job id: `112605279779`
- accepted job conclusion: SUCCESS

PR #146 was a superseded pre-acceptance attempt. Its old run #1 failed on the no-prior-origin comparison path. The implementation was corrected fail-closed and revalidated from the resulting exact head; run #2 is the sole acceptance evidence.

## Frozen upstream bindings

FM03 binds the frozen upstream contracts by canonical content hash:

- FM02 feature contract:
  `research/fm02/FM02_FEATURE_CONTRACT.json`
  SHA-256: `4298c1cd1fdc0e0b82f46ffa714430361165fe191f0b4b61567f3b1e7b81f56e`
- FM00 outer universe lock:
  `research/fm00/OU-M12-FM00-CATL-001.json`
  SHA-256: `63a828d081474193af3870dcf0996f2201466210fba2c5011de23312044f591e`

The lock remains FROZEN with 11 scheduled origins and horizon counts:

- 3M: 11
- 6M: 10
- 12M: 8

The exact state input cardinality is 22 origin×driver rows for 300750.SZ / REVENUE / NET_PROFIT.

## State semantics

FM03 uses deterministic, non-tuned mappings only.

Signed mappings:

- YOY_GROWTH: DOWN / FLAT / UP
- GROWTH_ACCELERATION: DECELERATING / FLAT / ACCELERATING
- SEASONAL_DEVIATION: NEGATIVE / NEUTRAL / POSITIVE
- MEAN_REVERSION_GAP: UPWARD / NEUTRAL / DOWNWARD

Comparison mappings use the immediately prior frozen origin for the same driver:

- ROLLING_GROWTH_VOL: FALLING / FLAT / RISING
- SLOPE_STABILITY: IMPROVING / STABLE / DETERIORATING

The first frozen origin has UNKNOWN for comparison-only dimensions because no prior frozen origin exists.

No empirical threshold fitting, quantile calibration, scaler, clustering, PCA, break detection, result-driven tuning, or current-price input is introduced.

## CI acceptance evidence

Accepted run #2 passed all dedicated FM03 gates:

1. Frozen FM03 contract schema validation and upstream hash verification: PASS.
2. Real FM02 PIT feature snapshot construction: PASS.
3. FM03 unit/adversarial tests: **14 / 14 PASS**.
4. FM03 state snapshot build: PASS.
5. Generated FM03 output schema validation: PASS.
6. Independent FM03 PIT/provenance audit: PASS.
7. Compileall: PASS.
8. Git diff-check: PASS.

The generated FM03 state build receipt reported:

- schema version: `IIOS-FM03-STATE-BUILD-0.1`
- status: PASS
- origin count: 11
- row count: 22
- security: `300750.SZ`
- drivers: `REVENUE`, `NET_PROFIT`
- snapshot canonical content hash:
  `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`
- confirmatory_eligible: false
- capability principal: `iios_research`
- capability grant: `m1.2.fm03.state_engine`

State UNKNOWN counts in the accepted real CATL build:

- DIRECTION: 0
- MOMENTUM: 0
- VOLATILITY: 6
- SEASONALITY: 6
- MEAN_REVERSION_PRESSURE: 6
- STRUCTURAL_STABILITY: 2
- DATA_QUALITY: 0

These counts are deterministic consequences of the frozen FM02 feature availability and the prior-origin prerequisite. No UNKNOWN value was imputed.

## Five retained boundaries

### PIT

Every FM02 input row is revalidated against the frozen origin cutoff. Feature-as-of and maximum feature input periods must precede every declared 3M / 6M / 12M target.

### UNKNOWN

FM03 accepts only AVAILABLE / UNKNOWN feature states. UNKNOWN remains UNKNOWN and comparison states become UNKNOWN when a required prior feature is unavailable.

### Provenance

Each state retains feature identifiers, FM02 row identifiers, and upstream DriverSeries record identifiers. Independent CI recomputes and audits these relations without using the FM03 engine as its own proof.

### Frozen origin schedule

FM03 accepts only the hash-bound FROZEN FM00 outer universe, exactly 11 origins × 2 drivers. Duplicate, missing, extra, or out-of-schedule rows fail closed.

### Capability isolation

The only granted capability is:

`principal=iios_research`
`grant=m1.2.fm03.state_engine`

The following remain explicitly forbidden:

- `m1.2.fm04.conditional_backtest`
- `m1.2.model_selection`
- `production.forecast_router`
- `production.automatic_execution`

FM03 has `confirmatory_eligible=false` and `usage=DEVELOPMENT_ONLY` under the contaminated FM00 research lineage.

## Acceptance boundary

FM03 is canonical as a **State Construction Research Capability** only.

It is not evidence that any state dimension is predictive, not model-selection evidence, and not production forecasting capability.

## Next boundary

**M1.2-FM04 Conditional Backtest**

FM04 must start from canonical main after this merge and must preserve the FM00 frozen research plan, origin partition, PIT semantics, UNKNOWN / NO_SELECTION semantics, provenance closure, and inner-selection / outer-evaluation separation.
