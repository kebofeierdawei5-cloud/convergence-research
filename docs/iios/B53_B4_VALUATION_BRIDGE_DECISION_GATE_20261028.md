# B53 — Company-wide B4 / Primary Valuation Bridge Consistency Gate

**Status:** implemented on the feature branch; unmerged and non-canonical. **Validation:** three B53 regression cases are authored but not run. Replay, CI and real macOS full-run acceptance remain deferred / not verified.

## Why this batch

B4 already reconciles its Bear/Base/Bull operating outputs against the overlapping financial bridge carried by the primary valuation scenario. Before B53, that comparison was stored as a diagnostic but did not directly affect primary EPS_MULTIPLE eligibility. A report could therefore contain a known numeric contradiction in two company-wide bridges while still calculating annualized return and target entry price.

B53 closes that decision-chain gap without turning missing values into fabricated differences.

## Changes

1. **Scope-safe comparison.** Direct B4-to-primary-valuation financial reconciliation is only comparable when B4 scope is `COMPANY_WIDE`. For `PROJECT_INCREMENTAL`, `PRODUCT_LINE`, or `UNKNOWN` scope, the result is `NOT_COMPARABLE_SCOPE`; incremental changes must flow through the explicit B5 transmission chain, not be compared as if they were company-wide totals. If the valuation bridge is not present at all, the existing `NOT_PROVIDED` state is preserved.
2. **Fail closed on known contradictions.** For an operator-selected `EPS_MULTIPLE` primary model, a `COMPANY_WIDE` reconciliation status of `MISMATCH` changes a previously matching model-consistency result to `B4_VALUATION_BRIDGE_MISMATCH`, records the issue, and makes `primary_model_price_calculation_eligible=false`. The downstream return solver already requires that eligibility, so annualized return and target entry price remain unavailable.
3. **Do not confuse missing comparability with mismatch.** A `PARTIAL` reconciliation gets an explicit non-blocking diagnostic and is not relabeled as a numeric mismatch. A `NOT_COMPARABLE_SCOPE` result explains the scope boundary. A fully `MATCH` result does not itself establish that inputs are true or formally admitted.
4. **Report the actual conflict.** The B52 core synthesis now displays the reconciliation state and up to six mismatched field pairs, with Bear/Base/Bull labels and both values. If a known mismatch is blocking the primary EPS_MULTIPLE model, the report explicitly says return math and target-entry-price output should remain UNKNOWN.

## Scope and authority boundaries

- This applies only to the company-wide B4 vs valuation financial bridge when EPS_MULTIPLE is selected as the primary model.
- It does not block SOTP via this reconciliation, force project-level assumptions to equal company-wide values, change the EPS × P/E formula, alter the 15% annualized-return hurdle, or calculate a replacement target entry price.
- Missing values are not treated as zero or numeric mismatch. Scope-incompatible comparison is separately identified.
- No new top-level JSON field is added. The gate result remains nested in existing `operating_driver_forecast.valuation_reconciliation` and `valuation_model_consistency` objects.
- The pilot remains non-canonical. This change does not create formal Evidence/PIT, Forecast or Valuation admission, a canonical Decision, or trade/execution authority.

## Regression cases and validation status

Three cases are authored in `tests/test_local_investment_pilot_v01.py`:

1. A known company-wide mismatch blocks primary EPS_MULTIPLE price-calculation eligibility even when the EPS_MULTIPLE adapter itself reports `CALCULATED`.
2. An incremental-project B4 forecast is not directly compared with a company-wide valuation bridge.
3. The core synthesis displays the actual mismatched metrics and values.

The cases have **not** been executed. No test pass, Replay match, CI pass, or macOS acceptance is claimed.
