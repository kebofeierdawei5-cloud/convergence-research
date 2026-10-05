# IIOS Long-Term Project Memory — 2026-09-30

## 1. Canonical project state

- IIOS = Intelligent Investment Operating System for China A-shares + Hong Kong stocks.
- Product scope: single user, low-frequency, candidate-only single-stock deep analysis after coarse screening; human remains final approver/executor; no automatic order placement.
- Core objective: repeatable, auditable, point-in-time reproducible investment decisions with strong resistance to LLM failure modes.
- Core decision chain remains: Candidate → Trust → Quality → Reality → Independent Forecast → Valuation → Market Implied Expectation → Expectation Gap → Risk → Market/Positioning → Decision → Position → Monitoring → Validation.
- Trust, Thesis, Valuation, and Investment Attractiveness are separate states.
- Fail-closed means affected permissions close; UNKNOWN/missing/stale/conflicting/unverifiable evidence must not silently become PASS/HOLD.
- Analytical artifacts are immutable versions: DRAFT → FROZEN → SUPERSEDED/INVALID; upstream invalidation propagates.
- AI Decision and Human Decision remain separate historical records.
- Deterministic calculations/state/permissions/dates/hashes/persistence are code-owned, not LLM-owned.

## 2. Governance baseline: G2

- G2 governance/runtime work is complete for the reference boundary.
- Final disposition: `G2 GOVERNANCE FREEZE = PASS — Reference Runtime`.
- Forecast Model Selection is officially `UNFROZEN` and may proceed.
- The frozen Governance Runtime Contract is immutable; future normative governance changes require successor candidate → validation → human approval → new freeze.
- Final independent re-audit used a freshly extracted clean package rather than development-directory self-certification.
- Final evidence summary from the latest handoff:
  - 16/16 fresh-process suites PASS
  - 144/144 assertions PASS
  - compileall rc=0
  - live IIOS service orphan = 0
  - runtime directory leak = 0
  - Trust Root reset = PASS
  - G2 Intelligence Matrix = 10/10 PASS
  - Final Cross-module Bypass = 6/6 PASS
  - Prior Cross-module Red-team = 40/40 PASS
  - Full Independent Re-audit = PASS
- Critical composition attacks previously found were closed:
  - Ledger tail truncation → DENY
  - forged/replayed attestation → DENY
  - unsigned runtime observation → DENY
  - self-issued Manifest/Capability → DENY
  - caller-selected TrustRootRegistry → DENY
  - custom registry verification → DENY
  - runtime security bypass flag → removed
- Production boundary remains open and must not be overstated as closed: MAC/SELinux/AppArmor, managed Secret/HSM, production network policy, TPM/measured/remote attestation, host-root/kernel-admin trust boundary, production deployment hardening.
- Important principle: `Reference Governance Freeze != Production Security Certification`.

## 3. M1.1 forecast-validation baseline already completed

- Rolling backtest uses PIT slicing: Forecast Origin → Origin Quarter End Cutoff → only Reality with `known_at <= cutoff` enters training.
- CATL quarterly Historical Reality currently covers 2021Q1–2026Q2, 22 quarters.
- Provenance distinguishes:
  - `DIRECT_PERIODIC_FILING`
  - `DERIVED_H1_MINUS_Q1`
  - `DERIVED_ANNUAL_MINUS_Q1_Q2_Q3`
- 2026Q2 may be derived from H1 minus Q1 but must never be represented as an independent filing.
- Forecast origins currently available:
  - 3M = 11
  - 6M = 10
  - 12M = 8
- Rolling origins are not iid; nominal N must not be presented as independent sample count.
- Existing benchmark family:
  - `SEASONAL_NAIVE`
  - `PERSISTENCE_YOY`
  - `TREND_LOG_LINEAR`
  - `MEAN_REVERSION_YOY`
- CATL historical benchmark results are `DESCRIPTIVE_ONLY`; no universal model reliability has been established.
- 2018–2020 was intentionally not backfilled because complete continuous quarterly PIT provenance was not established; principle: insufficient statistics is preferable to pseudo-precision.

## 4. M1.2 target architecture

Primary research pipeline:

`PIT Reality → Forecastability Features → PIT State → Conditional Backtest → Evidence → Model Selection Candidate`

Research-level anti-overfitting chain:

`Research Plan → Inner Selection → Frozen Router Instance → Outer Evaluation`

Three router objects are distinct and must not be collapsed:
1. `ROUTER_INSTANCE`: the choice actually made at one historical origin.
2. `GLOBAL_ROUTER_CANDIDATE`: cross-origin reusable rule inferred from multiple instances.
3. `PRODUCTION_ROUTER`: only after cross-company/cross-cycle and prospective shadow validation.

Research cleanliness distinction:
- `PIT-OOS != Research-Clean-OOS`.
- Historical M1.0/M1.1 results are already exposed and may be used for development/exploration/descriptive evidence.
- They must not be relabeled as clean confirmatory evidence.
- Any result-driven change to feature/state/threshold/method/metric/benchmark/horizon/training window/data cleaning/stopping rule/candidate space/parameterization creates a NEW research epoch unless pre-registered.
- New epochs inherit contamination lineage; they cannot wash contaminated results into clean confirmatory evidence.

## 5. M1.2 orthogonal Driver State design

Do not create one giant mutually-exclusive regime label.
Use an orthogonal state vector with dimensions:
- Direction
- Momentum / Acceleration
- Volatility
- Seasonality
- Mean-Reversion Pressure
- Structural Stability
- Data Quality

All state values must be constructed strictly from information available at the forecast origin.
Statistical break must not be conflated with economic explanation.
`UNKNOWN` and `NO_SELECTION` are first-class outcomes.

## 6. Feature Contract rules

Features are versioned research objects. Each feature must make explicit:
- formula
- inputs
- lookback
- transform
- PIT cutoff
- missing-data rule
- quality status

Any learned transform (mean/std/quantile/scaler/winsorization/clustering/PCA/break detection/etc.) is a research/modeling decision and must be fit inside the permitted PIT/inner boundary.

## 7. Conditional Backtest rules

Use explicit objects/lineage:
`Origin → ForecastRun → Prediction → Outcome → Evaluation`.

Pairwise model comparisons require:
- same origin universe
- same target
- same horizon
- same actual outcome
- same evaluation metric

Metrics are versioned; MAPE is not universal, especially for profit/cash-flow series.
Track and report:
- nominal N
- effective N
- dependence structure
- coverage
- missing/excluded origins with reasons
- state support / sparsity

Sparse states, missing PIT provenance, conflicts, unresolved dependence, or insufficient statistics may force `NO_SELECTION`.

## 8. FM-00 completed

Current implemented phase: `M1.2-FM-00 | Exploratory Research Epoch + Research Plan + Candidate Space Registry v0.1`.

FM-00 established a machine-readable research-control layer containing:
- `RESEARCH_EPOCH`
- `RESEARCH_PLAN`
- `CANDIDATE_SPACE_REGISTRY`
- `OUTER_UNIVERSE_LOCK`
- `EVALUATION_PURITY_BOUNDARY`
- deterministic validator

Current FM-00 status:
- Epoch type = `EXPLORATORY`
- Prior exposed results = contaminated/exposed lineage
- Confirmatory eligible = `FALSE`
- Current OOS visible = `FALSE`
- Production Router = `FALSE`
- Candidate Space = frozen
- Outer Universe = frozen
- Purity Boundary = frozen
- Validator = PASS
- 8/8 tests PASS
- leakage/tuning/exclusion/contamination/schema mutation controls killed as designed

A design correction was made during FM-00: 3M/6M/12M must not share a single origin-eligibility universe because their horizon-specific origin counts differ. Eligibility must be horizon-specific and explicit.

FM-00 package artifact created locally:
- `/mnt/data/IIOS_M1_2_FM00_Exploratory_Research_Epoch_v0.1.tar.gz`
- SHA-256: `3dea6513288abc28aae8a6b79e0bb4815004bd77ab4a09cc266b25fcb171fbc2`
- validation result: `/mnt/data/iios_m12_fm00_v0_1/FM00_VALIDATION_RESULT.json`

## 9. FM-01 current state

`M1.2-FM-01 | Driver History Foundation` implementation is complete at the code-contract layer.

Implemented and tested:
- machine-readable `DriverSeries` schema;
- PIT resolver using `known_at` cutoff;
- explicit revision sequencing;
- same-snapshot conflict detection;
- direct-vs-derived provenance enforcement;
- deterministic H1-minus-Q1 derivation;
- deterministic annual-minus-Q1-Q2-Q3 derivation;
- parent lineage requirements;
- deterministic dataset admission validator.

Current test status: `18/18 PASS`; `compileall PASS`.

CATL population status remains `BLOCKED_DATA_INGRESS`: the exact M1.1 historical source snapshot is not present in the FM-00 Git baseline. The repository therefore contains a zero-record CATL dataset placeholder plus an explicit blocking admission result. No numeric values are fabricated or substituted.

Target data coverage remains 2021Q1–2026Q2 (22 quarters) for `REVENUE` and `NET_PROFIT`.

## 10. Immediate next development step

First unblock the FM-01 data gate by materializing or recovering the exact hash-bound M1.1 CATL historical source snapshot. After exact source admission and independent PIT replay, proceed to:

`M1.2-FM-02 | PIT Feature Builder`

Do not jump to model selection before Driver History / Feature layers are reliable.

## 10. Engineering constitution for future agents

Every task states:
- Objective
- User Value
- Product Surface
- Test / Acceptance
- Out of Scope

Hard rules:
- Never fabricate missing data.
- Tests must be able to fail; verifier must not self-certify.
- Never weaken tests to obtain PASS.
- One narrow change per task where practical.
- Repository artifacts / ADR / CHANGELOG are continuity sources; chat is not authoritative.
- Deterministic system state/calculation/authorization/persistence belongs to code.
- No hidden current-price leakage into blind-forecast inputs.
- No silent evidence substitution.
- No direct LLM writes to authoritative state.

## 11. Information deliberately NOT kept as long-term memory

Do not treat these as current state unless a new artifact re-establishes them:
- old G2 v0.4/v0.6/v0.8 candidate statuses and blockers
- historical governance audit disputes already resolved by the final R10 re-audit
- old Batch5/RM2B/RM4/RM6 execution lineages as current evidence
- closed identity/authority reconciliation seams
- closed S7 metadata bug analysis
- raw individual receipt hashes that do not affect current architecture
- old `Handoff` statements saying Governance Runtime was still blocked

Those remain historical artifacts, not active roadmap state.

## 12. Default resumption instruction

When resuming IIOS work, start from this file plus the current repository/package artifacts.
Treat the frozen G2 Governance Runtime as an immutable contract and FM-00 as the current active research-control layer.
Next default task: `M1.2-FM-01 Driver History Foundation`.


## 13. Investment Decision Core — 2026-10-04 architecture decisions

### Human valuation-model selection is now the canonical company-side design

After two rounds of red-team review, the system explicitly does NOT attempt to automatically determine a single "most appropriate" company valuation model at the current stage.

Canonical chain:
`Company Value Core Scan → Economic Profile → Candidate Valuation Models → HUMAN Primary Model Selection → IIOS Model Consistency Gate → Primary / Secondary / Cross-check → Independent Forecast → Intrinsic Valuation`

Authority boundary:
- IIOS owns value-core structure, economic classification, candidate-model generation, suitability ranking, validation, model consistency, calculations, and replay.
- Human owns the final Primary Model, rationale, material Secondary/Cross-check choices, explicit override decisions, and final investment approval.
- `selection_method=HUMAN` is required.
- Missing primary model/rationale or invalid model selection fails closed.
- Selecting outside the candidate set requires `override_reason`.
- The Model Router is advisory only and must never silently replace the human-selected model.

Rationale:
The company-side valuation model is an investment judgment and is not always uniquely identifiable from currently available data. Do not spend the next milestone trying to turn the company-side Router into a black-box authority. Revisit automatic recommendation only after sufficient historical model-choice and outcome data exists.

Implementation status:
- PR #4 `refactor(iios): human-in-the-loop company valuation model selection` merged to `main`.
- Merge commit: `af2a1a6a019872c76ee9a49c4e05c0702b0c7e20`.
- Final MVP CI run #52 = SUCCESS.
- FM00 CI run #51 = SUCCESS.
- Human-selection contract: `docs/iios/HUMAN_VALUATION_MODEL_SELECTION_v1.0.md`.

### Batch 2 v0.1 is RED-TEAM BLOCKED

The current Batch 2 implementation must not be treated as a valid `Market Model Identification` implementation and must not be merged.

What the existing code actually does:
`Given Model + Given Human Operating Range + Current Price → Reverse Valuation`

Why it is insufficient:
- "Feasible" is determined mainly by whether the user supplied a mathematically valid range, not whether market observations support that model.
- Identifiability is effectively driven by how many model inputs the user provides, not by observable market evidence.
- Market model history / valuation behavior / price-fundamental relationship is not used.
- Market-model inputs lack the required evidence/PIT/provenance contract.
- `forecast` and `intrinsic` are not meaningfully used for market-model identification.
- The current expectation-gap path is mathematically/semantically invalid for non-PE models and incorrect for PE because the derived quantity is EPS, not a market-implied value.
- Current stability measures the width of a user-supplied range, not temporal/model/regime stability.
- Current Probability/Payoff and Kelly sizing are only experimental primitives and are not frozen as final IIOS formulas.
- Batch-2-specific tests were not part of the established MVP CI gate at the time of implementation.

Therefore:
- Preserve the reverse-solver logic only as a low-level `Market Reverse Valuation Primitive`.
- Do not add more ad-hoc reverse solvers or thresholds to the current identification layer.
- Redesign Batch 2 v0.2 from the data/identification question upward.

### Canonical Market-side target

The correct market-side problem is:
`Market Observable Evidence → Candidate Market Models → Historical / Current Fit → Feasible Solution Set → Identifiability → Stability → Reverse Valuation → Market Implied Expectations → Expectation Gap`

Target distinction:
- Company valuation model = "How should IIOS value the company independently?" → Human-authoritative today.
- Market valuation model = "What logic and expectations are embedded in the current market price?" → IIOS should progressively identify from evidence.

Market Model Identification must not be inferred from user-declared model hypotheses alone.

### Active workstream priority

For the investment-decision MVP, the next task is NOT continued Batch-2 coding.

Required sequence:
1. Red-team/audit current Batch 2 definition and evidence requirements — completed 2026-10-04.
2. Freeze the audit disposition: current Batch 2 v0.1 = BLOCKED; no merge.
3. Design the smallest correct Batch 2 v0.2 around actual market-observable evidence and PIT/provenance.
4. Only then implement and test the new market-model identification layer.
5. Reconnect expectation gap → probability/payoff → risk → position sizing only after market implied expectation is semantically valid.

Do not confuse this investment-core workstream with the separate M1.2 forecast-validation workstream; both remain active, but their contracts and gates must stay separate.

## 14. Long-term memory / continuity rule update

The 2026-10-04 investment-core decisions above supersede any earlier project notes that implied:
- the company-side Model Router should automatically choose the authoritative Primary Model;
- current Batch-2 v0.1 already performs true market model identification;
- current Batch-2 expectation-gap, stability, or sizing outputs are production-grade.

Repository continuity artifacts are the authoritative persistent record for these decisions. Chat discussion alone is not authoritative.


## 15. Horizon semantics amendment — 2026-10-04

- Default Decision / Expected Return reference horizon is H=1Y.
- 3Y is an explicit exception only, requiring horizon_override=true and a qualifying basis: MAJOR_INDUSTRY_LEADER and/or MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX.
- Every case carries horizon_selection_rationale.
- Actual holding cycle remains 1–3Y; H is not a forced sell date.
- DCF explicit forecast length is independent of Decision H.
- CATL 2027–2029 / ~14.20% is a CATL-specific 3Y Expected Return Reference, not the system default.
- Shared semantic validator: iios_mvp/horizon_semantics.py.
- This amendment is cross-module and must be reconciled across B1, CORE-03, valuation semantics and the future Decision Kernel.

## 16. B2-A single-company Evidence/PIT foundation — 2026-10-05

- PR #32 Horizon Semantics merged to main as merge commit a524390382044b9474c17f2712a2cef8adeb9612.
- Horizon policy is H=1Y default; H=3 requires explicit override + qualifying basis; actual holding cycle remains 1–3Y.
- B2-A is now the active Investment Core evidence track: single user-selected A-share/HK company, not CSI800/universe dependent.
- B2-A introduces Company Evidence Manifest, raw-artifact exact-byte verifier, case-bound evidence, PIT known_at validation, required field-group coverage and immutable manifest hash.
- A02/CSI800 remains Research Track only and is not an Investment Core release gate.
- PR #33 is the current B2-A implementation PR; it must pass remote B2/test-mvp/scope checks before merge.
