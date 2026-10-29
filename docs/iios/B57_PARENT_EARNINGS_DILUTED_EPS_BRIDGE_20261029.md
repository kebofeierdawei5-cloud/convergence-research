# B57 — Parent-attributable normalized earnings and diluted EPS bridge

Date: 2026-10-29  
Status: **BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## Goal

B57 extends B56's modeled after-tax profit proxy to a company-wide normalized net-profit-attributable-to-parent and diluted EPS proxy. It explicitly distinguishes recurring non-operating items, non-recurring items and the portion attributable to non-controlling interests (NCI). It does not claim that its output is reported EPS.

## Inputs

At the operating_driver_forecast input level:

- historical_earnings_attribution contains typed OBSERVED_ACTUAL measures:
  - non_operating_pre_tax_cny: signed net non-operating amount; income positive, expense negative.
  - non_recurring_pre_tax_cny: signed net one-off amount; gain positive, loss negative.
  - minority_interest_net_profit_after_tax_cny: signed after-tax NCI net profit including the entered non-recurring component.
  - minority_interest_nonrecurring_after_tax_cny: signed after-tax NCI share of the non-recurring amount.
  - diluted_weighted_average_shares: positive weighted-average diluted share count.
- Each Bear/Base/Bull scenario may provide the same five fields as explicit ISSUER_FORECAST or ANALYST_ASSUMPTION measures.

Signed metrics are permitted only for the four signed CNY fields above. Units, data-class, basis, evidence-reference and cutoff checks remain enforced. No missing item, NCI allocation or share count defaults to zero. Zero or negative diluted shares block the scenario.

## Calculation

The bridge is company-wide only. A product-line or incremental-project profit cannot be divided by company shares to claim EPS.

For each historical/forward period:

1. B56 PBT proxy + signed recurring non-operating net amount = normalized PBT proxy.
2. Apply B56's explicit effective tax rate using the existing simplified tax rule (max(PBT, 0) × tax rate) to estimate normalized consolidated profit after tax.
3. Add the signed non-recurring pre-tax amount to normalized PBT and reapply the tax proxy to expose a modeled all-items result, clearly labeled as a proxy rather than reported profit.
4. Normalized NCI = total after-tax NCI profit including one-offs − the after-tax NCI share of non-recurring items.
5. Normalized parent-attributable profit = normalized consolidated profit after tax − normalized NCI.
6. Normalized diluted EPS proxy = normalized parent-attributable profit ÷ explicit diluted weighted-average shares.

The change in normalized parent-attributable profit is reconciled to the change in B56 modeled net profit, the after-tax effect of recurring non-operating items, and the change in normalized NCI attribution, within CNY 1. One-off effects are reported separately and are not left inside normalized earnings. EPS growth rate is calculated only when historical normalized diluted EPS is positive; otherwise growth is UNKNOWN / not meaningful.

## Fail-closed states and boundaries

- NOT_COMPARABLE_SCOPE: input scope is not COMPANY_WIDE.
- BLOCKED_BY_B56: B56 scenario lacks a reconciled modeled profit proxy.
- NOT_IDENTIFIABLE: one or more required typed inputs are missing, unusable, source-ineligible or the diluted-share denominator is non-positive.
- CALCULATED_AND_RECONCILED: required inputs are usable and profit attribution reconciles within CNY 1.
- PARTIAL: some, but not all, scenarios are calculable.
- DIAGNOSTIC_CALCULATED: all Bear/Base/Bull scenarios are calculable.

This is not formal admission, a reported financial metric, or a decision input. B57 does not alter B5/B6, valuation multiples, target prices, the 15% annualized return hurdle, formal Decision or execution authority. Tax still uses B56's simplified tax proxy; deferred taxes, tax incentives, loss carryforwards, actual item-specific tax treatment and instrument-specific dilution remain limitations.

## Output and report

Nested at operating_driver_forecast.baseline_transition.per_share_earnings_bridge to preserve the existing Replay comparison scope without adding a new top-level analysis field. Reports expose historical measure lineage, NCI/non-recurring definitions, normalized parent profit, diluted EPS, missing inputs and why non-positive-baseline EPS growth is not calculated.

## Regression cases and validation

Five B57 cases are authored: complete parent-attributable profit/EPS bridge and reconciliation, product-line scope refusal, missing NCI/non-recurring share plus zero dilution denominator, report boundary/visibility, and absent B4 shape. They have not been run. No Replay, CI, merge or macOS end-to-end acceptance is claimed.
