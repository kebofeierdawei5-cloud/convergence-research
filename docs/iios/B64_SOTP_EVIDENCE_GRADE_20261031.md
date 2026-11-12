# B64 — SOTP 分部盈利与终值倍数证据等级

Date: 2026-10-31

Status: branch proposal on \`feat/b45-normalized-earnings-variance-attribution-20261027\`; not merged, not tested.

## 1. Objective

B63 has established a conditionally reconciled bridge between the selected SOTP segment earnings, B4 normalized parent-attributable segment forecast, and B61's price-implied Required Return value pool. B64 addresses a different question:

**Which parts of each segment's value are connected to disclosed facts, operating mechanisms, analyst profit assumptions, or terminal-multiple assumptions—and which parts remain unknown?**

B64 grades the support structure for each segment's attributable normalized profit and selected terminal P/E separately. It deliberately does not create one blended score: a well-supported profit forecast can still be paired with a weakly supported terminal multiple.

## 2. Five-level evidence grade

| Grade | Meaning | Minimum structural condition |
|---|---|---|
| G1 — DISCLOSURE_LINKED_TO_PROFIT | Disclosed facts / issuer guidance are explicitly linked to the segment profit input | Explicit support type and summary; support references are a subset of that profit measure's own references; at least one cutoff-compatible source is labelled EXCHANGE_PRIMARY, REGULATOR_PRIMARY or ISSUER_PRIMARY |
| G2 — BUSINESS_MECHANISM_AND_EVIDENCE_LINKED | An operating mechanism connects evidence to the profit input | Explicit support type; at least two causal-chain steps; at least one observable operating indicator; at least one reversal signal; valid support references attached to the profit measure |
| G3 — ANALYST_ASSUMPTION_ONLY | Profit is an analyst assumption rather than a directly linked issuer forecast / fact | The normalized profit measure is explicitly tagged ANALYST_ASSUMPTION; derivation details may improve traceability but do not upgrade the grade by themselves |
| G4 — MULTIPLE_ASSUMPTION_ONLY | The selected terminal P/E remains a valuation assumption | Numeric positive P/E and ANALYST_ASSUMPTION data class; optional peer observations are shown separately but do not prove the selected P/E is fair |
| G5 — UNKNOWN | Support relationship, data class or source linkage cannot be identified | Missing/invalid measure, unresolved or non-cutoff-compatible support refs, incompatible declarations, or no sufficient support path for an ISSUER_FORECAST profit |

The grades are not a quality score, probability, or investment action. G1–G2 only mean that the declared support relationship has the required structure and basic reference checks; they do not mean the software has read and verified the source documents.

## 3. Structured support annotation

The existing \`attributable_net_profit_cny\` and \`pe_multiple_x\` measure objects may include an additional \`support_assessment\` object. The SOTP adapter preserves this object solely for B64; it is not used in SOTP arithmetic.

Recommended fields:

- \`support_type\`: profit uses DISCLOSED_FACTS, ISSUER_GUIDANCE, BUSINESS_MECHANISM, ANALYST_DERIVATION or UNKNOWN. P/E uses COMPARABLE_MULTIPLES, PURE_MULTIPLE_ASSUMPTION or UNKNOWN.
- \`support_summary\`: describe the specific disclosed fact, guidance, mechanism or multiple rationale.
- \`support_evidence_refs\`: references that directly support the claim. They must be a subset of the same measure's \`evidence_refs\`; general industry reading cannot be silently treated as direct profit evidence.
- \`mechanism_chain\`: ordered causal links (at least two entries for G2).
- \`key_operating_indicators\`: observable metrics that can test the mechanism.
- \`derivation_steps\`: calculation / reasoning steps for an analyst-derived profit.
- \`counter_evidence_refs\`: references to evidence that challenges the claim.
- \`reversal_signals\`: observable signals that would invalidate or reverse the mechanism.
- \`comparable_observations\`: for P/E only, each candidate record contains \`entity\`, \`as_of_date\`, \`observed_pe_x\`, \`evidence_ref\` and \`comparability_adjustment\`.

A candidate comparable set requires at least two distinct entities, positive numeric multiples, valid dates, evidence references attached to the P/E measure, and explicit comparability adjustments. It remains a manually supplied candidate set, not a peer-selection or valuation engine.

## 4. Validation rules

1. B64 only runs for a calculated SOTP selected as the primary valuation model and a B63 overall status of CONDITIONAL_ATTRIBUTION_CALCULATED or PARTIAL.
2. Each Bear/Base/Bull segment universe must match B63's reconciled segment rows exactly; a B63 scenario mismatch blocks that scenario.
3. A support reference must be present in the same measure's evidence references, resolve to the evidence register, and have \`PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED\` timing status. Counter-evidence references are separately resolved and time-checked.
4. G1 requires a non-placeholder support summary, valid supporting references and a primary-source class. The source class and timing are structural metadata only; issuer-domain identity and the source's substantive content remain subject to human review.
5. G2 requires a complete mechanism chain, operating indicators, reversal signals and valid supporting references. It does not establish causal elasticity or prove that the forecast amount follows from the mechanism.
6. G3 remains G3 even when analyst assumptions cite background evidence, unless the declared support path itself meets the separately defined G1/G2 structural conditions.
7. G4 remains the P/E grade even when peer observations are recorded. Peer comparability adjustments, growth, cyclicality, capital return, accounting definitions, leverage and valuation dates require independent analyst review.
8. G5 remains visible; no missing reference, support type, historical fact, or multiple is filled with a guessed default.

Profit and P/E grade distributions are reported separately. They are not added together or collapsed into a single segment grade.

## 5. Output placement and authority

New module: \`iios_mvp/sotp_evidence_grade_v01.py\`

Nested output:

\`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.evidence_grade_assessment\`

The SOTP adapter only preserves \`support_assessment\` metadata. The local pilot invokes B64 after B63 and displays it after the B63 valuation-gap bridge.

B64 does not modify SOTP segment values, selected P/Es, B4/B5/B6, B61/B62/B63 arithmetic, external MIE, expectation_gap, the 15% annualized return hurdle, target entry price, portfolio constraints, Decision, formal evidence admission or execution authority. It has no valuation weighting or action authority.

## 6. Regression and acceptance

Nine cases are authored in \`tests/test_sotp_evidence_grade_v01.py\`:

- G1 disclosure-linked profit and separate G4 terminal P/E;
- G2 business-mechanism chain;
- G3 analyst-only profit;
- G5 issuer forecast without support linkage;
- refusal of a support reference not attached to the measure;
- two-observation candidate comparable set that remains G4;
- B63 scenario reconciliation blocker;
- non-selected SOTP non-applicability; and
- preservation of support annotations through the SOTP adapter without altering the calculated value.

Tests have not been executed. Replay, CI, unified tests and real macOS acceptance remain deferred. B64 is a branch-only diagnostic proposal, not formal evidence admission or valuation approval.
