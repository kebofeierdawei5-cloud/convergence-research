# B6 — Price zone, binding constraint and sensitivity ladder (2026-10-15)

## User problem addressed

B5 now updates project-adjusted per-share scenarios only when its EPS-multiple bridge is complete and the operator confirms that the baseline excludes the project. B6 explains how the existing entry-return, annualized-return and Bear-risk caps constrain the current input price; it is not a second return solver.

## Binding entry-price cap

B6 consumes the existing `return_metrics` outputs and reports the minimum valid price cap among:
- entry-return cushion of at least 15%;
- expected annualized return of at least the 15% fundamental hurdle;
- expected annualized return of at least the required return;
- Bear-case loss within the existing max-loss constraint.

Equal minimum caps are reported as tied constraints. B6 does not modify any thresholds or recalculate their formulas independently.

The current price is classified against this combined cap and the current entry-value reference: at/below the combined cap; above the cap but at/below the reference value; above the reference value; or UNKNOWN when the inputs do not support classification.

## 90% / 100% / 110% price ladder

B6 re-runs the **existing `_return_metrics` path**, which calls the current v0.3 `calculate_return_metrics` solver, at 90%, 100% and 110% of the operator-entered current price. Each row reports annualized return, entry-return cushion, Bear return, individual price-gate pass/fail values, aggregate return-gate result and each corresponding cap. The 100% row is checked against the primary current-price result to detect drift.

The sensitivity calculation uses the post-B5 forecast valuation returned by the preparation step, so a valid B5-adjusted Base entry-value anchor and per-share scenarios are the source of truth. Where B5 does not apply, its unchanged base valuation is used.

## Action boundary

B6 emits `IIOS-PRICE-ZONE-SENSITIVITY-0.1` under the analysis JSON and a Chinese report section, with explicit `price_screen_only=true` and `decision_action_changed=false`. It is not allowed to upgrade an action. The independent existing decision kernel still determines the provisional action and retains Trust, Thesis, MIE/expectation-gap, evidence, risk and portfolio constraints. Missing/invalid return inputs keep the zone and all sensitivity rows UNKNOWN.

No data acquisition, formal admission, authentication/signature gate, price threshold or portfolio policy was added. No order execution is possible. CI is not a new real macOS acceptance.
