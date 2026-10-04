# B0 REPAIR OVERRIDE — 2026-10-04

This file retains historical acceptance records below. For the active repair program, read `docs/iios/B0_AUTHORITY_AUDIT_FREEZE_2026-10-04.md` first.

Active repair baseline: `d209b33b7f922866f2fdc1190785c27edb8a28e4`
Active repair stage: **B0 PASS → B1 PASS → CORE-00 PASS → CORE-01 PASS → CORE-02 Company Economic Core PASS → CORE-03**
P4-F is merged historical/conditional infrastructure; P5/P6 feature expansion remains paused.
B1 semantic contract v0.3 is now frozen and its runtime migration is accepted. The owner-approved distinction between (a) 15% BUY-entry threshold / safety-margin policy and (b) 1–3Y annualized target >=15% is now normative in v0.3.

---

# IIOS Project Status — 2026-10-04

## Canonical State

Continuity / macro plan: `docs/iios/IIOS_PROJECT_CONTINUITY_AND_MACRO_PLAN_2026-10-04.md`

Consolidated post-red-team development plan: `docs/iios/IIOS_CONSOLIDATED_POST_REDTEAM_DEVELOPMENT_PLAN_2026-10-04.md`

- Current canonical `main` is the source of truth.
- State Reconciliation: COMPLETE.
- Investment Core Contract v0.2: **HISTORICAL / LEGACY**.
- Investment Core Contract v0.3: **FROZEN / B1 SEMANTIC PASS**.
- Contract: `docs/iios/IIOS_INVESTMENT_CORE_CONTRACT_v0.3.md`

## CORE-02 Active Boundary

- Current execution gate: **CORE-03 Market Expectation + Expectation Gap**
- CORE-02 is now PASS / MERGED on canonical `main`
- Input: admitted company-specific evidence + explicit evidence-linked economic assessments
- Output: PIT-bound Reality, Trust, Quality, Value Core, Value Driver Ranking and candidate valuation-model route
- Evidence must be ADMITTED, case-bound, exact-byte backed and `known_at <= cutoff`
- Trust / Quality fail closed; Value Core and drivers require evidence-domain binding
- A02 / CSI800 / CSI Industry remain Research Track only

## CORE-02 Completed Boundary

- CORE-02 is **PASS / MERGED** on canonical `main`.
- PR #29 / merge commit `2a1c376e2bf3c608ebdf88a95d8be5aeaf8580b9`.
- Dedicated CORE-02 CI: run #6 / `37209264413` — SUCCESS.
- CORE-02 regression: **30 passed**.
- Investment Core CI: run #214 / `37209264423` — SUCCESS.
- CORE-01 CI: run #10 / `37209264528` — SUCCESS.
- Evidence-domain and temporal-lineage red-team hardening was included before merge.
- CORE-02 does not perform forecast, MIE, Expectation Gap or decision execution.

## CORE-00 Completed Boundary

- Current execution gate: **CORE-00 Scope Reset & Architecture Reconciliation**
- Investment Core = **single-company case + per-case evidence/PIT + decision**
- A02 / CSI800 / CSI Industry / historical full-market universe = **Research Track only**
- A02 completion is **not** an Investment Core release gate
- Historical single-company cases still require defensible PIT `known_at` semantics
- P3/P4 MIE infrastructure is retained; under B1 v0.3 MIE is explanatory/non-mandatory for BUY/ADD

## CORE-01 Completed Boundary

- CORE-01 is **PASS / MERGED** on canonical `main`.
- Minimal input now creates a deterministic Research Case Envelope.
- Evidence/identity/price remain evidence-dependent and cannot be fabricated.
- PIT remains mandatory; historical current-state substitution is forbidden.

## Investment Decision Core

- Initial MVP Decision Vertical Slice: MERGED
- Batch 1-B Company Value Core: MERGED
- Human-authoritative Company Valuation Model Selection: MERGED
- Batch 2 Market Model Identification v0.1: OPEN / RED-TEAM BLOCKED / NOT CURRENT CAPABILITY
- Investment Core semantic contract v0.2: FROZEN / SEMANTIC PASS
- P2-A machine schema + executable invariants: **FINAL PASS / MERGED**
- P2-B Market Model Domain Foundation: **FINAL PASS / MERGED**
- P3-A ratio-family Market Model Identification: **FINAL PASS / MERGED**
- P3-B complex model-specific Market Model Identification baseline (DCF/DDM/SOTP/rNPV): **FINAL PASS / MERGED**
- P3 capability classification: **conditional / candidate-set-bound baseline; not proof of unconditional true-market-model identification**
- P4-A MIE Qualification Boundary: **FINAL PASS / MERGED**
- P4-B Ratio-family MIE Vertical Slice: **FINAL PASS / MERGED**
- P4-C DCF/DDM Conditional MIE Vertical Slice: **FINAL PASS / MERGED**
- P4-D SOTP/rNPV MIE Vertical Slice: **FINAL PASS / MERGED**
- P4-E Multi-model Market Implied Expectation Set: **FINAL PASS / MERGED**
- P4-F PIT / Replay / Fail-closed MIE Integration: **FINAL PASS / MERGED**
- B1 v0.3 return/decision runtime migration: **ACCEPTED / 190 TESTS PASS**
- Production investment decision kernel: NOT YET

## P4-C Final Acceptance

P4-C is formally **FINAL PASS / MERGED** on canonical `main`.

- PR #12: MERGED
- pre-merge HEAD: `620977682155f5f633f1dcd71ddbc6d71a2005e1`
- merge commit: `b6bfb8df10a8ffee5f01154fbe4b47201f6048fe`
- PR Investment Core CI #143 / `37189169223`: **SUCCESS**
- PR FM00 CI #115 / `37189169218`: **SUCCESS**
- post-merge main Investment Core CI #144 / `37189193858`: **SUCCESS**
- post-merge main FM00 CI #116 / `37189193862`: **SUCCESS**
- final regression: **128 passed**
- acceptance: `docs/iios/P4C_FINAL_ACCEPTANCE_2026-10-04.md`

Semantic boundary:

- DCF → conditional implied `fcf`;
- DDM → conditional implied `dividend`;
- explicit current conditioning/context inputs are provenance-bound;
- output remains `CONDITIONAL_IMPLIED_VARIABLE / CONDITIONAL_ONLY`;
- no full multidimensional feasible assumption-space claim;
- no market-truth claim.

Completed: P4-D. See P4-E acceptance below.

## P4-D Final Acceptance

P4-D is formally **FINAL PASS / MERGED** on canonical `main`.

- PR #13: MERGED
- pre-merge HEAD: `dd3e2cc775677b63ee1d48cdd15940b03af1f498`
- merge commit: `13729e7493850cb513843567dd5ee263c2301f36`
- PR Investment Core CI #147 / `37189771181`: **SUCCESS**
- PR FM00 CI #121 / `37189771200`: **SUCCESS**
- post-merge main Investment Core CI #148 / `37189797363`: **SUCCESS**
- post-merge main FM00 CI #122 / `37189797243`: **SUCCESS**
- final regression reported by CI: **139 passed**
- acceptance matrix: `docs/iios/P4D_SOTP_RNPV_MIE_ACCEPTANCE_MATRIX_v0.2.md`
- acceptance record: `docs/iios/P4D_FINAL_ACCEPTANCE_2026-10-04.md`

Semantic boundary:

- SOTP → implied `residual_value` conditional on explicit current segment-value construction;
- rNPV → one implied `pipeline_value` requirement per pipeline, derived from the accepted P3-B total using observed current pipeline-value composition;
- observed probability and timing remain conditioning inputs, never market-implied probabilities;
- multiple pipelines remain separately represented;
- all positive outputs remain `CONDITIONAL_IMPLIED_VARIABLE / CONDITIONAL_ONLY`;
- no generic implied net profit;
- no Expectation Gap / Expected Return implementation.

Completed: P4-E. See P4-F acceptance below.
## P4-E Final Acceptance

P4-E is formally **FINAL PASS / MERGED** on canonical `main`.

- PR #14: MERGED
- pre-merge HEAD: `60e40bed89f96bcc30df4a31967ff55d84847423`
- merge commit: `3c1b4944d715bbb0e4716bab3a0721c78f0f4157`
- PR Investment Core CI #155 / `37190663254`: **SUCCESS**
- PR FM00 CI #130 / `37190663258`: **SUCCESS**
- post-merge main Investment Core CI #157 / `37190695693`: **SUCCESS**
- post-merge main FM00 CI #132 / `37190695593`: **SUCCESS**
- final regression: **156 passed**
- acceptance matrix: `docs/iios/P4E_MULTI_MODEL_MIE_SET_ACCEPTANCE_MATRIX_v0.2.md`
- acceptance record: `docs/iios/P4E_FINAL_ACCEPTANCE_2026-10-04.md`

Semantic boundary:

- P4-E aggregates accepted P4-A through P4-D MIE outputs; it does not recompute inverse valuation.
- Every admitted candidate receives one explicit disposition: `MATERIALIZED`, `NO_FEASIBLE_SOLUTION`, or `BLOCKED`.
- Multiple materialized models remain `AMBIGUOUS / CONDITIONAL_ONLY`; no winner, ranking, weighting, averaging, or cross-model pseudo-variable is created.
- A unique model requires complete candidate coverage and explicit non-feasible dispositions for all alternatives.
- Any blocked candidate or insufficient candidate/evidence assessment fails closed to `INSUFFICIENT_EVIDENCE / BLOCKED`.
- Materialized expectations must share the exact same price/PIT observation basis.
- Evidence closure and deterministic model-evaluation ordering are enforced.
- No Expectation Gap, Expected Return, or generic `market_implied_net_profit` is introduced.

## P4-F Final Acceptance

P4-F is formally **FINAL PASS / MERGED** on canonical `main`.

- PR #16: MERGED
- pre-merge HEAD: `e498466549bc040085ddf46a2512a9208e3d7a12`
- merge commit: `9732f33d3b0163832d317661b8171046d93c6455`
- PR Investment Core CI #164 / `37192169418`: **SUCCESS**
- PR FM00 CI #141 / `37192169420`: **SUCCESS**
- post-merge main Investment Core CI #165 / `37192209207`: **SUCCESS**
- post-merge main FM00 CI #142 / `37192209217`: **SUCCESS**
- final regression: **171 passed**
- acceptance matrix: `docs/iios/P4F_PIT_REPLAY_FAILCLOSED_ACCEPTANCE_MATRIX_v0.2.md`
- acceptance record: `docs/iios/P4F_FINAL_ACCEPTANCE_2026-10-04.md`

Semantic boundary:

- Every evidence ID referenced by the P4-E set is bound to explicit provenance: variable, unit, basis, observation date, `known_at`, source, source location, content SHA-256 and capture timestamp.
- PIT requires `observation_date <= cutoff` and `known_at.date() <= cutoff`. Post-cutoff capture is allowed when the evidence was knowable before cutoff.
- Each materialized MIE price observation ID is explicitly bound to `market_price` provenance with matching date and currency/unit.
- All materialized MIEs in one snapshot must share the exact same observation basis and use the snapshot cutoff.
- Snapshot identity is protected by MIE-set hash, provenance hash and final snapshot hash; disk persistence is create-once.
- Replay independently validates integrity, PIT, provenance closure, price binding and P4-E resolution/qualification semantics and fails closed on any mismatch.
- P4-F does not implement Expectation Gap, Expected Return or the production v0.2 decision engine.

## B1 Return / Decision Semantics

- BUY Entry Return Cushion threshold: **15%**, non-annualized.
- Fundamental target: **1–3 year Expected Annualized Return >=15%** for standard fundamental BUY/ADD.
- Expected Total Return_H and Expected Annualized Return_H are derived from probability-weighted terminal wealth.
- Required Return is an independent annualized risk/opportunity-cost comparator.
- The two 15% policies and Required Return are conjunctive, not additive.
- Conventional Margin of Safety is distinct from the 15% return-form entry cushion.
- UNKNOWN never silently becomes HOLD; unresolved material uncertainty routes to REVIEW_REQUIRED.
- MIE is explanatory and non-mandatory for BUY/ADD in v0.3.

## P1 Contract Boundary

The frozen contract separates:

1. Company-side independent valuation.
2. Market-side model identification.
3. Model-specific Market Implied Expectation.
4. Semantic Expectation Gap.
5. Positive Expected Return >15%.
6. Trust / Thesis / Risk / Portfolio gates.
7. Human approval and no auto-execution.

## Forecast Research

- G2 Reference Governance Runtime: FROZEN
- FM-00: PASS
- FM-01 implementation foundation: PASS
- FM-01 CATL exact data ingress: BLOCKED_DATA_INGRESS
- FM-02: WAITING FOR EXACT SOURCE ADMISSION
- Production forecast router: FALSE

## P2-A Final Acceptance

P2-A is formally **FINAL PASS** on canonical `main`.

- PR #5: MERGED
- P2-A pre-merge HEAD: `ec208f347fde64b08694d181d8ee8cf2f433e7ed`
- CI run #70 / `37183859358`: **SUCCESS**
- merge commit: `203aed6ce22c5ed34dfa4aba4639de3dde0801b8`
- acceptance record: `docs/iios/P2A_FINAL_ACCEPTANCE_2026-10-04.md`

P2-A proves the machine-readable v0.2 Contract/invariants and legacy-isolation boundary. It does **not** make the v0.2 decision engine production-capable.

## P2-B Foundation Acceptance

P2-B Foundation is formally **FINAL PASS** on canonical `main`.

- PR #6: MERGED
- pre-merge HEAD: `5d2260264fe5769e69ea9ee47923b5514eba93b9`
- CI run #73 / `37184109345`: **SUCCESS**
- merge commit: `9ba4529edeacfc3bc0b818002f04badcd1834f0d`
- acceptance record: `docs/iios/P2B_FOUNDATION_ACCEPTANCE_2026-10-04.md`

The foundation defines the canonical MarketObservableEvidence / CandidateMarketModel / ModelFit / FeasibleSolutionSet / Identifiability / Stability domain boundary. It does not implement production model identification.

## P3-A Final Acceptance

P3-A is formally **FINAL PASS** on canonical `main`.

- PR #7: MERGED
- pre-merge HEAD: `fe03d27bdd4ac46125fff04c7d3405b8285d3139`
- CI run #96 / `37185092488`: **SUCCESS**
- CI: compileall + 68 tests + schema validation + existing MVP run/replay
- merge commit: `53bdde65c3bfa20d227d398259a2e0268bc4da5d`
- acceptance record: `docs/iios/P3A_RATIO_IDENTIFICATION_ACCEPTANCE_2026-10-04.md`

P3-A implements deterministic evidence-backed identification for forward PE, PS, PB and EV/EBITDA.

## P3-B Final Acceptance

P3-B is formally **FINAL PASS** on canonical `main`.

- PR #8: MERGED
- pre-merge HEAD: `ee295b59c4ce59110da6496991b51dee9ec487a5`
- CI run #112 / `37186090902`: **SUCCESS**
- CI: **80 tests passed** + compileall + schema validation + MVP run/replay
- merge commit: `77022db416f5b1d32c306f5d644e3642c0f5936b`
- acceptance record: `docs/iios/P3B_COMPLEX_IDENTIFICATION_ACCEPTANCE_2026-10-04.md`

P3-B implements model-specific evidence-backed identification for DCF, DDM, SOTP and rNPV, including model-specific inverse constraints, feasible solution sets, conservative identifiability, and historical date-level leave-one-out stability. It does not implement P4 or semantic Expectation Gap / return calculation.

## P4-B Final Acceptance

P4-B is formally **FINAL PASS** on canonical `main`.

- PR #11: MERGED
- P4-B merge commit: `741b3fc0bff3a8da5e993f1a0c0aec25cb823420`
- CI #131 / `37187856731`: **SUCCESS**
- CI #99 / `37187856715`: **SUCCESS**
- Post-merge main CI #133 / `37187900444`: **SUCCESS**
- Post-merge main FM00 CI #101 / `37187900457`: **SUCCESS**
- Final regression result: **114 passed**
- Acceptance record: `docs/iios/P4B_FINAL_ACCEPTANCE_2026-10-04.md`

P4-B materializes ratio-family P3 feasible ranges as P4-A model-semantic MIE outputs without recomputing the inverse or forcing ambiguous winners.

## P4-A Final Acceptance

P4-A is formally **FINAL PASS** on canonical `main`.

- PR #9 merge: `b347df63270b0389c8bfc531ed05eed5a14c843e`
- PR #9 CI #120 / `37187273721`: **SUCCESS**
- PR #10 merge: `ff46b1ed30e8521041d30eb5d1cebd2e4d6ccad0`
- PR #10 CI #125 / `37187410083`: **SUCCESS**
- Final P4-A test result: **101 passed**
- Post-merge main CI #126 / `37187434857`: **SUCCESS**
- Acceptance record: `docs/iios/P4A_FINAL_ACCEPTANCE_2026-10-04.md`

P4-A establishes the typed qualification boundary between P3 inverse interpretations and decision-grade Market Implied Expectation.

## B1 Acceptance

B1 semantic package and runtime migration accepted on the repair line. Evidence: `docs/iios/B1_CODE_MIGRATION_ACCEPTANCE_2026-10-04.md`; code red-team: `docs/iios/B1_CODE_MIGRATION_REDTEAM_v0.3.md`.

## Immediate Next Engineering Step

**CORE-03 — Market Expectation + Expectation Gap.**

CORE-02 is complete and canonical. CORE-03 must consume the admitted economic core, independent forecast and existing P4-F MIE set without bypassing PIT/provenance/replay.

CORE-00 and CORE-01 are merged and accepted on canonical `main`. The next Investment Core gate is CORE-02: admitted company evidence → Reality → Trust → Quality → Value Core → valuation-model route input.

P4-A through P4-F are complete. P5 must compare economically equivalent independent variables against the P4 model-semantic market requirement, fail closed on incompatible or ambiguous interpretations, validate Bear/Base/Bull probabilities, and enforce strict positive Expected Return >15% before any decision layer.

P4-E must consume the accepted P4-A through P4-D typed outputs and organize multiple feasible/conditional market-model explanations without forcing a winner.

The expectation set must retain:

- model identity and qualification;
- model-native economic variables;
- conditional assumptions/context;
- candidate coverage;
- evidence sufficiency;
- identifiability and stability;
- PIT/provenance.

Do not calculate Expectation Gap or Expected Return until P4-F closes PIT/replay/fail-closed integration.

P2-C Company Value Core hardening remains parallel where needed for real-company acceptance.

Do not resume or merge the blocked Batch 2 v0.1 PR #3.
