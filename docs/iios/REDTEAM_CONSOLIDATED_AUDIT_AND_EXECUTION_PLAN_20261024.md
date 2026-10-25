# IIOS Consolidated Red-Team Audit and Execution Plan — 2026-10-24

## Purpose and audit boundary

This document consolidates the first and second red-team reviews against the original IIOS investment purpose: **at this price, is the company worth buying, what future change drives value, what is already implied by the market, and what facts would invalidate the thesis?** The target product remains a personal single-user local-first research workflow, free-first, no paid provider API requirement, no local LLM requirement for the personal pilot, no screening-universe expansion, and no automatic trading.

Audited implementation baseline before B32 was `main@d0cd990aaf866b9f93f34eb328487c975c689809`. B32 is merged as `ac9eab4b7da4787b9df1f8315de0b26be66bf222`; B33 is now merged as `main@9162a6adadbeacda984d2253ce1f776b9c00cd60`. B33 exact tested head `d364bb3ede436cd8cd7151bc63ff8e480442ceda` passed 350 Local Investment Pilot + Replay/acceptance tests and 6/6 triggered workflows. This is code/CI evidence, not a claim that current-main macOS acceptance or investment performance is verified.

## Consolidated findings

### F1 — Current-price leakage into “independent” forecast reasoning (confirmed, priority P0)

The guided wizard currently constructs a single prompt containing the complete price-bearing template, including structured `price_input`, operator valuation controls, MIE/expectation-gap fields and the forecast/valuation schema. The same request asks the model to form the Bear/Base/Bull/operating forecast and answer how much the current price implies. Prompt wording alone cannot establish forecast independence when price is present in the same context.

**Required optimization:** implement two genuinely separated model requests. Round A must receive the company identity, cutoff, primary source context and forecast schema, but not the current price, current valuation multiple/valuation choice, MIE, expectation-gap, current position or portfolio limits. Its company-side forecast and causal evidence artifact must be frozen and hashed. Round B receives that frozen artifact plus protected price/cutoff and performs internal valuation, MIE, expectation-gap, risks, positioning and entry-price analysis. No second LLM/local model or paid API is required; the existing manual browser workflow may remain, with one additional deliberate handoff. Avoid adding speculative predictive models.

### F2 — Computation readiness conflated with independent forecast / valuation gate state (confirmed and repaired in B32)

The pilot had used the existence of return metrics and a non-empty value anchor to set Forecast/Valuation statuses to PASS. This blurred “a numeric result can be calculated” with “the forecast/valuation is admitted and decision-ready.”

**B32 repair:** separate `computation_readiness` (return calculation and primary valuation arithmetic) from `formal_forecast_admission` and `formal_valuation_admission`; the latter remain `NOT_ADMITTED` in the non-canonical pilot. The shared decision-policy input now preserves Forecast/Valuation gate states as UNKNOWN. This does not change valuation arithmetic or the 15% hurdle.

PR [#583](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/583) merged as `ac9eab4b7da4787b9df1f8315de0b26be66bf222`. Exact tested head `1ad65031f0cf11e73553a8d072882a84fda6751d` passed 346 Local Investment Pilot + Replay/acceptance tests and 6/6 triggered PR checks.

### F3 — MIE / expectation-gap cross-field inconsistency (confirmed and repaired in B32)

A submitted expectation-gap claim could remain PASS even when the market-implied expectation was NOT_IDENTIFIABLE or otherwise not PASS. A positive direction field was also passed to the policy kernel without requiring the gap status itself to be PASS.

**B32 repair:** when MIE is not PASS/identifiable, a submitted expectation-gap PASS is preserved as an input diagnostic but downgraded to UNKNOWN, the direction becomes UNKNOWN, and an explicit status issue is emitted. The decision-policy positive-gap flag now requires both gap status PASS and direction POSITIVE.

**Policy boundary deliberately unchanged:** MIE remains optional/explanatory under the current frozen pilot decision policy. This audit does not change it to a universal BUY/ADD hard gate. The essential rule is no fabricated market expectation and no “verified expectation gap” without an identifiable market-side basis. A conditional reverse-engineered scenario may be shown only as a clearly labeled conditional scenario, not as observed market consensus.

### F4 — Real macOS acceptance remains unverified (open gate)

B28–B32 exact-head CI demonstrates code/tests, not the operator's real current-main macOS execution. The current-main full-run + Replay and review of the private bundle remains OPEN / NOT VERIFIED. Historical pilot bundles predating the latest valuation/EPS/SOTP/gating changes cannot be used to accept the current build.

### F5 — Personal pilot and formal canonical runtime remain distinct

Manual ChatGPT Free Web handoff remains `PILOT_NON_CANONICAL`; hashes demonstrate byte integrity, not model-origin assurance or evidence truth. Formal Evidence/PIT admission, appropriate source-use rights/review, formal decision, human approval and full canonical run receipt remain separate gates. These formalization requirements must not be substituted for or made prerequisites to improving the personal non-canonical research workflow. No automatic trading or local LLM is added as part of the personal-pilot fix.

## Decision on scope

**Operator priority update (2026-10-25): core-function completion comes before the full test/acceptance round.** The former B34 real-Mac acceptance gate is deferred and non-blocking during development; it remains OPEN / NOT VERIFIED, not passed. Continue grouped feature work on one branch and run the comprehensive test/Replay/red-team matrix only after the core scope is frozen. Do not add a PR or trigger the full test matrix per micro-batch.

The code scope remains **not** a new valuation model family, new screener, provider API integration, broad anti-tamper project or generic gate expansion. The immediate core-function improvement is explicit industry-cycle position and inflection evidence, normalized through-cycle earnings, and a grounded bridge from the cycle to per-share earnings/cash/value. Follow with report prioritization and monitoring/reassessment/usability gaps as required by implementation findings. Price-blind/price-aware stage separation and fail-closed handling remain in force.

## Execution batches

| Batch | Work | Acceptance criteria | Boundary |
|---|---|---|---|
| B32 | Calculation vs. admission semantics; MIE/gap consistency | Exact-head tests prove unknown admission remains unknown; MIE non-PASS prevents expectation-gap PASS; gap direction cannot override gap status; 346 pilot/replay tests and 6/6 PR checks passed | Merged; no economic formula or MIE policy change |
| B33 | True price-blind Round A / price-aware Round B | 350 Local Pilot + Replay/acceptance tests and 6/6 workflows passed; Round-A allowlist excludes price/position/valuation/MIE/gap fields; frozen company artifact and two-round lineage are hash-bound; Round B cannot patch frozen Round-A fields; receipt/report/bundle verification and Replay comparison include phase summary | Merged PR #585; real Mac acceptance remains open |
| B34 | Core function: explicit industry-cycle and through-cycle earnings reasoning | Development-branch code adds Round-A cycle/turn evidence guidance, distinguishes recovery from restocking/pull-forward/one-offs, requires Round-B normalized-earnings value transmission, and displays a separate cycle/normalization section. No new schema or valuation formula. | Implementation in progress; tests deliberately deferred |
| B35 | Investor-facing report prioritization and monitoring/usability completion | Development-branch code adds a front-loaded causal investment summary: earnings engine, top value drivers, cycle status, internal valuation vs. MIE, return/entry cap, Bear vs. thesis-break stress, thesis failure conditions, reassessment triggers and risk monitoring; prompt guidance requires observable trigger → threshold/direction → review cadence/time → decision implication without invented thresholds. | Implementation in progress on same branch; tests deliberately deferred |
| B36 | Unified validation and current-main Mac acceptance | Exact-head compile/schema/contract tests, full pilot+Replay, independent red-team, relevant CI, then real Mac full run, Replay and private bundle review | After core scope freeze; OPEN / NOT RUN |
| B37 | Grouped remediation and state sync | Fix only findings from the unified gate; retest narrow affected areas during repair, then one final unified gate | After B36 findings |

## Acceptance and frozen investment semantics

- 15% annualized return is a fundamental new-capital return hurdle, not a discount rate.
- Required Return remains a separate operator policy input.
- Default reference horizon remains 1Y; 3Y requires an explicit permitted override and reason. Forecast year and terminal date remain separate.
- Trust > Portfolio Constraint > Long-term Value > Expectation Gap > Tactical remains the intended priority.
- Unknown/unsupported values stay UNKNOWN / NOT_IDENTIFIABLE; do not invent consensus or source verification.
- EPS_MULTIPLE and the bounded CNY SOTP adapter remain as currently implemented; no new model family in B33.
- Formal decision, actual execution and actual dividend entitlement remain false/unconfirmed; no auto-execution.
- Current-main real macOS run + Replay stays OPEN / NOT VERIFIED until an actual operator-environment artifact is independently reviewed.

## Source of truth

- [Canonical state index](../PROJECT_STATE_INDEX.md)
- [Current batch plan](IIOS_BATCH_EXECUTION_PLAN_20261010.md)
- [Current macOS E2E runbook](MACOS_REAL_E2E_ACCEPTANCE_RUNBOOK_20261021.md)
- [Local pilot implementation](../../iios_mvp/local_investment_pilot_v01.py)
- [B32 PR](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/583)
