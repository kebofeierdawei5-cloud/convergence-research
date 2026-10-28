# B49 — Component-Level FCF Variance Reconciliation

**Status:** implemented on the feature branch; unmerged and non-canonical. **Validation:** tests are authored but not run; Replay, CI, and macOS full-run acceptance remain deferred / not verified.

## Purpose

B48 reconciles the FCF bridge total. B49 closes a residual attribution gap: total contributions may sum to the correct B4-minus-normalized FCF difference even when category amounts are assigned to the wrong economic drivers. A reconciled total is therefore insufficient without independently measured component deltas.

B49 is diagnostic-only. It does not alter B4/B5/B6, valuation scenarios, the entry-price ceiling, the 15% annualized return hurdle, portfolio constraints, position sizing, or a decision status. It creates no formal Forecast/Valuation admission and no execution authority.

## Component formula and sign convention

Both B4 and normalized FCF must reconcile within CNY 1 to:

`FCF = EBIT - max(EBIT, 0) × tax_rate + depreciation/amortization - cash_capex - effective_change_working_capital`

The variance sign remains:

`B4 FCF - normalized FCF`

A positive contribution raises B4 FCF relative to normalized FCF; a negative contribution lowers it.

For each Bear/Base/Bull scenario the bridge measures five categories:

| Category | Measured B4-minus-normalized contribution |
|---|---|
| `OPERATING_CASH_CONVERSION` | B4 after-tax EBIT proxy minus normalized after-tax EBIT proxy |
| `NON_CASH_EARNINGS` | B4 depreciation/amortization minus normalized depreciation/amortization |
| `CAPEX` | Normalized cash capex minus B4 cash capex |
| `WORKING_CAPITAL` | Depends on the inventory treatment described below |
| `INVENTORY_MOVEMENT` | Depends on the inventory treatment described below |

All five categories must be present in `fcf_variance_attribution`, including explicit zero rows. For each category, the sum of user-provided attribution rows must match the independently measured category contribution within CNY 1. The five measured component contributions must also sum to B4-minus-normalized FCF within CNY 1, and the full attribution total must reconcile within the same tolerance. A zero total residual cannot override a category mismatch.

## Component → driver → review trigger → evidence contract

The B49 baseline permits **one numeric attribution row per Bear/Base/Bull component category** when no independently measured driver-level decomposition is available. B50 adds a narrowly bounded exception: multiple rows are permitted only when every row carries typed B4 and normalized component measures, the contribution is independently recomputed, and the driver-level B4 values and normalized values each reconcile separately to their own aggregate component totals. This prevents the category total from passing through offsetting or invented sub-amounts.

The row must still resolve to a known `driver_id`, a review trigger with the same driver, and valid evidence. In addition, the row amount evidence references must overlap the evidence references for the corresponding normalized-FCF component:

- `OPERATING_CASH_CONVERSION`: both EBIT and tax-rate evidence;
- `NON_CASH_EARNINGS`: depreciation/amortization evidence;
- `CAPEX`: cash-capex evidence;
- `WORKING_CAPITAL`: raw working-capital evidence when inventory is excluded, otherwise effective-working-capital evidence;
- `INVENTORY_MOVEMENT`: inventory cash-impact-proxy evidence when inventory is excluded; otherwise effective-working-capital evidence must support the explicit zero standalone contribution.

The amount evidence must independently overlap the linked trigger evidence as well. A shared driver ID alone, or a total that happens to reconcile, is insufficient. Under B50, multiple rows in one category must also identify distinct drivers; duplicate rows for the same driver are rejected even if their measure IDs differ. Missing component evidence, a mismatched link, or multiple numeric rows without valid B50 structured measurements withholds the affected amounts and prevents the scenario from being marked reconciled. The normalized component evidence references used by each row-level gate are preserved in the machine output and rendered beside the attribution amount, driver, and review-trigger ID so the reviewer can inspect the chain.

## Inventory and working-capital treatment

- **Inventory included in reported/raw working capital:** `WORKING_CAPITAL` is measured as normalized effective working capital minus B4 effective working capital. `INVENTORY_MOVEMENT` must be exactly zero as a separate contribution because inventory is already embedded in the effective working-capital total.
- **Inventory excluded from raw working capital in both paths:** `WORKING_CAPITAL` is normalized raw non-inventory working-capital change minus B4 raw non-inventory working-capital change. `INVENTORY_MOVEMENT` is normalized inventory cash-impact proxy minus B4 inventory cash-impact proxy. Their sum must match the normalized-minus-B4 effective-working-capital delta, so inventory is neither omitted nor double-counted.
- **Inventory not applicable in both paths:** working capital uses the effective-working-capital difference and the separate inventory contribution is zero.
- **Treatment mismatch, missing proxy, or inconsistent arithmetic:** do not assert component reconciliation. The result remains `REVIEW_REQUIRED` or `NOT_COMPARABLE`.

B4 is also independently checked for its own inventory reconciliation and for consistency between its reported FCF proxy and its typed cash components. Normalized-FCF component checks from B48 remain prerequisites.

## Output and fail-closed behavior

The new `normalized_fcf_bridge.component_variance_bridge` node contains scenario-level B4 and normalized component values, measured contributions, component residuals, inventory treatment basis, issues, and a diagnostic-only eligibility flag. `variance_attribution.scenarios[*].component_attribution_reconciliation` exposes the measured amount, attributed category total, residual, and status for each required category.

The bridge must fail closed if any of the following occur:
- `normalized_fcf.metric` is omitted, unknown, or different from `UNLEVERED_FCF_PROXY_CNY`; the evaluator must not silently supply the expected metric identifier.
- B4 FCF does not reconcile to its components within CNY 1.
- Any required component is absent or invalid.
- B4 and normalized inventory treatments are not comparable.
- B4 and normalized FCF must agree on both inventory treatment and reconciliation status; `ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED` and `NOT_APPLICABLE_NO_TONNAGE_BASIS` are distinct states, not interchangeable evidence.
- Raw non-inventory working capital plus inventory proxy does not equal effective working capital when inventory is excluded.
- Any of the five measured categories is missing or misattributed by more than CNY 1.
- Any scenario total remains unreconciled.

The renderer now shows component contributions and category-level reconciliation alongside the B48 reference/adjustment bridge. The local research prompt requires the B49 inputs and rules.

## Deferred validation

B49 regression tests have been added to `tests/test_cycle_earnings_monitor_v01.py`. They are authored, not executed, per the current direction to finish core functionality before a unified test pass. No claim of test pass, Replay match, CI pass, or macOS acceptance is made. The feature branch remains unmerged.
