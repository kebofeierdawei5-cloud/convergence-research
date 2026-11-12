# B46 — Earnings-variance → EPS / constant-P/E sensitivity

Date: 2026-10-27  
Branch: `feat/b45-normalized-earnings-variance-attribution-20261027`  
Status: branch-only proposal; authored regression cases are deferred and have not been run.

## Objective

B45 reconciles the signed company-wide net-profit difference (B4 forecast minus normalized-earnings point) to named driver contributions. B46 adds a downstream, explicitly conditional translation into EPS and fixed-P/E per-share-value sensitivities, so a profit variance is not silently treated as a share-level or valuation conclusion.

## Inputs and calculation

The diagnostic may calculate only when all of the following hold:

- B45 reports `ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY`, and each Bear/Base/Bull scenario remains reconciled.
- The EPS earnings bridge is calculation-eligible; the scenario's bridge row is `CALCULATED`, its declared EPS matches its bridge, and diluted shares are positive and explicitly denominated in `shares`.
- Net-profit variance, EPS bridge and normalized earnings use the same forecast period and CNY currency. No CNY/HKD conversion is inferred.
- The selected primary valuation model is EPS_MULTIPLE; its adapter is `CALCULATED`, selected for the primary model, CNY-denominated, and matches both the EPS bridge period/terminal date and the current primary per-share values.
- Scenario P/E is a positive typed multiple in `x`.

For a scenario, with signed variance defined as B4 net profit minus normalized net profit:

`implied EPS sensitivity = net-profit variance (CNY) / diluted shares`

`constant-P/E value sensitivity = implied EPS sensitivity × selected scenario P/E`

Each B45 attribution item gets the same conditional translation and preserves its `driver_id`, `attribution_id`, and same-driver `review_trigger_id`.

## Fail-closed behavior

Any unresolved upstream variance, period/currency mismatch, missing or nonpositive denominator, non-calculated EPS bridge, invalid P/E, unselected EPS_MULTIPLE adapter, unidentifiable primary value, or adapter/primary-value mismatch prevents numeric sensitivity output for the affected scenario. Incomplete scenarios do not retain partial item calculations in the report.

The metric is **not** a new EPS forecast or fair value. It assumes non-controlling interests, other after-tax attribution adjustments, diluted shares, and P/E remain constant. It is not applicable to SOTP as a constant-P/E computation. It does not alter B4, B5, B6, normalized earnings, the primary valuation, target entry price, the 15% annualized return hurdle, position sizing, a Decision, or order/execution authority. It does not create formal Forecast/Valuation admission.

The evaluated node is nested inside `cycle_earnings_monitor`, already covered by the existing `REPLAY_COMPARISON_FIELDS` entry. No separate Replay field is added.

## Deferred verification

Five new regression cases cover: signed EPS and constant-P/E sensitivity arithmetic; CNY/HKD mismatch; an unreconciled B45 upstream variance; an unselected EPS_MULTIPLE adapter; and explicit exclusion of SOTP from fixed-P/E sensitivity. The file `tests/test_cycle_earnings_monitor_v01.py` now contains 18 authored tests in total. **None were run for this batch**, in accordance with the instruction to defer tests to unified validation. No Replay, CI, PR, merge, or macOS acceptance was performed. Real macOS two-round full-run + independent Replay remains OPEN / NOT VERIFIED.
