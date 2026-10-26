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

The code scope remains **not** a new valuation model family, new screener, provider API integration, broad anti-tamper project or generic gate expansion. B36 reconciles normalized values to B4 and guards actual EPS-bridge use. B39 adds an independently recomputable operating-driver normalization method to the same candidate contract: volume × net ASP, volume × unit cost, fixed costs, D&A, finance costs, taxes, capex and working capital produce normalized net profit plus a separate FCF proxy. Optional cross-method checks require an explicit reasoned resolution or block adoption on divergence. B40 binds the normalized product ID/name set to B4's exact product universe, requires normalized production per line, and checks production against source-qualified annual capacity only for explicit full-year periods; identity/scope/duplicate/malformed-row issues or a known overrun block adoption. B41 reconciles normalized production, sales volume, net ASP and unit variable cost to source-qualified B4 historical actuals, reports deltas, and blocks any non-zero historical deviation without an identifiable reason plus cutoff-compatible official primary-source refs. Unqualified actuals remain UNKNOWN; no arbitrary threshold or formal Evidence/PIT or Forecast/Valuation admission is introduced. Outputs remain non-admitted analyst assumptions. B42 further reconciles normalized production-minus-sales with the qualified historical flow gap; non-zero or changed gaps need an explicit evidence-backed treatment, and inventory-related treatments must connect to a usable company-wide working-capital input. Missing/inconsistent treatment blocks adoption; no inventory value or materiality threshold is invented. Continue core usability work before the single unified validation round. Price-blind/price-aware phase separation and fail-closed handling remain in force.

## Execution batches

| Batch | Work | Acceptance criteria | Boundary |
|---|---|---|---|
| B32 | Calculation vs. admission semantics; MIE/gap consistency | Exact-head tests prove unknown admission remains unknown; MIE non-PASS prevents expectation-gap PASS; gap direction cannot override gap status; 346 pilot/replay tests and 6/6 PR checks passed | Merged; no economic formula or MIE policy change |
| B33 | True price-blind Round A / price-aware Round B | 350 Local Pilot + Replay/acceptance tests and 6/6 workflows passed; Round-A allowlist excludes price/position/valuation/MIE/gap fields; frozen company artifact and two-round lineage are hash-bound; Round B cannot patch frozen Round-A fields; receipt/report/bundle verification and Replay comparison include phase summary | Merged PR #585; real Mac acceptance remains open |
| B34 | Core function: explicit industry-cycle and through-cycle earnings reasoning | Round A captures cycle stage/turn evidence, counter-evidence, reversal signals, and a structured normalized-earnings profile; guidance distinguishes recovery from restocking/pull-forward/one-offs. Normalized earnings remain a research statement and do not auto-replace B4. | Implemented on development branch; validation deferred |
| B35 | Investor-facing report prioritization and monitoring/usability completion | Report prioritizes causal investment logic and per-item thesis-break/reassessment/risk monitoring. Missing dates/frequency/thresholds remain UNKNOWN; no calendar alerts or capital actions are created; numeric zero is preserved. | Implemented on development branch; validation deferred |
| B36 | Cycle-normalization → B4 → EPS → primary per-share-value reconciliation | Persist typed-dimension/numeric reconciliation, explicit candidate choices, exact cycle-ID linkage, formula lineage and actual three-scenario EPS-consumption checks; original B4/FCF remain preserved. | Implemented on development branch; validation deferred |
| B39 | Normalized operating-driver net profit + FCF bridge and cross-method reconciliation | Recompute normalized revenue, variable cost, contribution, EBITDA, EBIT, PBT, net profit and FCF from typed product/global assumptions; require scope coverage, period/units, cutoff-compatible exchange/regulator-domain evidence, analyst-assumption class and exact Decimal result. Independently recompute optional alternative methods; divergence needs reasoned explicit resolution or blocks adoption. Existing three-scenario adoption/use guards remain. | Implemented on development branch; validation deferred |
| B40 | B4 product scope and physical feasibility for cycle-normalized earnings | Exact product IDs/names vs B4; normalized production is mandatory; known annual capacity checked only for explicit full-year periods; mismatch/duplicate/malformed identities or known overrun block adoption; report exposes reconciliation and UNKNOWN states | Implemented on development branch; validation deferred |
| B41 | Historical actuals comparison and explicit deviation rationale | Compare normalized production/sales/ASP/unit cost to source-qualified B4 actuals; output deltas; non-zero deltas need identifiable reason and cutoff-compatible official primary refs; missing explanation blocks adoption; unknown history stays UNKNOWN | Implemented on development branch; validation deferred |
| B42 | Production/sales flow and inventory working-capital reconciliation | Non-zero or changed production-sales gap requires rationale, explicit treatment and qualified primary evidence; inventory treatment must link to usable global working-capital input; report exposes historical/current gaps and status | Implemented on development branch; validation deferred |
| B37 | Unified validation and current-main Mac acceptance | After core scope freeze: exact-head compile/schema/contract checks, one grouped pilot+Replay and independent red-team round, relevant CI, then real Mac full run, independent Replay, and private bundle review | OPEN / NOT RUN; not a per-batch gate |
| B38 | Grouped remediation and state sync | Fix findings from unified validation, perform only targeted verification during repair, then one final unified gate and real-Mac acceptance | After B37 findings |

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


**B39 implementation complete on development branch `feat/core-function-completion-unified-validation-20261025` (latest code commit `08390da735c906eeb1ed081f66f88d94acd71ff3`):** added the normalized operating-driver bridge and cross-method comparison under the existing formula contract. No tests, CI, Replay, PR, merge or Mac acceptance were run. All changes remain non-canonical and validation is deferred.


B39 implementation complete on development branch `feat/core-function-completion-unified-validation-20261025`, latest code commit `ec7bb9bb214d8b0d248735f0ebd308b536508ce5`. No tests, CI, Replay, PR, merge or Mac acceptance were run; validation remains deferred.


## B40 — B4 product scope and capacity feasibility binding — 2026-10-26

Status: **UNMERGED IMPLEMENTATION / VALIDATION DEFERRED / REAL MAC ACCEPTANCE OPEN**

- The normalized operating-driver bridge compares the full product ID/name set with B4's canonical `product_lines`. Invalid B4 product-identity context blocks adoption; coverage is checked against the actual B4 product set rather than relying only on self-asserted coverage text.
- `normalized_production_tonnes` is required alongside normalized sales volume, net ASP and unit variable cost. Production is not substituted for sales in the profit formula; it is separately checked against known nameplate annual capacity.
- If period is an explicit full fiscal year and B4 has source-qualified annual capacity, production above capacity blocks the normalized candidate. Unknown capacity and non-full-year alignment remain explicit and are not filled with assumptions.
- Duplicate/malformed rows, missing/extra/unmapped IDs and product-name mismatches are reported and block the candidate. Existing cross-method reconciliation, all-three-scenario choice, actual EPS-bridge-use guard and preservation of B4/FCF remain unchanged.
- Latest code commit: `67fb511f9421e40481fa213573f1d5179d77ae27`. No tests, compile check, Replay or unified validation was run; this branch remains unmerged and real Mac acceptance is OPEN / NOT VERIFIED.



## B41 — Historical actuals comparison and deviation rationale — 2026-10-26

Status: **UNMERGED IMPLEMENTATION / VALIDATION DEFERRED / REAL MAC ACCEPTANCE OPEN**

- Per-product historical actuals are reusable as numeric comparison baselines only when each metric has the expected unit, is typed OBSERVED_ACTUAL, is calculation-usable, and its evidence refs are cutoff-compatible with official exchange/regulator-domain class match.
- Normalization outputs expose historical value/period/status, normalized value, absolute delta, relative change where mathematically defined, rationale and supporting refs for production, sales volume, net ASP and unit variable cost.
- For every non-zero deviation from qualified history, historical_deviation_explanations[field] must contain an identifiable reason and valid primary evidence refs; otherwise the candidate fails closed. If actual data cannot be qualified, the system reports UNKNOWN instead of treating it as a historical anchor. No universal deviation threshold is fabricated.
- Code commit: `f3df1516fdad64e88ada5c6f8d7a2d78f3e6bfe5`. No tests, compile check, Replay, unified CI, PR, merge or real macOS acceptance were run. This remains an unmerged, non-canonical implementation.


## B42 — Production/sales flow and inventory working-capital reconciliation — 2026-10-26

Status: **UNMERGED IMPLEMENTATION / VALIDATION DEFERRED / REAL MAC ACCEPTANCE OPEN**

- The normalized operating-driver bridge now computes each product's normalized production-minus-sales quantity and, where qualified historical production/sales exist, the historical gap and change from that baseline.
- Any non-zero current gap or change from qualified historical gap requires `production_sales_reconciliation` with an identifiable reason, a supported treatment and cutoff-compatible official exchange/regulator primary-source evidence.
- Inventory build/release/gap-reconciliation treatments are explicitly linked to the company-wide `change_working_capital_cny` input; without a usable value, the normalized candidate is blocked. A non-inventory timing/scope explanation remains possible only with explicit rationale and evidence. No arbitrary materiality threshold or unsupported inventory numbers are invented.
- Product balance diagnostics are present in both structured calculation results and report prose. The product-name whitespace regex was corrected. Code commits: `8e2f8249fdf5e0b65f1417f74d915a4d7e75f854` and `5a7ca09b5a13ea20c1fa8dcbda8a3e36fd6945d5`. No tests, compile check, Replay, unified CI, PR, merge or macOS acceptance were run.
