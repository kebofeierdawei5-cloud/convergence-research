# B7 — Primary Valuation Model and Terminal-Date Contract

**Status:** Implementation on branch b07-primary-model-terminal-date-20261017; automated tests/workflows passed at code head dafa95cb6c14c3c64bf8856788dacf11819e6a0f (122 local-pilot/Replay tests and 14 PR checks); live Mac full-run + Replay acceptance remains open.  
**Scope:** Local single-user investment pilot only. This does not create a canonical investment Decision.

## Problem confirmed from source

The local pilot normalized the operator-owned valuation model selection and ran the B5 adapter, but the return solver consumed the pre-existing forecast_valuation.scenarios regardless of a B5 status such as NOT_LINKED_UNSUPPORTED_MODEL_FAMILY. The adapter correctly avoided pretending SOTP was EPS_MULTIPLE, but its status was not connected to the final price-calculation gate. As a result, an EPS_MULTIPLE-derived price could be shown even when the operator selected SOTP.

The return solver validated the nominal horizon_years and used it for both annualized return and annualized hurdle price. It had no explicit valuation terminal date or elapsed calendar days, so a 2027FY terminal value could be treated as though it were exactly one year from an October 2026 cutoff.

## Contract changes

### 1. Separate selected model from calculated model

- operator_valuation_context.selected_model_family remains operator-owned.
- forecast_valuation.model_family identifies the actual model used to generate Bear/Base/Bull terminal values and the entry-reference anchor.
- The two families must match, and the human-readable model name must be present, before the scenarios may feed the primary return/entry-price calculation.
- Unknown selection, unknown calculation family, or mismatch blocks return_metrics, target entry price and B6 sensitivity. The existing scenario values remain in the report/JSON as ALTERNATIVE_OR_UNRESOLVED_ONLY; they are not silently converted or used as primary-model outputs.
- For PROJECT_INCREMENTAL operating forecasts, price calculation is also blocked unless B5 has applied the incremental value or explicitly confirmed that the baseline already contains it. This check is not applied to an explicitly company-wide model merely because B5 is unsupported.
- No model-override authorization is introduced in this patch.

### 2. Bind annualization to the actual terminal date

- forecast_valuation.valuation_terminal_date is an explicit ISO date; valuation_terminal_date_basis explains which forecast period/fiscal-year endpoint it represents.
- The pilot records cutoff date, forecast period, terminal date, elapsed calendar days, ACT/365F year fraction, formula and validation status in valuation_timing.
- Annualized return is (expected_terminal_wealth / current_price) ** (1 / year_fraction) - 1.
- The 15% annualized-return entry cap is expected_terminal_wealth / (1 + 0.15) ** year_fraction. The Bear loss cap and entry-cushion cap retain their existing independent definitions; the overall target remains the minimum of the existing applicable caps.
- decision_parameters.horizon_years remains the policy/reference horizon and continues to use the existing 1–3Y validation and 3Y exception rules. It is no longer silently used as a substitute for a calendar-date-derived holding period.
- Missing or invalid endpoint, missing date basis, endpoint on/before the cutoff, non-identifiable supported forecast-period label, or material period-year mismatch blocks the return solver and keeps B6 values UNKNOWN.

## Conservative boundary

The current period-alignment check understands annual YYYYFY labels and accepts a terminal-date calendar year equal to the labelled year or the following year, allowing fiscal years that end in the following calendar year. It does not independently prove the issuer's fiscal year-end date; the model must explicitly supply the endpoint and its basis, and the report labels period alignment as not independently verified. Additional half-year/quarter period validators should be added only with explicit calendar semantics rather than guessed.

## Automated verification and acceptance boundary

- At code head `dafa95cb6c14c3c64bf8856788dacf11819e6a0f`, the dedicated local-pilot workflow compiled the pilot/core files and launchers, ran local pilot + Replay acceptance tests (**122 passed**), and passed diff check. All 14 PR checks passed at that head.
- The added negative test confirms that missing `valuation_terminal_date_basis` blocks return metrics and B6 even if a JSON input bypasses wizard validation.
- A fresh Mac full-run and same-run comparison of `analysis.json`, `report.md`, and `pilot_receipt.json` remain required; CI does not establish the real ChatGPT response or on-device workflow.

## Not changed

- No automatic SOTP/DCF/DDM adapter is fabricated; B5's implemented transmission family remains EPS_MULTIPLE.
- No market-implied expectation is inferred from internal valuation.
- The 15% annualized return hurdle, Bear risk cap, decision priority and human approval/no-auto-trading governance remain unchanged.
- Hash/Replay engineering is not expanded in this batch. Report/JSON output still needs a real new Mac pilot run to establish live acceptance after the patch merges.
