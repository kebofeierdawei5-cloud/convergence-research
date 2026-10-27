# B44 — Industry cycle, normalized earnings, and position-review causal chain

**Date:** 2026-10-27  
**Branch:** `feat/b44-cycle-normalized-earnings-review-chain-20261027`  
**Status:** Implemented as branch-only code; not merged. Regression tests are authored but deliberately not run. Replay and CI are deferred by operator direction.

## Problem addressed

The pilot already models product-level operating drivers (B4), per-share value transmission (B5), valuation/return calculations (B6), and thesis reassessment language. However, those pieces do not yet require one structured object to tie the industry-cycle claim and its counter-evidence to a normalized earnings range, then to observable reversal signals and a holding-review trigger. Text in separate fields can look coherent without sharing stable driver identities, periods, scope, and numerical reconciliation.

## Implementation

- Adds `iios_mvp/cycle_earnings_monitor_v01.py` with schema `IIOS-CYCLE-EARNINGS-MONITOR-0.1`.
- The raw node is nested under Round A's existing `operating_driver_forecast.cycle_earnings_monitor` input, preserving the B33 price-blind prompt, response allowlist, frozen-artifact shape, and Round B's inability to rewrite Round A.
- Industry-cycle assessment records a supported phase, a separate counter-evidence set, named leading indicators, thresholds/review dates, and reversal signals linked to indicator IDs. Evidence references are checked against the existing evidence register and time-status gate; this remains a pilot-level check, not formal admission.
- Bear/Base/Bull normalized net-profit ranges require an explicit reference-profit measure, a separate `reference_period` and normalized target `period`, plus signed rationale-bearing adjustments. Each point estimate must reconcile to reference profit plus adjustments within CNY 1; each scenario must have low ≤ point ≤ high; the scenario point estimates must be ordered Bear ≤ Base ≤ Bull.
- The normalized target period and scope are compared with B4's forecast period and scope. Where aligned and **all three** B4 scenario net profits are calculable, differences to B4 net profit are shown as diagnostics. Missing B4 scenarios cannot produce an aggregate comparison PASS; the monitor never automatically selects or replaces B4 values.
- Review triggers must reference a recognized driver and specify a condition, threshold, review date, operating impact, valuation path, and an ordered chain from `INDUSTRY_CYCLE` through `NORMALIZED_EARNINGS`, `EPS_OR_FCF`, and `PER_SHARE_VALUE` to `POSITION_REVIEW`.
- Adds a B44 report section and top-level analysis projection, while keeping the raw payload nested in the B4 input so the existing Round A freeze and Round B protection continue to apply. The evaluated node is included in `REPLAY_COMPARISON_FIELDS`. After B5/primary-model selection and timing are finalized, B44 also reads the current Bear/Base/Bull terminal per-share values and entry anchor as read-only context; missing model eligibility, timing, anchor or scenario values leaves the value node unidentified. It explicitly marks that it does not recompute per-share value from normalized earnings.

## Hard boundaries

B44 is a diagnostic chain only. It does not replace B4 net profit/FCF, amend the B5 EPS_MULTIPLE or SOTP adapters, feed normalized profit directly into a valuation, change the 15% annualized hurdle or holding-period semantics, pass formal Evidence/PIT/Forecast/Valuation admission, generate a canonical Decision, modify portfolio risk authorization, or place trades. Missing evidence, a missing counter-case, inconsistent period/scope, unreconciled adjustments, or broken IDs/causal paths remain visible as `REVIEW_REQUIRED`.

## Deferred verification

`tests/test_cycle_earnings_monitor_v01.py` covers complete diagnostic chain, period mismatch, missing counter-evidence/reversal signals, arithmetic reconciliation, after-cutoff evidence, and unknown input. The tests have **not** been executed. No Replay, CI, PR, merge, or macOS acceptance was performed. The current-main two-round macOS full-run + independent Replay remains OPEN / NOT VERIFIED.
