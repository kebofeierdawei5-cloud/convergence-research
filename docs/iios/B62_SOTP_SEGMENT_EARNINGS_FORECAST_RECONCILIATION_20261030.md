# B62 — B4 normalized segment earnings ↔ SOTP ↔ current-price hurdle reconciliation

Date: 2026-10-30

Status: implementation proposal on feat/b45-normalized-earnings-variance-attribution-20261027; not merged, not tested.

## 1. Investor question

For the same forecast period and the same defined earnings basis:

- What normalized parent-attributable profit does B4 independently forecast for each business segment?
- What segment profits and P/E multiples are currently used by the selected SOTP scenario?
- Given the protected current price, current holding-period return hurdle and B61's required total segment-equity pool, what does the complete B4 segment forecast imply?
- Is the gap explained by segment operating earnings, selected segment P/E, parent-level adjustments, net cash/debt, other adjustments, or diluted share count?

B62 is a reconciliation and sensitivity layer. It does not decide whether the B4 forecast is true, whether SOTP multiples are fair, or what the external market consensus is.

## 2. Three different inputs; do not blend their authority

### B4 product operating forecast

B4 product-line data use product_id. Each product line may additionally provide a stable business_segment_id. Several product lines may map to one business segment. The map must be explicit and ID-based; product/segment name matching is prohibited.

A COMPANY_WIDE B4 forecast is required. PROJECT_INCREMENTAL and PRODUCT_LINE scope cannot be silently elevated into a complete SOTP segment forecast.

### Segment-specific financial inputs

B4's new historical_segment_financials array contains one row per mapped segment. Every Bear/Base/Bull scenario contains a segment_financials array with the same segment IDs.

Each row requires these typed measures:

| Field | Unit | Historical class | Forward class |
|---|---|---|---|
| fixed_cash_opex_cny | CNY | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |
| depreciation_amortization_cny | CNY | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |
| finance_cost_cny | CNY | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |
| tax_rate | ratio (0–1) | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |
| recurring_non_operating_pre_tax_cny | CNY | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |
| non_recurring_pre_tax_cny | CNY | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |
| minority_interest_net_profit_after_tax_cny | CNY | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |
| minority_interest_nonrecurring_after_tax_cny | CNY | OBSERVED_ACTUAL | ISSUER_FORECAST / ANALYST_ASSUMPTION |

Each measure keeps its own value, unit, data_class, basis, and evidence_refs. Missing values do not default to zero. A zero must be explicitly supported. Group-level fixed cost or minority interest may not be allocated to segments by revenue or by an unsupported percentage.

### SOTP selected scenario

The SOTP input/output adds a pass-through earnings_basis label for each segment. No SOTP arithmetic changes. B62 compares only NORMALIZED_PARENT_ATTRIBUTABLE, which means same-period parent-attributable normalized net profit after excluding non-recurring items and subtracting normalized NCI.

If the selected SOTP profit is all-items, pre-NCI, post-NCI on a different basis, or unlabelled, B62 returns a non-comparable status rather than inferring comparability.

### B61 price inversion

B61 already calculates the required total equity and required segment equity pool for Required Return, along with separate one-at-a-time segment profit thresholds. B62 consumes the B61 without_distributions Required Return view for a clear baseline. It does not re-solve or modify B61.

## 3. B4 segment normalized earnings bridge

For segment s, B55's already reconciled product contribution is summed over its explicitly mapped products:

C(s,t) = sum over products p in s of [sales(p,t) × net ASP(p,t) − variable cost(p,t)]

For historical and forward periods separately:

CorePBT(s,t) = Contribution(s,t) − FixedOpex(s,t) − D&A(s,t) − FinanceCost(s,t)

CoreTax(s,t) = max(CorePBT(s,t), 0) × TaxRate(s,t)

CoreNP(s,t) = CorePBT(s,t) − CoreTax(s,t)

Add only the explicit recurring non-operating pre-tax amount for normalized profit:

NormalizedPBT(s,t) = CorePBT(s,t) + RecurringNonOperating(s,t)

NormalizedTax(s,t) = max(NormalizedPBT(s,t), 0) × TaxRate(s,t)

NormalizedConsolidatedNP(s,t) = NormalizedPBT(s,t) − NormalizedTax(s,t)

NormalizedNCI(s,t) = TotalNCI(s,t) − NonRecurringNCI(s,t)

NormalizedParentNP(s,t) = NormalizedConsolidatedNP(s,t) − NormalizedNCI(s,t)

Non-recurring effects are calculated separately as all-items diagnostics, not included in normalized earnings. The modeled tax rule is deliberately limited; it does not model loss tax assets, deferred tax, tax incentives or special tax effects.

The historical-to-forward normalized parent profit change is decomposed into B55 contribution change, fixed cost, depreciation, financing, core modeled tax, recurring non-operating after-tax effect and normalized NCI effect. The core profit identity and the normalized parent-profit identity each reconcile within CNY 1. If a required input is missing, incorrectly classified, out of scope, or not supported by source/cutoff checks, the relevant segment/scenario remains UNKNOWN or blocked.

## 4. B62 current-price comparison

For scenario q, let B4's normalized parent-attributable forecast for segment s be NP(B4,s,q), and the selected SOTP terminal multiple be PE(s,q).

The complete B4 forecast segment pool under unchanged SOTP multiples is:

B4SegmentPool(q) = sum over segments s of NP(B4,s,q) × PE(s,q)

B62 compares this with the B61 required segment pool for the Required Return hurdle without distributions:

SegmentPoolHeadroom(q) = B4SegmentPool(q) − RequiredSegmentPool(B61,q)

The implied total equity and per-share terminal value keep the selected B61 parent-level adjustments fixed:

B4Equity(q) = B4SegmentPool(q) − CapitalizedCentralCost(q) + NetCashDebt(q) + OtherAdjustments(q)

B4TerminalValuePerShare(q) = B4Equity(q) / DilutedShares(q)

This is a complete vector comparison in which all B4 segment earnings replace the current selected SOTP scenario at once. It is not the sum of one-at-a-time sensitivities.

For each segment, the report separately displays:
- B4 forward normalized parent-attributable profit.
- Current selected SOTP attributable profit and P/E.
- B4-minus-SOTP earnings difference.
- The value effect of that profit difference at the unchanged selected SOTP P/E.
- B4 forecast profit minus B61's one-at-a-time signed required profit.
- A second conditional sensitivity: the P/E required for this segment's B4 forecast profit to meet the Required Return pool when all other segments remain at their B4 forecast profits, plus selected P/E minus that required P/E. This is one segment's P/E sensitivity, not a sum of segment P/E targets.

The last comparison keeps B61's original interpretation: the selected segment changes while all other segment profits remain at the current selected SOTP scenario. These alternative segment thresholds must never be summed.

## 5. Explaining the hurdle gap

B62 displays the selected capitalized parent central cost, net cash/debt, other adjustments and diluted shares. It also shows:
- the direction in which a +CNY 1 change to each parent adjustment changes the required segment pool;
- the B4-implied break-even diluted share count at the required terminal value per share;
- the additional required terminal equity caused by a 1% increase in diluted shares.

B62 quantifies the change from B4 segment earnings through the unchanged SOTP P/E, and also calculates a conditional one-segment required P/E threshold using the B4 full-forecast vector as the other-segment reference. It does not claim that this required P/E is fair, observable or likely; it is a hurdle-implied sensitivity only. It must not attribute an amount to a future parent cost, cash/debt or other-adjustment change when no explicit forward assumption is supplied. In that case the explanation is NOT_IDENTIFIABLE_WITHOUT_EXPLICIT_FORWARD_PARENT_ADJUSTMENT_INPUTS.

## 6. Placement and safety boundary

B4 output:
operating_driver_forecast.baseline_transition.segment_normalized_earnings_bridge

B62 output:
assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.segment_earnings_reconciliation

No new top-level JSON field is created. B62 does not change:
- B4/B5/B6 formulas or inputs;
- the SOTP primary model or the B61 inversion;
- external MIE or expectation-gap status;
- target entry price, 15% annualized hurdle or required-return policy;
- portfolio constraints, Decision, formal admission or execution authority.

## 7. Status and acceptance

Only a complete, same-scope, same-period, same-segment-universe, same-earnings-basis and reconciled comparison can return CONDITIONAL_RECONCILIATION_CALCULATED. Missing or inconsistent mappings, a B4 bridge blocker, a non-normalized SOTP earnings basis, a period mismatch or a failed arithmetic identity remains visible as blocked, partial, not comparable or not identifiable.

Eight regression cases are authored in tests/test_local_investment_pilot_v01.py. They have not been executed. Replay, CI, unified validation and macOS acceptance have not been performed. This design/code batch is not a PASS or formal investment admission.
