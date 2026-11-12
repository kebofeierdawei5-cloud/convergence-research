# B42 — Production/sales inventory balance and working-capital reconciliation (2026-10-26)

**Status:** branch-only implementation, not merged and not canonical. Branch: `feat/b42-inventory-working-capital-20261026`, based on canonical `main@2fd009b10bd4b13467ebdd8b2692eab62a772878`.

## Objective

Close the operating bridge gap where revenue and variable cost are based on sales volume, while production volume has no explicit inventory/cash relationship. Normalize product-name whitespace consistently at the source boundary.

## Contract

For each product line:

- `inventory_change_tonnes = production_tonnes - sales_volume_tonnes` when both inputs are calculation-usable.
- Positive difference means inventory build / potential cash use; negative difference means inventory drawdown / potential cash release; zero means no modeled production-sales inventory movement. This is a **production-sales balance proxy**, not a full beginning-to-ending inventory ledger; opening inventory, work in process, yields/losses, transfers and other accounting adjustments are not reconstructed.
- `inventory_cash_impact_proxy_cny = inventory_change_tonnes × variable_cost_cny_per_tonne` only when this proxy is identifiable. It is a simplified variable-cost proxy, **not** full accounting inventory valuation; it may omit fixed manufacturing cost, work in process, yield loss, product mix and inventory valuation adjustments.
- `inventory_working_capital_treatment` must be one of:
  - `INCLUDED_IN_CHANGE_WORKING_CAPITAL`: the supplied `change_working_capital_cny` is total working-capital change and already includes inventory movement; do not add the inventory proxy again.
  - `EXCLUDED_FROM_CHANGE_WORKING_CAPITAL`: the supplied amount excludes inventory movement; add the modeled inventory proxy only when the product-level balance and cost proxy are usable.
  - `UNKNOWN`: where a tonnage basis exists, a nonzero or unknown production-sales movement without a declared treatment blocks a usable FCF result.
  - `NOT_APPLICABLE`: accepted only if no tonnage basis is present or every product-level inventory movement is zero.
- The original `change_working_capital_cny` stays as the declared input. `effective_change_working_capital_cny` shows the value actually subtracted in the FCF proxy. A missing/contradictory reconciliation leaves FCF unavailable and downstream financial outputs non-decision-usable.
- Product names collapse leading/trailing and repeated Unicode whitespace into one ASCII space before blank-name validation and output. Whitespace-only product names remain invalid rather than becoming a usable placeholder.

## Scope and safety

This is a bounded change to the non-canonical local pilot's operating bridge and report. It does not change valuation formulas, the 15% annualized return hurdle, Required Return, forecast/valuation admission, portfolio policy, decision authority or execution behavior. B33's real macOS two-round full-run + independent Replay acceptance gate remains OPEN / NOT VERIFIED.

## Deferred verification

Regression cases are included for working-capital-included, working-capital-excluded, unknown treatment, signed inventory movement, report visibility, and Unicode whitespace/blank product names. Per operator instruction, unified tests, Replay and CI have **not** been run or triggered in this batch. No PASS is claimed.
