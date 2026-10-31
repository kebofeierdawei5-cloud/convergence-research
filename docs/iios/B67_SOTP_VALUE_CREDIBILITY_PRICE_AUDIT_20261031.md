# B67 — SOTP 估值可信度与现价要求审计

Date: 2026-10-31

Status: branch proposal on feat/b45-normalized-earnings-variance-attribution-20261027; not merged, not tested.

## 1. Objective

B61–B66 now provide local price inversion, segment earnings reconciliation, value-gap attribution, separate profit/multiple evidence grades, peer comparability, and explicit terminal P/E calibration. B67 consolidates these outputs into one read-only audit view:

1. What creates the selected SOTP segment value?
2. How much of the selected P/E is represented by an explicit reference anchor versus analyst adjustments?
3. Can the independent B4 normalized-earnings vector support the value pool required by B61's Required Return?
4. How do current parent-level adjustments and diluted shares translate required equity into a per-share hurdle?

B67 is an audit layer, not another valuation model. It does not use generic evidence weights, valuation-quality scores, probabilities, or automatic discounts.

## 2. Input contracts

B67 consumes the selected SOTP valuation, B63 valuation-gap attribution, B64 evidence-grade assessment, and B66 multiple-calibration assessment. It uses existing scenario and segment IDs only. Segment IDs must match exactly; row ordering is never used as a join key.

B63 must be fully reconciled at scenario level before B67 presents its complete current-price requirement waterfall. If B63 is not fully reconciled, B67 blocks that scenario.

## 3. Value-source structure

For each segment:

Selected segment value = normalized parent-attributable profit × selected terminal P/E

B67 rechecks the segment product and the aggregate selected SOTP segment pool.

### Profit evidence and independent earnings contribution

The B64 profit grade is retained per segment: G1 (disclosure-linked), G2 (business-mechanism-linked), G3 (analyst assumption), or G5 (unknown). The B64 terminal P/E grade is shown separately (normally G4 or G5). B67 does not combine the two dimensions, convert them into a score, or infer a probability or percentage of value that is verified. Missing or unknown grades remain visible and make the audit PARTIAL.

The independent B4 earnings effect remains B63's existing formula:

(B4 normalized parent-attributable profit − selected SOTP normalized profit) × unchanged selected P/E

B67 independently checks each segment and the aggregate identity:

Selected SOTP pool + B4 earnings effect = B4 forecast pool at selected P/Es

### Reference P/E and explicit adjustment value

Only when B66 declares MULTIPLE_BRIDGE_RECONCILED and B67 independently reproduces the bridge does B67 calculate:

Selected segment value = profit × reference P/E + profit × explicit adjustment sum

B67 aggregates a company-wide reference/adjustment waterfall only when every selected segment has a reconciled reference bridge. If any segment has NO_COMPARABLE_REFERENCE or incomplete inputs, identified segment values remain visible, aggregate coverage is PARTIAL, and missing contribution is not treated as zero. Peer median, historical self-range and other explicit references remain separately labelled.

## 4. Parent adjustments and dilution

B67 carries B63's signed parent-level bridge: capitalized central-cost load, net-cash/net-debt offset, other adjustments, and net parent load. It checks:

Required segment pool = required total equity + capitalized central cost − net cash/debt − other adjustments

No future parent-adjustment change is estimated without an independent forward forecast.

The diluted-share bridge checks:

Required total equity = required terminal value per share × diluted shares

Share count remains an equity-to-per-share translation, not an operating earnings contribution.

## 5. Current-price Required Return requirement

B67 presents B63's waterfall:

1. selected SOTP segment pool;
2. B4 earnings effect at unchanged selected P/Es;
3. B4 forecast segment pool at selected P/Es;
4. residual common-P/E scaling effect;
5. B61 Required Return required segment pool.

It checks the common P/E scale factor against required pool ÷ B4 forecast pool, independently recalculates each segment's required common P/E from its unchanged selected P/E × the common factor, and preserves the resulting segment-level conditional values. The common P/E is calculated from the full B4 normalized-profit vector; it is not a standalone fair P/E for an individual segment.

The displayed hurdle is B61 Required Return without distributions as carried by B63. It is a conditional price-implied return hurdle, not external MIE, broker consensus, or an observed market expectation. Whether B4 meets the hurdle is a conditional model comparison, not a BUY/SELL instruction.

## 6. Status semantics

B67 reports independent sub-statuses for selected-value arithmetic, B4 earnings attribution, reference-multiple coverage, parent adjustments, dilution, and current-price requirement.

- VALUE_SOURCE_AUDIT_RECONCILED_DIAGNOSTIC_ONLY: the value and hurdle arithmetic reconcile and evidence/reference coverage is structurally complete.
- PARTIAL: arithmetic may reconcile, but evidence grades, reference anchors, or an upstream diagnostic are incomplete.
- RECONCILIATION_MISMATCH: an independent arithmetic or segment-identity recheck fails.
- BLOCKED_BY_B63_SCENARIO: B63 is not fully reconciled, so the complete value-pool/hurdle chain is withheld.

There is no composite credibility score, probability, confidence interval, fair-value certification, formal evidence admission, or decision promotion.

## 7. Integration and authority

New module: iios_mvp/sotp_value_credibility_audit_v01.py

Nested output: assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.value_credibility_price_audit

The local pilot invokes B67 after B66 and renders each segment's profit/value, B4 earnings contribution, reference P/E and explicit adjustment value where reconciled, separate B64 grades, parent adjustments, dilution, and B61 Required Return hurdle.

B67 does not modify SOTP inputs or values, B4/B5/B6, B61–B66, external MIE, expectation_gap, the 15% annualized hurdle, target entry price, portfolio constraints, Decision, Evidence/PIT admission, or execution authority.

## 8. Regression coverage and acceptance

Eleven regression cases are authored in tests/test_sotp_value_credibility_audit_v01.py. They cover the value and hurdle waterfall, B4 earnings contribution, reference-plus-adjustment decomposition, separate grades, missing reference coverage, B63 mismatch/blocking, parent adjustment mismatch, missing evidence grades, segment-universe mismatch, SOTP non-applicability, and an independent recheck of a falsely reconciled B66 bridge, and per-segment recalculation of Required Common P/E.

Tests have not been executed. Replay, CI, unified test suite and real macOS acceptance remain deferred.
