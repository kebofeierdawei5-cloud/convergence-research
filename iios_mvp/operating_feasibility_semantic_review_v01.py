from __future__ import annotations

"""B71: human semantic review of B70 operating-feasibility evidence claims.

This layer records structured reviewer assertions. It does not verify the
reviewer's identity, source bytes or source truth, and does not grant admission.
"""

from datetime import datetime
from typing import Any, Mapping

B71_SCHEMA = "IIOS-OPERATING-FEASIBILITY-SEMANTIC-REVIEW-0.1"
INPUT_SCHEMA = "IIOS-OPERATING-FEASIBILITY-SEMANTIC-REVIEWS-0.1"
B70_ELIGIBLE = "PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED"
_OUTCOMES = {
    "SUPPORTS",
    "PARTIALLY_SUPPORTS",
    "DOES_NOT_SUPPORT",
    "CONTRADICTS",
    "UNABLE_TO_VERIFY",
}
_CHECK_STATES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}

_COMMON = ("SOURCE_CONTENT_READ", "PRODUCT_SCOPE_MATCH", "PERIOD_SCOPE_MATCH")
_REQUIRED_CHECKS = {
    "SUPPORTED_SALES_VOLUME": _COMMON + (
        "CUSTOMER_IDENTITY_AND_CREDIT_SCOPE_VERIFIED",
        "ORDER_OR_CONTRACT_BINDING_STATUS_VERIFIED",
        "DELIVERY_QUANTITY_NET_OF_CANCELLATIONS_RECONCILED",
        "DUPLICATE_OR_OVERLAPPING_ORDERS_CHECKED",
        "DELIVERY_WINDOW_AND_CUSTOMER_ACCEPTANCE_MATCH",
    ),
    "SUPPORTED_NET_ASP": _COMMON + (
        "CUSTOMER_AND_PRODUCT_PRICE_SCOPE_MATCH",
        "CONTRACTUAL_OR_REALIZED_PRICE_STATUS_VERIFIED",
        "GROSS_TO_NET_TAX_FREIGHT_DISCOUNT_REBATE_BASIS_RECONCILED",
        "PRICE_EFFECTIVE_DATE_AND_DELIVERY_WINDOW_MATCH",
        "PRICE_MIX_NOT_CONFUSED_WITH_LIKE_FOR_LIKE_PRICE",
    ),
    "SUPPORTED_UNIT_VARIABLE_COST": _COMMON + (
        "COST_COMPONENTS_AND_ALLOCATION_BASIS_RECONCILED",
        "INPUT_ENERGY_YIELD_AND_UTILITIES_BASIS_VERIFIED",
        "UNIT_COST_COMPARABILITY_AND_PERIOD_MATCHED",
    ),
    "EFFECTIVE_CAPACITY_AVAILABLE": _COMMON + (
        "EFFECTIVE_CAPACITY_DISTINGUISHED_FROM_NAMEPLATE",
        "BOTTLENECK_MAINTENANCE_AND_YIELD_CONSTRAINTS_CHECKED",
        "PRODUCT_LINE_AND_SHARED_CAPACITY_SCOPE_VERIFIED",
        "AVAILABLE_DURING_REQUIRED_PRODUCTION_WINDOW",
    ),
    "CAPACITY_AVAILABLE_DATE": _COMMON + (
        "PROJECT_IDENTITY_AND_SCOPE_MATCH",
        "PERMIT_CONSTRUCTION_AND_EQUIPMENT_STATUS_VERIFIED",
        "COMMISSIONING_OR_ACCEPTANCE_EVIDENCE_VERIFIED",
        "RAMP_UP_AND_FIRST_QUALIFIED_OUTPUT_DATE_VERIFIED",
        "AVAILABLE_DATE_MATCHES_REQUIRED_PERIOD",
    ),
    "INCREMENTAL_CAPEX_REQUIRED": _COMMON + (
        "PROJECT_COST_SCOPE_AND_ESTIMATE_BASIS_RECONCILED",
        "TAX_CONTINGENCY_AND_ESCALATION_BASIS_CHECKED",
        "INCREMENTAL_TO_B4_FORWARD_PLAN_RECONCILED",
        "PAYMENT_TIMING_AND_APPROVAL_STATUS_VERIFIED",
    ),
    "INCREMENTAL_CAPEX_FUNDED": _COMMON + (
        "FUNDING_COMMITMENT_BINDING_STATUS_VERIFIED",
        "AMOUNT_UNRESTRICTED_AND_AVAILABLE_VERIFIED",
        "FUNDING_AVAILABILITY_DATE_MATCHED_TO_SPEND",
        "ALREADY_ALLOCATED_OR_DOUBLE_COUNTED_FUNDS_CHECKED",
        "INCREMENTAL_TO_B4_FORWARD_PLAN_RECONCILED",
    ),
    "INCREMENTAL_WORKING_CAPITAL_REQUIRED": _COMMON + (
        "WORKING_CAPITAL_COMPONENTS_AND_CASH_CYCLE_RECONCILED",
        "INCREMENTAL_TO_B4_FORWARD_PLAN_RECONCILED",
        "CUSTOMER_CREDIT_INVENTORY_AND_SUPPLIER_TERMS_CHECKED",
        "SEASONAL_PEAK_AND_TIMING_NEED_CHECKED",
    ),
    "INCREMENTAL_WORKING_CAPITAL_FUNDED": _COMMON + (
        "FUNDING_COMMITMENT_BINDING_STATUS_VERIFIED",
        "AMOUNT_UNRESTRICTED_AND_AVAILABLE_VERIFIED",
        "FUNDING_AVAILABILITY_DATE_MATCHED_TO_CASH_NEED",
        "ALREADY_ALLOCATED_OR_DOUBLE_COUNTED_FUNDS_CHECKED",
        "INCREMENTAL_TO_B4_FORWARD_PLAN_RECONCILED",
    ),
}
_DYNAMIC_CHECKS = {
    "SUPPORTED_UNIT_VARIABLE_COST": {
        "OBSERVED_ACTUAL": "ACTUAL_COST_BASELINE_AND_ALLOCATION_RECONCILED",
        "ISSUER_FORECAST": "COST_SAVING_ACTION_OWNER_AND_EXECUTION_MILESTONES_VERIFIED",
        "ANALYST_ASSUMPTION": "COST_SAVING_ACTION_OWNER_AND_EXECUTION_MILESTONES_VERIFIED",
    }
}


def _txt(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _datetime(value: Any) -> tuple[str | None, str | None]:
    raw = _txt(value)
    if not raw:
        return None, "REVIEWED_AT_REQUIRED"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None, "REVIEWED_AT_MUST_BE_ISO_DATETIME"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, "REVIEWED_AT_MUST_INCLUDE_TIMEZONE"
    return parsed.isoformat(), None


def _index_b70(rows: Any) -> tuple[dict[str, Mapping[str, Any]], set[str]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    duplicates: set[str] = set()
    if not isinstance(rows, list):
        return indexed, duplicates
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        record_id = _txt(row.get("record_id"))
        if not record_id:
            continue
        if record_id in indexed:
            duplicates.add(record_id)
        else:
            indexed[record_id] = row
    return indexed, duplicates


def _requirements(claim_type: str, data_class: str) -> tuple[str, ...]:
    checks = _REQUIRED_CHECKS.get(claim_type, ())
    dynamic = _DYNAMIC_CHECKS.get(claim_type, {}).get(data_class)
    return checks + ((dynamic,) if dynamic else ())


def _review_one(
    raw: Any,
    *,
    b70_records: Mapping[str, Mapping[str, Any]],
    duplicate_b70_ids: set[str],
    duplicate_reviews: set[str],
    duplicate_review_ids: set[str],
) -> dict[str, Any]:
    review = raw if isinstance(raw, Mapping) else {}
    review_id = _txt(review.get("review_id"))
    record_id = _txt(review.get("record_id"))
    reviewer_id = _txt(review.get("reviewer_id"))
    reviewed_at, datetime_issue = _datetime(review.get("reviewed_at"))
    method = _txt(review.get("review_method")).upper()
    decision = _txt(review.get("decision")).upper()
    refs = [
        str(item).strip()
        for item in (review.get("reviewed_evidence_refs") if isinstance(review.get("reviewed_evidence_refs"), list) else [])
        if str(item).strip()
    ]
    notes = _txt(review.get("review_notes"))
    issues: list[str] = []
    if not review_id:
        issues.append("REVIEW_ID_REQUIRED")
    if review_id in duplicate_review_ids:
        issues.append("DUPLICATE_REVIEW_ID")
    if not record_id:
        issues.append("B70_RECORD_ID_REQUIRED")
    if record_id in duplicate_reviews:
        issues.append("DUPLICATE_REVIEW_FOR_B70_RECORD")
    if record_id in duplicate_b70_ids:
        issues.append("B70_RECORD_ID_AMBIGUOUS")
    b70_record = b70_records.get(record_id)
    if b70_record is None:
        issues.append("B70_RECORD_NOT_FOUND")
    if not reviewer_id:
        issues.append("REVIEWER_ID_REQUIRED")
    if datetime_issue:
        issues.append(datetime_issue)
    if method != "HUMAN_SOURCE_CONTENT_REVIEW":
        issues.append("REVIEW_METHOD_MUST_BE_HUMAN_SOURCE_CONTENT_REVIEW")
    if decision not in _OUTCOMES:
        issues.append("REVIEW_DECISION_INVALID")
    if not notes:
        issues.append("HUMAN_REVIEW_NOTES_REQUIRED")
    if not refs:
        issues.append("REVIEWED_EVIDENCE_REFERENCES_REQUIRED")

    claim_type = _txt(_map(b70_record).get("claim_type")).upper()
    data_class = _txt(_map(b70_record).get("data_class")).upper()
    required = set(_requirements(claim_type, data_class))
    if not required:
        issues.append("B70_CLAIM_TYPE_HAS_NO_SEMANTIC_REVIEW_CHECKLIST")
    b70_refs = set(
        str(item).strip()
        for item in (_map(b70_record).get("evidence_refs") if isinstance(_map(b70_record).get("evidence_refs"), list) else [])
        if str(item).strip()
    )
    if b70_record and _txt(b70_record.get("status")) != B70_ELIGIBLE:
        issues.append("B70_CLAIM_NOT_ELIGIBLE_FOR_SEMANTIC_REVIEW")
    if refs and b70_refs and set(refs) != b70_refs:
        issues.append("REVIEW_MUST_COVER_EXACT_B70_EVIDENCE_REFERENCE_SET")
    elif b70_record and not b70_refs:
        issues.append("B70_CLAIM_HAS_NO_EVIDENCE_REFERENCES")

    checks_raw = review.get("checks")
    checks_raw = checks_raw if isinstance(checks_raw, list) else []
    checks_by_id: dict[str, Mapping[str, Any]] = {}
    duplicate_check_ids: set[str] = set()
    for check in checks_raw:
        if not isinstance(check, Mapping):
            continue
        check_id = _txt(check.get("check_id"))
        if not check_id:
            continue
        if check_id in checks_by_id:
            duplicate_check_ids.add(check_id)
        else:
            checks_by_id[check_id] = check
    if duplicate_check_ids:
        issues.append("DUPLICATE_SEMANTIC_CHECK_IDS")

    missing_checks = sorted(required - set(checks_by_id))
    unexpected_checks = sorted(set(checks_by_id) - required)
    if missing_checks:
        issues.extend(f"REQUIRED_SEMANTIC_CHECK_MISSING:{item}" for item in missing_checks)
    if unexpected_checks:
        issues.extend(f"UNRECOGNIZED_SEMANTIC_CHECK:{item}" for item in unexpected_checks)

    normalized_checks: list[dict[str, Any]] = []
    check_states: list[str] = []
    for check_id in sorted(required):
        raw_check = checks_by_id.get(check_id)
        if raw_check is None:
            continue
        state = _txt(raw_check.get("status")).upper()
        basis = _txt(raw_check.get("basis"))
        check_refs = [
            str(item).strip()
            for item in (raw_check.get("evidence_refs") if isinstance(raw_check.get("evidence_refs"), list) else [])
            if str(item).strip()
        ]
        check_issues: list[str] = []
        if state not in _CHECK_STATES:
            check_issues.append("CHECK_STATUS_INVALID")
        if not basis:
            check_issues.append("CHECK_BASIS_REQUIRED")
        if state == "PASS" and not check_refs:
            check_issues.append("PASS_CHECK_REQUIRES_EVIDENCE_REFERENCES")
        if any(ref not in refs for ref in check_refs):
            check_issues.append("CHECK_REFERENCE_NOT_IN_REVIEWED_EVIDENCE_SET")
        if state == "NOT_APPLICABLE":
            check_issues.append("REQUIRED_SEMANTIC_CHECK_CANNOT_BE_NOT_APPLICABLE")
        if check_issues:
            issues.extend(f"{check_id}:{item}" for item in check_issues)
        check_states.append(state)
        normalized_checks.append({
            "check_id": check_id,
            "status": state or "UNKNOWN",
            "basis": basis or "UNKNOWN",
            "evidence_refs": check_refs,
            "issues": check_issues,
        })

    missing_refs = sorted(ref for ref in refs if b70_record and ref not in b70_refs)
    if missing_refs:
        issues.extend(f"REVIEW_REFERENCE_NOT_IN_B70_CLAIM:{ref}" for ref in missing_refs)

    all_required_pass = bool(required) and len(check_states) == len(required) and all(
        state == "PASS" for state in check_states
    )
    any_failed = any(state == "FAIL" for state in check_states)
    any_unknown = any(state == "UNKNOWN" for state in check_states)
    if any_failed or any_unknown or missing_checks or unexpected_checks:
        all_required_pass = False

    if issues:
        status = "SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE"
    elif any_failed and decision == "SUPPORTS":
        status = "SEMANTIC_REVIEW_CHECK_FAILURE_CONFLICTS_WITH_SUPPORT_DECISION"
    elif any_failed:
        status = "SEMANTIC_REVIEW_CHECKS_FAILED"
    elif decision == "CONTRADICTS":
        status = "SEMANTIC_REVIEW_CONTRADICTED"
    elif decision == "DOES_NOT_SUPPORT":
        status = "SEMANTIC_REVIEW_NOT_SUPPORTED"
    elif decision == "UNABLE_TO_VERIFY":
        status = "SEMANTIC_REVIEW_UNABLE_TO_VERIFY"
    elif decision == "PARTIALLY_SUPPORTS":
        status = "SEMANTIC_REVIEW_PARTIAL"
    elif all_required_pass and decision == "SUPPORTS":
        status = "HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY"
    else:
        status = "SEMANTIC_REVIEW_NOT_COMPLETE"

    return {
        "review_id": review_id or None,
        "record_id": record_id or "UNKNOWN",
        "claim_type": claim_type or "UNKNOWN",
        "product_id": _txt(_map(b70_record).get("product_id")) or "UNKNOWN",
        "scenario": _txt(_map(b70_record).get("scenario")) or "UNKNOWN",
        "forecast_period": _txt(_map(b70_record).get("forecast_period")) or "UNKNOWN",
        "reviewer_id": reviewer_id or "UNKNOWN",
        "reviewed_at": reviewed_at,
        "review_time_is_pit_evidence": False,
        "review_method": method or "UNKNOWN",
        "decision": decision or "UNKNOWN",
        "reviewed_evidence_refs": refs,
        "required_check_ids": sorted(required),
        "checks": normalized_checks,
        "required_checks_all_pass": all_required_pass,
        "review_notes": notes or "UNKNOWN",
        "status": status,
        "issues": list(dict.fromkeys(issues)),
        "human_identity_independently_verified": False,
        "source_content_semantically_verified_by_automation": False,
        "formal_evidence_pit_admission": False,
    }


def build_operating_feasibility_semantic_review(
    *,
    raw_reviews: Any,
    b70_assessment: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply claim-type-specific human semantic review without automatic admission."""
    result: dict[str, Any] = {
        "schema_version": B71_SCHEMA,
        "status": "SEMANTIC_REVIEW_NOT_PROVIDED",
        "reviews": [],
        "reviewed_claim_count": 0,
        "conditionally_supported_claim_count": 0,
        "blocked_or_incomplete_claim_count": 0,
        "contradicted_claim_count": 0,
        "overall_operational_feasibility_status": "NOT_IDENTIFIABLE",
        "human_review_is_a_recorded_assertion_not_independent_identity_verification": True,
        "formal_evidence_pit_admission_created": False,
        "decision_authority": False,
        "limitations": [
            "B71 记录人工审核声明和逐项检查结果，不验证审核人真实身份、独立性、利益冲突或本机是否实际打开原始材料。",
            "自动程序不能证明合同法律效力、订单不重叠、客户真实性、净售价可实现、成本项目可执行或资金无抵押/重复占用；这些需要人工查看原始材料并承担审核责任。",
            "只有 B70 已通过来源引用和 PIT 时间初检的记录才允许进行语义审核；B71 不修复 B70 的缺失来源或时间问题。",
            "语义审核结果仍不是正式 Evidence/PIT admission、预测准入、估值准入或投资决策。",
        ],
    }
    if not isinstance(raw_reviews, Mapping):
        return result
    if _txt(raw_reviews.get("schema_version")) != INPUT_SCHEMA:
        result["status"] = "INVALID_INPUT_SCHEMA"
        result["issues"] = ["OPERATING_FEASIBILITY_SEMANTIC_REVIEW_SCHEMA_MISMATCH"]
        return result
    raw_rows = raw_reviews.get("reviews")
    if not isinstance(raw_rows, list):
        result["status"] = "INVALID_REVIEWS"
        result["issues"] = ["OPERATING_FEASIBILITY_SEMANTIC_REVIEWS_MUST_BE_LIST"]
        return result

    b70_records, duplicate_b70_ids = _index_b70(_map(b70_assessment).get("records"))
    counts: dict[str, int] = {}
    for row in raw_rows:
        if isinstance(row, Mapping):
            rid = _txt(row.get("record_id"))
            if rid:
                counts[rid] = counts.get(rid, 0) + 1
    duplicate_reviews = {key for key, count in counts.items() if count > 1}
    review_id_counts: dict[str, int] = {}
    for row in raw_rows:
        if isinstance(row, Mapping):
            review_id = _txt(row.get("review_id"))
            if review_id:
                review_id_counts[review_id] = review_id_counts.get(review_id, 0) + 1
    duplicate_review_ids = {key for key, count in review_id_counts.items() if count > 1}

    normalized = [
        _review_one(
            row,
            b70_records=b70_records,
            duplicate_b70_ids=duplicate_b70_ids,
            duplicate_reviews=duplicate_reviews,
            duplicate_review_ids=duplicate_review_ids,
        )
        for row in raw_rows
    ]
    result["reviews"] = normalized
    result["reviewed_claim_count"] = len(normalized)
    result["conditionally_supported_claim_count"] = sum(
        row.get("status") == "HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY"
        for row in normalized
    )
    result["blocked_or_incomplete_claim_count"] = sum(
        row.get("status") in {"SEMANTIC_REVIEW_BLOCKED_OR_INCOMPLETE", "SEMANTIC_REVIEW_NOT_COMPLETE", "SEMANTIC_REVIEW_PARTIAL", "SEMANTIC_REVIEW_UNABLE_TO_VERIFY"}
        for row in normalized
    )
    result["contradicted_claim_count"] = sum(
        row.get("status") in {"SEMANTIC_REVIEW_CONTRADICTED", "SEMANTIC_REVIEW_NOT_SUPPORTED"}
        for row in normalized
    )
    result["status"] = (
        "SEMANTIC_REVIEW_RECORDED"
        if normalized else "SEMANTIC_REVIEW_NOT_PROVIDED"
    )
    result["overall_operational_feasibility_status"] = (
        "NOT_IDENTIFIABLE_PENDING_BROADER_COVERAGE_AND_INDEPENDENT_ADMISSION"
    )
    result["summary"] = (
        "B71 对 B70 的经营主张执行逐类型、逐项人工语义审核记录。审核完成只表示操作者记录的检查项齐备，"
        "不证明审核人身份或原始来源内容真实，也不创建正式证据准入。"
    )
    result["duplicate_reviewed_record_ids"] = sorted(duplicate_reviews)
    result["duplicate_review_ids"] = sorted(duplicate_review_ids)
    result["duplicate_b70_record_ids"] = sorted(duplicate_b70_ids)
    return result
