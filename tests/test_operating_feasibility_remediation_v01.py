from __future__ import annotations

from copy import deepcopy

from iios_mvp.operating_feasibility_remediation_v01 import (
    INPUT_SCHEMA,
    build_operating_feasibility_remediation_assessment,
)


REQ = "base:B63_FULL_B4_VECTOR_THRESHOLD:SEG-P1:P1:SUPPORTED_SALES_VOLUME"
ACTION = f"B72:SUPPORTED_SALES_VOLUME:{REQ}"


def _case(*, exception_status="CONDITIONALLY_SUPPORTED_NOT_FORMALLY_ADMITTED"):
    b69 = {"schema_version": "IIOS-SOTP-OPERATING-FEASIBILITY-AUDIT-0.1", "forecast_period": "FY2027"}
    b70 = {
        "schema_version": "IIOS-OPERATING-FEASIBILITY-EVIDENCE-ASSESSMENT-0.1",
        "records": [{
            "record_id": "NEW-REC", "scenario": "base", "product_id": "P1",
            "forecast_period": "FY2027", "claim_type": "SUPPORTED_SALES_VOLUME",
            "data_class": "ISSUER_FORECAST", "evidence_refs": ["EV-NEW"],
        }],
    }
    b71 = {
        "schema_version": "IIOS-OPERATING-FEASIBILITY-SEMANTIC-REVIEW-0.1",
        "reviews": [{
            "review_id": "NEW-REV", "record_id": "NEW-REC",
            "status": "HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY",
            "review_independence_conditionally_declared": True,
        }],
    }
    b72 = {
        "schema_version": "IIOS-OPERATING-FEASIBILITY-EXCEPTION-REGISTER-0.1",
        "requirement_rows": [{
            "requirement_id": REQ, "scenario": "base",
            "lens": "B63_FULL_B4_VECTOR_THRESHOLD", "segment_id": "SEG-P1",
            "product_id": "P1", "requirement_type": "SUPPORTED_SALES_VOLUME",
            "exception_status": exception_status, "b70_record_ids": ["NEW-REC"],
            "b71_review_ids": ["NEW-REV"], "evidence_refs": ["EV-NEW"],
            "remediation": {"action_id": ACTION, "status": "OPEN_REMEDIATION_REQUIRED"},
        }],
    }
    submissions = {
        "schema_version": INPUT_SCHEMA,
        "submissions": [{
            "submission_id": "REM-01", "requirement_id": REQ, "action_id": ACTION,
            "submitted_by": "operator-01", "submitted_at": "2026-10-31T20:00:00+08:00",
            "remediation_summary": "Replaced stale evidence and obtained a new independent review.",
            "prior_exception_status": "EVIDENCE_NOT_PROVIDED",
            "prior_b70_record_ids": ["OLD-REC"], "prior_b71_review_ids": ["OLD-REV"],
            "superseded_b70_record_ids": ["OLD-REC"], "superseded_b71_review_ids": ["OLD-REV"],
        }],
    }
    return submissions, b69, b70, b71, b72


def _run(submissions, b69, b70, b71, b72):
    return build_operating_feasibility_remediation_assessment(
        raw_submissions=submissions, b69_audit=b69, b70_assessment=b70,
        b71_review=b71, b72_register=b72,
    )


def test_conditional_support_waits_for_formal_admission():
    submissions, b69, b70, b71, b72 = _case()
    result = _run(submissions, b69, b70, b71, b72)
    assert result["submissions"][0]["status"] == "REASSESSMENT_PASSED_PENDING_FORMAL_ADMISSION"
    assert result["summary"]["closed_verified_count"] == 0
    assert result["manual_close_allowed"] is False
    assert result["formal_evidence_pit_admission_created"] is False


def test_missing_submissions_is_backward_compatible():
    _, b69, b70, b71, b72 = _case()
    result = _run(None, b69, b70, b71, b72)
    assert result["status"] == "REMEDIATION_SUBMISSIONS_NOT_PROVIDED"
    assert result["submissions"] == []


def test_invalid_schema_blocks():
    submissions, b69, b70, b71, b72 = _case()
    submissions["schema_version"] = "wrong"
    assert _run(submissions, b69, b70, b71, b72)["status"] == "REMEDIATION_INPUT_BLOCKED"


def test_manual_close_fields_are_rejected():
    submissions, b69, b70, b71, b72 = _case()
    submissions["submissions"][0]["closed"] = True
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert row["status"] == "REASSESSMENT_BLOCKED"
    assert any("OPERATOR_CLOSE_FIELDS_NOT_ALLOWED" in issue for issue in row["issues"])


def test_action_id_must_match_current_b72_row():
    submissions, b69, b70, b71, b72 = _case()
    submissions["submissions"][0]["action_id"] = "wrong"
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "B72_ACTION_ID_MISMATCH" in row["issues"]


def test_unknown_requirement_id_blocks():
    submissions, b69, b70, b71, b72 = _case()
    submissions["submissions"][0]["requirement_id"] = "wrong"
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "B72_REQUIREMENT_ID_NOT_FOUND" in row["issues"]


def test_duplicate_requirement_id_blocks():
    submissions, b69, b70, b71, b72 = _case()
    b72["requirement_rows"].append(deepcopy(b72["requirement_rows"][0]))
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "B72_REQUIREMENT_ID_AMBIGUOUS" in row["issues"]


def test_superseded_b70_id_still_active_blocks():
    submissions, b69, b70, b71, b72 = _case()
    b70["records"].append({
        "record_id": "OLD-REC", "scenario": "base", "product_id": "P1",
        "forecast_period": "FY2027", "claim_type": "SUPPORTED_SALES_VOLUME",
        "evidence_refs": ["EV-OLD"],
    })
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "SUPERSEDED_B70_RECORD_STILL_ACTIVE" in row["issues"]


def test_superseded_b71_id_still_active_blocks():
    submissions, b69, b70, b71, b72 = _case()
    b71["reviews"].append({"review_id": "OLD-REV", "record_id": "NEW-REC", "status": "SEMANTIC_REVIEW_NOT_COMPLETE"})
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "SUPERSEDED_B71_REVIEW_STILL_ACTIVE" in row["issues"]


def test_prior_ids_must_be_retained_or_superseded():
    submissions, b69, b70, b71, b72 = _case()
    submissions["submissions"][0]["superseded_b70_record_ids"] = []
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "PRIOR_B70_RECORD_NOT_RETAINED_OR_EXPLICITLY_SUPERSEDED" in row["issues"]


def test_duplicate_b70_record_id_blocks():
    submissions, b69, b70, b71, b72 = _case()
    b70["records"].append(deepcopy(b70["records"][0]))
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert any(issue.startswith("B70_RECORD_ID_MISSING_OR_AMBIGUOUS") for issue in row["issues"])


def test_scope_period_and_claim_must_match():
    submissions, b69, b70, b71, b72 = _case()
    b70["records"][0].update({"scenario": "bull", "product_id": "P2", "forecast_period": "FY2028", "claim_type": "SUPPORTED_NET_ASP"})
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "B70_RECORD_SCENARIO_MISMATCH:NEW-REC" in row["issues"]
    assert "B70_RECORD_PRODUCT_MISMATCH:NEW-REC" in row["issues"]
    assert "B70_RECORD_PERIOD_MISMATCH:NEW-REC" in row["issues"]
    assert "B70_RECORD_CLAIM_TYPE_MISMATCH:NEW-REC" in row["issues"]


def test_b71_must_conditionally_support_each_record():
    submissions, b69, b70, b71, b72 = _case()
    b71["reviews"][0]["status"] = "SEMANTIC_REVIEW_NOT_SUPPORTED"
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "B71_REVIEW_NOT_CONDITIONALLY_SUPPORTED:NEW-REC" in row["issues"]


def test_b71_independence_declaration_is_required():
    submissions, b69, b70, b71, b72 = _case()
    b71["reviews"][0]["review_independence_conditionally_declared"] = False
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "B71_REVIEW_INDEPENDENCE_NOT_DECLARED:NEW-REC" in row["issues"]


def test_b71_must_cover_all_current_records():
    submissions, b69, b70, b71, b72 = _case()
    b72["requirement_rows"][0]["b71_review_ids"] = []
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "CURRENT_B71_REVIEWS_REQUIRED_FOR_REASSESSMENT" in row["issues"]


def test_evidence_refs_must_match_current_records():
    submissions, b69, b70, b71, b72 = _case()
    b72["requirement_rows"][0]["evidence_refs"] = ["wrong-ref"]
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "B72_EVIDENCE_REFS_DO_NOT_MATCH_CURRENT_B70_RECORDS" in row["issues"]


def test_numeric_gap_is_not_closed_by_operator_declaration():
    submissions, b69, b70, b71, b72 = _case(exception_status="QUANTIFIED_REQUIREMENT_GAP")
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert row["status"] == "REASSESSMENT_FAILED"


def test_unmodeled_dimension_requires_upstream_rebuild():
    submissions, b69, b70, b71, b72 = _case()
    target = b72["requirement_rows"][0]
    target["requirement_type"] = "PRICE_ELASTICITY_AND_COMPETITIVE_RESPONSE"
    target["requirement_id"] = "base:B63_FULL_B4_VECTOR_THRESHOLD:SEG-P1:P1:PRICE_ELASTICITY_AND_COMPETITIVE_RESPONSE"
    target["remediation"]["action_id"] = "B72:PRICE_ELASTICITY_AND_COMPETITIVE_RESPONSE:NEW"
    submissions["submissions"][0]["requirement_id"] = target["requirement_id"]
    submissions["submissions"][0]["action_id"] = target["remediation"]["action_id"]
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert row["status"] == "REASSESSMENT_BLOCKED_UPSTREAM_SCOPE_REQUIRED"


def test_duplicate_submission_ids_block_all():
    submissions, b69, b70, b71, b72 = _case()
    submissions["submissions"].append(deepcopy(submissions["submissions"][0]))
    result = _run(submissions, b69, b70, b71, b72)
    assert all(row["status"] == "REASSESSMENT_BLOCKED" for row in result["submissions"])


def test_timestamp_requires_timezone():
    submissions, b69, b70, b71, b72 = _case()
    submissions["submissions"][0]["submitted_at"] = "2026-10-31T20:00:00"
    row = _run(submissions, b69, b70, b71, b72)["submissions"][0]
    assert "SUBMITTED_AT_MUST_INCLUDE_TIMEZONE" in row["issues"]


def test_closed_verified_is_never_emitted():
    submissions, b69, b70, b71, b72 = _case()
    result = _run(submissions, b69, b70, b71, b72)
    assert result["summary"]["closed_verified_count"] == 0
    assert all(row["status"] != "CLOSED_VERIFIED" for row in result["submissions"])
