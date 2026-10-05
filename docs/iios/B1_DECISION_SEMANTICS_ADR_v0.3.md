# IIOS B1 — Decision Semantics ADR v0.3

Date: 2026-10-04
Status: FROZEN — IMPLEMENTED IN CORE-04
Scope: Decision actions, Trust, Investability, Portfolio Constraint, Unknown and MIE role
Parent: B1 Return Semantics v0.3

## 1. Purpose

The decision layer consumes versioned evidence, company economics, forecast, valuation and return outputs. It does not redefine upstream economics and does not authorize orders.

## 2. Action semantics

BUY: position is zero; all mandatory gates pass; current entry conditions and position package pass.

ADD: existing position is positive; the same fundamental return standards as BUY pass; current position remains below policy maximum; portfolio constraint passes.

HOLD: intentional retention of an existing position after current forward economics are assessed. HOLD is never a default for UNKNOWN or missing evidence.

REDUCE: decrease an existing position because current forward return, risk, thesis strength, portfolio exposure or execution conditions deteriorate without requiring full exit.

EXIT: close an existing position under an explicit hard-exit condition such as broken thesis, permanent impairment, severe risk breach or an explicit Trust hard-exit rule.

NO-BUY: no position should be initiated because known current economics or policy conditions are unattractive or failed.

WATCH: no position now, but the case remains potentially investable and has an explicit re-evaluation condition such as price entry zone or identifiable evidence update.

REVIEW_REQUIRED: material unresolved semantic, evidence, Trust, PIT, valuation, forecast or policy contradiction prevents safe economic adjudication. It is not HOLD.

REVIEW_REQUIRED operational effect: no new capital, no automatic execution, no automatic reduction or exit; Human review is required. Existing positions remain unchanged pending review unless an independent emergency control applies.

## 3. Decision status

Decision status should distinguish READY, BLOCKED, REVIEW_REQUIRED and SUPERSEDED.

BLOCKED is a definitive gate failure. REVIEW_REQUIRED is unresolved material uncertainty or contradiction.

## 4. Trust

Trust asks whether the company and evidence are reliable enough to permit capital commitment.

PASS permits downstream evaluation. REVALIDATION blocks BUY/ADD. FAIL blocks new capital. UNKNOWN blocks new capital and normally routes to REVIEW_REQUIRED.

Trust FAIL alone does not automatically mean EXIT. EXIT requires a separate hard-exit rule.

## 5. Investability

Investability asks whether a trustworthy company is currently suitable for capital allocation under valuation, return, risk, liquidity, portfolio and execution constraints.

States: INVESTABLE, WATCH, NOT_INVESTABLE, UNKNOWN.

Investability cannot upgrade Trust or Quality.

## 6. Portfolio Constraint

Portfolio Constraint is a permission and position-control layer, not a valuation input.

States: PASS, BLOCKED, UNKNOWN.

Portfolio BLOCKED prevents new allocation. A hard exposure breach can trigger REDUCE for existing holdings. Portfolio policy must never rewrite intrinsic value, Expected Return, Quality or Thesis.

## 7. MIE role in v0.3

Market Implied Expectation is explanatory market-side infrastructure, not a universal BUY/ADD gate.

MIE may strengthen, weaken or explain the investment thesis when it is qualified. Its absence, UNKNOWN, BLOCKED or AMBIGUOUS state does not automatically veto a direct company-side opportunity.

A verified material contradiction MAY affect a decision only through an explicit versioned policy rule. CORE-04 v0.1 does not invent a contradiction threshold and therefore does not silently convert a non-positive/advisory gap into a veto.

MIE must still obey provenance, PIT and semantic compatibility when present.

A future version may promote MIE to a mandatory gate only through separate evidence and owner approval.

## 8. New return semantics at decision layer

Standard fundamental BUY/ADD requires:

1. Entry Return Cushion >= 15%.
2. Expected Annualized Return over the explicit H >= 15%.
3. Expected Annualized Return over H >= Required Return.
4. Trust/PIT/forecast/valuation/risk/portfolio gates pass.
5. Complete position package exists.

These are independent conjunctive conditions.

15% + Required Return is invalid. The two 15% values are not aliases.

## 9. Deterministic precedence

Recommended precedence:

1. Semantic/version/PIT integrity failure -> REVIEW_REQUIRED.
2. Trust hard failure -> NO-BUY for new positions; EXIT only when an explicit hard-exit rule applies; otherwise REVIEW_REQUIRED for unresolved severity.
3. Thesis BROKEN -> EXIT if held, otherwise NO-BUY.
4. Portfolio hard constraint -> REDUCE if an existing position violates a hard limit; otherwise NO-BUY for a new position.
5. Definitive valuation/forecast/risk failure -> NO-BUY or REDUCE according to current position and policy.
6. BUY gates pass with zero position -> BUY.
7. ADD gates pass with existing position -> ADD.
8. Existing position with no ADD, REDUCE or EXIT trigger -> HOLD.
9. No position with plausible thesis but current entry conditions unmet -> WATCH.
10. Any remaining material unresolved contradiction -> REVIEW_REQUIRED.

Reason labels must not determine behavior by themselves.

## 10. Unknown

UNKNOWN is never silently converted to HOLD.

Examples:
- Trust UNKNOWN -> REVIEW_REQUIRED, no new capital.
- Portfolio UNKNOWN -> REVIEW_REQUIRED, no new capital.
- Required Return UNKNOWN -> REVIEW_REQUIRED because return adequacy cannot be certified.
- Forecast material variable UNKNOWN -> REVIEW_REQUIRED if required for valuation.
- Thesis UNKNOWN -> REVIEW_REQUIRED unless a separate definitive NO-BUY condition applies.
- MIE UNKNOWN -> does not itself block BUY/ADD in v0.3.

## 11. Current-position economics

HOLD/REDUCE/EXIT and future ADD decisions use current forward opportunity economics and current decision price. Historical cost basis is portfolio information, not a reason to retain or add capital.

## 12. Position package

BUY/ADD must include entry price or entry zone, initial position, target position, maximum position, thesis-break triggers and monitoring triggers.

## 13. Human boundary

AI/deterministic code produces the standardized proposal. Human owns final approval/rejection, portfolio constraints, special information, authorized exceptions and execution.

AI Decision, Human Decision and Human Override must remain separate immutable records. Override must record field, reason, scope and timestamp.

## 14. Acceptance

B1 Decision Semantics passes only when:
1. all eight actions have explicit meanings;
2. UNKNOWN is not HOLD;
3. REVIEW_REQUIRED has defined operational effect;
4. Trust and Investability are separate;
5. Portfolio Constraint cannot rewrite value;
6. MIE is non-mandatory in v0.3;
7. new return semantics are consumed without additive thresholds;
8. current opportunity, not cost basis, controls capital allocation;
9. precedence is deterministic;
10. Human override cannot mutate historical AI decision;
11. BUY/ADD require a position package;
12. no action authorizes automatic execution.

## 15. Status

B1 Decision Semantics v0.3: FROZEN — IMPLEMENTED.

CORE-04 consumes this semantic contract through the versioned production decision kernel. Legacy decision-state behavior remains compatibility-only; Investment Core v0.3 explicitly uses OPTIONAL_EXPLANATORY MIE policy.