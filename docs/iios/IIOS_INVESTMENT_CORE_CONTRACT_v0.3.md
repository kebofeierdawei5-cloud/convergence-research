# IIOS Investment Core Contract v0.3

Version: v0.3
Status: FROZEN — B1 SEMANTIC CONTRACT
Date: 2026-10-04
Parent: IIOS Investment Core Contract v0.2
Scope: Single-company fundamental investment decision core for China A-shares / Hong Kong equities

## 1. Purpose

This successor contract is the accepted B1 semantic target for the repaired Investment Core. Runtime migration has passed the B1 implementation acceptance test suite; this contract remains the normative semantic authority.

Core chain:

Company Reality
→ Quality
→ Value Core
→ Independent Forecast
→ Horizon Valuation
→ Entry Value Reference
→ Expected Return
→ Required Return
→ Risk / Portfolio Constraints
→ Decision
→ Human Approval
→ Monitoring
→ Validation

Market Implied Expectation remains a separate market-side explanatory layer and is not automatically a BUY gate in v0.3 until separately qualified.

## 2. Return semantic objects

The contract MUST represent separately:
- buy_entry_return_cushion_threshold
- entry_value_reference
- margin_of_safety
- horizon_years
- scenario_terminal_wealth
- expected_total_return
- expected_annualized_return
- required_return_annualized
- fundamental_target_return_annualized

No semantic alias may collapse these objects.

## 3. Dual 15% policy values

Current policy values:
- buy_entry_return_cushion_threshold = 15%
- fundamental_target_return_annualized = 15%

The values are numerically equal but semantically independent.

## 4. Horizon

Fundamental investment cases use:
1 <= horizon_years <= 3.

The normative default Decision / Expected Return reference horizon is H = 1 year.

H remains an explicit case field. Default means policy default; the runtime MUST NOT silently invent, replace or upgrade a missing horizon.

Rules:
- H = 1 is the standard default case.
- H may be selected above 1 and below 3 when the case has an explicit economic rationale.
- H = 3 is an explicit exception only and MUST set horizon_override = true.
- A 3Y override MUST record at least one qualifying basis: MAJOR_INDUSTRY_LEADER and/or MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX.
- horizon_selection_rationale is mandatory for every case.
- horizon_override MUST be false for any H other than exactly 3.
- A 3Y horizon is never implied merely because a valuation model uses a multi-year explicit forecast.

H is the period over which expected investment outcome is evaluated. It is not a mandatory exit date.

## 5. Entry Return Cushion

Given independent conservative entry value reference V_entry_ref and intended entry price P_entry:

Entry Return Cushion = V_entry_ref / P_entry − 1

BUY-entry threshold:
Entry Return Cushion >= buy_entry_return_cushion_threshold

The threshold is not annualized.

## 6. Margin of Safety

Derived conventional value-relative MoS:

MoS = 1 − P_entry / V_entry_ref

The current normative 15% policy is the return-form entry cushion, not the conventional MoS percentage.

## 7. Scenario terminal wealth

For Bear/Base/Bull at common horizon H:

W_H,s = V_H,s + D_H,s

V_H,s = scenario terminal equity value per share.
D_H,s = cumulative investor-attributable cash distributions per share.

## 8. Expected total return

E[W_H] = Σ p_s × W_H,s

Expected Total Return_H = E[W_H] / P_entry − 1

## 9. Expected annualized return

Expected Annualized Return_H = (E[W_H] / P_entry)^(1/H) − 1

The primary calculation MUST NOT use Σ p_s × AnnualizedReturn_s.

## 10. Long-term target

fundamental_target_return_annualized = 15%

For standard fundamental BUY/ADD, this target is a hard qualification condition: Expected Annualized Return_H MUST be >= 15%.

Target Total Return_H = (1 + 15%)^H − 1

Examples:
- H=1 → 15.00%
- H=2 → 32.25%
- H=3 → 52.09%

This is distinct from the BUY-entry threshold.

## 11. Required Return

required_return_annualized is a risk/opportunity-cost benchmark established independently from both 15% policies.

required_return_total_H = (1 + required_return_annualized)^H − 1

Required Return MUST NOT be added to either 15% value and MUST NOT contain a hidden premium that duplicates valuation uncertainty already handled by the entry-value reference.

## 12. Return gate exposure

The return layer MUST expose independently:
- entry cushion pass/fail;
- expected total return;
- expected annualized return;
- required-return comparison;
- fundamental-target comparison;
- conventional MoS.

BUY/ADD consumption of these metrics requires an explicit Decision Semantics policy.

## 13. Existing-position semantics

BUY/ADD/HOLD/REDUCE/EXIT assessment uses current forward economics and current intended transaction price.

Historical cost basis is portfolio information, not the current opportunity value basis.

## 14. Fail-closed

No BUY/ADD when material return inputs are missing, ambiguous, semantically incompatible, non-PIT, or unverifiable.

No fabricated H, probabilities, value reference or 15% values.

## 15. Migration boundary

The v0.2 fields/logic RETURN_HURDLE, hurdle_pct and the old expected-return expression are historical semantics. They MUST NOT silently acquire v0.3 meanings.

## 16. Deferred decisions

This draft does not yet freeze:
- the exact construction methodology for Required Return;
- exception handling for a Human-authorized strategy-policy override to the 1–3Y target;
- position sizing;
- final MIE BUY-gate role;
- monitoring triggers.

These belong to subsequent B1 Decision Semantics / B5 / B6 contracts.

## 17. Status

FROZEN — B1 SEMANTIC CONTRACT

Owner-adjudicated on 2026-10-04. Implementation is governed by this contract and its versioned acceptance evidence.


## 18. Decision semantics

Supported actions:
BUY / ADD / HOLD / REDUCE / EXIT / NO-BUY / WATCH / REVIEW_REQUIRED.

HOLD is intentional retention of an existing position after current forward economics are assessed. It is never the default for UNKNOWN.

REVIEW_REQUIRED is the action for unresolved material semantic, evidence, Trust, PIT, valuation, forecast or policy contradictions. It permits no new capital, no automatic execution and no automatic liquidation. Human review is required.

Trust and Investability are distinct:
- Trust asks whether company/evidence is reliable enough for capital commitment.
- Investability asks whether the current opportunity is suitable under valuation, return, risk, liquidity, portfolio and execution constraints.

Portfolio Constraint is a permission/position layer. It may block or cap allocation and may require reduction of an over-limit position, but it cannot change intrinsic value, Expected Return, Quality or Thesis.

MIE is non-mandatory for BUY/ADD in v0.3. Its absence or ambiguity does not itself veto a direct company-side opportunity. A material qualified contradiction may trigger REVIEW_REQUIRED only under an explicit decision-policy materiality rule.

Standard fundamental BUY/ADD return conditions are conjunctive:
- Entry Return Cushion >= 15%;
- Expected Annualized Return_H >= 15%;
- Expected Annualized Return_H >= Required Return;
- all mandatory Trust/PIT/forecast/valuation/risk/portfolio gates pass;
- complete position package exists.

No additive threshold is allowed. The two 15% values remain independent policies.

Unknown semantics: UNKNOWN upstream states never silently become HOLD. Trust/Portfolio/Required Return/material Forecast UNKNOWN normally route to REVIEW_REQUIRED and block new capital. MIE UNKNOWN does not itself block BUY/ADD in v0.3.

Current-position decisions use current forward economics and current decision price, not historical cost basis.

Action precedence is deterministic and defined in B1 Decision Semantics ADR v0.3.

Human override preserves the original AI decision and records the override field, reason, scope and timestamp. No action authorizes automatic trading.
