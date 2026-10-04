# IIOS Project Continuity & Macro Development Plan — 2026-10-04

## 0. Purpose

This document is the canonical continuity summary for the IIOS development effort as of 2026-10-04.

It consolidates the durable conclusions from the recent engineering/red-team rounds so future work can resume from the validated state without reconstructing context from chat history.

Canonical source of truth:

- Git `main`
- frozen governance/contract documents
- accepted CI evidence
- this continuity record
- current-state index / status documents

Historical commits and acceptance records remain immutable evidence.

---

## 0A. Current execution scope after second red-team

The immediate Investment Core path is now governed by CORE-00:

```
CORE-00 Scope Reset
    ↓
CORE-01 Single Company Research Intake
    ↓
CORE-02 Company Economic Core
    ↓
CORE-03 Market Expectation + Expectation Gap
    ↓
CORE-04 Decision Kernel
    ↓
CORE-05 Immutable Decision / Replay / Real Case
```

A02 / CSI800 / CSI Industry historical-universe work is a separate Research Track.

The distinction is:

```
Research Track
  └─ cross-company universe / forecast research

Investment Core
  └─ one user-selected company + per-case PIT evidence + decision
```

Removing the universe dependency does not remove PIT. Historical single-company cases still require defensible `known_at <= cutoff` evidence.

P3/P4 Market Implied Expectation infrastructure remains part of the Investment Core capability surface, but B1 v0.3 continues to make MIE explanatory/non-mandatory for BUY/ADD.

## 1. IIOS North Star

IIOS is not primarily an equity research report generator.

It is a personal investment decision operating system that connects:

```
Company / Industry Reality
        ↓
Company Value Core
        ↓
Human Primary Valuation Model
        ↓
Independent Forecast
        ↓
Independent Intrinsic Value
        +
Market Observable Evidence + Price
        ↓
Candidate Market Models
        ↓
Historical / Current Fit
        ↓
Feasible Solution Set
        ↓
Identifiability
        ↓
Stability
        ↓
Market Implied Expectation
        ↓
Semantic Expectation Gap
        ↓
Probability-weighted Expected Return
        ↓
Expected Return > 15%
        ↓
Trust / Thesis / Risk / Portfolio
        ↓
AI Action Proposal
        ↓
Human Approval
        ↓
Execution / Monitoring / Revision
```

Core philosophy remains:

- fundamental reality first;
- market expectation is inferred, not assumed;
- company-side valuation and market-side pricing model are separate questions;
- economic variables must never be silently substituted;
- unresolved evidence must fail closed;
- human retains final valuation-model authority and execution authority.

Canonical return hurdle:

**positive expected return >15%**

No mandatory 1–3 year holding period and no annualized-return core hurdle.

---

## 2. Hard-Frozen Decisions

### 2.1 Investment Core Contract v0.2

Status: **FROZEN / SEMANTIC PASS**

The frozen contract establishes:

- PIT evidence semantics;
- Trust Gate precedence;
- human-authoritative company valuation model;
- market-model candidate / fit / feasible-solution semantics;
- Identifiability states;
- Stability states;
- model-specific Market Implied Expectation;
- semantic Expectation Gap;
- probability-weighted Expected Return;
- strict >15% hurdle;
- decision actions;
- human / AI boundary;
- replay / version semantics;
- fail-closed rules.

### 2.2 Batch 2 v0.1

PR #3 is:

**OPEN / RED-TEAM BLOCKED / NOT MERGED**

It is not a current production capability and must not be extended as the next implementation path.

Any retained low-level primitive may only be reused after semantic review and isolation under the frozen v0.2 contract.

### 2.3 Forecast Research Track

M1.2 Forecast Model Selection is a separate engineering/research track.

Current relevant status:

- FM-00 = PASS;
- FM-01 implementation foundation = PASS;
- CATL exact source ingress = BLOCKED_DATA_INGRESS;
- FM-02 waits for exact source admission.

Do not use forecast research to mask missing investment-core semantics.

---

## 3. What Has Been Completed and Accepted

### P0 — State Reconciliation

**COMPLETE**

Established canonical main, reconciled historical work, corrected return-hurdle semantics, separated investment core from forecast research, and explicitly quarantined blocked PR #3.

### P1 — Investment Core Contract v0.2

**COMPLETE / FROZEN / SEMANTIC PASS**

### P2-A — Machine Contract / Invariants

**FINAL PASS / MERGED**

Evidence:

- PR #5
- pre-merge HEAD: `ec208f347fde64b08694d181d8ee8cf2f433e7ed`
- CI #70: `37183859358`
- merge: `203aed6ce22c5ed34dfa4aba4639de3dde0801b8`

Key result: v0.2 semantics are executable and legacy decision-path bypass is fail-closed.

### P2-B — Typed Market Model Domain

**FINAL PASS / MERGED**

Evidence:

- PR #6
- pre-merge HEAD: `5d2260264fe5769e69ea9ee47923b5514eba93b9`
- CI #73: `37184109345`
- merge: `9ba4529edeacfc3bc0b818002f04badcd1834f0d`

Canonical typed objects include:

- MarketObservableEvidence
- CandidateMarketModel
- FitDiagnostic
- ModelFit
- FeasibleSolution
- FeasibleSolutionSet
- IdentifiabilityResult
- StabilityObservation
- StabilityResult

Supported model families:

- forward PE
- PS
- PB
- EV/EBITDA
- DCF
- DDM
- SOTP
- rNPV

### P3-A — Ratio-family Market Model Identification

**FINAL PASS / MERGED**

Evidence:

- PR #7
- pre-merge HEAD: `fe03d27bdd4ac46125fff04c7d3405b8285d3139`
- CI #96: `37185092488`
- merge: `53bdde65c3bfa20d227d398259a2e0268bc4da5d`

Implemented:

- evidence-backed PE / PS / PB / EV-EBITDA fitting;
- historical/current fit;
- model-specific feasible solution range;
- conservative identifiability;
- leave-one-out stability;
- fail-closed ambiguity / insufficiency handling.

Important limit:

P3-A is a deterministic baseline based on observed historical multiple ranges. It is not a calibrated statistical classifier of investor pricing behavior.

### P3-B — Complex Model-Specific Market Model Identification

**FINAL PASS / MERGED**

Evidence:

- PR #8
- pre-merge HEAD: `ee295b59c4ce59110da6496991b51dee9ec487a5`
- CI #112: `37186090902`
- merge: `77022db416f5b1d32c306f5d644e3642c0f5936b`
- final acceptance: `docs/iios/P3B_COMPLEX_IDENTIFICATION_ACCEPTANCE_2026-10-04.md`

Implemented baselines:

- DCF: one-stage FCFF perpetuity inverse → implied FCF;
- DDM: Gordon-growth inverse → implied dividend;
- SOTP: segment construction → implied residual value;
- rNPV: probability/timing pipeline composition → implied pipeline value.

Critical red-team conclusions preserved:

1. Complex-model observations must be isolated by candidate family.
2. Same-date market context must be internally consistent.
3. rNPV multi-pipeline inversion must preserve observed composition; probability-weight sum alone is not sufficient.
4. Complex-model stability perturbation unit is a complete historical date, not an individual variable row.
5. Observation evidence is bound to economic variable and unit.
6. Model identification remains conservative and fail-closed.
7. A passing inverse does not prove the market actually uses that model.

Post-merge canonical main CI remained green.

---

## 4. Current Capability Boundary

### Implemented

- evidence/PIT validation foundation;
- Trust / fail-closed framework;
- snapshot / replay foundation;
- structured Company Value Core;
- human-authoritative company valuation model selection;
- deterministic intrinsic valuation foundation;
- P2-A executable contract;
- P2-B typed market-model domain;
- P3-A ratio-model identification;
- P3-B complex-model identification.

### Not yet production-capable

- model-specific Market Implied Expectation engine;
- semantic Expectation Gap;
- primary Expected Return >15% decision gate connected to market-implied expectations;
- production-grade decision engine;
- complete execution receipt / trigger / revision lifecycle;
- real-company end-to-end acceptance;
- independent audit.

### Important technical limitation

P3-A/P3-B are deterministic identification baselines, not proof of actual investor behavior.

Current candidate completeness is caller-supplied.

P3 IDENTIFIABLE is therefore candidate-set-conditional. It must not be represented as proof that the market's true pricing model has been identified.

No MIE can be treated as decision-grade unless:

- candidate coverage is sufficient for the decision context;
- evidence materially distinguishes alternatives;
- interpretation is stable;
- provenance and PIT are valid;
- conditional inverse results are explicitly labeled as conditional.

---

## 5. The Macro Architecture Going Forward

The project should now stop growing sideways and complete the vertical decision chain.

Three workstreams should run with explicit boundaries:

### Workstream A — Investment Core Completion

```
P4 Market Implied Expectation
        ↓
P5 Semantic Expectation Gap + Return Gate
        ↓
P6 Decision Engine
        ↓
P7 Execution / Revision / Monitoring
```

This is the critical path to a usable investment operating system.

### Workstream B — Data / Evidence Capability

```
Public / Free Source Inventory
        ↓
Source-specific adapters
        ↓
PIT normalization
        ↓
Evidence manifests
        ↓
Conflict / stale-data detection
        ↓
Replayable case snapshots
```

This is a first-class dependency because the user is a personal investor without paid broker/commercial data.

The system must prefer:

1. exchange / company filings;
2. official public databases;
3. reproducible public endpoints / APIs;
4. media only as lower-tier evidence.

Never silently substitute inaccessible commercial data with invented values.

### Workstream C — Real Company Acceptance

Use materially different real companies to prevent overfitting to synthetic fixtures.

Minimum acceptance set:

- CATL;
- 科伦药业.

The cases should exercise different economics and valuation paths.

---

## 6. Detailed Macro Roadmap

### P4 — Market Implied Expectation Engine

**COMPLETE / P4-A COMPLETE / P4-B COMPLETE / P4-C COMPLETE / P4-D COMPLETE / P4-E COMPLETE / P4-F COMPLETE**

Purpose:

Convert validated market-model interpretations into the economic requirements implied by the current price.

Recommended sequence:

```
P4-A
Market Implied Expectation qualification contract — FINAL PASS
        ↓
P4-B
Ratio-family MIE vertical slice — FINAL PASS
        ↓
P4-C
DCF / DDM conditional MIE — FINAL PASS
        ↓
P4-D
SOTP / rNPV expectation extraction — FINAL PASS
        ↓
P4-E
Multi-model expectation-set handling
        ↓
P4-F
PIT / replay / fail-closed integration
```

Core semantic rule:

- ratio families preserve their native economic variables;
- DCF/DDM conditional inverses remain explicitly conditional;
- SOTP/rNPV must preserve segment/residual or pipeline/probability/timing semantics;
- generic `market_implied_net_profit` remains forbidden.

### P4-C Completion

**FINAL PASS / MERGED**

P4-C completed the DCF/DDM conditional MIE vertical slice on 2026-10-04.

Semantic red line:

`conditional inverse ≠ full feasible assumption space ≠ market truth`.

DCF emits conditional implied `fcf`; DDM emits conditional implied `dividend`. The remaining model variables are explicit current conditioning/context inputs, not separately asserted market-implied outputs. All positive outputs remain `CONDITIONAL_IMPLIED_VARIABLE / CONDITIONAL_ONLY`.

Evidence:

- PR #12;
- merge `b6bfb8df10a8ffee5f01154fbe4b47201f6048fe`;
- pre-merge HEAD `620977682155f5f633f1dcd71ddbc6d71a2005e1`;
- PR CI #143 / `37189169223`: SUCCESS;
- post-merge main Investment Core CI #144 / `37189193858`: SUCCESS;
- post-merge main FM00 #116 / `37189193862`: SUCCESS;
- final regression: 128 passed.

Completed: **P4-D — SOTP / rNPV expectation extraction**.

### P4-D Completion

**FINAL PASS / MERGED**

P4-D completed the SOTP/rNPV Market Implied Expectation vertical slice on 2026-10-04.

- PR #13
- merge: `13729e7493850cb513843567dd5ee263c2301f36`
- pre-merge HEAD: `dd3e2cc775677b63ee1d48cdd15940b03af1f498`
- PR Investment Core CI #147 / `37189771181`: SUCCESS
- post-merge main Investment Core CI #148 / `37189797363`: SUCCESS
- post-merge main FM00 #122 / `37189797243`: SUCCESS
- final regression: 139 passed.

Semantic red lines:

- SOTP segment values are conditioning inputs; residual value is the conditional market requirement.
- rNPV probability and timing are conditioning inputs, not market-implied probabilities.
- rNPV pipeline requirements remain pipeline-specific.
- no generic implied net profit.
- no decision-grade promotion through P4-D.

Completed: **P4-E — multi-model expectation-set handling**. Completed: **P4-F — PIT / replay / fail-closed MIE integration**. Next gate: **P5 — Semantic Expectation Gap + Return Gate**.

### P4-E Completion

**FINAL PASS / MERGED**

P4-E completed the multi-model Market Implied Expectation Set + ambiguity-handling boundary on 2026-10-04.

Evidence:

- PR #14
- pre-merge HEAD: `60e40bed89f96bcc30df4a31967ff55d84847423`
- merge commit: `3c1b4944d715bbb0e4716bab3a0721c78f0f4157`
- PR Investment Core CI #155 / `37190663254`: SUCCESS
- PR FM00 CI #130 / `37190663258`: SUCCESS
- post-merge main Investment Core CI #157 / `37190695693`: SUCCESS
- post-merge main FM00 #132 / `37190695593`: SUCCESS
- final regression: 156 passed

Semantic boundary:

- P4-E is an organization/qualification layer over accepted P4-A through P4-D typed MIE outputs; it does not recompute inverse valuation.
- Every admitted candidate model gets exactly one explicit evaluation disposition.
- `NO_FEASIBLE_SOLUTION` is distinct from `BLOCKED`, preventing an unevaluated candidate from masquerading as evidence for a unique model.
- Two or more materialized models remain `AMBIGUOUS / CONDITIONAL_ONLY`; there is no winner, ranking, weighting, averaging, or cross-model pseudo-variable.
- Any blocked candidate or insufficient candidate/evidence assessment fails closed.
- All materialized MIEs share one exact price/PIT observation basis.
- Set-level evidence closure and deterministic canonical model ordering are enforced.
- No Expectation Gap / Expected Return implementation is introduced.

Next gate: **P4-F — PIT / replay / fail-closed MIE integration**.

### P4-F Completion

**FINAL PASS / MERGED**

P4-F completed the PIT / provenance / immutable snapshot / replay / fail-closed boundary for the P4-A through P4-E Market Implied Expectation chain on 2026-10-04.

Evidence:

- PR #16
- pre-merge HEAD `e498466549bc040085ddf46a2512a9208e3d7a12`
- merge commit `9732f33d3b0163832d317661b8171046d93c6455`
- PR Investment Core CI #164 / `37192169418`: SUCCESS
- PR FM00 CI #141 / `37192169420`: SUCCESS
- post-merge main Investment Core CI #165 / `37192209207`: SUCCESS
- post-merge main FM00 #142 / `37192209217`: SUCCESS
- final regression: 171 passed

Semantic boundary:

- every P4-E evidence ID is bound to explicit source provenance;
- PIT is defined by observation date and `known_at` relative to cutoff;
- snapshot is hash-addressed and immutable on disk;
- replay revalidates snapshot integrity and P4-E semantics rather than trusting stored qualification;
- any missing/stale/inconsistent provenance fails closed;
- P4-F remains separate from the production v0.2 decision engine.

Next gate: **P5 — Semantic Expectation Gap + Return Gate**.

### P5 — Semantic Expectation Gap + Return Gate

**Immediately after P4**

Pipeline:

```
Independent Forecast / Intrinsic Value
        +
Market Implied Expectation
        ↓
Semantic compatibility gate
        ↓
Expectation Gap
        ↓
Scenario probability validation
        ↓
Probability-weighted Expected Return
        ↓
STRICT >15% gate
```

Critical red-team requirements:

- economically equivalent variables only;
- explicit units and basis;
- no gap calculation when model semantics are incompatible;
- no forced choice under materially ambiguous market interpretation;
- no fabricated probabilities;
- exactly 15% fails.

At this stage the system should finally be able to answer the real IIOS question:

> “What does the current market price require, and does my independently supported view exceed that requirement by enough to clear the >15% hurdle?”

### P6 — Production Decision Engine

The current decision engine is only partial.

Rebuild the v0.2 decision path around:

```
Trust
+ PIT
+ Thesis
+ Independent Value
+ Market Model Identifiability
+ Stability
+ Market Implied Expectation
+ Expectation Gap
+ Expected Return >15%
+ Risk
+ Portfolio Constraints
        ↓
BUY / ADD / HOLD / REDUCE / EXIT / NO-BUY
```

Priority ordering remains:

**Trust Gate > Portfolio Constraint > Long-term Value > Expectation Gap > Tactical Market / Positioning**

Human approval remains mandatory.

No automatic order placement.

### P7 — Monitoring / Revision / Execution Receipt

Complete the audit lifecycle:

```
Research Run
 ↓
Immutable Snapshot
 ↓
Decision Revision
 ↓
Human Approval
 ↓
Execution Receipt
 ↓
Monitoring
 ↓
Trigger
 ↓
New Run
 ↓
New Revision
```

The purpose is not operational complexity; it is preventing thesis drift and allowing post-mortem validation.

### P8 — Real Company Acceptance

Do not call the system production-capable before real cases pass.

Acceptance should cover at minimum:

- full PIT evidence;
- company reality;
- Value Core;
- human valuation model selection;
- independent forecast;
- intrinsic value;
- market model identification;
- market implied expectations;
- expectation gap;
- >15% return gate;
- risk / portfolio;
- human approval;
- replay.

CATL and 科伦药业 should deliberately stress different model semantics.

### P9 — Independent Audit

The final audit should test:

- semantic correctness;
- evidence provenance;
- PIT;
- model identification;
- feasible-solution semantics;
- identifiability;
- stability;
- Market Implied Expectation;
- Expectation Gap;
- return gate;
- Trust boundary;
- decision gate;
- human authority;
- snapshot/replay;
- fail-closed behavior.

---

## 7. Recommended Parallel Data Plan

Because data availability is likely to become the practical bottleneck before code complexity does, data work should proceed in parallel rather than waiting until the end.

### Tier A — Free / Primary

- SSE / SZSE / HKEX;
- company annual / interim / quarterly reports;
- company investor-relations disclosures;
- official industry / government databases;
- CSRC / exchange notices where relevant.

### Tier B — Reproducible Public Data

- public APIs / datasets with stable provenance;
- source-vintage metadata;
- explicit capture date and publication date.

### Tier C — Secondary Evidence

- reputable media;
- research commentary.

Tier C can support context, but should not silently override primary evidence for key accounting / valuation variables.

Every material variable entering a real decision should carry:

- source;
- source location;
- observation date;
- known_at;
- unit;
- accounting / adjustment basis;
- evidence ID;
- snapshot / version linkage.

---

## 8. Engineering Rules Carried Forward

The following rules should be treated as default project constraints:

### Rule 1 — Exact bytes first

For frozen artifacts / evidence packages:

**exact bytes → hash → provenance → PASS**

Never accept self-declared identity as final proof.

### Rule 2 — Contract before implementation

Do not implement around an ambiguous semantic contract.

### Rule 3 — No domain redesign without demonstrated need

P3-B succeeded without reopening the P2-B typed domain.

Future additions should likewise be justified by a concrete semantic or implementation gap.

### Rule 4 — Fail closed

Missing, stale, conflicting, unverifiable or semantically incompatible evidence blocks positive inference.

### Rule 5 — Inverse solvability is not market-model identification

A model that can algebraically reproduce price is only a candidate explanation.

### Rule 6 — Do not collapse economic variables

Revenue, EBITDA, EPS, FCF, dividend, book equity, residual value and pipeline value are different economic objects.

### Rule 7 — Stability must perturb the right unit

For multi-variable model observations, perturb a complete coherent historical unit.

### Rule 8 — Synthetic tests are necessary but insufficient

Passing fixtures proves implementation semantics, not real-market validity.

### Rule 9 — Build the vertical chain before adding breadth

Finish P4 → P5 → P6 before expanding into broad screening, advanced portfolio optimization or auto-trading.

### Rule 10 — Human authority is retained

AI/deterministic system computes and proposes.

Human decides / approves / executes.

---

## 9. What Should Not Be Done Next

Do not:

- revive or extend PR #3;
- jump to broad stock screening;
- build auto-trading;
- freeze Kelly / sizing formulas before empirical validation;
- build unnecessary distributed infrastructure;
- fabricate historical market-model datasets;
- treat P3-A/P3-B as a calibrated universal classifier;
- add model-specific shortcuts that bypass Market Implied Expectation semantics;
- use commercial-data assumptions that the user cannot reproduce.

---

## 10. Strategic End State

The correct development endpoint is not “all modules are implemented”.

It is:

```
A real company
   ↓
evidence-backed reality
   ↓
independent value thesis
   ↓
human-authoritative valuation model
   ↓
independent forecast
   ↓
market price
   ↓
evidence-backed candidate market models
   ↓
identified / ambiguous / unstable interpretation
   ↓
model-semantic Market Implied Expectation
   ↓
semantic Expectation Gap
   ↓
Expected Return >15%
   ↓
Trust / Risk / Portfolio
   ↓
explainable decision
   ↓
human approval
   ↓
execution
   ↓
monitoring
   ↓
validation / post-mortem
```

The system is successful when the full chain is repeatable, auditable, and useful for actual investment decisions—not when individual module test counts are high.

---

## 11. Current Next Step

**P4-E is the next implementation gate.**

Implement the smallest SOTP/rNPV Market Implied Expectation vertical slice directly on the accepted P3-B typed domain and P4-A qualification boundary.

Preserve:

- SOTP segment / residual semantics;
- rNPV pipeline / probability / timing semantics;
- candidate coverage and evidence sufficiency;
- PIT and provenance;
- fail-closed ambiguity / instability / insufficiency.

Do not start P5 until P4-E and P4-F close the remaining Market Implied Expectation path.
## 12. Canonical Current State

As of 2026-10-04:

- P4-B acceptance baseline / pre-state commit: `02d6a9a7dc9626ae3d82132d0152bdf65ebc16ec`
- P4-B merge commit: `741b3fc0bff3a8da5e993f1a0c0aec25cb823420`
- P4-C pre-merge HEAD: `620977682155f5f633f1dcd71ddbc6d71a2005e1`
- P4-C merge commit: `b6bfb8df10a8ffee5f01154fbe4b47201f6048fe`
- P4-C PR CI #143 / `37189169223`: SUCCESS
- P4-C post-merge main Investment Core CI #144 / `37189193858`: SUCCESS
- P4-C post-merge main FM00 #116 / `37189193862`: SUCCESS
- P4-C final regression: 128 passed
- Investment Core Contract v0.2: FROZEN / SEMANTIC PASS
- P2-A: FINAL PASS / MERGED
- P2-B: FINAL PASS / MERGED
- P3-A: FINAL PASS / MERGED
- P3-B: FINAL PASS / MERGED
- P4: ACTIVE / P4-A FINAL PASS / P4-B FINAL PASS / P4-C FINAL PASS / P4-D FINAL PASS / P4-E NEXT
- Production investment decision kernel: NOT YET
- Real-company acceptance: NOT STARTED
- Independent audit: NOT STARTED
- Batch 2 v0.1 PR #3: OPEN / RED-TEAM BLOCKED / NOT MERGED
- M1.2 forecast research: separate track; CATL exact source admission remains blocked.
## 13. Continuity Rule

When future work begins, first reconcile against this document and current Git `main`.

Do not reconstruct project state from memory or from an old branch when current canonical evidence exists.

