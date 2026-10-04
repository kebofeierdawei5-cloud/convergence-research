# B0 REPAIR OVERRIDE — 2026-10-04

Active repair baseline: `d209b33b7f922866f2fdc1190785c27edb8a28e4`
Active stage: **B0 PASS → B1 PASS → B2 Data/Evidence/PIT Foundation**

This index retains the incumbent v0.2 and P4 acceptance records below for historical continuity. They do not override the B0 authority freeze. The incumbent return statement and P5 next-step text are superseded as the active repair target until B1 is approved.

B1 v0.3 is now the active frozen Investment Core semantic contract. It separately defines BUY-entry threshold/safety cushion, 1–3Y annualized target, Expected Return, Required Return, Horizon, action semantics, Unknown/Trust/Investability/Portfolio boundaries and non-mandatory MIE.

---

# IIOS Current-State Index

Continuity / macro development plan: `docs/iios/IIOS_PROJECT_CONTINUITY_AND_MACRO_PLAN_2026-10-04.md`

Consolidated post-red-team execution plan: `docs/iios/IIOS_CONSOLIDATED_POST_REDTEAM_DEVELOPMENT_PLAN_2026-10-04.md`

Snapshot: 2026-10-04

## Canonical State

Current canonical state is defined by:

- current Git `main`
- `docs/iios/STATE_RECONCILIATION_2026-10-04.md`
- `docs/iios/IIOS_INVESTMENT_CORE_CONTRACT_v0.2.md`
- this index
- `STATUS.md`

## Investment Core

Semantic contract:

`docs/iios/IIOS_INVESTMENT_CORE_CONTRACT_v0.3.md`

Status: **FROZEN / B1 SEMANTIC PASS**

Core chain:

```
Company / Industry Reality
        ↓
Company Value Core
        ↓
Human Primary Valuation Model
        ↓
Independent Forecast / Intrinsic Value
        +
Market Observable Evidence + Price
        ↓
Candidate Market Models
        ↓
Feasible Solution Set
        ↓
Identifiability + Stability
        ↓
Market Implied Expectation
        ↓
Semantic Expectation Gap
        ↓
Positive Expected Return >15%
        ↓
Trust / Thesis / Risk / Portfolio
        ↓
AI Proposal → Human Approval
```

## Current Capability Boundary

Implemented / merged:

- PIT / Trust / fail-closed foundation
- Snapshot hash / Replay
- Decision Series / Revision / Human Approval skeleton
- Company Value Core structured scan
- Candidate valuation model generation
- Human-authoritative Primary Model selection
- deterministic valuation calculators for supported models
- P2-A Investment Core v0.2 machine schema + executable invariants (FINAL PASS / MERGED)
- P2-B Market Model Domain Foundation (FINAL PASS / MERGED)
- P3-A ratio-family Market Model Identification baseline (FINAL PASS / MERGED)
- P3-B complex-model Market Model Identification baseline (FINAL PASS / MERGED)
- P4-A Market Implied Expectation Qualification Boundary (FINAL PASS / MERGED)
- P4-B Ratio-family Market Implied Expectation Vertical Slice (FINAL PASS / MERGED)
- P4-C DCF/DDM Conditional Market Implied Expectation Vertical Slice (FINAL PASS / MERGED)
- P4-D SOTP/rNPV Market Implied Expectation Vertical Slice (FINAL PASS / MERGED)
- P4-E Multi-model Market Implied Expectation Set (FINAL PASS / MERGED)
- P4-F PIT / Replay / Fail-closed MIE Integration (FINAL PASS / MERGED)

P2-A acceptance evidence:

- PR #5 merged to main
- pre-merge HEAD `ec208f347fde64b08694d181d8ee8cf2f433e7ed`
- CI #70 / `37183859358` = SUCCESS
- final acceptance: `docs/iios/P2A_FINAL_ACCEPTANCE_2026-10-04.md`

B1 implemented/accepted:

- v0.3 return semantics runtime
- v0.3 decision actions and Unknown/Trust/Investability/Portfolio behavior
- deterministic snapshot/replay routing

Not yet implemented as production capability:

- complete company Reality/Quality/Value Core economic chain
- full independent forecast contract
- frozen probability / edge / position-sizing policy
- complete Execution Receipt / Trigger lifecycle
- real-company acceptance / independent audit

Batch 2 v0.1 PR #3 remains OPEN / RED-TEAM BLOCKED / NOT MERGED and must not be extended as the next production layer.

P2-B foundation evidence:

- PR #6 merged to main
- pre-merge HEAD `5d2260264fe5769e69ea9ee47923b5514eba93b9`
- CI #73 / `37184109345` = SUCCESS
- final acceptance: `docs/iios/P2B_FOUNDATION_ACCEPTANCE_2026-10-04.md`

P3-A evidence:

- PR #7 merged to main
- pre-merge HEAD `fe03d27bdd4ac46125fff04c7d3405b8285d3139`
- CI #96 / `37185092488` = SUCCESS
- final acceptance: `docs/iios/P3A_RATIO_IDENTIFICATION_ACCEPTANCE_2026-10-04.md`

P3-B evidence:

- PR #8 merged to main
- pre-merge HEAD `ee295b59c4ce59110da6496991b51dee9ec487a5`
- CI #112 / `37186090902` = SUCCESS
- 80 tests passed + compileall + schema + MVP run/replay
- merge commit `77022db416f5b1d32c306f5d644e3642c0f5936b`
- final acceptance: `docs/iios/P3B_COMPLEX_IDENTIFICATION_ACCEPTANCE_2026-10-04.md`

P4-F remains retained as historical/conditional MIE infrastructure. It is not the active repair gate.

P4-A acceptance: `docs/iios/P4A_FINAL_ACCEPTANCE_2026-10-04.md`
P4-B acceptance: `docs/iios/P4B_FINAL_ACCEPTANCE_2026-10-04.md`

## P4-C Acceptance Evidence

P4-C is **FINAL PASS / MERGED**.

- PR #12
- pre-merge HEAD: `620977682155f5f633f1dcd71ddbc6d71a2005e1`
- merge commit: `b6bfb8df10a8ffee5f01154fbe4b47201f6048fe`
- PR CI #143 / `37189169223`: SUCCESS
- post-merge main Investment Core CI #144 / `37189193858`: SUCCESS
- post-merge main FM00 #116 / `37189193862`: SUCCESS
- final regression: 128 passed
- acceptance: `docs/iios/P4C_FINAL_ACCEPTANCE_2026-10-04.md`

P4-C keeps DCF/DDM conditional outputs as `CONDITIONAL_IMPLIED_VARIABLE / CONDITIONAL_ONLY`; it does not claim a full multidimensional feasible assumption space or market truth.

Completed: **P4-D — SOTP / rNPV expectation extraction**.

## P4-D Acceptance Evidence

P4-D is **FINAL PASS / MERGED**.

- PR #13
- pre-merge HEAD `dd3e2cc775677b63ee1d48cdd15940b03af1f498`
- merge commit `13729e7493850cb513843567dd5ee263c2301f36`
- PR CI #147 / `37189771181`: SUCCESS
- post-merge main Investment Core CI #148 / `37189797363`: SUCCESS
- post-merge main FM00 #122 / `37189797243`: SUCCESS
- final regression: 139 passed

P4-D keeps SOTP residual and rNPV pipeline requirements model-native and conditional. rNPV probability/timing are conditioning inputs only; no market-implied probability is emitted.

Completed: **P4-E — multi-model expectation-set handling**. Completed: **P4-F — PIT / replay / fail-closed MIE integration**. Next: **B2 — Data / Evidence / PIT Foundation**.
## P4-E Acceptance Evidence

P4-E is **FINAL PASS / MERGED**.

- PR #14
- pre-merge HEAD `60e40bed89f96bcc30df4a31967ff55d84847423`
- merge commit `3c1b4944d715bbb0e4716bab3a0721c78f0f4157`
- PR Investment Core CI #155 / `37190663254`: SUCCESS
- PR FM00 CI #130 / `37190663258`: SUCCESS
- post-merge main Investment Core CI #157 / `37190695693`: SUCCESS
- post-merge main FM00 #132 / `37190695593`: SUCCESS
- final regression: 156 passed

P4-E provides a candidate-complete typed expectation set over accepted P4-A through P4-D outputs. It preserves model identity and model-native economic variables, distinguishes `NO_FEASIBLE_SOLUTION` from `BLOCKED`, marks multiple surviving models as `AMBIGUOUS / CONDITIONAL_ONLY`, prevents unique claims under incomplete coverage, enforces exact observation-basis consistency and evidence closure, and performs no model selection, Expectation Gap, or Expected Return calculation.

B1 complete. Next: **B2 — Data / Evidence / PIT Foundation**.

## P4-F Acceptance Evidence

P4-F is **FINAL PASS / MERGED**.

- PR #16
- pre-merge HEAD `e498466549bc040085ddf46a2512a9208e3d7a12`
- merge commit `9732f33d3b0163832d317661b8171046d93c6455`
- PR Investment Core CI #164 / `37192169418`: SUCCESS
- PR FM00 CI #141 / `37192169420`: SUCCESS
- post-merge main Investment Core CI #165 / `37192209207`: SUCCESS
- post-merge main FM00 CI #142 / `37192209217`: SUCCESS
- final regression: 171 passed

P4-F closes the PIT/provenance and immutable replay boundary around the P4-A through P4-E Market Implied Expectation path. It does not make the production v0.2 decision engine runnable and does not calculate Expectation Gap or Expected Return.

Next: **P5 — Semantic Expectation Gap + Return Gate**.

## B1 Return / Decision Semantics

The frozen v0.3 contract defines two separate 15% policies: a non-annualized 15% BUY-entry return cushion and a 15% 1–3Y annualized fundamental target. Required Return is independent and non-additive. UNKNOWN routes to REVIEW_REQUIRED, and MIE is non-mandatory for BUY/ADD.

## Forecast Research

- FM-00 = PASS
- FM-01 implementation foundation = PASS
- FM-01 CATL exact source ingress = BLOCKED pending exact source snapshot
- FM-02 waits for exact source admission

## Authority Precedence

1. Frozen governance artifacts and accepted evidence chains.
2. Current canonical Git repository state.
3. Independent CI / execution evidence.
4. Historical audit records as point-in-time records.
5. Chat context.
