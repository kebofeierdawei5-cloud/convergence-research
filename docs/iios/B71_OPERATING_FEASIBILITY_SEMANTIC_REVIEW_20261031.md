# B71 — Operating feasibility evidence semantic review

Date: 2026-10-31

**Status: BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## 1. Objective

B70 validates that an operating claim has a unique, cutoff-compatible, primary-class source reference and that its declared number can be compared with a B68/B69 threshold. It does not establish that the referenced document actually supports the claim.

B71 adds a structured human source-content review record for every B70 claim. Review requirements are claim-type-specific. A generic "looks supported" checkbox is not accepted.

B71 records an operator/reviewer assertion and a checklist trail. It does **not** independently authenticate reviewer identity, open or hash the source document, verify legal enforceability, prove customer identity, or grant formal Evidence/PIT admission.

## 2. Optional input contract

Top-level input:

\`operating_feasibility_semantic_reviews\`

Schema:

\`IIOS-OPERATING-FEASIBILITY-SEMANTIC-REVIEWS-0.1\`

Example:

\`\`\`json
{
  "schema_version": "IIOS-OPERATING-FEASIBILITY-SEMANTIC-REVIEWS-0.1",
  "reviews": [
    {
      "review_id": "REV-P1-BASE-ORDER-01",
      "record_id": "DEMAND-BASE-P1-01",
      "reviewer_id": "operator-01",
      "reviewed_at": "2026-10-31T16:30:00+08:00",
      "review_method": "HUMAN_SOURCE_CONTENT_REVIEW",
      "decision": "SUPPORTS",
      "reviewed_evidence_refs": ["EVIDENCE-001"],
      "checks": [
        {
          "check_id": "SOURCE_CONTENT_READ",
          "status": "PASS",
          "basis": "Opened and read the original order document, including appendices.",
          "evidence_refs": ["EVIDENCE-001"]
        }
      ],
      "review_notes": "Human review notes; the complete claim-type checklist is required."
    }
  ]
}
\`\`\`

The example shows only the record shape; a valid supported review must include every required checklist item for that claim type and data class.

Each review requires:
- unique \`review_id\` and exactly one \`record_id\` from the B70 assessment;
- non-empty \`reviewer_id\`;
- timezone-aware ISO \`reviewed_at\`;
- exact method \`HUMAN_SOURCE_CONTENT_REVIEW\`;
- explicit decision: \`SUPPORTS\`, \`PARTIALLY_SUPPORTS\`, \`DOES_NOT_SUPPORT\`, \`CONTRADICTS\` or \`UNABLE_TO_VERIFY\`;
- \`reviewed_evidence_refs\` exactly equal to the B70 claim's evidence reference set;
- complete required \`checks\`, each with \`check_id\`, \`status\`, descriptive \`basis\` and evidence references for every PASS; and
- non-empty reviewer notes.

Review time is process metadata, not a source fact or PIT evidence.

## 3. Claim-specific semantic checks

### Sales volume

Common checks cover source content, customer/product scope, delivery period, customer identity/credit status, quantity net of cancellations, duplicate/overlapping orders and delivery/customer-acceptance timing.

For \`ISSUER_FORECAST\`, the additional required check is \`FIRM_ORDER_AND_CANCELLATION_RIGHTS_VERIFIED\`. Framework cooperation, MOU, non-binding forecast, capacity reservation and firm purchase order are not interchangeable.

For \`OBSERVED_ACTUAL\`, the additional required check is \`INVOICED_SHIPPED_AND_CUSTOMER_ACCEPTED_QUANTITY_RECONCILED\`. An order is not a completed sale; invoice, dispatch and acceptance/return/cancellation evidence must be examined.

### Net selling price

Common checks cover product and customer scope, contractual/realized status, taxes, freight, rebates, discounts, credits and effective delivery period. A price/mix effect cannot be mistaken for like-for-like price growth.

For \`OBSERVED_ACTUAL\`, B71 requires \`ACTUAL_INVOICED_NET_PRICE_RECONCILED_TO_CREDITS_AND_RECEIPTS\`.

For \`ISSUER_FORECAST\`, B71 requires \`CONTRACTUAL_PRICE_TERMS_AND_VOLUME_REBATES_VERIFIED\`.

### Unit variable cost

Common checks cover product scope, cost component and allocation basis, input/energy/yield/utilities and period comparability.

For \`OBSERVED_ACTUAL\`, B71 requires \`ACTUAL_COST_BASELINE_AND_ALLOCATION_RECONCILED\`.

For \`ISSUER_FORECAST\`, B71 requires \`COST_SAVING_ACTION_OWNER_AND_EXECUTION_MILESTONES_VERIFIED\`. A target percentage reduction or management aspiration alone does not satisfy this item.

### Effective capacity and capacity availability date

Capacity checks distinguish nameplate from effective output and require review of maintenance, yield, bottlenecks, shared lines, product mapping and required production window.

Expansion-date checks require the project scope, permits, construction/equipment progress, commissioning/acceptance, ramp-up and first qualified-output date. A mechanical completion date is not necessarily a customer-qualified production date.

### Incremental capex and working capital

Required-capex checks review project cost scope, estimate basis, tax/contingency/escalation, incremental amount relative to B4 and approval/payment timing.

Funded-capex checks review binding status, unrestricted availability, draw timing and already allocated/duplicated funds.

Working-capital checks review inventory, receivables/customer credit, supplier terms, cash-cycle and seasonal peak funding. Both required and funded values must be incremental to the B4 forward plan, not re-labelled existing B4 cash capex or working capital.

## 4. Review outcomes and fail-closed rules

- \`HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY\`: only when the B70 record is eligible, all exact evidence refs are reviewed, every required check is present and PASS, and the reviewer decision is SUPPORTS.
- \`SEMANTIC_REVIEW_PARTIAL\`: reviewer says only part of the claim is supported.
- \`SEMANTIC_REVIEW_NOT_SUPPORTED\`: the examined source does not support the claim.
- \`SEMANTIC_REVIEW_CONTRADICTED\`: review finds evidence contradicting the claim.
- \`SEMANTIC_REVIEW_UNABLE_TO_VERIFY\`: reviewer cannot resolve the claim.
- \`SEMANTIC_REVIEW_CHECK_FAILURE_CONFLICTS_WITH_SUPPORT_DECISION\`: a reviewer marks SUPPORTS despite a required failed check.
- \`SEMANTIC_REVIEW_NOT_COMPLETE\`: unknown/missing required checks prevent a support outcome.
- \`SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE\`: B70 record is not eligible, references are mismatched, identity/timestamp/method is missing, check IDs duplicate or unknown, or required fields fail validation.

Duplicate reviews for the same B70 record or duplicate review IDs are ambiguous and all affected reviews are blocked. A required check cannot be marked NOT_APPLICABLE. A PASS check must cite at least one of the exact B70 evidence refs being reviewed.

## 5. Output and placement

New module:

\`iios_mvp/operating_feasibility_semantic_review_v01.py\`

Nested output:

\`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.operating_feasibility_semantic_review\`

The local pilot report prints reviewer, review time, explicit decision, checklist status, basis and source IDs. The raw optional review input is preserved and included in Replay comparison fields.

## 6. Governance and no-change boundary

B71 does not:
- infer review completion from an AI-generated status or an unstructured note;
- verify reviewer identity, independence or conflicts of interest;
- prove the source file was opened or its content was accurately understood;
- override B70 PIT/source blockers;
- grant formal Evidence/PIT, Forecast or Valuation admission;
- modify B4/B42/B43/B55/B61–B70, SOTP, MIE, expectation_gap, 15% annualized hurdle, target entry price, portfolio constraints or Decision; or
- enable execution authority.

Even when an individual record passes the human checklist, overall operational feasibility remains NOT_IDENTIFIABLE pending complete claim coverage, independent review and formal admission through the appropriate governance process.

## 7. Regression coverage and acceptance

Twenty-seven regression cases are authored in \`tests/test_operating_feasibility_semantic_review_v01.py\`, covering:
- missing/invalid input and B70 record eligibility;
- complete and incomplete checklists;
- exact evidence-reference set and per-check source linkage;
- reviewer identity, method, notes and timezone-aware review timestamp;
- PASS/FAIL/UNKNOWN/NOT_APPLICABLE behavior;
- contradiction, not-supported, partial and unable-to-verify distinctions;
- duplicate B70 record reviews and duplicate review IDs; and
- class-specific sales and unit-cost review requirements.

Tests have not been executed. Replay, CI, unified tests and real macOS acceptance remain deferred / not verified. No PASS is claimed.
