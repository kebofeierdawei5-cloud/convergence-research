# B68 — 现价隐含经营要求反向工程

Date: 2026-10-31

Status: branch proposal on feat/b45-normalized-earnings-variance-attribution-20261027; not merged, not tested.

## 1. Objective

B68 translates the conditional profit requirements already calculated by B61/B63 into B4 normalized segment contribution requirements and then into alternative product-level operating-driver sensitivities.

It answers: at the selected SOTP P/Es and the B61 Required Return hurdle implied by the protected current price, what normalized parent-attributable profit and product contribution would be needed? Under a strict one-variable-at-a-time sensitivity, what sales volume, net ASP, or unit variable cost would mathematically achieve that contribution?

B68 is not a new forecast or an automatic distribution of the value gap across business segments or products.

## 2. Two non-additive required-profit lenses

For each segment and Bear/Base/Bull scenario, B68 preserves two separate threshold bases.

### B61 one-segment-at-a-time threshold

Uses B62's b61_one_at_a_time_required_attributable_profit_cny_signed. That threshold changes one segment while all other segments remain at selected SOTP profits. It is an alternative sensitivity for each segment and cannot be summed.

### B63 full-B4-vector threshold at selected P/Es

Starts with B63's full B4 forecast segment value pool and the B61 Required Return required segment pool:

profit_required_for_segment = B4_segment_profit + (Required_segment_pool − B4_full_vector_pool) ÷ selected_segment_P/E

This changes one segment's profit only; every other segment remains at its B4 forecast profit. A positive residual is a shortfall; a negative residual is headroom. The individual segment thresholds are mutually alternative and non-additive.

If B63 is blocked, the B63 lens remains NOT_IDENTIFIABLE. B61 remains separately visible where B62 is reconciled.

## 3. Reverse normalized parent profit into contribution

B68 uses the same B62 normalized parent-attributable formula and the current B4 forward segment assumptions.

Let NCI be the normalized after-tax non-controlling-interest amount and tax rate be t.

target_normalized_PBT_after_recurring_nonop = (target_parent_profit + NCI) ÷ (1 − t) when the result is positive.

For a non-positive result, the existing B62 proxy applies zero modeled cash tax:

target_normalized_PBT_after_recurring_nonop = target_parent_profit + NCI

Then:

required_segment_contribution = required_normalized_PBT + fixed_cash_opex + D&A + finance_cost − recurring_non_operating_pre_tax

Fixed cash opex, D&A, finance cost, tax rate, recurring non-operating amount and normalized NCI are held at B4's typed forward assumptions. The current normalized profit is independently recalculated before accepting the inversion. Missing, inconsistent or out-of-range values stay NOT_IDENTIFIABLE / RECONCILIATION_MISMATCH.

This uses B62's simplified max(PBT,0) × tax_rate rule. It does not model loss carryforwards, deferred tax, tax credits or special tax effects.

## 4. Reverse segment contribution into product drivers

B68 joins B55 product rows to B62 segment rows by explicit business_segment_id and stable product_id. For each product, it calculates three mutually exclusive alternatives:

- Sales-volume-only: required product contribution ÷ unchanged unit contribution margin.
- Net-ASP-only: unchanged unit variable cost + required product contribution ÷ unchanged sales volume.
- Unit-variable-cost-only: unchanged net ASP − required product contribution ÷ unchanged sales volume.

Each alternative holds the other two drivers in the same product and all other products' assumptions fixed. Product revenue and variable-cost effects are recalculated for that alternative. No revenue mix or product-level profit gap is allocated by a guessed percentage.

If a denominator is zero/non-positive, or a required ASP, sales volume, or variable cost is economically non-feasible (non-positive ASP / negative sales / negative cost), that specific alternative remains NOT_IDENTIFIABLE or NOT_FEASIBLE; the other alternatives can remain available.

### Production, capacity and inventory

Sales volume is not production volume. A volume-required output is not considered operationally feasible without an explicit production/inventory release policy. B68 carries the B4 product-master nameplate capacity into the report when present and displays existing production/inventory context, but it does not convert required sales into required production or ignore B42/B43 inventory/working-capital treatment.

## 5. Source and authority handling

B68 carries B55 typed forward data classes, bases and evidence references for each sales-volume / ASP / unit-cost input, as well as B4 segment financial measure lineage. ISSUER_FORECAST and ANALYST_ASSUMPTION remain distinct. A complete structured reference is not semantic verification or formal Evidence/PIT admission.

No B68 output overwrites B4, B55, B62, B63, SOTP selected profit/P/E, external MIE, expectation_gap, the 15% annualized return hurdle, target entry price, portfolio constraints or Decision. It creates no formal forecast admission and no execution authority.

## 6. Output and integration

New module: iios_mvp/sotp_operating_requirement_reverse_engineering_v01.py

Nested output:

assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.operating_requirement_reverse_engineering

Local pilot invokes B68 after B63/B67 and adds a Chinese report section with the two profit-target lenses and product-level one-variable sensitivities.

## 7. Regression coverage and acceptance

Eleven regression cases are authored in tests/test_sotp_operating_requirement_reverse_engineering_v01.py, covering:

- profit-to-contribution inversion under the positive-tax branch;
- volume / ASP / unit-cost alternatives;
- B61 vs B63 threshold separation;
- missing financial/tax input;
- piecewise non-positive PBT tax treatment;
- 100% tax-rate non-identifiability;
- infeasible negative unit cost;
- sales vs production/inventory distinction;
- non-company-wide scope blocking;
- segment-universe mismatch; and
- missing product driver preservation.

Tests have not been executed. Replay, CI, unified tests and real macOS acceptance remain deferred.
