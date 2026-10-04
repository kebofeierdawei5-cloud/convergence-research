# IIOS Investment Core v0.2 — Reconciled Development Roadmap

> Canonical planning document after the 2026-10-04 State Reconciliation.
>
> Historical v0.2 roadmap assumptions that conflict with this document are superseded for future engineering; historical commits remain immutable evidence.

## 1. North Star

IIOS 的核心不是生成一份“估值报告”，而是把真实公司的经营现实、市场价格与独立判断连接成一条可复核、可执行的投资决策链：

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
Market Observable Evidence + Current Price
        ↓
Candidate Market Models
        ↓
Feasible Solution Set
        ↓
Identifiability + Stability
        ↓
Market Implied Expectation
        ↓
Expectation Gap
        ↓
Positive Return > 15%
        ↓
Trust / Thesis / Risk / Portfolio Constraints
        ↓
BUY / ADD / HOLD / REDUCE / EXIT / NO-BUY
```

The core comparison is:

> **Independent view of company value / future economics vs. what the current market price requires.**

The system should not force a fixed 1–3 year holding period and should not make annualized return >15% a mandatory core gate.

## 2. Reconciled Current Baseline

### Current main

Current canonical branch: `main`

Current state is defined by:

- current Git `main`
- `docs/iios/STATE_RECONCILIATION_2026-10-04.md`
- `docs/iios/IIOS_CURRENT_STATE_INDEX.md`
- `STATUS.md`

### Already implemented on current main

- PIT / Trust / fail-closed validation foundation
- Snapshot hash + Replay
- Decision Series / Revision / Human Approval skeleton
- Company Value Core Scan / structured Value Construction Map
- Economic attribute classification
- Candidate valuation model generation
- Human-authoritative Primary Model selection
- Deterministic valuation calculators for the currently supported model families
- Basic intrinsic-value aggregation / Bear-Base-Bull outputs

### Explicitly not current capability

- true evidence-based Market Model Identification
- valid multi-model Feasible Solution Set from historical/current observable evidence
- calibrated Identifiability
- temporal/regime Stability
- general model-correct Market Implied Expectation
- general semantic Expectation Gap
- frozen Probability / Odds / Edge / Position-sizing formulas
- complete Execution Receipt / Trigger lifecycle
- production real-company acceptance

### Blocked work that must remain blocked

PR #3 / Batch 2 v0.1 is **OPEN / RED-TEAM BLOCKED / NOT MERGED**.

Do not extend or merge it as the next production layer.

Its reverse-valuation routines may be retained only as low-level primitives after the v0.2 semantic contract is frozen.

## 3. Core Architecture

### 3.1 Company side

```
Reality
  ↓
Value Construction Map
  ↓
Economic Profile
  ↓
Candidate Valuation Models
  ↓
HUMAN Primary Model Selection
  ↓
Consistency Gate
  ↓
Independent Forecast
  ↓
Intrinsic Valuation
```

Model Router remains advisory.

Human authority is mandatory for the Primary Model and rationale. An out-of-candidate model requires explicit override rationale.

### 3.2 Market side

```
Market Observable Evidence
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
Reverse Valuation
  ↓
Market Implied Expectation
```

This is the major missing semantic layer.

Market model identification must explain not merely which mathematical inverse can produce the current price, but which candidate market model is actually consistent with observed valuation behavior, relevant fundamentals, historical regime evidence, and current price.

### 3.3 Expectation Gap

Expectation Gap is not a generic subtraction between two value numbers.

The comparison must use:

- the same economic variable;
- compatible accounting semantics;
- the same relevant observation point;
- compatible scenario / forecast definitions;
- compatible valuation-model semantics.

Examples:

- PE: independent EPS / earnings vs market-implied EPS / earnings.
- PS: independent revenue vs market-implied revenue.
- EV/EBITDA: independent EBITDA vs market-implied EBITDA, with enterprise-value bridge.
- PB: independent book equity vs market-implied book equity.
- DCF / DDM: independent assumptions vs market-implied assumptions.
- SOTP: independently valued segments vs market price's implied residual / segment valuation.

## 4. Return Hurdle

Canonical investment hurdle:

> **Positive expected return > 15%.**

This is a return hurdle, not an annualized return hurdle.

Rules:

- no mandatory 1–3 year holding period;
- no mandatory annualized calculation;
- do not invent a horizon merely to annualize a return;
- any future holding-period or annualized-return analysis is supplemental unless separately promoted into a new contract.

The deterministic engine must eventually calculate the return definition appropriate to the selected valuation semantics and current investment decision, and must expose the exact input assumptions.

## 5. Development Order

### P0 — State Reconciliation

Status: **COMPLETE / CURRENT**

Deliverables:

- current main identity
- merged / unmerged capability reconciliation
- blocked PR reconciliation
- return-hurdle correction
- separation of investment core and M1.2 forecast research
- canonical continuity documents

### P1 — Investment Core Contract v0.2

Status: **NEXT**

Freeze machine semantics before further Batch 2 implementation.

Must define:

- current-price observation and PIT semantics
- company reality / evidence contract
- company value-core contract
- human valuation-model selection
- market-model candidate definition
- fit / Feasible Solution Set
- Identifiability
- Stability
- model-specific reverse valuation
- model-specific Market Implied Expectation
- semantic Expectation Gap
- positive-return >15% gate
- Trust / thesis / risk interaction
- fail-closed rules
- version and replay semantics

### P2 — Company Value Core v1.x hardening

Status: **IMPLEMENTED BASE / NEEDS HARDENING**

Do not redesign the human-authority decision.

Focus on the remaining gap:

```
Raw / evidence-backed company reality
        ↓
Structured business / asset nodes
        ↓
Economic attributes
        ↓
Value Construction Map
        ↓
Core Value Drivers
```

The existing scanner currently validates/classifies structured nodes; it does not fully discover the company value map from raw evidence.

Priority hardening areas:

- evidence linkage
- capital intensity / reinvestment semantics
- CAPEX → depreciation / amortization → FCF → incremental return on capital
- capital allocation
- dilution / per-share transmission
- value-contribution transparency

### P3 — Market Model Identification v0.2

Status: **NOT STARTED**

Redesign Batch 2 from the contract, rather than extending PR #3.

Acceptance requires:

- observable evidence inputs
- candidate model set
- historical / current fit
- explicit feasible solution set
- conservative identifiability
- stability across reasonable perturbations / regimes
- model-specific reverse valuation
- fail-closed when interpretation is ambiguous

### P4 — Market Implied Expectation Engine

Status: **NOT STARTED**

For each identified / feasible model, produce the economic variables that the current price requires.

Never collapse different model semantics into one generic “implied net profit”.

### P5 — Expectation Gap + Return Gate

Status: **NOT STARTED**

Compute the gap between:

```
Independent Economic View
        vs
Market Implied Economic Requirement
```

Then determine whether the independently supported opportunity implies:

> positive return >15%.

Do not convert a merely ambiguous market interpretation into a BUY.

### P6 — Decision Engine

Status: **PARTIAL / NEEDS REWORK**

Reconnect:

```
Trust
+ PIT
+ Thesis
+ Independent Value
+ Market Implied Expectation
+ Expectation Gap
+ Return >15%
+ Risk
+ Portfolio Constraints
        ↓
Action
```

The final decision remains deterministic where appropriate and requires Human Approval for execution.

### P7 — Execution Receipt / Revision / Trigger Lifecycle

Status: **PARTIAL / NEEDS COMPLETION**

Complete the technical audit chain:

```
Run
 ↓
Snapshot
 ↓
Decision Revision
 ↓
Human Approval
 ↓
Current Projection
 ↓
Execution Receipt
 ↓
Monitoring / Trigger
 ↓
New Run / New Revision
```

No automatic order placement.

### P8 — Real Company Acceptance

Status: **NOT STARTED**

At minimum:

- CATL
- 科伦药业

Cases must exercise materially different economic structures and strict PIT evidence.

### P9 — Independent Audit

Status: **NOT STARTED**

Audit:

- semantic correctness
- PIT correctness
- market-model identification
- value / expectation comparison
- return gate
- persistence / replay
- fail-closed behavior
- human authority boundary

## 6. What We Do Not Build Yet

Before P1–P8 close, do not expand into:

- full-market scanning
- auto trading
- complex portfolio optimization
- unnecessary microservice/event-bus infrastructure
- unrelated governance layers
- fabricated or commercial-data-dependent historical datasets
- frozen Kelly / probability formulas without prior empirical validation

M1.2 Forecast Research remains a separate track.

## 7. Forecast Research Track

```
Exact Source Admission
        ↓
FM-02 PIT Feature Builder
        ↓
FM-03 State Engine
        ↓
FM-04 Conditional Backtest
        ↓
FM-05 Scope Freeze
        ↓
FM-07 Amendment Gate
```

Current status:

- FM-00 PASS
- FM-01 implementation foundation PASS
- CATL exact source ingress BLOCKED

The forecast-research track must not be used to mask missing investment-core semantics.

## 8. Definition of Done — Investment Core

The core can be considered production-capable only when all of the following are demonstrated:

- company reality is evidence-backed and structured;
- human-authoritative primary valuation model is explicit;
- intrinsic value is deterministic and replayable;
- market model interpretation is evidence-based;
- feasible solution set / identifiability / stability are meaningful;
- market implied expectation is model-semantic correct;
- expectation gap is economically coherent;
- positive return >15% is computed under explicit assumptions;
- risk / thesis / trust gates are enforced;
- human approval remains separate;
- execution receipt, revision history and replay are complete;
- at least two real companies pass acceptance;
- an independent audit passes.

---

**Version: reconciled v0.2 roadmap — 2026-10-04**
