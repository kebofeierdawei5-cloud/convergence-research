# B73 — Evidence-driven remediation reassessment

Date: 2026-10-31

**Status: CODE/DOC COMMITTED TO PROPOSAL BRANCH / NOT MERGED / NOT TESTED.**

## 1. Objective

B72 converts B69/B70/B71 analysis into explicit requirement/action rows. B73 adds a lightweight reassessment layer so an operator can submit remediation context and have the current pilot run checked against the exact B72 requirement and action.

B73 is not a ticketing system, workflow scheduler, formal evidence-admission service or manual close button. It consumes B69, B70, B71 and B72 outputs already recomputed during the current pilot run.

## 2. Input contract

Optional top-level pilot input: operating_feasibility_remediation_submissions.

Schema: IIOS-OPERATING-FEASIBILITY-REMEDIATION-SUBMISSIONS-0.1.

Each submission contains:
- submission_id: unique local submission identifier;
- requirement_id and action_id: exact identifiers from the current B72 row;
- submitted_by, timezone-aware submitted_at and remediation_summary;
- prior_b70_record_ids and prior_b71_review_ids: operator-declared previous record identifiers;
- superseded_b70_record_ids and superseded_b71_review_ids: previous identifiers explicitly replaced.

The operator updates the existing operating_feasibility_evidence and/or operating_feasibility_semantic_reviews inputs using their existing contracts. B73 does not introduce a second copy of those records. The current B72 output supplies current B70 and B71 identifiers.

## 3. Reassessment rules

B73 validates:
1. requirement_id resolves to exactly one current B72 row;
2. action_id exactly matches that row's deterministic remediation action;
3. previous IDs are retained or explicitly declared superseded;
4. declared superseded IDs are absent from current B70/B71 outputs;
5. current B70 records match B72 scenario, product, forecast period and claim type (paired funding claims remain paired);
6. each current B70 record has exactly one current B71 review;
7. every review reports conditional semantic support and the B71 independence declaration;
8. B72 evidence references equal those on current B70 records; and
9. current B72 exception status has moved to CONDITIONALLY_SUPPORTED_NOT_FORMALLY_ADMITTED.

Remaining numerical gaps, evidence blockers, contradictions, missing reviews, duplicate IDs, scope mismatches and unmodeled operating dimensions cannot be marked resolved by an operator assertion.

## 4. Status and close authority

Possible states:
- REASSESSMENT_BLOCKED;
- REASSESSMENT_BLOCKED_UPSTREAM_SCOPE_REQUIRED;
- REASSESSMENT_FAILED; and
- REASSESSMENT_PASSED_PENDING_FORMAL_ADMISSION.

**B73 never emits CLOSED_VERIFIED.** B72's conditional support is not formal Evidence/PIT admission. B73 does not own that admission process and cannot close it. A successful reassessment means only that the current B69–B72 run shows conditional numerical/evidence/semantic support, pending separate formal admission.

No B4/B68/B69, SOTP, external MIE, expectation gap, 15% annualized return hurdle, target entry price, portfolio constraint, Decision or execution authority is changed.

## 5. Limitations

- Superseded IDs are operator-declared. B73 verifies that they are absent from the current output; it cannot authenticate that they existed in a previous run.
- B71 reviewer identity, real independence, source-document content and enforceability remain human assertions, not automated facts.
- Demand sustainability/elasticity, competitive price response, cost curves/savings execution, B69 capacity arithmetic and other upstream model changes cannot be repaired solely by replacing B70/B71 records. Upstream B4/B68/B69 assumptions must be corrected and the full pipeline rerun.
- The current pilot execution recalculates B69, B70, B71 and B72 before B73. B73 itself does not fetch sources or schedule asynchronous work.

## 6. Regression coverage and acceptance

Twenty-one regression cases are authored in tests/test_operating_feasibility_remediation_v01.py. Coverage includes exact requirement/action binding, duplicate IDs, stale and superseded versions, scope/period/claim matching, B71 review coverage and independence declarations, evidence-reference consistency, unresolved numerical gaps, unmodeled dimensions, timezone validation and manual-close prohibition.

Tests have **not** been executed. Replay, CI, unified tests and real macOS acceptance have **not** been run or verified. No PASS is claimed.
