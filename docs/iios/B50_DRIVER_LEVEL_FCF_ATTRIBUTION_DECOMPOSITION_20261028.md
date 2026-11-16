# B50 — Driver-Level FCF Component Attribution Decomposition

**Status:** implemented on the feature branch; unmerged and non-canonical. **Validation:** five regression cases have been authored but not run. Replay, CI, and macOS full-run acceptance remain deferred / not verified.

## Objective

B49 established component-level FCF reconciliation and deliberately allowed only one numeric attribution row per category until the system could prove the individual driver's component amount rather than accept a manually split category total. B50 introduces that missing contract: multi-driver decomposition is permitted only when every driver row carries explicit, typed measurements for both the B4 side and the normalized-FCF side.

B50 remains diagnostic-only. It does not alter B4/B5/B6, valuation inputs, entry-price ceilings, return hurdles, portfolio constraints, Decision or execution authority.

## Input contract

A row in `fcf_variance_attribution` may include `driver_component_measure`:

- `measure_id`: unique within the scenario;
- `category` and `driver_id`: must exactly match the parent attribution row;
- `component_basis`: a category-specific enum listed below;
- `basis`: a meaningful explanation of how this driver's contribution was measured;
- `b4_value_cny` and `normalized_value_cny`: typed CNY measures, each with a supported `data_class`, meaningful basis, non-empty evidence references, and valid cutoff-compatible source provenance.

Within the same scenario/category, driver IDs must be unique; two measure IDs do not make repeated rows for the same driver a valid multi-driver decomposition. The driver's trigger must exist and name the same driver. B51 tightens provenance linkage: B4-side and normalized-side evidence must each overlap the same driver's trigger evidence independently; the parent `amount_cny` evidence must overlap both side-measurement evidence sets, not only their union; and normalized-side evidence must overlap every corresponding normalized aggregate input required by that component (both EBIT and tax-rate inputs for after-tax operating cash conversion). A gap on any side blocks the driver row. These are reference-link checks only: they make the evidence chain traceable but do not establish that a source's content semantically supports the claimed amount. The amount must still match the computed driver contribution within CNY 1. Downstream reconciliation uses the **computed value**, not an unverified copied amount.

## Component bases and sign conventions

| Category | `component_basis` | Computed driver FCF contribution |
|---|---|---|
| `OPERATING_CASH_CONVERSION` | `AFTER_TAX_EBIT_CONTRIBUTION` | B4 after-tax EBIT contribution − normalized after-tax EBIT contribution |
| `NON_CASH_EARNINGS` | `DEPRECIATION_AMORTIZATION` | B4 D&A − normalized D&A |
| `CAPEX` | `CASH_CAPEX` | Normalized capex − B4 capex |
| `WORKING_CAPITAL` | `RAW_WORKING_CAPITAL_CHANGE` when inventory is excluded; otherwise `EFFECTIVE_WORKING_CAPITAL_CHANGE` | Normalized working-capital change − B4 working-capital change |
| `INVENTORY_MOVEMENT` | `INVENTORY_CASH_IMPACT_PROXY`, only when both paths explicitly exclude inventory | Normalized inventory cash-impact proxy − B4 proxy |

The `AFTER_TAX_EBIT_CONTRIBUTION` values are already the driver-attributed after-tax EBIT portions; they must not be tax-adjusted a second time by the monitor. The sum of those values is checked against the aggregate `EBIT − max(EBIT, 0) × tax_rate` on each side.

When inventory is already embedded in effective working capital, or inventory is not applicable, the separate inventory category remains a single explicit zero row. It cannot be decomposed into multiple rows because that would duplicate an amount already embedded in working capital or invent an inapplicable component.

## Dual-side reconciliation — not just net difference

For each scenario/category containing structured driver measures, the monitor independently requires:

1. Sum of all driver-level `b4_value_cny` values equals the B4 aggregate component within CNY 1.
2. Sum of all driver-level `normalized_value_cny` values equals the normalized-FCF aggregate component within CNY 1.
3. Sum of computed driver-level FCF contributions equals the independently measured B4-minus-normalized category contribution within CNY 1.
4. All five category contributions sum to the total B4-minus-normalized FCF difference within CNY 1.

This prevents a false pass where both sides are wrong by the same amount and their difference happens to match the top-level variance. A claimed contribution that differs from the measured pair, a wrong component basis, a duplicated measurement ID, invalid evidence, or a B4/normalized side-total mismatch keeps the scenario at `REVIEW_REQUIRED` or `NOT_COMPARABLE`.

## Backward compatibility and limits

A single row without `driver_component_measure` remains available as the prior B49 diagnostic path and must still pass the existing driver/trigger, evidence and category-total gates. Multiple rows for the same scenario/category are accepted only when **every** row contains a valid structured measurement. Mixed measured/unmeasured rows fail closed.

A driver measure is not created by splitting a company-level category total. The submitting research must have independent, source-backed B4 and normalized component amounts for that driver. Where those source-backed amounts do not exist, keep the category single-row diagnostic or retain `REVIEW_REQUIRED`; do not manufacture an allocation.

The engine retains each driver's measurement fields, each side's data class and basis, and evidence references in machine output. The Chinese report prints the measure ID, component basis, B4 and normalized values with their data classes/bases, computed contribution, both evidence-reference sets, driver and review-trigger ID.

## Scope and deferred verification

Five regression cases cover a successful two-driver capex decomposition, incorrect gross-side totals despite the same net difference, a claimed amount inconsistent with measured inputs, multiple rows without independent measures, and duplicate driver IDs across rows. They are authored in `tests/test_cycle_earnings_monitor_v01.py` but **not run**. No test pass, Replay match, CI pass, macOS acceptance, formal Forecast/Valuation admission or execution authority is claimed.
