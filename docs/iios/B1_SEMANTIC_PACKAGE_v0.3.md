# IIOS B1 — Semantic Package v0.3

Date: 2026-10-04
Status: PROPOSED FOR OWNER ADJUDICATION
Baseline lineage: B0 -> B1 Return Semantics -> B1 Decision Semantics

## 1. Normative target

B1 creates one semantic target for the repaired Investment Core. No implementation change is authorized until this package is owner-approved.

## 2. Return policy

15% BUY Entry Return Cushion is a non-annualized entry safety condition derived from an independent conservative Entry Value Reference.
15% Fundamental Target Annualized Return is a separate 1–3 year strategy qualification condition.

Expected Total Return_H and Expected Annualized Return_H are derived from probability-weighted terminal wealth.
Required Return is an independent annualized risk/opportunity-cost benchmark.
Entry cushion, target return, Required Return and conventional Margin of Safety are non-additive.

## 3. Decision actions

BUY: no position + all mandatory gates pass.
ADD: existing position + all mandatory gates pass + position limits allow.
HOLD: intentional retention after current forward economics are assessed.
REDUCE: decrease existing position for deterioration or hard exposure/risk reasons without full exit.
EXIT: close only under explicit hard-exit conditions.
NO-BUY: known current economics/policy conditions reject new capital.
WATCH: potentially investable but current entry conditions are not met; explicit re-evaluation trigger required.
REVIEW_REQUIRED: unresolved material contradiction/unknown prevents safe adjudication; no new capital, no auto-execution.

## 4. State boundaries

Trust = reliability of company/evidence.
Investability = suitability of the current opportunity under value/return/risk/liquidity/portfolio/execution constraints.
Portfolio Constraint = permission and sizing control; never a valuation input.
MIE = explanatory market-side layer; non-mandatory for BUY/ADD in v0.3.

## 5. Unknown

UNKNOWN is not HOLD.
Trust / Portfolio / Required Return / material Forecast UNKNOWN -> REVIEW_REQUIRED and no new capital.
MIE UNKNOWN -> does not itself block BUY/ADD in v0.3.

## 6. Standard fundamental BUY/ADD

Entry Return Cushion >= 15%
AND Expected Annualized Return_H >= 15%
AND Expected Annualized Return_H >= Required Return
AND mandatory Trust/PIT/forecast/valuation/risk/portfolio gates PASS
AND complete position package

These are separate conjunctive tests. Never add the rates.

## 7. Existing positions

Current forward opportunity and current transaction price govern new capital allocation and HOLD/REDUCE/EXIT assessment. Historical cost basis is retained for portfolio reporting only.

## 8. Human boundary

AI/deterministic system produces proposal. Human owns final approval, exceptions, portfolio policy, special information and execution.
AI Decision and Human Decision are immutable separate records; override preserves the AI record.

## 9. Deferred but explicitly bounded

- exact Required Return construction methodology;
- exact Entry Value Reference construction policy;
- position sizing formula;
- monitoring trigger implementation;
- evidence-based decision materiality thresholds for MIE contradictions;
- later promotion of MIE to a mandatory gate.

## 10. Migration gate

After owner approval:
semantic contract v0.3 finalization
-> schema migration
-> deterministic return engine
-> decision kernel
-> semantic regression and mutation validation.

Before approval: no production semantic code changes.