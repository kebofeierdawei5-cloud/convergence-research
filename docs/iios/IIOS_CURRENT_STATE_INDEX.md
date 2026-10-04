# IIOS Current-State Index

Continuity / macro development plan: `docs/iios/IIOS_PROJECT_CONTINUITY_AND_MACRO_PLAN_2026-10-04.md`

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

`docs/iios/IIOS_INVESTMENT_CORE_CONTRACT_v0.2.md`

Status: **FROZEN / SEMANTIC PASS**

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
- P3-A ratio-family Market Model Identification (FINAL PASS / MERGED)

P2-A acceptance evidence:

- PR #5 merged to main
- pre-merge HEAD `ec208f347fde64b08694d181d8ee8cf2f433e7ed`
- CI #70 / `37183859358` = SUCCESS
- final acceptance: `docs/iios/P2A_FINAL_ACCEPTANCE_2026-10-04.md`

Not yet implemented as production capability:

- complex-model evidence-backed market-model identification (DCF/DDM/SOTP/rNPV)
- broader/calibrated Market Model Identification beyond the P3-A ratio-family baseline
- meaningful Feasible Solution Set
- calibrated Identifiability
- temporal / regime Stability
- model-specific Market Implied Expectation
- semantic Expectation Gap
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

P4 is now the next engineering gate: Market Implied Expectation Engine.

## Return Target

**Positive expected return >15%.**

No fixed 1–3 year holding period and no annualized-return core gate.

For the primary Expected Return Gate, validated Bear/Base/Bull probabilities are required. No fabricated probability fallback is permitted.

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
