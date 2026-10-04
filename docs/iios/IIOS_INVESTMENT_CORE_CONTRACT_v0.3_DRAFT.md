# IIOS Investment Core Contract v0.3 — Draft

Version: v0.3
Status: PROPOSED SEMANTIC SUCCESSOR
Date: 2026-10-04
Parent: IIOS Investment Core Contract v0.2
Scope: Single-company fundamental investment decision core for China A-shares / Hong Kong equities

## 1. Purpose

This successor contract repairs the return/horizon semantics without claiming that implementation is already compliant.

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
1 <= horizon_years <= 3

H is selected per case according to thesis/economics.
H is mandatory for annualized return.

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
- whether the 1–3Y target is a hard BUY/ADD gate, a soft attractiveness target, or a strategy objective;
- position sizing;
- final MIE BUY-gate role;
- monitoring triggers.

These belong to subsequent B1 Decision Semantics / B5 / B6 contracts.

## 17. Status

PROPOSED — SEMANTIC SUCCESSOR DRAFT

Implementation/schema changes require owner approval of the complete B1 semantic package.
