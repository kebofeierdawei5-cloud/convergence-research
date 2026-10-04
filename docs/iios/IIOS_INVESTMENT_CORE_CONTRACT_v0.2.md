# IIOS Investment Core Contract v0.2

Version: v0.2
Status: FROZEN SEMANTIC CONTRACT
Effective date: 2026-10-04
Scope: Single-company investment decision core for China A-shares / Hong Kong equities

## 1. Purpose

本 Contract 冻结 IIOS 投资核心的语义边界。

目标不是决定“最聪明的估值模型”，而是形成一条不偷换经济变量、不把市场价格解释成确定事实、可 PIT、可 replay、可 fail-closed 的决策链：

```
Company / Industry Reality
        ↓
Company Value Core
        ↓
Human Primary Valuation Model
        ↓
Independent Forecast
        ↓
Independent Intrinsic Value / Scenario Values
        +
Market Observable Evidence + Price
        ↓
Candidate Market Models
        ↓
Fit
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
Positive Expected Return > 15%
        ↓
Trust / Thesis / Risk / Portfolio Constraints
        ↓
AI Action Proposal
        ↓
Human Approval
```

This contract supersedes conflicting future-development assumptions in older roadmap documents. Historical documents and commits remain immutable historical evidence.

---

## 2. Non-negotiable Principles

### 2.1 Company-side and market-side questions are different

Company-side question:

> How should IIOS independently value this company, given its actual economic structure?

Market-side question:

> What economic outcome / valuation assumptions must be true for the current market price to make sense?

The system MUST NOT use the company-selected Primary Model as proof that the market uses the same model.

### 2.2 Human authority remains on company valuation model choice

The deterministic router generates candidate models and suitability evidence.

It does not choose the authoritative Primary Model.

Required:

`selection_method = HUMAN`

Human must provide:

- Primary Model
- rationale
- explicit override rationale when selecting outside the candidate set

### 2.3 Market model identification is an inference problem, not an inverse-calculation problem

Reverse valuation alone does not identify the market model.

A valid market-model interpretation requires evidence that the candidate model is consistent with:

- relevant observable operating fundamentals;
- current price / market capitalization / enterprise value;
- historical valuation behavior when available;
- current regime / structural state when material;
- accounting and economic semantics required by the model.

When evidence cannot distinguish materially different candidate explanations, the output MUST remain ambiguous.

### 2.4 Expectation Gap is semantic, not merely numerical

Expectation Gap MUST compare economically equivalent objects.

Examples:

- PE: independent EPS / earnings versus market-implied EPS / earnings.
- PS: independent revenue versus market-implied revenue.
- PB: independent book equity versus market-implied book equity.
- EV/EBITDA: independent EBITDA versus market-implied EBITDA, with enterprise-value bridge.
- DCF: independent FCF / margin / growth / reinvestment / discount assumptions versus market-implied assumption set.
- DDM: independent dividend / payout / growth assumptions versus market-implied assumption set.
- SOTP: independent segment values versus market-implied residual / segment value requirements.
- rNPV: independent probability-adjusted asset economics versus market-implied pipeline value / probability / timing requirements.

A generic field such as `market_implied_net_profit` MUST NOT be emitted for models for which net profit is not the economically correct inverted variable.

### 2.5 No forced certainty

The system MUST be able to return:

- PASS
- BLOCKED
- IDENTIFIABLE
- AMBIGUOUS
- UNIDENTIFIABLE
- STABLE
- UNSTABLE
- INSUFFICIENT_EVIDENCE

rather than fabricating a winner.

---

## 3. Case and PIT Contract

A decision case MUST declare:

- `case_id`
- `market`
- `symbol`
- `company`
- `as_of_date`
- `cutoff_date`
- `current_price_observation`
- `company_evidence_manifest`
- `market_evidence_manifest`
- `trust`
- `reality`
- `forecast`
- `valuation`
- `risk`
- `portfolio`
- `thesis`

### 3.1 PIT rule

For every evidence item and market observation used by the decision:

```
known_at <= cutoff_date
```

Evidence whose known time is unknown, unverifiable, or later than cutoff MUST NOT support a PASS decision.

Price data MUST also have an observation timestamp/date and source provenance.

### 3.2 Current price is evidence

The current market price is not a free-floating parameter.

It is a PIT market observation with:

- value
- currency
- observation time/date
- source
- known_at / publication availability
- adjustment semantics if applicable

Corporate-action-adjusted and unadjusted price series MUST NOT be silently mixed.

---

## 4. Trust Gate

Trust precedes valuation.

Trust is PASS only when no material unresolved issue exists in:

- accounting / evidence integrity;
- management integrity;
- governance / minority-shareholder protection;
- material fraud indicators;
- material source conflict.

A Trust FAIL or unresolved critical contradiction MUST block new BUY / ADD.

Existing holdings may still be routed to HOLD / REDUCE / EXIT according to the decision policy; Trust failure must not be converted into a positive-value conclusion.

---

## 5. Company Reality Contract

Reality is a structured representation of the company's actual economic state known as of cutoff.

It SHOULD cover, when material:

- segment / business structure;
- volumes / price / mix;
- revenue;
- margins;
- operating cash flow;
- capex;
- depreciation / amortization;
- working capital;
- debt / net cash;
- share count / dilution;
- capital allocation;
- pipeline / option assets;
- subsidiaries / investments;
- industry state and relevant cyclicality.

Every material input MUST trace to evidence.

The contract does not require every possible field for every company. Materiality is determined by the company Value Core and the selected valuation model.

---

## 6. Company Value Core Contract

The Value Core layer converts evidence-backed company reality into a structured Value Construction Map.

Minimum conceptual output:

```
Value Nodes
  ↓
Economic Profiles
  ↓
Core Value Drivers
  ↓
Candidate Valuation Models
```

The current v1.x scanner is a deterministic structured classifier / validator. It does not claim automatic discovery of all business and asset nodes from raw filings.

Material gaps MUST be exposed, not silently filled.

---

## 7. Human Valuation Model Selection

The canonical company-side sequence is:

```
Company Value Core
    ↓
Economic Profile
    ↓
Candidate Models
    ↓
HUMAN Primary Model Selection
    ↓
Model Consistency Gate
    ↓
Independent Forecast
    ↓
Intrinsic Valuation
```

Required selection fields:

- `selection_method = HUMAN`
- `economic_profile`
- `primary_model`
- `rationale`

Optional:

- `secondary_models`
- `cross_check_models`
- `alternatives`
- `override_reason`

The Primary Model is authoritative for independent valuation.

Secondary / cross-check models are evidence, not an automatic average.

---

## 8. Independent Forecast Contract

The independent forecast MUST be prepared without using the current market price as a forecast input.

At minimum, the forecast SHOULD provide:

- Bear
- Base
- Bull

For each scenario, all variables material to the selected valuation model MUST be explicit.

Examples:

- PE → earnings / EPS and relevant share-count assumptions.
- PS → revenue and share count.
- EV/EBITDA → EBITDA and net-debt / cash assumptions.
- DCF → FCF build, growth, margins, reinvestment, discounting and terminal assumptions.
- DDM → dividends / payout, growth and discounting assumptions.
- SOTP → segment-specific forecasts and model inputs.
- rNPV → pipeline cash flows, probabilities, timing and commercialization assumptions.

Probabilities, when used in the decision-return Gate, MUST be explicit, non-negative, and sum to 100%.

---

## 9. Independent Intrinsic Value Contract

Independent valuation MUST produce:

- Primary Model
- scenario values
- value per share
- valuation assumptions
- model-input provenance
- sensitivity / range where appropriate
- model status
- cross-check outputs where used

The calculation layer MUST be deterministic and replayable.

The system MUST NOT silently:

- replace the human Primary Model;
- average unrelated valuation models;
- override missing critical inputs;
- substitute current price into independent forecast variables.

---

## 10. Market Observable Evidence Contract

Market-side analysis MUST start from observable evidence.

Minimum evidence classes, when material:

- current market price;
- market capitalization / enterprise value;
- historical valuation multiples or model-consistent market variables;
- current and historical operating fundamentals;
- share count / capital structure;
- segment / asset disclosures;
- industry valuation regime;
- relevant peer / benchmark evidence where used.

Historical market evidence MUST itself obey the cutoff rule.

The absence of enough evidence to distinguish market models is a valid outcome.

---

## 11. Candidate Market Models

The system MAY consider:

- forward PE
- PS
- PB
- EV/EBITDA
- DCF
- DDM
- SOTP
- rNPV
- other models only when explicitly supported by a versioned contract

Candidate generation MUST be evidence-constrained.

A model MUST NOT enter the feasible set merely because its inverse equation can solve for a number.

---

## 12. Market Model Fit

Each candidate model MUST produce a fit assessment based on available observable evidence.

Fit is a structured object, not a single LLM opinion.

Conceptually:

```
Model
→ Required Observable Inputs
→ Historical / Current Evidence
→ Fit Diagnostics
→ Residual / Inconsistency
→ Constraints
→ Feasible / Infeasible
```

Fit diagnostics SHOULD include, where data permits:

- historical explanatory fit;
- current consistency;
- accounting bridge consistency;
- peer / benchmark consistency;
- regime consistency;
- parameter plausibility.

No single diagnostic is universally mandatory; the contract is that the evidence used and the rule applied are explicit.

---

## 13. Feasible Solution Set

For each candidate model, reverse valuation returns a set or interval of model-consistent solutions:

```
Candidate Model
    ↓
Observed Price + Evidence
    ↓
Model Constraints
    ↓
Feasible Solution Set
```

Examples:

- PE → feasible implied EPS / earnings / multiple combinations.
- PS → feasible implied revenue / multiple combinations.
- PB → feasible implied book equity / multiple combinations.
- EV/EBITDA → feasible implied EBITDA / multiple / enterprise-value bridge.
- DCF → feasible growth / margin / FCF / reinvestment / terminal-value assumptions subject to constraints.
- DDM → feasible dividend / payout / growth assumptions.
- SOTP → feasible segment / residual valuations.
- rNPV → feasible pipeline-value / probability / timing requirements.

The system MUST preserve the solution set until identifiability has been assessed.

---

## 14. Identifiability

Identifiability answers:

> Do available data materially distinguish one market-model explanation from other feasible explanations?

Canonical states:

### IDENTIFIABLE

A materially preferred interpretation remains after evidence and constraints, and competing feasible explanations are either eliminated or economically immaterial.

### AMBIGUOUS

Two or more materially different explanations remain feasible.

### UNIDENTIFIABLE

Evidence is insufficient, contradictory, or no supported model can be established.

### INSUFFICIENT_EVIDENCE

A distinct evidence insufficiency exists and must be surfaced before further inference.

The system MUST NOT map AMBIGUOUS or UNIDENTIFIABLE directly to a positive BUY Gate.

---

## 15. Stability

Stability answers:

> Does the market-model interpretation remain materially similar under reasonable changes in evidence windows, assumptions, or market regime boundaries?

Stability is NOT simply the relative width of one numerical interval.

The implementation SHOULD test, where applicable:

- observation-window perturbation;
- reasonable parameter perturbation;
- historical sub-periods;
- current regime boundaries;
- alternative but admissible evidence subsets.

Canonical outputs:

- STABLE
- UNSTABLE
- INSUFFICIENT_EVIDENCE

A narrow interval that changes model interpretation under a small perturbation is not stable.

---

## 16. Market Implied Expectation

Market Implied Expectation is the economic requirement implied by the current price under the feasible market-model interpretation.

It MUST be represented as a model-semantic object:

```
market_model
identifiability
stability
economic_variable(s)
value / range
units
observation basis
assumption set
confidence / evidence sufficiency
```

It is not necessarily a single intrinsic-value number.

For multiple materially feasible models:

```
Market Implied Expectation Set
        =
{model_1 expectation,
 model_2 expectation,
 ...}
```

If the set cannot be narrowed sufficiently, the decision layer MUST retain ambiguity.

---

## 17. Expectation Gap

Expectation Gap compares the independent forecast/value with the Market Implied Expectation under compatible semantics.

Canonical form:

```
Independent Economic View
        vs
Market Implied Economic Requirement
        ↓
Expectation Gap
```

The output MUST state:

- compared variable(s);
- independent value / range;
- market-implied value / range;
- units;
- model;
- scenario / horizon basis;
- gap direction;
- gap magnitude;
- evidence sufficiency.

A positive numeric difference with mismatched economic variables is INVALID.

### 17.1 Model-specific examples

PE:

`independent_forward_EPS > market_implied_forward_EPS`

PS:

`independent_revenue > market_implied_revenue`

EV/EBITDA:

`independent_EBITDA > market_implied_EBITDA`

DCF / DDM:

Compare independently forecast assumptions with the market-implied feasible assumption set rather than manufacturing an unrelated profit number.

SOTP:

Compare independent segment value construction with the segment/residual value required by the current market capitalization.

---

## 18. Return Definition

The core hurdle is:

> **Positive expected return > 15%.**

No fixed 1–3 year holding period is required.

No annualized return is required for the core Gate.

### 18.1 Primary return metric

When Bear/Base/Bull probabilities are explicitly validated, the primary decision return is:

```
Expected Value
    = Σ(probability_s × intrinsic_value_s_per_share)

Expected Return
    = Expected Value / Entry Price - 1
```

Core Gate:

```
Expected Return > 15%
```

The probability-weighted Expected Return is the primary hurdle metric.

### 18.2 Supplementary return metrics

The system MAY additionally show:

- Base-case return
- Bear-case return
- Bull-case return
- upside / downside range
- expected payoff
- probability of positive return
- probability of beating the 15% hurdle

These are supplementary and MUST NOT silently replace the primary Expected Return definition.

### 18.3 Probability integrity

Scenario probabilities used in the core return calculation MUST:

- be explicit;
- satisfy 0 ≤ p ≤ 1;
- sum exactly to 1 within the contract's numeric representation;
- have evidence / rationale appropriate to the forecast process.

If valid probabilities are unavailable, the system MUST NOT fabricate them.

A future contract may define a separate deterministic Base-case hurdle, but that would be a new semantic choice, not an implicit fallback.

---

## 19. Entry Price

Return is measured against the actual intended entry price.

For a new position:

`entry_price = decision-case entry price / evaluated market price`

For an existing position, portfolio return analysis MAY additionally use cost basis, but the investment decision itself MUST preserve the distinction between:

- current market opportunity;
- historical cost basis.

A low historical cost basis MUST NOT make a currently unattractive new capital deployment look attractive.

---

## 20. Risk and Margin of Safety

The positive-return hurdle is necessary but not sufficient.

BUY / ADD requires, at minimum:

- Trust PASS;
- PIT PASS;
- Thesis not BROKEN;
- Independent valuation PASS;
- Market-implied interpretation sufficiently identifiable;
- Expectation Gap materially positive;
- Expected Return >15%;
- Bear / downside within the applicable risk limit;
- portfolio constraints PASS;
- position package complete.

The exact thresholds for position size are separate from this semantic contract.

---

## 21. Decision Semantics

Available actions:

- BUY
- ADD
- HOLD
- REDUCE
- EXIT
- NO-BUY

### BUY

New position may be initiated only when all mandatory BUY Gates pass.

### ADD

Existing position may be increased only when all mandatory ADD Gates pass and portfolio constraints permit.

### HOLD

Current position is retained when thesis remains valid but new capital should not be added.

### REDUCE

Risk, valuation deterioration, expectation deterioration, thesis weakening, or portfolio constraints justify reducing exposure without requiring a full exit.

### EXIT

Thesis is broken, Trust fails materially, or other defined hard-exit conditions are met.

### NO-BUY

No position should be initiated under current evidence and constraints.

No action may imply automatic order execution.

---

## 22. Fail-Closed Rules

The system MUST fail closed on:

- missing / unverifiable material evidence;
- PIT violation;
- unresolved material Trust issue;
- missing company reality required by selected model;
- missing human Primary Model selection;
- model/profile mismatch;
- unsupported valuation model;
- invalid valuation inputs;
- missing material market evidence;
- no feasible market model;
- ambiguous market interpretation where the decision requires uniqueness;
- unstable market interpretation where instability is material;
- incompatible Expectation Gap variables;
- missing or invalid scenario probabilities when using the primary Expected Return Gate;
- contradiction between published decision fields and deterministic calculations;
- replay mismatch;
- version / schema mismatch affecting semantics.

Fail-closed means the system may still issue HOLD / REDUCE / EXIT / NO-BUY where policy allows, but it MUST NOT convert an unresolved blocker into BUY / ADD.

---

## 23. Human / AI Boundary

### AI / deterministic system owns

- evidence schema validation;
- PIT checks;
- company Value Core structure validation;
- candidate model generation;
- deterministic valuation calculations;
- market-model fit calculations defined by contract;
- feasible-solution calculations;
- identifiability / stability calculations;
- expectation-gap calculations;
- probability arithmetic;
- return calculations;
- decision gates;
- snapshot / hash / replay;
- persistence.

### Human owns

- final Primary Model selection;
- model-selection rationale;
- research judgment;
- forecast assumptions and scenario probabilities;
- interpretation of evidence where multiple plausible realities remain;
- final approval / rejection;
- portfolio constraints and special information;
- execution.

LLM MUST NOT directly alter deterministic outputs or bypass a gate.

---

## 24. Version / Replay Semantics

Every real decision MUST retain:

- case identifier;
- as-of / cutoff;
- price observation provenance;
- evidence manifest;
- engine version;
- schema version;
- model-selection version;
- forecast version / provenance;
- market-model contract version;
- input snapshot hash;
- decision snapshot hash;
- replay status.

Changing any semantic contract version that can alter the decision requires a new decision revision.

Historical revisions remain immutable.

---

## 25. Minimum Acceptance Tests for v0.2 Contract

Before calling the semantic contract implemented, tests MUST demonstrate at least:

1. PE case: independent EPS vs market-implied EPS.
2. PS case: independent revenue vs market-implied revenue.
3. EV/EBITDA case: enterprise-value bridge and implied EBITDA.
4. DCF case: market-implied assumptions rather than invented implied net profit.
5. SOTP case: segment / residual implied value semantics.
6. Multiple feasible market models → AMBIGUOUS.
7. No feasible market model → BLOCKED / UNIDENTIFIABLE.
8. Perturbation changes model interpretation → UNSTABLE.
9. Mismatched expectation-gap variables → BLOCKED.
10. Missing scenario probabilities → cannot calculate primary Expected Return Gate.
11. Expected Return = 15% exactly → FAIL Gate.
12. Expected Return >15% + all other mandatory Gates PASS → BUY/ADD eligible.
13. Trust failure → no BUY/ADD.
14. PIT leakage → no BUY/ADD.
15. Replay mismatch → fail closed.

---

## 26. Explicit Non-goals

This Contract does not freeze:

- a universal market-model scoring formula;
- a universal identifiability threshold;
- a universal stability threshold;
- a fixed position-sizing formula;
- a Kelly formula;
- automatic company-model selection;
- automatic trading;
- full-market stock screening;
- M1.2 forecast-model selection.

Those require separate evidence / research / contracts.

---

## 27. Contract Gate

P1 is PASS only when:

- the semantic definitions in Sections 1–26 are accepted;
- current roadmap references this Contract;
- the implementation roadmap no longer requires the blocked Batch 2 v0.1 as a prerequisite;
- no current document defines annualized >15% as the core hurdle;
- no current document treats Batch 2 v0.1 as production capability.

This Contract itself does not claim implementation PASS.

---

**Canonical contract: IIOS Investment Core Contract v0.2**
