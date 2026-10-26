# B43 — Reconcile FCF-effective working capital across the B4-to-valuation bridge (2026-10-26)

**Status:** branch-only follow-up, not merged or canonical. Branch: `feat/b43-effective-wc-cross-node-reconciliation-20261026`, based on B42 branch head `d4c2ad12e450b2bd0c4048240a2a73612a26276b`.

## Finding

B42 distinguishes the declared `change_working_capital_cny` input from `effective_change_working_capital_cny`, which is the total actually subtracted when calculating the B4 FCF proxy. If the input expressly excludes inventory and B42 adds the inventory cash proxy, the declared input is no longer the total used in the cash-flow formula.

The existing cross-node reconciliation previously compared the raw B4 `change_working_capital_cny` against `forecast_valuation.scenarios.*.operating_financial_bridge.change_working_capital_cny`. That could incorrectly report a match when the B4 FCF calculation had added inventory but the valuation bridge had not, or report a false mismatch when the valuation bridge already used total working capital.

## Change

B43 changes the reconciliation pair to:

`operating_driver_forecast.scenarios.*.effective_change_working_capital_cny`

versus

`forecast_valuation.scenarios.*.operating_financial_bridge.change_working_capital_cny`.

The raw B4 input remains present for audit and display. It is not substituted into the comparison as if it were the effective total.

## Regression contract

A focused regression fixture supplies raw non-inventory working capital of 3,000, an inventory proxy of 20,000 and effective total working capital of 23,000; the valuation bridge states 23,000. The cross-node check must compare effective B4 value 23,000 against the valuation bridge and return MATCH for that pair.

## Boundary

B43 does not alter B4 profit calculations, the inventory proxy method, valuation formulas, the 15% annualized return hurdle, Required Return, valuation admission, Decision authority or execution behavior. This is a source-level regression case only. No tests, Replay or CI have been run or triggered; B42/B43 remain unmerged and the real macOS two-round acceptance gate remains OPEN / NOT VERIFIED.
