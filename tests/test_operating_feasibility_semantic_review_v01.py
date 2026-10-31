from __future__ import annotations

from iios_mvp.operating_feasibility_semantic_review_v01 import (
    INPUT_SCHEMA,
    build_operating_feasibility_semantic_review,
)


def _b70(claim_type="SUPPORTED_SALES_VOLUME", data_class="ISSUER_FORECAST", record_id="R1", refs=None, status="PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED"):
    return {
        "records": [{
            "record_id": record_id,
            "claim_type": claim_type,
            "product_id": "P1",
            "scenario": "base",
            "forecast_period": "FY2027",
            "value": "120",
            "unit": "tonnes",
            "data_class": data_class,
            "basis": "Signed customer volume claim",
            "evidence_refs": refs or ["E1"],
            "status": status,
        }]
    }


def _review(b70=None, *, decision="SUPPORTS", checks=None, refs=None, reviewed_at="2026-10-31T10:00:00+08:00", method="HUMAN_SOURCE_CONTENT_REVIEW", reviewer_id="analyst-01", review_id="RV1", record_id="R1"):
    claim = _b70() if b70 is None else b70
    row = claim["records"][0]
    from iios_mvp.operating_feasibility_semantic_review_v01 import _requirements
    required = _requirements(row["claim_type"], row["data_class"])
    normalized_checks = checks if checks is not None else [
        {
            "check_id": check_id,
            "status": "PASS",
            "basis": f"Reviewed original source evidence for {check_id}",
            "evidence_refs": ["E1"],
        }
        for check_id in required
    ]
    return {
        "schema_version": INPUT_SCHEMA,
        "reviews": [{
            "review_id": review_id,
            "record_id": record_id,
            "reviewer_id": reviewer_id,
            "claim_preparer_id": "analyst-preparer-01",
            "reviewer_role": "INDEPENDENT_REVIEWER",
            "reviewer_relationship_status": "INDEPENDENT_OF_CLAIM_PREPARER",
            "conflict_of_interest_status": "NO_KNOWN_CONFLICT",
            "reviewed_at": reviewed_at,
            "review_method": method,
            "decision": decision,
            "reviewed_evidence_refs": refs or row.get("evidence_refs", ["E1"]),
            "checks": normalized_checks,
            "review_notes": "Opened source document and checked the claim scope.",
        }],
    }, claim


def _run(raw, b70=None):
    return build_operating_feasibility_semantic_review(
        raw_reviews=raw,
        b70_assessment=_b70() if b70 is None else b70,
    )


def _base_result():
    raw, b70 = _review()
    return _run(raw, b70)


def test_b71_missing_reviews_remain_not_provided():
    result = build_operating_feasibility_semantic_review(raw_reviews=None, b70_assessment=_b70())
    assert result["status"] == "SEMANTIC_REVIEW_NOT_PROVIDED"
    assert result["overall_operational_feasibility_status"] == "NOT_IDENTIFIABLE"


def test_b71_rejects_wrong_review_schema():
    raw, b70 = _review()
    raw["schema_version"] = "WRONG"
    result = _run(raw, b70)
    assert result["status"] == "INVALID_INPUT_SCHEMA"


def test_b71_all_required_sales_checks_and_exact_refs_allow_conditional_human_review():
    result = _base_result()
    review = result["reviews"][0]
    assert review["status"] == "HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY"
    assert review["required_checks_all_pass"] is True
    assert review["record_id"] == "R1"
    assert review["product_id"] == "P1"
    assert review["scenario"] == "base"
    assert result["conditionally_supported_claim_count"] == 1
    assert result["formal_evidence_pit_admission_created"] is False


def test_b71_does_not_claim_human_identity_or_source_truth_is_automatically_verified():
    result = _base_result()
    review = result["reviews"][0]
    assert review["human_identity_independently_verified"] is False
    assert review["source_content_semantically_verified_by_automation"] is False
    assert review["review_time_is_pit_evidence"] is False


def test_b71_requires_exact_b70_evidence_reference_set():
    raw, b70 = _review(refs=["E1", "E2"])
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert "REVIEW_MUST_COVER_EXACT_B70_EVIDENCE_REFERENCE_SET" in result["reviews"][0]["issues"]


def test_b71_missing_required_semantic_check_blocks_support():
    raw, b70 = _review()
    raw["reviews"][0]["checks"].pop()
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert any(issue.startswith("REQUIRED_SEMANTIC_CHECK_MISSING:") for issue in result["reviews"][0]["issues"])


def test_b71_unknown_required_check_prevents_conditional_support():
    raw, b70 = _review()
    raw["reviews"][0]["checks"][0]["status"] = "UNKNOWN"
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_NOT_COMPLETE"
    assert result["reviews"][0]["required_checks_all_pass"] is False


def test_b71_failed_check_conflicts_with_support_decision():
    raw, b70 = _review()
    raw["reviews"][0]["checks"][0]["status"] = "FAIL"
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_CHECK_FAILURE_CONFLICTS_WITH_SUPPORT_DECISION"


def test_b71_required_check_cannot_be_marked_not_applicable():
    raw, b70 = _review()
    raw["reviews"][0]["checks"][0]["status"] = "NOT_APPLICABLE"
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"


def test_b71_pass_check_requires_specific_source_reference():
    raw, b70 = _review()
    raw["reviews"][0]["checks"][0]["evidence_refs"] = []
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert any("PASS_CHECK_REQUIRES_EVIDENCE_REFERENCES" in issue for issue in result["reviews"][0]["issues"])


def test_b71_check_reference_must_be_in_reviewed_reference_set():
    raw, b70 = _review()
    raw["reviews"][0]["checks"][0]["evidence_refs"] = ["OTHER"]
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert any("CHECK_REFERENCE_NOT_IN_REVIEWED_EVIDENCE_SET" in issue for issue in result["reviews"][0]["issues"])


def test_b71_review_timestamp_requires_timezone():
    raw, b70 = _review(reviewed_at="2026-10-31T10:00:00")
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert "REVIEWED_AT_MUST_INCLUDE_TIMEZONE" in result["reviews"][0]["issues"]


def test_b71_review_method_must_be_human_source_content_review():
    raw, b70 = _review(method="AI_AUTOMATED_REVIEW")
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert "REVIEW_METHOD_MUST_BE_HUMAN_SOURCE_CONTENT_REVIEW" in result["reviews"][0]["issues"]


def test_b71_requires_reviewer_id_and_review_notes():
    raw, b70 = _review(reviewer_id="")
    raw["reviews"][0]["review_notes"] = ""
    result = _run(raw, b70)
    assert "REVIEWER_ID_REQUIRED" in result["reviews"][0]["issues"]
    assert "HUMAN_REVIEW_NOTES_REQUIRED" in result["reviews"][0]["issues"]


def test_b71_refuses_b70_record_that_failed_pit_linkage():
    b70 = _b70(status="NOT_IDENTIFIABLE")
    raw, _ = _review(b70=b70)
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert "B70_CLAIM_NOT_ELIGIBLE_FOR_SEMANTIC_REVIEW" in result["reviews"][0]["issues"]


def test_b71_duplicate_reviews_for_same_b70_claim_are_ambiguous():
    raw, b70 = _review()
    duplicate = dict(raw["reviews"][0])
    duplicate["review_id"] = "RV2"
    raw["reviews"].append(duplicate)
    result = _run(raw, b70)
    assert result["duplicate_reviewed_record_ids"] == ["R1"]
    assert all(row["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE" for row in result["reviews"])


def test_b71_duplicate_review_ids_are_blocked():
    raw, b70 = _review()
    second_claim = _b70(record_id="R2")["records"][0]
    b70["records"].append(second_claim)
    second_review = dict(raw["reviews"][0])
    second_review["record_id"] = "R2"
    raw["reviews"].append(second_review)
    result = _run(raw, b70)
    assert result["duplicate_review_ids"] == ["RV1"]
    assert all("DUPLICATE_REVIEW_ID" in row["issues"] for row in result["reviews"])


def test_b71_records_explicit_contradiction():
    raw, b70 = _review(decision="CONTRADICTS")
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_CONTRADICTED"
    assert result["contradicted_claim_count"] == 1


def test_b71_records_does_not_support_separately_from_contradiction():
    raw, b70 = _review(decision="DOES_NOT_SUPPORT")
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_NOT_SUPPORTED"


def test_b71_records_partial_support_without_promoting_claim():
    raw, b70 = _review(decision="PARTIALLY_SUPPORTS")
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_PARTIAL"


def test_b71_cost_forecast_requires_executable_savings_action_check():
    b70 = _b70(claim_type="SUPPORTED_UNIT_VARIABLE_COST", data_class="ISSUER_FORECAST")
    raw, _ = _review(b70=b70)
    ids = [item["check_id"] for item in raw["reviews"][0]["checks"]]
    assert "COST_SAVING_ACTION_OWNER_AND_EXECUTION_MILESTONES_VERIFIED" in ids
    assert "ACTUAL_COST_BASELINE_AND_ALLOCATION_RECONCILED" not in ids


def test_b71_observed_cost_requires_actual_baseline_not_savings_project():
    b70 = _b70(claim_type="SUPPORTED_UNIT_VARIABLE_COST", data_class="OBSERVED_ACTUAL")
    raw, _ = _review(b70=b70)
    ids = [item["check_id"] for item in raw["reviews"][0]["checks"]]
    assert "ACTUAL_COST_BASELINE_AND_ALLOCATION_RECONCILED" in ids
    assert "COST_SAVING_ACTION_OWNER_AND_EXECUTION_MILESTONES_VERIFIED" not in ids


def test_b71_unknown_b70_claim_type_cannot_be_semantically_approved():
    b70 = _b70(claim_type="UNRECOGNIZED_CLAIM")
    raw, _ = _review(b70=b70)
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert "B70_CLAIM_TYPE_HAS_NO_SEMANTIC_REVIEW_CHECKLIST" in result["reviews"][0]["issues"]


def test_b71_future_sales_claim_requires_firm_order_and_cancellation_review():
    b70 = _b70(claim_type="SUPPORTED_SALES_VOLUME", data_class="ISSUER_FORECAST")
    raw, _ = _review(b70=b70)
    ids = [item["check_id"] for item in raw["reviews"][0]["checks"]]
    assert "FIRM_ORDER_AND_CANCELLATION_RIGHTS_VERIFIED" in ids
    assert "INVOICED_SHIPPED_AND_CUSTOMER_ACCEPTED_QUANTITY_RECONCILED" not in ids


def test_b71_observed_sales_claim_requires_invoice_shipment_and_acceptance_review():
    b70 = _b70(claim_type="SUPPORTED_SALES_VOLUME", data_class="OBSERVED_ACTUAL")
    raw, _ = _review(b70=b70)
    ids = [item["check_id"] for item in raw["reviews"][0]["checks"]]
    assert "INVOICED_SHIPPED_AND_CUSTOMER_ACCEPTED_QUANTITY_RECONCILED" in ids
    assert "FIRM_ORDER_AND_CANCELLATION_RIGHTS_VERIFIED" not in ids


def test_b71_explicit_contradiction_is_not_hidden_as_generic_check_failure():
    raw, b70 = _review(decision="CONTRADICTS")
    raw["reviews"][0]["checks"][0]["status"] = "FAIL"
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_CONTRADICTED"


def test_b71_explicit_not_supported_is_distinct_from_failed_check_status():
    raw, b70 = _review(decision="DOES_NOT_SUPPORT")
    raw["reviews"][0]["checks"][0]["status"] = "FAIL"
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_NOT_SUPPORTED"


def test_b71_self_review_cannot_be_conditionally_supported():
    raw, b70 = _review()
    raw["reviews"][0]["claim_preparer_id"] = raw["reviews"][0]["reviewer_id"]
    raw["reviews"][0]["reviewer_relationship_status"] = "SAME_PERSON"
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_INDEPENDENCE_UNRESOLVED"
    assert result["reviews"][0]["review_independence_conditionally_declared"] is False


def test_b71_disclosed_conflict_cannot_be_conditionally_supported():
    raw, b70 = _review()
    raw["reviews"][0]["conflict_of_interest_status"] = "CONFLICT_DISCLOSED"
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_INDEPENDENCE_UNRESOLVED"


def test_b71_requires_claim_preparer_and_reviewer_role():
    raw, b70 = _review()
    raw["reviews"][0]["claim_preparer_id"] = ""
    raw["reviews"][0]["reviewer_role"] = ""
    result = _run(raw, b70)
    assert "CLAIM_PREPARER_ID_REQUIRED" in result["reviews"][0]["issues"]
    assert "REVIEWER_ROLE_REQUIRED" in result["reviews"][0]["issues"]


def test_b71_every_b70_source_reference_must_map_to_a_specific_check():
    b70 = _b70(refs=["E1", "E2"])
    raw, _ = _review(b70=b70)
    result = _run(raw, b70)
    assert result["reviews"][0]["status"] == "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    assert "REVIEWED_SOURCE_NOT_MAPPED_TO_ANY_SEMANTIC_CHECK:E2" in result["reviews"][0]["issues"]
