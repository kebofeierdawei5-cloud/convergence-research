# IIOS B0 — Semantic Conflict Register

Date: 2026-10-04
Status: OPEN FOR B1 ADJUDICATION
Baseline: d209b33b7f922866f2fdc1190785c27edb8a28e4

This register is a controlled list of semantic conflicts that must not be silently resolved in code. Each critical conflict requires an owner-approved B1 decision before implementation changes.

## Critical conflicts

### B0-S01 — Dual 15% semantics

Incumbent: the v0.2 contract/code treats 15% as the strict Expected Return hurdle.

Owner target clarification:

1. 15% BUY-entry threshold / safety-margin requirement — a current-entry policy criterion that determines whether an opportunity reaches the investment-entry zone.
2. 15% 1–3Y annualized target — a separate long-term expectation for the outcome of a fundamental investment held for approximately 1–3 years.

The two concepts are independent despite the same current numerical value.

Forbidden implementation pattern: one field such as RETURN_HURDLE = 15% being reused to represent both.

B1 decision must define:
- exact variable names;
- exact units;
- whether the entry threshold is expressed as return, discount, valuation ratio, or a compound policy;
- exact relation between Entry Threshold, Expected Return, Required Return and Margin of Safety;
- how the 1–3Y horizon is represented and when annualization is used.

### B0-S02 — Horizon

The repaired system must carry the investment horizon explicitly enough to distinguish a point-in-time entry decision from a multi-year fundamental thesis.

The horizon must not be invented by silently converting a non-annualized return into an annualized return after the fact.

### B0-S03 — Expected Return / Required Return

Expected Return is an output of forecast + valuation under an explicit horizon basis.

Required Return is a risk-compensation requirement and must not be implicitly manufactured by adding several overlapping risk premiums to the same hurdle.

The relationship between the two must be explicit and deterministic.

### B0-S04 — Margin of Safety

Margin of Safety is a valuation/price protection concept. It must not become a second hidden return hurdle.

The repair must determine whether the 15% BUY-entry threshold is itself the policy expression of the desired safety margin, or whether MoS is an additional independent check.

The system must prevent double counting either interpretation.

### B0-S05 — Quality

Quality cannot remain merely an economic-profile classifier. The repaired object must distinguish:

economic reality → quality evidence/metrics → durable advantage → incremental returns → cash conversion → value drivers

and make clear which part is factual evidence versus analyst judgment.

### B0-S06 — Trust / Investability

Trust concerns whether the evidence/company can be relied upon sufficiently to commit capital.

Investability concerns whether, despite being a trustworthy company, the current opportunity is investable under valuation, risk, liquidity, portfolio and execution constraints.

The two must remain separate.

### B0-S07 — MIE

The P4 MIE chain is retained as conditional explanatory infrastructure. It is not automatically a universal BUY gate until B8 re-evaluation shows that the evidence, semantics and utility justify that role.

### B0-S08 — Unknown

UNKNOWN must not silently imply HOLD.

A decision policy is required for each action family and for missing/blocked upstream states.

### B0-S09 — Existing holdings

HOLD / REDUCE / EXIT must be evaluated using the current opportunity and current forward economics, not by treating a favorable historical cost basis as a reason to retain capital.

## Deferred but tracked conflicts

- portfolio constraints versus intrinsic value;
- tactical positioning versus core thesis;
- scenario-probability authority and sensitivity;
- monitoring idempotency / hysteresis;
- cross-version replay and semantic invalidation;
- evidence-source confidence versus truth claims;
- A/H price/currency/adjustment semantics.

## B1 approval rule

No critical semantic conflict may be marked RESOLVED solely by implementation convenience or test compatibility with the incumbent v0.2 contract.

A critical conflict becomes RESOLVED only after:

Owner decision → versioned ADR → contract update → implementation/schema update → semantic regression → independent red-team
