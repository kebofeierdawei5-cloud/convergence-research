# B66 — SOTP 终值 P/E 独立校准与敏感性

Date: 2026-10-31

Status: branch proposal on \`feat/b45-normalized-earnings-variance-attribution-20261027\`; not merged, not tested.

## 1. Objective

B64 distinguishes the evidence grade of segment normalized profit from the terminal P/E assumption. B65 checks whether the peer set is genuinely comparable. B66 then addresses:

**Why is this segment assigned this terminal P/E, what explicit adjustment bridge leads to that number, how wide is the analyst's reasonable sensitivity range, and how does the selected multiple compare with the conditional multiple requirement implied by the current price?**

B66 does not generate a fair P/E from ROIC, growth, industry cycle or quality labels. Those variables must be explicitly interpreted by the analyst; no fixed weights or generic multiple formula is imposed.

## 2. Peer reference anchor

B66 calculates descriptive minimum / median / maximum only from peers that:

- are marked PEER_COMPARABILITY_COMPLETE by B65;
- are eligible in the B65 candidate peer set;
- have positive numeric observed P/E; and
- match the target segment on all three valuation-definition dimensions: accounting basis, earnings reference period and P/E measurement basis.

The three valuation-definition values must be identifiable, not the literal string UNKNOWN, and must be declared SIMILAR by B65. TTM reported, NTM forecast and normalized P/E are never mixed in one median.

At least two peers are required before the median is identifiable. Other complete peers can remain visible as qualitative comparisons but cannot enter this same-basis numerical anchor if the three definition dimensions differ.

If the peer anchor is insufficient, an analyst may use HISTORICAL_SELF_RANGE or OTHER_EXPLICIT_REFERENCE with a positive reference multiple, explanation and cutoff-compatible references attached to the selected P/E measure. If no reliable anchor exists, use NO_COMPARABLE_REFERENCE; the result remains assumption-only / PARTIAL and is not represented as a reconciled calibration.

## 3. Explicit selected-multiple bridge

The per-scenario \`pe_multiple_x.support_assessment.selected_multiple_bridge\` contains:

- \`reference_method\`: PEER_MEDIAN, HISTORICAL_SELF_RANGE, OTHER_EXPLICIT_REFERENCE or NO_COMPARABLE_REFERENCE;
- \`reference_description\` and, for explicit historical/other references, \`reference_multiple_x\` plus \`reference_evidence_refs\`;
- \`adjustments\`: an array of explicit analyst adjustments; and
- \`selected_multiple_explanation\`.

Each adjustment contains \`dimension\`, \`direction\` (TARGET_PREMIUM / TARGET_DISCOUNT / NEUTRAL), \`adjustment_x\`, \`rationale\` and \`evidence_refs\`.

Rules:
- A premium adjustment must be positive; a discount adjustment must be negative; neutral must be zero.
- A dimension can only be adjusted once per bridge.
- Its directional label must be supported by B65's completed peer review. Conflicting target-premium and target-discount directions on the same dimension block that adjustment.
- Every adjustment reference must belong to the selected P/E measure's own \`evidence_refs\`, resolve in the evidence register and be cutoff-compatible.
- The selected terminal P/E must be tagged ANALYST_ASSUMPTION.
- Exact arithmetic is checked within 0.01x: \`reference_multiple_x + sum(adjustments.adjustment_x) = selected pe_multiple_x\`.

A reconciled arithmetic bridge proves only that the analyst's stated steps arrive at the selected P/E. It does not prove the chosen anchor or adjustments are economically correct or that the final P/E is fair.

## 4. Analyst P/E sensitivity range

Each selected P/E has \`support_assessment.selected_multiple_range\` containing:

- \`data_class=ANALYST_ASSUMPTION\`;
- positive \`lower_bound_pe_x\` and \`upper_bound_pe_x\`;
- \`basis\`, \`downside_rationale\` and \`upside_rationale\`; and
- cutoff-compatible \`evidence_refs\` attached to the same P/E measure.

The lower bound must not exceed the selected P/E, and the upper bound must not be below it. B66 computes, per segment, normalized profit multiplied by the lower / selected / upper multiple.

Only when every segment in a scenario has a complete range and the existing selected SOTP equity/per-share arithmetic reconciles does B66 calculate the all-segment sensitivity: all lower bounds simultaneously, selected P/Es, and all upper bounds simultaneously, with existing parent adjustments and diluted shares held unchanged. This is a conditional stress range, not a confidence interval, a probability-weighted value, a target price or a promise.

## 5. Current-price Required Return comparison

B66 displays B63's \`required_pe_under_common_scale_x\` next to the selected segment P/E. The required value is derived from the full B4 normalized segment profit vector under B63's parallel common-multiple scaling assumption.

It is not the independently required fair P/E of the individual segment. It does not change the selected P/E or the SOTP valuation. The report preserves this interpretation to prevent one segment's scaled multiple from being read as an additive or standalone hurdle.

B66 cross-checks the selected P/E against the same segment in B65 and B63. If either value differs from the SOTP input, the scenario is PARTIAL.

## 6. Output and authority

New module: \`iios_mvp/sotp_multiple_calibration_v01.py\`

Nested output:

\`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.multiple_calibration_assessment\`

The local pilot invokes B66 after B65 and displays the peer anchor, adjustment bridge, sensitivity range, B63 required-multiple comparison and aggregate SOTP-per-share sensitivity.

B66 does not modify SOTP segment profits or P/Es, B4/B5/B6, B61/B62/B63/B64/B65 outputs, external MIE, expectation_gap, the 15% annualized return hurdle, target entry price, portfolio constraints, Decision, formal evidence admission or execution authority.

## 7. Regression and acceptance

Eighteen cases are authored in \`tests/test_sotp_multiple_calibration_v01.py\`:

- same-basis peer median plus an explicit premium adjustment reconciles to selected P/E;
- per-segment and aggregate SOTP multiple-range sensitivity;
- mismatched P/E measurement basis excluded from peer median;
- adjustment sum does not reconcile;
- premium/discount adjustment sign invalid;
- adjustment evidence not attached / unresolved;
- selected P/E outside analyst range;
- no comparable anchor remains assumption-only / partial, and a declared absence is rejected when B65 already has a same-basis peer anchor;
- historical self-reference with explicit source can reconcile;
- B63 / B65 gate failure;
- SOTP not selected;
- literal UNKNOWN in a key P/E basis does not enter the median;
- selected P/E mismatch against B65 and B63; 
- selected P/E data class other than ANALYST_ASSUMPTION; and
- UNKNOWN selected-multiple explanation.

Tests have not been executed. Replay, CI, unified tests and real macOS acceptance remain deferred. B66 is a branch-only research diagnostic, not valuation approval.
