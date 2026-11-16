# B52 — Core Investment Expectation Synthesis

**Status:** implemented on the feature branch; unmerged and non-canonical. **Validation:** four B52 regression cases are authored but not run. Replay, CI, and real macOS full-run acceptance remain deferred / not verified.

## Why this batch

The two red-team reviews found that the recent B42–B51 line is related to the original investment goal but has become increasingly concentrated on detailed diagnostics. The next incremental step should not add more FCF categories or generic evidence tags. It should put the three main investor questions at the center of the research workflow and report:

1. What is the company's current fundamental reality, based on cutoff-compatible facts?
2. What does the current price/valuation require, and which parts are externally evidenced market expectations versus conditional model inversion?
3. What is a reasonable Bear/Base/Bull projection from the present operating baseline, explicit drivers, and falsifiable assumptions?

## Changes

### 1. Research priority order

The price-blind Round A prompt now explicitly prioritizes current fundamental reality and verifiable operating baselines first, the most important one-year forward variables and Bear/Base/Bull projections second, and detailed attribution/monitoring diagnostics after those essentials. It discourages forcing unsupported detailed FCF allocations merely to populate fields.

The price-aware Round B prompt now prioritizes current-price requirements, aligned comparison against Round A's independent forecast, and risk/return implications before auxiliary discussion.

### 2. External market evidence versus conditional price inversion

The existing `assessment.market_implied_expectation` remains the home for external, cutoff-compatible MIE status, summary and evidence. B52 allows a separate nested `price_implied_analysis` object within that existing field; no new top-level JSON field is introduced.

The conditional object can express:

- `status`, `method`, `model_family` and `reference_price`;
- explicit `assumptions`;
- `implied_requirements` with metric, value, unit, period, interpretation/basis and evidence references;
- `sensitivity` and `limitations`.

The reference price must equal the protected structured `price_input.price`. The local input normalizer downgrades a declared expectation-gap PASS to UNKNOWN when its `comparison_basis` claims price-implied comparison but the inversion lacks a supported model family/method, reference-price match, assumptions, implied results or limitations. The report checks equality and contract completeness, calls out a mismatch or missing fields, and suppresses the dependent numeric comparison when the inversion is inconsistent. This does not independently recompute the inversion formula or establish the truth of the submitted assumptions.

Crucially, conditional price inversion is **not external MIE**. It cannot upgrade `assessment.market_implied_expectation.status`; where external market evidence is unavailable, that status remains `NOT_IDENTIFIABLE`. Likewise, a model-derived conditional comparison cannot by itself make an externally verified expectation gap PASS.

### 3. Aligned expectation-gap representation

The existing `assessment.expectation_gap` can provide `comparison_basis` and `comparisons` rows. Each row should compare like with like—metric definition, unit and period—between an external market observation or explicitly labeled conditional price-implied requirement and the independent forecast. The report shows both sides, their difference/direction, period and limitation. Missing or non-comparable values remain `UNKNOWN`; the report does not manufacture a value or silently infer direction.

A critical decision boundary applies: when `comparison_basis` uses `PRICE_IMPLIED`, the local normalizer leaves the decision-usable expectation-gap status/direction as `UNKNOWN`, even if the conditional inversion's reference-price and field-shape checks pass. The reported difference is useful as a **conditional sensitivity**, not a verified external MIE gap, because the local engine has not independently recomputed the analyst-supplied inversion. Only a comparable gap that directly uses cutoff-compatible external MIE evidence can support the external expectation-gap gate. The original model-submitted status/direction is preserved for audit.

### 4. One-screen three-lens report summary

A read-only summary now appears at the beginning of the Chinese report and groups existing outputs into:

- current fundamental reality: Trust/Reality/Quality, core thesis, top value drivers and cycle state;
- current price-implied requirements: protected reference price, external MIE status, separate conditional inversion and expectation-gap comparisons;
- future projection: B4 Bear/Base/Bull net profit and FCF proxy where available, selected model terminal outputs, annualized-return calculation, the 15% hurdle and target-entry-price cap.

This is a presentation layer over existing fields. It does not invent missing measures, change B4/B5/B6 or recalibrate the decision kernel.

## Scope preserved

- Existing JSON envelope and allowed top-level research-patch fields remain unchanged.
- Round A remains price-blind; Round B cannot rewrite the frozen Round A artifact.
- The 15% annualized return requirement remains an entry hurdle, not a discount rate.
- Unknown external MIE remains `NOT_IDENTIFIABLE`; internal Base value or a conditional inversion is not a substitute for market evidence.
- Current price remains the single protected input. A price-implied analysis referencing a different price is visibly flagged.
- No valuation formula, target entry price arithmetic, formal admission, canonical Decision, portfolio authority, or execution behavior is changed.
- B42–B51 remain in scope as currently implemented, but additional FCF-diagnostic expansion is paused unless a concrete case establishes that a specific gap affects a core decision.

## Regression cases and validation status

Four cases are authored in `tests/test_local_investment_pilot_v01.py`:

1. Round A visibly prioritizes fundamental reality and forward scenarios before auxiliary FCF diagnostics.
2. Round B separates external MIE from conditional price inversion.
3. The report distinguishes external MIE, the conditional inversion, forward-scenario comparison and their limitations.
4. A conditional inversion whose reference price differs from the protected price is visibly flagged.

They have **not been executed**. No test pass, Replay match, CI pass, macOS acceptance, formal Evidence/PIT admission, formal Forecast/Valuation admission, canonical Decision, or execution authority is claimed.
