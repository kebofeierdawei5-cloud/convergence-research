# B65 — SOTP 同行可比性审计

Date: 2026-10-31

Status: branch proposal on \`feat/b45-normalized-earnings-variance-attribution-20261027\`; not merged, not tested.

## 1. Objective

B64 established two separate facts: (1) each SOTP normalized segment profit has a declared evidence grade; and (2) the selected terminal P/E remains an analyst assumption even when peer observations exist.

B65 answers the next question:

**Do the observed peer companies have sufficiently comparable economics, accounting definitions and valuation dates to be useful reference points for this segment's terminal P/E?**

B65 is a comparability audit, not a peer screener, multiple-selection engine, fair-value model or numerical adjustment calculator.

## 2. Thirteen mandatory comparability dimensions

Each SOTP segment has one target profile. Every peer observation must provide a corresponding peer profile and a dimension assessment for each of the following:

1. Business model.
2. Revenue mix.
3. End market and customer mix.
4. Growth stage.
5. Industry cycle phase.
6. Profit quality (recurring vs. non-recurring, normalized vs. reported).
7. ROIC / capital return.
8. Capital intensity.
9. Leverage / net cash-debt position.
10. Free-cash-flow conversion.
11. Accounting basis and consolidation / attribution scope.
12. Earnings reference period.
13. P/E measurement basis (e.g. TTM reported, NTM forecast or normalized earnings).

Values must be explicit descriptions, defined ranges or numeric observations. Missing information remains UNKNOWN. The tool does not fill profile values from broad industry statements or infer a target company's ROIC, leverage or FCF conversion.

## 3. Dimension-level audit contract

Each peer's \`dimension_assessments[dimension]\` contains:

- \`target_value\` and \`peer_value\`, which must exactly match the target and peer profiles for that dimension;
- \`comparison\`: SIMILAR, DIFFERENT, NOT_COMPARABLE or UNKNOWN;
- \`target_multiple_implication\`: TARGET_PREMIUM, TARGET_DISCOUNT, NEUTRAL or UNKNOWN;
- \`multiple_adjustment_treatment\`: SELECTED_PE_ADJUSTED, NO_NUMERIC_ADJUSTMENT, PEER_EXCLUDED or UNKNOWN;
- \`rationale\` and \`adjustment_rationale\`; and
- \`evidence_refs\`, drawn from the P/E measure's own evidence references and resolved to cutoff-compatible source records.

Rules:

- SIMILAR must be NEUTRAL and NO_NUMERIC_ADJUSTMENT.
- DIFFERENT requires a reasoned direction and an explanation of whether the selected P/E already reflects the difference or why no numeric adjustment was made.
- NOT_COMPARABLE requires PEER_EXCLUDED and a clear exclusion rationale. Such a company cannot count toward the eligible peer set.
- UNKNOWN, missing dimension values, inconsistent declared values or unresolved/time-incompatible references prevent a peer from being counted as a complete comparable observation.

TARGET_PREMIUM / TARGET_DISCOUNT describe a qualitative relative direction for the target segment versus the peer. They are not numeric P/E adjustment factors. Differences are not summed or weighted into one score.

## 4. Valuation-date and earnings-basis control

Every peer's observed P/E needs an explicit \`as_of_date\` and \`pe_measurement_basis\`.

- A peer observation dated after the case cutoff is blocked.
- An earlier observation is not silently treated as a same-day observation; it needs a \`date_alignment_rationale\` explaining why the date gap remains usable or how it was rebased.
- TTM reported P/E, NTM forecast P/E and normalized P/E must not be casually mixed. The peer's earnings reference period and measurement basis are explicit comparability dimensions.
- A dimension reference must be a subset of the SOTP P/E measure's own \`evidence_refs\`, resolve to the evidence register, and carry \`PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED\` timing. This is a time/linkage check, not formal evidence admission or source-content verification.

## 5. Candidate peer-set status

Each peer is independently marked complete, partial or excluded. A segment requires at least two distinct peers whose 13 dimensions are complete and that are not marked NOT_COMPARABLE before its candidate peer set can be shown as:

\`COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED\`

Fewer than two eligible peers yields \`PEER_SET_INSUFFICIENTLY_COMPARABLE\`. Missing or conflicting dimensions yield PARTIAL. The audit preserves the selected terminal P/E unchanged in all cases.

The tool reports:
- peer count, eligible count, excluded count and partial count;
- date lag and date-alignment status;
- dimension-by-dimension observations, qualitative direction and rationale;
- missing / excluded dimensions; and
- qualitative target-premium, target-discount and neutral dimension lists.

It does not calculate peer median/mean P/E, a premium/discount percentage, an adjustment coefficient, or a revised target multiple.

## 6. Placement and authority

New module: \`iios_mvp/sotp_comparability_audit_v01.py\`

B64 now preserves the target comparability profile, peer profile, dimension assessments and date-alignment rationale from the P/E measure's \`support_assessment\` for B65. The local pilot invokes B65 after B64.

Nested output:

\`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.comparable_company_audit\`

B65 does not modify SOTP, B4/B5/B6, B61/B62/B63/B64 arithmetic, selected segment P/E, external MIE, expectation_gap, the 15% annualized return hurdle, target entry price, portfolio constraints, Decision, formal evidence admission or execution authority.

## 7. Regression and acceptance

Ten cases are authored in \`tests/test_sotp_comparability_audit_v01.py\`:

- complete 13-dimension audit with different-but-explained growth/cycle/ROIC profiles;
- required dimension missing;
- profile / dimension value mismatch;
- different dimension with no direction or treatment rationale;
- NOT_COMPARABLE peer excluded from the eligible set;
- peer valuation date after cutoff;
- earlier peer date without rebase rationale;
- dimension evidence reference not attached to the P/E measure;
- invalid case cutoff and blocked B64; and
- separation of accounting / earnings-period / P/E-basis differences.

Tests have not been executed. Replay, CI, unified tests and real macOS acceptance remain deferred. B65 is a branch-only diagnostic proposal, not valuation approval.
