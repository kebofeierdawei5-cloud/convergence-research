# B58 — Normalized earnings proxy versus primary EPS consistency

Date: 2026-10-29  
Status: **BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## Goal

B57 exposes a normalized parent-attributable net-profit and diluted EPS proxy; the primary EPS_MULTIPLE valuation independently uses the scenario EPS passed through eps_multiple_valuation. B58 compares these two paths without replacing either input or forcing the model EPS to equal the normalized EPS.

## Placement

The diagnostic is nested at operating_driver_forecast.baseline_transition.primary_eps_consistency, inside an existing B4 result that is already included in Replay comparison. The computation is attached only after the pilot's final EPS bridge and B5 project-inclusion revalidation, so the comparison reflects the EPS and bridge states that remain in the final analysis output.

## Comparison contract

For each Bear/Base/Bull scenario, B58 checks:

- Selected primary model family is EPS_MULTIPLE and the EPS_MULTIPLE adapter actually completed a calculation.
- B4 and B57 scope are COMPANY_WIDE.
- The B57 forward earnings reference period, B4 forecast period, primary EPS bridge period and EPS_MULTIPLE valuation period are identical. The valuation terminal date remains a separate field and is never treated as the earnings period.
- B57 all-items parent-attributable net-profit proxy divided by B57 diluted weighted-average shares is compared with both the primary EPS bridge's calculated EPS and the EPS value actually used by the primary EPS_MULTIPLE adapter. Absolute EPS difference tolerance is CNY 0.005/share.
- B57 and primary diluted weighted-average share counts must be exactly equal, and the primary denominator must be stated in shares.
- A non-zero other_after_tax_attribution_adjustment in the primary EPS bridge is not silently treated as comparable: until that adjustment is explicitly mapped to B57, status is NOT_COMPARABLE_ADJUSTMENT_BASIS.
- A primary bridge that is ASSUMPTION_ONLY may be compared numerically to B57's all-items proxy, but the result remains ASSUMPTION_ONLY; no independent earnings/share denominator reconciliation is claimed.
- B57 normalized EPS is displayed as context only because it explicitly excludes one-off items; it is not used for a like-for-like match against all-items primary EPS.

## Status behavior

- NOT_APPLICABLE_NOT_EPS_MULTIPLE: another primary model is selected.
- NOT_COMPARABLE_CURRENCY: primary valuation EPS is not CNY, because B57 currently has no explicit FX/foreign-share bridge.
- PRIMARY_EPS_NOT_CALCULATED: the actual primary EPS_MULTIPLE adapter has not produced a usable calculation.
- BLOCKED_BY_B57, NOT_IDENTIFIABLE, PERIOD_MISMATCH, SHARE_DENOMINATOR_MISMATCH, EPS_MISMATCH, NOT_COMPARABLE_ADJUSTMENT_BASIS, ASSUMPTION_ONLY, PARTIAL and MATCH make the blockers and outcome explicit.
- B58 does not modify the primary EPS input, EPS×P/E terminal values, B5/B6, target price, the 15% annualized return hurdle, admission status, Decision or trade authority.

## Regression cases and validation

Six B58 cases are authored in tests/test_local_investment_pilot_v01.py: successful comparable match, non-zero primary attribution-adjustment boundary, period/share denominator mismatches, primary assumption-only status, non-EPS_MULTIPLE non-applicability and report-boundary visibility. They have not been executed. No Replay, CI, merge or real macOS acceptance is claimed.
