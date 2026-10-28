# B55 — Observed Baseline to Forward Operating Driver Bridge

**Status:** implemented on the feature branch; unmerged and non-canonical. **Validation:** nine B55 regression cases are authored but not run. Replay, CI and real macOS full-run acceptance remain deferred / not verified.

## Why this batch

B4 already stores typed product-line historical actuals (production, sales volume, net ASP and unit variable cost) and Bear/Base/Bull forward assumptions. Before B55, the report showed those values in separate places, but did not explicitly quantify how the same product's forward operating assumptions changed its contribution versus the observed baseline.

B55 adds a deliberately bounded bridge from the historical observed unit-economics baseline to forward scenario contribution. It does not fabricate a company-wide historical net-profit bridge from missing fixed expenses, tax, financing, ownership or diluted-share values.

## Calculation

The comparison is limited to comparable product/line scopes (`COMPANY_WIDE` or `PRODUCT_LINE`) with identical product IDs and explicit full-year periods. The forecast year must be later than the baseline year. Partial years, rolling periods, same-year labels, reversed periods, unknown scope and `PROJECT_INCREMENTAL` are not directly comparable to existing-business actuals.

For each mapped product:

- Baseline contribution = observed sales volume × (observed net ASP − observed unit variable cost).
- Forward contribution = scenario sales volume × (scenario net ASP − scenario unit variable cost).
- The total change is decomposed with a symmetric Shapley allocation so it does not depend on the order in which the three variables are changed:
  - sales-volume effect = change in volume × average of baseline and forward unit contribution;
  - net-ASP effect = change in net ASP × average sales volume;
  - unit-variable-cost effect = negative change in unit cost × average sales volume.

The three computed effects must reconcile to the contribution change within CNY 1. Each product and Bear/Base/Bull scenario is separately statused. Missing baseline or forward inputs remain UNKNOWN; inconsistent historical/forecast reported revenue or variable cost versus their typed volume × price/cost bridge blocks that product's comparison.

## Output placement and report

If B4 is absent or has an invalid schema, the `baseline_transition` node remains present with an explicit `NOT_PROVIDED` or `INVALID_SCHEMA` status; readers need not infer absence from a missing key. The report also shows baseline-level blockers and retains data-class/source-reference lineage for failed rows.

The result is nested in the existing `operating_driver_forecast.baseline_transition` object. The Chinese B4 report now shows:

- comparison status, scope and baseline/forward periods;
- baseline versus forecast revenue, variable cost, contribution and contribution change for each complete scenario;
- volume, ASP and unit-cost contribution effects and reconciliation residual;
- mapped product-level baseline/forward values, changes, and typed data classes/evidence references;
- production/inventory context as a separate disclosure, not included in the contribution decomposition.

This is an explanatory diagnostic only. It does not change B4's financial results, B5 transmission, B6 return/entry-price calculations, the 15% annualized-return hurdle, or formal decision gating. It is not an EPS or per-share-valuation input.

## Explicit limitations

1. Product contribution after variable costs is not operating profit, net profit or FCF.
2. The current template does not consistently provide an aligned historical baseline for fixed cash opex, depreciation/amortization, financing costs, tax rate, non-controlling interests and diluted shares. B55 therefore does not pretend to explain a complete net-profit delta.
3. Production and production-minus-sales inventory movement are shown as context only; inventory/working-capital cash impacts remain on the B42/B43 explicit inclusion/reconciliation path and are not added again to this contribution bridge.
4. An `OBSERVED_ACTUAL` or `ISSUER_FORECAST` designation plus cutoff-compatible source reference is not formal Evidence/PIT admission. `ANALYST_ASSUMPTION` stays an assumption.
5. A fully reconciled bridge means only that the stated unit-economics arithmetic is internally consistent—not that the forecast is likely, that source content is true, or that the current stock price is attractive.

## Regression cases and validation status

Nine cases are authored in `tests/test_local_investment_pilot_v01.py`:

1. Historical baseline to all three forward contribution scenarios reconciles.
2. Symmetric decomposition separates ASP and unit-cost effects.
3. Partial-year / non-forward annual periods block comparison.
4. `PROJECT_INCREMENTAL` is not miscompared to existing-business actuals.
5. Missing historical unit economics blocks contribution comparison.
6. A direct historical revenue conflict blocks the baseline bridge.
7. The report preserves observed-vs-assumption labels and explains that the bridge is not a valuation input.
8. Missing B4 input returns an explicit `NOT_PROVIDED` transition node.
9. Invalid B4 schema returns an explicit `INVALID_SCHEMA` transition node.

They have **not** been executed. No test pass, Replay match, CI pass, or macOS acceptance is claimed.
