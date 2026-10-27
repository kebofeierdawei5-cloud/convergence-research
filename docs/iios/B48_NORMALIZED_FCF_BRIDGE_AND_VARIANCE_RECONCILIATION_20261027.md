# B48 — Independent normalized FCF bridge and variance reconciliation

Date: 2026-10-27  
Branch: `feat/b45-normalized-earnings-variance-attribution-20261027`  
Status: branch-only proposal; authored regression cases are deferred and have not been run.

## Objective

B47 separated cash-flow attribution from net-profit attribution but correctly refused to claim an FCF variance without a normalized-FCF benchmark. B48 introduces that independent benchmark plus a second reconciliation layer. It does not infer normalized FCF from normalized net profit.

## Layer 1 — reference FCF to normalized FCF point

The `normalized_fcf` node requires `metric=UNLEVERED_FCF_CNY`, explicit `scope`, `reference_period`, normalized target `period`, and `normalization_basis`. Bear/Base/Bull each require:

- typed `reference_fcf_cny` in CNY, with basis and evidence provenance;
- explicit, signed typed `adjustments`, each carrying an ID, driver, review trigger, category, rationale, and evidence;
- `low_fcf_cny`, `point_fcf_cny`, `high_fcf_cny`, and `scenario_basis`.

For each scenario the monitor reconciles:

`reference FCF + sum(signed normalization adjustments) = normalized FCF point ± CNY 1`

It also requires low ≤ point ≤ high and Bear point ≤ Base point ≤ Bull point. The adjustment list must explicitly cover all three major channels in every scenario: `CAPEX`, `WORKING_CAPITAL`, and `INVENTORY_MOVEMENT`. A non-applicable/zero contribution must be explicitly stated with a reason; omission does not mean zero. Every adjustment amount must resolve to a source that is compatible with the analysis cutoff and overlap the linked same-driver review trigger's evidence references.

## Layer 2 — B4 FCF to normalized FCF point

The monitor compares `operating_driver_forecast.scenarios[scenario].unlevered_fcf_proxy_cny` with the normalized FCF point only when all three B4 scenarios declare `financial_outputs_decision_usable=true`, scope matches, and forecast period matches exactly. The sign convention is:

`B4 unlevered FCF proxy − normalized FCF point`

Positive means B4 FCF is higher; negative means B4 FCF is lower. This comparison remains a diagnostic, not a valuation input.

## Layer 3 — explicit FCF variance attribution

A separate `fcf_variance_attribution` list explains each comparable Bear/Base/Bull FCF difference. Every item requires `scenario`, `fcf_attribution_id`, `driver_id`, `review_trigger_id`, `category`, `rationale`, and a typed signed CNY `amount_cny`. The driver must be known and match the referenced trigger. The amount's own evidence references must be cutoff-compatible and overlap the trigger's evidence references.

Each scenario's signed contributions must add to the B4-minus-normalized FCF difference within CNY 1. The attribution must explicitly include `CAPEX`, `WORKING_CAPITAL`, and `INVENTORY_MOVEMENT` rows, including reasoned zero contributions where there is no explanatory effect. Missing categories, unresolved inputs, invalid evidence, or an unexplained residual prevent the scenario from claiming reconciliation.

## What B48 deliberately does not do

- It does not infer FCF from net profit, EPS, accounting depreciation, or a profit-only attribution.
- It does not conflate the sign of the working-capital balance movement with the sign of its FCF impact.
- It does not treat the inventory cash-impact proxy as full accounting inventory value.
- It does not aggregate B47 cash-flow assessment items into FCF variance.
- It does not overwrite B4, B5, B6, the primary valuation, target entry price, the 15% annualized return hurdle, position sizing, Decision, or execution authority.
- It creates no formal Forecast/Valuation admission.

The evaluated node is nested under the existing `cycle_earnings_monitor` object, which is already covered by `REPLAY_COMPARISON_FIELDS`. No new top-level result or separate Replay field is added.

## Deferred verification

Seven new regression cases were authored for a reconciled normalized-FCF bridge, an internal bridge residual, an unallocated FCF-variance residual, signed CAPEX/working-capital/inventory contributions, period mismatch, missing component coverage, and evidence/trigger mismatch. `tests/test_cycle_earnings_monitor_v01.py` now contains 32 authored tests total. **None were run for this batch.** No Replay, CI, PR, merge, or macOS acceptance was performed. Real macOS two-round full-run + independent Replay remains OPEN / NOT VERIFIED.
