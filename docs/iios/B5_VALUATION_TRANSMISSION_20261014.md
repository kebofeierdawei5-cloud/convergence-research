# B5 — Valuation transmission and entry-price remapping (2026-10-14)

## Purpose

Use B4's product/project operating scenarios to improve per-share valuation and the existing v0.3 entry-price calculation without creating a second valuation or decision engine. Main inputs and the decision kernel remain unchanged unless a complete, internally consistent B5 bridge is available.

## Operator-owned valuation choice

The local wizard asks the operator to confirm the primary model family independently of the AI response:

- `EPS_MULTIPLE`: current batch's only supported transmission adapter.
- `FCF_DCF`, `DDM`, `SOTP`, `RNPV`, `OTHER`: preserved as the selected model family but not forced through the EPS-multiple formula.
- `UNKNOWN`: no transmission is applied.

For the supported EPS-multiple family, the operator separately confirms whether the existing Bear/Base/Bull per-share terminal values and entry-value reference already include the project. If already included, B5 displays a sensitivity only; if unknown, the old valuation remains unchanged. Only an explicit operator confirmation that the existing valuation excludes the project allows an incremental adjustment.

The AI-response handoff cannot author this operator-owned selection; the local wizard adds it after the response is read and validated.

## Calculation

For each Bear/Base/Bull scenario:

`incremental attributable after-tax profit = B4 project net profit × ownership ratio − displaced existing-business after-tax attributable profit`

`basic EPS delta = incremental attributable after-tax profit ÷ basic shares`

`diluted EPS delta = incremental attributable after-tax profit ÷ (basic shares + convertible-bond incremental shares + other dilution shares)`

`incremental per-share value = diluted EPS delta × the same selected EPS multiple`

If the complete bridge passes, the diluted incremental per-share value is added atomically to all three terminal values. The Base-case incremental value is also added to the entry-value reference anchor so that the existing 15% expected-return / required-return / entry-return-cushion price solver operates on a consistent set of per-share inputs. The thesis-break stress value is not automatically increased.

## Preconditions and stop conditions

- B4 scope must be `PROJECT_INCREMENTAL`; company-wide forecasts are not added a second time.
- Forecast earnings period must exactly match the B4 operating forecast period.
- Operator-selected model family, B5-declared family and exact model name must match.
- Project after-tax profit, ownership, lost profit from existing-business substitution/cannibalization, basic shares, convertible-bond/other dilution, and scenario multiple must be calculation-usable for all three scenarios.
- Known reported/issuer values require a registered cutoff-compatible reference. Assumptions remain visibly `ANALYST_ASSUMPTION`.
- Shares are represented as actual share counts (unit `shares`), not millions of shares. Share counts must be integer-valued.
- All three adjusted scenario total-wealth values must retain Bear ≤ Base ≤ Bull. If any scenario is invalid, no scenario is partially adjusted.
- Baseline-scope uncertainty, missing attribution, unknown dilution or a model/period mismatch means no value adjustment; it does not weaken the existing decision rules.

## Boundaries

This is a `PILOT_NON_CANONICAL` feature. It creates no formal Forecast/Valuation Admission, Decision, human execution approval or automatic order. The adapter is intentionally limited to EPS multiples; DCF/FCF, DDM, SOTP and RNPV need their own model-consistent transmission formulas in a later batch. CI is code evidence, not a new macOS real-run acceptance.
