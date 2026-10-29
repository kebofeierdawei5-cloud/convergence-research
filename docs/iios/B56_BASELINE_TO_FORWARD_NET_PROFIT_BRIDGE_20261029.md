# B56 — Historical contribution to forward modeled net-profit bridge

Date: 2026-10-29  
Status: **BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## Goal

B55 connects a comparable observed product/line contribution baseline to Bear/Base/Bull forward assumptions. B56 adds the next arithmetic step: subtract aligned fixed cash operating expenses, depreciation/amortization and financing costs, then apply an explicit tax-rate proxy to compare modeled after-tax profit. It must never treat contribution change as net-profit or EPS growth.

## Input contract

At the same operating-driver input level as product_lines and scenarios, the caller may provide:

- historical_financials.fixed_cash_opex_cny (CNY)
- historical_financials.depreciation_amortization_cny (CNY)
- historical_financials.finance_cost_cny (CNY)
- historical_financials.tax_rate (ratio, 0–1)

Every historical measure must be typed OBSERVED_ACTUAL, have an identifiable basis and, under existing source rules, a resolvable cutoff-compatible source reference. Bear/Base/Bull forward measures reuse each scenario's existing expense and tax-rate fields and must be typed ISSUER_FORECAST or ANALYST_ASSUMPTION. No missing value defaults to zero.

## Calculation contract

B56 only proceeds when the corresponding B55 scenario is CALCULATED_AND_RECONCILED; B55's scope and adjacent complete-year gates remain authoritative. An unresolved forward production-over-nameplate-capacity constraint blocks the corresponding financial bridge.

For each period:

- EBITDA proxy = contribution after variable costs − fixed cash operating expenses.
- EBIT proxy = EBITDA proxy − depreciation/amortization.
- PBT proxy = EBIT proxy − financing costs.
- Modeled tax expense proxy = max(PBT proxy, 0) × effective tax rate.
- Modeled net-profit proxy = PBT proxy − modeled tax expense proxy.

The net-profit change is decomposed as contribution change minus the changes in fixed cash opex, depreciation/amortization, financing costs and modeled tax expense. The component sum must reconcile to the modeled net-profit change within CNY 1. This is an arithmetic attribution, not proof that any input causes the observed outcome.

## Fail-closed statuses and boundaries

- BLOCKED_BY_B55: the historical-to-forward contribution bridge is not comparable/reconciled.
- BLOCKED_BY_OPERATING_CONSTRAINT: a registered annual nameplate capacity overrun remains unresolved.
- NOT_IDENTIFIABLE: a required historical actual or explicit forward assumption is missing, misclassified, invalid, source-ineligible or inconsistent.
- CALCULATED_AND_RECONCILED: all required inputs are usable and net-profit attribution residual is within CNY 1.
- PARTIAL: only some Bear/Base/Bull scenarios are fully identifiable.
- DIAGNOSTIC_CALCULATED: all three scenarios reconcile.

Tax is deliberately a proxy: the model does not estimate loss carryforwards, deferred taxes, tax incentives or non-recurring tax adjustments. This node is not reported net profit, net profit attributable to owners, EPS, FCF or per-share value. Non-controlling interests and diluted shares remain future work; missing values are not inferred. No B5/B6/valuation input, 15% annualized-return hurdle, formal admission, decision state or execution authority is modified.

## Output and report

The result is nested inside operating_driver_forecast.baseline_transition.net_profit_bridge, preserving the existing Replay comparison path without a new top-level analysis field. The Chinese report shows historical measure data classes and source references, each scenario's baseline/forward modeled profit, expense/tax effects, reconciliation residual and missing-input blockers.

## Regression cases and validation

Four B56 cases were added to tests/test_local_investment_pilot_v01.py: complete bridge reconciliation, misclassified/missing historical baseline, missing forward tax rate localized to one scenario, and report/EPS boundary visibility. These cases are authored but not executed. No Replay, CI, merge or macOS end-to-end acceptance is claimed.
