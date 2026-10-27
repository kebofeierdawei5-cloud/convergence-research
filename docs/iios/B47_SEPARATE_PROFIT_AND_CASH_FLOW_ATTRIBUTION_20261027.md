# B47 — Separate profit variance from cash-flow / working-capital attribution

Date: 2026-10-27  
Branch: `feat/b45-normalized-earnings-variance-attribution-20261027`  
Status: branch-only; regression cases authored but deferred and not run.

## Objective

B45 explains the difference between B4 forecast net profit and the normalized-net-profit point. B46 translates that reconciled net-profit variance into a conditional EPS / constant-P/E sensitivity. B47 adds a separate cash-flow path so neither layer silently implies that higher accounting profit necessarily means higher free cash flow.

## One-to-one causal mapping

For every evaluated B45 attribution item and scenario, `cash_flow_assessments` must supply one row with:

- `scenario` and `attribution_id` matching the profit-attribution item;
- identical `driver_id` and `review_trigger_id`;
- channel, direction, quantification status, a meaningful rationale, and cutoff-compatible `evidence_refs`. At least one cash-assessment source reference must overlap the linked review trigger's evidence references.

A missing row, duplicate row, orphan row, changed driver or trigger link, unresolved source, after-cutoff evidence, or timing-uncertain evidence is a review blocker for the cash-flow path and the overall diagnostic chain.

## Cash-flow contract

Channels: `OPERATING_CASH_CONVERSION`, `WORKING_CAPITAL`, `INVENTORY_MOVEMENT`, `CAPEX`, `NON_CASH_EARNINGS`, `FINANCE_CASH_COST`, `TAX_CASH_TIMING`, `NO_DIRECT_CASH_EFFECT`, `UNKNOWN`.

Directions: `IMPROVES_FCF`, `REDUCES_FCF`, `MIXED_OR_TIMING_DEPENDENT`, `NO_DIRECT_EFFECT`, `UNKNOWN`.

Quantification status: `QUANTIFIED`, `QUALITATIVE_ONLY`, `NOT_APPLICABLE`, `UNKNOWN`.

- `QUANTIFIED` requires a typed CNY `cash_flow_effect_cny`, an identifiable basis, evidence checks, a decision-usable B4 scenario, and the applicable B4 channel amount. Positive amounts mean an FCF improvement; negative amounts mean an FCF reduction. This sign is **not** the sign of the working-capital balance change.
- Quantified direction must agree with the amount's sign. Incomplete context or direction mismatches withhold the numeric amount from the report.
- `NO_DIRECT_CASH_EFFECT` is allowed only with direction `NO_DIRECT_EFFECT` and status `NOT_APPLICABLE`. It is an explicit assessment, not a blank default.
- A cash-flow item must use the same review trigger as its net-profit attribution, and that trigger must name the same driver.

## Reading the B4 cash context without inventing normalized FCF

The report separately exposes B4's own decision-usable cash-capex, working-capital, inventory-impact-proxy, inventory-treatment/reconciliation, depreciation, finance-cost, and unlevered-FCF-proxy fields for each scenario. If B4 financial outputs are not decision-usable, the context is marked accordingly and cannot support a quantitative assessment.

The cash-flow assessment is **not** itself a normalized FCF forecast. There is no normalized FCF Bear/Base/Bull comparator in this contract. Consequently:

- the diagnostic does not add individual driver amounts into a purported total FCF variance;
- `normalized_fcf_comparison_available` and `fcf_variance_reconciled` remain false;
- the B4 inventory cash impact is still a cost proxy, not the full accounting value of inventory;
- net-profit / EPS calculations do not automatically flow into FCF;
- none of this changes B4, B5, B6, primary valuation, target entry price, annualized return hurdle, portfolio sizing, Decision, or execution authority.

## Wiring and deferred verification

The research template now includes `operating_driver_forecast.cycle_earnings_monitor.cash_flow_assessments`, and the Round A prompt describes the separate path and its sign/evidence constraints. The evaluated node is nested inside `cycle_earnings_monitor`, already present in `REPLAY_COMPARISON_FIELDS`; no separate handoff or Replay field was added.

Six regression cases were authored for separate profit/cash paths, trigger drift, lack of usable B4 cash context for quantification, missing source evidence, direction/sign mismatch, and source overlap with the review trigger. `tests/test_cycle_earnings_monitor_v01.py` now contains 24 authored tests total. **None were run for this batch.** No Replay, CI, PR, merge, or macOS acceptance was performed. Real macOS two-round full-run + independent Replay remains OPEN / NOT VERIFIED.
