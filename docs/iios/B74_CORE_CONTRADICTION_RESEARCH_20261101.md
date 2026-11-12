# B74 — Core Contradiction Research Priority

**Status:** original implementation was on a main-based isolated branch; this implementation is ported onto `feat/b76-core-integrated-20261101` atop the B73 proposal chain. Unmerged and non-canonical.  
**Validation:** regression assertions were added but not executed. Replay, CI, and real macOS acceptance were not run.

## Objective

Improve the quality of the company's first-pass fundamental research by making the current primary contradiction—not a broad inventory of metrics—the organizing question of price-blind Round A.

This batch is limited to:
1. identify one current primary fundamental contradiction;
2. identify its decisive variables and supporting/counter evidence;
3. explain its causal transmission to future earnings, cash flow where material, EPS and per-share value.

It does not build future-event orchestration, market expectation-gap analysis, win-rate/odds estimation, or a new decision engine. Those remain later batches.

## Audit findings

### Existing capability to reuse

- B33 already separates price-blind Round A from price-aware Round B and freezes/hash-binds the company-side artifact.
- The existing Round A patch contract already permits `assessment.thesis`, `assessment.value_drivers`, `evidence_register`, and `operating_driver_forecast`.
- Existing driver normalization already preserves rank, impact, historical evidence, valuation transmission, rationale and driver-specific evidence references.
- The local report already renders the thesis and ranked drivers. No new top-level JSON field or separate research module is needed.

### Remaining gap

The former Round A prompt asked for the company's business, important changes, evidence, operating-driver forecast and falsifiers, but did not force an explicit choice of one primary contradiction or require a reason why it dominates alternative drivers. Ranked value drivers could therefore remain a list rather than a hierarchy of causes.

B52 on the B73 proposal branch introduced a priority preamble, but that branch is not canonical. Its later active Round A prompt also retained extensive mandatory FCF/variance-attribution detail. The preamble alone did not reliably remove diagnostic workload from the researcher's primary task. B73's 321-commit proposal branch was not merged or used as this batch's base.

## B74 implementation

- Reworked the canonical-main Round A prompt on a branch created directly from current `main`.
- Requires exactly one primary contradiction, with at most two material secondary contradictions; requires an explicit comparison explaining why the primary issue dominates.
- Reuses `assessment.thesis.core_statement` for the concise primary-contradiction statement.
- Reuses `assessment.value_drivers`; rank 1 is the primary contradiction's leading determinant, with at most two secondary drivers.
- Requires both supporting and counter evidence, cutoff-compatible references, a current baseline, the key determining variables, and a causal explanation.
- Requires the leading driver's existing `valuation_transmission` to explain the economically material path to revenue, profit, cash flow where relevant, diluted shares, EPS and per-share value.
- Makes detailed FCF and variance-attribution work conditional on materiality and independent evidence; it must not displace the main contradiction analysis or trigger invented/mechanical allocations.
- Updates the local report labels to surface the thesis as the current primary contradiction and rank 1 as a research candidate, while explicitly stating that ranking is not independent proof of causality or forecast truth.
- Adds regression assertions for the Round A prompt. Tests were not run, consistent with the current test-deferral direction.

## Compatibility and boundaries

- No new top-level fields or schema changes.
- Round A remains price-blind; no price, position, MIE, expectation gap, valuation or action fields are introduced.
- Round B and its frozen-artifact boundary are unchanged.
- Existing B4/B42/B55–B62 calculations and diagnostic contracts are not changed.
- No B69–B73 expansion, formal evidence admission, forecast/valuation admission, canonical Decision or execution authority is introduced.
- The prompt requests analytical judgments; it does not turn source references into semantic verification.

## Acceptance intent for later unified validation

A real-company Round A should make it possible to answer quickly:
- What is the one primary contradiction today?
- Which 1–3 variables actually determine its direction?
- What cutoff-compatible evidence supports and contradicts the view?
- Why does this matter more than other possible drivers?
- How does it transmit to future earnings and per-share value?
- What observable evidence would invalidate the view?

**No test pass, Replay match, CI pass, or macOS acceptance is claimed.**
