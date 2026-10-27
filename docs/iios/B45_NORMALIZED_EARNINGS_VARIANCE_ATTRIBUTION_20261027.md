# B45 — Normalized-earnings variance attribution

**Date:** 2026-10-27  
**Branch:** `feat/b45-normalized-earnings-variance-attribution-20261027`  
**Base:** B44 branch `feat/b44-cycle-normalized-earnings-review-chain-20261027`  
**Status:** Implemented as branch-only code. Tests are authored but deliberately not run. Replay and CI remain deferred by operator direction.

## Problem addressed

B44 establishes the comparison between B4 Bear/Base/Bull net profit and normalized net-profit points, but a numeric difference alone does not explain why the two differ. Unstructured prose can claim that a gap is due to the cycle without quantifying its contribution, explaining its mechanism, or linking it to a review trigger.

## Implementation

- Adds structured `variance_attribution` under the existing Round-A `operating_driver_forecast.cycle_earnings_monitor` node; no top-level Round-A allowlist expansion is required.
- Sign convention is fixed: **B4 forecast net profit minus normalized net-profit point**. Positive means B4 is higher; negative means B4 is lower.
- Each attribution item requires a unique scenario-scoped ID, Bear/Base/Bull scenario, a recognized driver ID, supported category, meaningful rationale, typed CNY amount, and a `review_trigger_id`. The named trigger must exist and have the same driver ID.
- For every comparable scenario, the signed attribution components must sum to the reported B4-minus-normalized difference within CNY 1. An unexplained residual, missing attribution, unusable component, duplicate identity, invalid category, or trigger/driver mismatch makes that scenario `REVIEW_REQUIRED`.
- Zero differences also need an explicit reasoned zero-contribution row. The module does not manufacture a residual plug or silently label an unassigned remainder as `OTHER`.
- Attribution results and residuals are displayed in the Chinese report, nested under the B44 node in `analysis.json`, and consequently included in the existing `cycle_earnings_monitor` Replay comparison field.
- The node is strictly explanatory. It does not change B4 earnings, B5, B6, EPS, FCF, terminal value, target entry price, return hurdle, or decision authority.

## Category contract

Accepted categories are `INDUSTRY_CYCLE`, `PRICE_VOLUME_MIX`, `UNIT_PRICE`, `UNIT_COST_MARGIN`, `CAPACITY_UTILIZATION`, `FIXED_COST_OPERATING_LEVERAGE`, `FINANCE_TAX`, `NON_RECURRING`, `ACCOUNTING_SCOPE`, `PRODUCT_MIX_OR_PERIMETER`, and `OTHER`. This is a net-profit variance bridge; cash-only capex or working-capital items cannot be passed off as direct net-profit contributors.

## Deferred verification

`tests/test_cycle_earnings_monitor_v01.py` now contains 13 authored tests, including a signed non-zero delta that reconciles, a non-zero residual that must block PASS, missing attribution, and a missing/mismatched review-trigger relationship. These tests have **not** been executed. No Replay, CI, PR, merge, or macOS acceptance was run as part of this batch. The current-main two-round macOS full-run + independent Replay remains OPEN / NOT VERIFIED.
