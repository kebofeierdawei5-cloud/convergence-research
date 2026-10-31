from __future__ import annotations

"""B73: evidence-driven reassessment of B72 remediation submissions."""

from datetime import datetime
from typing import Any, Mapping

B73_SCHEMA = "IIOS-OPERATING-FEASIBILITY-REMEDIATION-ASSESSMENT-0.1"
INPUT_SCHEMA = "IIOS-OPERATING-FEASIBILITY-REMEDIATION-SUBMISSIONS-0.1"
_SCHEMAS = {
    "b69": "IIOS-SOTP-OPERATING-FEASIBILITY-AUDIT-0.1",
    "b70": "IIOS-OPERATING-FEASIBILITY-EVIDENCE-ASSESSMENT-0.1",
    "b71": "IIOS-OPERATING-FEASIBILITY-SEMANTIC-REVIEW-0.1",
    "b72": "IIOS-OPERATING-FEASIBILITY-EXCEPTION-REGISTER-0.1",
}
_PASS = "CONDITIONALLY_SUPPORTED_NOT_FORMALLY_ADMITTED"
_UPSTREAM_ONLY = {
    "B69_NAMEPLATE_CAPACITY_ARITHMETIC",
    "CUSTOMER_DEMAND_SUSTAINABILITY_AND_ELASTICITY",
    "PRICE_ELASTICITY_AND_COMPETITIVE_RESPONSE",
    "COST_CURVE_AND_SAVINGS_EXECUTION",
}
_FORBIDDEN_CLOSE_FIELDS = {
    "closed", "closed_at", "closed_verified", "close_reason",
    "manual_close", "resolution_status", "verified_by",
}


def _txt(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _ids(value: Any, field: str, issues: list[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        issues.append(f"{field}_MUST_BE_LIST")
        return []
    values = [_txt(item) for item in value]
    if any(not item for item in values):
        issues.append(f"{field}_CONTAINS_EMPTY_ID")
    clean = [item for item in values if item]
    if len(clean) != len(set(clean)):
        issues.append(f"{field}_CONTAINS_DUPLICATE_ID")
    return list(dict.fromkeys(clean))


def _timestamp(value: Any) -> tuple[str | None, str | None]:
    raw = _txt(value)
    if not raw:
        return None, "SUBMITTED_AT_REQUIRED"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None, "SUBMITTED_AT_MUST_BE_ISO_DATETIME"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, "SUBMITTED_AT_MUST_INCLUDE_TIMEZONE"
    return parsed.isoformat(), None


def _index(rows: list[Mapping[str, Any]], field: str):
    indexed: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        key = _txt(row.get(field))
        if key:
            indexed.setdefault(key, []).append(row)
    duplicates = {key for key, matches in indexed.items() if len(matches) != 1}
    return indexed, duplicates


def _claim_types(requirement_type: str) -> set[str]:
    return {
        "INCREMENTAL_CAPEX_REQUIRED": {
            "INCREMENTAL_CAPEX_REQUIRED", "INCREMENTAL_CAPEX_FUNDED"
        },
        "INCREMENTAL_WORKING_CAPITAL_REQUIRED": {
            "INCREMENTAL_WORKING_CAPITAL_REQUIRED",
            "INCREMENTAL_WORKING_CAPITAL_FUNDED",
        },
    }.get(requirement_type, {requirement_type})


def _assess_one(
    raw: Mapping[str, Any],
    *,
    b69: Mapping[str, Any],
    b71: Mapping[str, Any],
    requirements: Mapping[str, list[Mapping[str, Any]]],
    duplicate_requirements: set[str],
    records: Mapping[str, list[Mapping[str, Any]]],
    duplicate_records: set[str],
    reviews: Mapping[str, list[Mapping[str, Any]]],
    duplicate_reviews: set[str],
    all_record_ids: set[str],
    all_review_ids: set[str],
) -> dict[str, Any]:
    issues: list[str] = []
    submission_id = _txt(raw.get("submission_id"))
    requirement_id = _txt(raw.get("requirement_id"))
    action_id = _txt(raw.get("action_id"))
    submitted_at, time_issue = _timestamp(raw.get("submitted_at"))
    for key, value in (
        ("SUBMISSION_ID_REQUIRED", submission_id),
        ("REQUIREMENT_ID_REQUIRED", requirement_id),
        ("ACTION_ID_REQUIRED", action_id),
        ("SUBMITTED_BY_REQUIRED", _txt(raw.get("submitted_by"))),
        ("REMEDIATION_SUMMARY_REQUIRED", _txt(raw.get("remediation_summary"))),
    ):
        if not value:
            issues.append(key)
    if time_issue:
        issues.append(time_issue)
    forbidden = sorted(_FORBIDDEN_CLOSE_FIELDS.intersection(raw))
    if forbidden:
        issues.append("OPERATOR_CLOSE_FIELDS_NOT_ALLOWED:" + ",".join(forbidden))

    matches = requirements.get(requirement_id, [])
    requirement = matches[0] if len(matches) == 1 else {}
    if requirement_id in duplicate_requirements or len(matches) > 1:
        issues.append("B72_REQUIREMENT_ID_AMBIGUOUS")
    elif not requirement:
        issues.append("B72_REQUIREMENT_ID_NOT_FOUND")
    expected_action = _txt(_map(requirement.get("remediation")).get("action_id"))
    if requirement and (not expected_action or action_id != expected_action):
        issues.append("B72_ACTION_ID_MISMATCH")
    if requirement and _map(requirement.get("remediation")).get("status") != "OPEN_REMEDIATION_REQUIRED":
        issues.append("B72_REMEDIATION_STATE_NOT_OPEN")

    scenario = _txt(requirement.get("scenario")).lower()
    product_id = _txt(requirement.get("product_id"))
    requirement_type = _txt(requirement.get("requirement_type")).upper()
    upstream_block = requirement_type in _UPSTREAM_ONLY
    if upstream_block:
        issues.append("UPSTREAM_OPERATING_MODEL_SCOPE_REQUIRED")

    prior_b70 = _ids(raw.get("prior_b70_record_ids"), "PRIOR_B70_RECORD_IDS", issues)
    prior_b71 = _ids(raw.get("prior_b71_review_ids"), "PRIOR_B71_REVIEW_IDS", issues)
    superseded_b70 = _ids(raw.get("superseded_b70_record_ids"), "SUPERSEDED_B70_RECORD_IDS", issues)
    superseded_b71 = _ids(raw.get("superseded_b71_review_ids"), "SUPERSEDED_B71_REVIEW_IDS", issues)
    if not set(superseded_b70).issubset(prior_b70):
        issues.append("SUPERSEDED_B70_IDS_MUST_BE_DECLARED_PRIOR_IDS")
    if not set(superseded_b71).issubset(prior_b71):
        issues.append("SUPERSEDED_B71_IDS_MUST_BE_DECLARED_PRIOR_IDS")

    current_b70 = _ids(requirement.get("b70_record_ids"), "B72_CURRENT_B70_RECORD_IDS", issues)
    current_b71 = _ids(requirement.get("b71_review_ids"), "B72_CURRENT_B71_REVIEW_IDS", issues)
    if not (set(current_b70) - set(prior_b70) or set(current_b71) - set(prior_b71)):
        issues.append("NO_NEW_B70_RECORD_OR_B71_REVIEW_VERSION")
    if not (set(prior_b70) - set(superseded_b70)).issubset(current_b70):
        issues.append("PRIOR_B70_RECORD_NOT_RETAINED_OR_EXPLICITLY_SUPERSEDED")
    if not (set(prior_b71) - set(superseded_b71)).issubset(current_b71):
        issues.append("PRIOR_B71_REVIEW_NOT_RETAINED_OR_EXPLICITLY_SUPERSEDED")
    if set(superseded_b70).intersection(all_record_ids):
        issues.append("SUPERSEDED_B70_RECORD_STILL_ACTIVE")
    if set(superseded_b71).intersection(all_review_ids):
        issues.append("SUPERSEDED_B71_REVIEW_STILL_ACTIVE")
    if set(superseded_b70).intersection(current_b70) or set(superseded_b71).intersection(current_b71):
        issues.append("SUPERSEDED_ID_REUSED_AS_CURRENT_ID")

    allowed_types = _claim_types(requirement_type)
    expected_period = _txt(b69.get("forecast_period"))
    current_records: list[Mapping[str, Any]] = []
    for record_id in current_b70:
        found = records.get(record_id, [])
        if record_id in duplicate_records or len(found) != 1:
            issues.append(f"B70_RECORD_ID_MISSING_OR_AMBIGUOUS:{record_id}")
            continue
        record = found[0]
        current_records.append(record)
        checks = (
            (_txt(record.get("scenario")).lower() == scenario, "SCENARIO"),
            (_txt(record.get("product_id")) == product_id, "PRODUCT"),
            (_txt(record.get("claim_type")).upper() in allowed_types, "CLAIM_TYPE"),
            (not expected_period or _txt(record.get("forecast_period")) == expected_period, "PERIOD"),
        )
        for passed, label in checks:
            if not passed:
                issues.append(f"B70_RECORD_{label}_MISMATCH:{record_id}")
        if not _ids(record.get("evidence_refs"), f"RECORD_{record_id}_EVIDENCE_REFS", issues):
            issues.append(f"B70_RECORD_HAS_NO_EVIDENCE_REFS:{record_id}")
    if not current_b70:
        issues.append("CURRENT_B70_RECORDS_REQUIRED_FOR_REASSESSMENT")
    if not current_b71:
        issues.append("CURRENT_B71_REVIEWS_REQUIRED_FOR_REASSESSMENT")

    current_review_rows: list[Mapping[str, Any]] = []
    for review_id in current_b71:
        found = reviews.get(review_id, [])
        if review_id in duplicate_reviews or len(found) != 1:
            issues.append(f"B71_REVIEW_ID_MISSING_OR_AMBIGUOUS:{review_id}")
        else:
            current_review_rows.append(found[0])

    by_record: dict[str, list[Mapping[str, Any]]] = {}
    for review in _rows(b71.get("reviews")):
        record_id = _txt(review.get("record_id"))
        if record_id in current_b70:
            by_record.setdefault(record_id, []).append(review)
    linked_review_ids: set[str] = set()
    for record_id in current_b70:
        linked = by_record.get(record_id, [])
        if len(linked) != 1:
            issues.append(f"B71_REVIEW_COVERAGE_NOT_UNIQUE_FOR_RECORD:{record_id}")
            continue
        review = linked[0]
        review_id = _txt(review.get("review_id"))
        if review_id:
            linked_review_ids.add(review_id)
        if _txt(review.get("status")).upper() != "HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY":
            issues.append(f"B71_REVIEW_NOT_CONDITIONALLY_SUPPORTED:{record_id}")
        if review.get("review_independence_conditionally_declared") is not True:
            issues.append(f"B71_REVIEW_INDEPENDENCE_NOT_DECLARED:{record_id}")
    if linked_review_ids != set(current_b71):
        issues.append("B71_REVIEW_IDS_DO_NOT_EXACTLY_COVER_CURRENT_RECORDS")
    if len(current_review_rows) != len(current_b71):
        issues.append("B71_REVIEW_ROWS_INCOMPLETE")

    current_refs = sorted({
        ref for record in current_records
        for ref in _ids(record.get("evidence_refs"), "B70_EVIDENCE_REFS", issues)
    })
    b72_refs = sorted(_ids(requirement.get("evidence_refs"), "B72_EVIDENCE_REFS", issues))
    if current_refs != b72_refs:
        issues.append("B72_EVIDENCE_REFS_DO_NOT_MATCH_CURRENT_B70_RECORDS")

    exception_status = _txt(requirement.get("exception_status")).upper()
    if upstream_block:
        status = "REASSESSMENT_BLOCKED_UPSTREAM_SCOPE_REQUIRED"
    elif issues:
        status = "REASSESSMENT_BLOCKED"
    elif exception_status == _PASS:
        status = "REASSESSMENT_PASSED_PENDING_FORMAL_ADMISSION"
    else:
        status = "REASSESSMENT_FAILED"

    return {
        "submission_id": submission_id or None,
        "requirement_id": requirement_id or None,
        "action_id": action_id or None,
        "scenario": scenario or None,
        "lens": _txt(requirement.get("lens")) or None,
        "segment_id": _txt(requirement.get("segment_id")) or None,
        "product_id": product_id or None,
        "requirement_type": requirement_type or None,
        "submitted_by": _txt(raw.get("submitted_by")) or None,
        "submitted_at": submitted_at,
        "remediation_summary": _txt(raw.get("remediation_summary")) or None,
        "prior_exception_status_operator_declared": _txt(raw.get("prior_exception_status")) or None,
        "prior_b70_record_ids_operator_declared": prior_b70,
        "prior_b71_review_ids_operator_declared": prior_b71,
        "superseded_b70_record_ids": superseded_b70,
        "superseded_b71_review_ids": superseded_b71,
        "current_b70_record_ids": current_b70,
        "current_b71_review_ids": current_b71,
        "current_evidence_refs": current_refs,
        "current_b72_exception_status": exception_status or "UNKNOWN",
        "current_b70_record_count": len(current_records),
        "current_b71_review_count": len(current_review_rows),
        "status": status,
        "issues": list(dict.fromkeys(issues)),
        "prior_lineage_is_operator_declared_not_independently_authenticated": True,
        "formal_evidence_pit_admission": False,
        "automatically_closed": False,
        "decision_authority": False,
    }


def build_operating_feasibility_remediation_assessment(
    *,
    raw_submissions: Any,
    b69_audit: Mapping[str, Any],
    b70_assessment: Mapping[str, Any],
    b71_review: Mapping[str, Any],
    b72_register: Mapping[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": B73_SCHEMA,
        "status": "REMEDIATION_SUBMISSIONS_NOT_PROVIDED",
        "submissions": [],
        "summary": {
            "submission_count": 0,
            "reassessment_passed_pending_formal_admission_count": 0,
            "reassessment_failed_count": 0,
            "reassessment_blocked_count": 0,
            "closed_verified_count": 0,
            "manual_close_authority": False,
            "formal_evidence_pit_admission_created": False,
        },
        "formal_evidence_pit_admission_created": False,
        "forecast_or_valuation_admission_created": False,
        "decision_authority": False,
        "execution_authority": False,
        "automatically_closed": False,
        "manual_close_allowed": False,
        "closed_verified_status_is_emitted": False,
        "reassessment_uses_current_b69_b70_b71_b72_outputs": True,
        "limitations": [
            "B73 只核验本次 pilot 已重新计算的 B69/B70/B71/B72 输出；不会异步抓取资料或调度后台任务。",
            "此前记录 ID 与此前例外状态由操作者声明；系统只检查被声明替换的 ID 不再出现于本轮结果，不能认证历史真实性。",
            "B71 审核人身份、组织关系、实际独立性及来源内容不由自动程序认证。",
            "B72 条件性支持仍不是正式 Evidence/PIT 准入；本模块无权创建正式准入或关闭该要求。",
            "需求弹性、价格竞争反应、成本曲线/节约执行等未覆盖维度必须回到上游经营模型整改。",
        ],
    }
    if raw_submissions is None:
        return result
    if not isinstance(raw_submissions, Mapping):
        result["status"] = "REMEDIATION_INPUT_BLOCKED"
        result["issues"] = ["REMEDIATION_SUBMISSIONS_MUST_BE_OBJECT"]
        return result
    if _txt(raw_submissions.get("schema_version")) != INPUT_SCHEMA:
        result["status"] = "REMEDIATION_INPUT_BLOCKED"
        result["issues"] = ["REMEDIATION_SUBMISSIONS_SCHEMA_MISMATCH"]
        return result
    rows = raw_submissions.get("submissions")
    if not isinstance(rows, list):
        result["status"] = "REMEDIATION_INPUT_BLOCKED"
        result["issues"] = ["REMEDIATION_SUBMISSIONS_MUST_BE_LIST"]
        return result

    upstream = {"b69": b69_audit, "b70": b70_assessment, "b71": b71_review, "b72": b72_register}
    for name, schema in _SCHEMAS.items():
        if _txt(_map(upstream[name]).get("schema_version")) != schema:
            result["status"] = "REMEDIATION_REASSESSMENT_BLOCKED"
            result["issues"] = [f"{name.upper()}_SCHEMA_MISSING_OR_MISMATCH"]
            return result

    requirements, dup_req = _index(_rows(b72_register.get("requirement_rows")), "requirement_id")
    records, dup_records = _index(_rows(b70_assessment.get("records")), "record_id")
    reviews, dup_reviews = _index(_rows(b71_review.get("reviews")), "review_id")
    all_record_ids, all_review_ids = set(records), set(reviews)
    submission_counts: dict[str, int] = {}
    for raw in rows:
        if isinstance(raw, Mapping):
            sid = _txt(raw.get("submission_id"))
            if sid:
                submission_counts[sid] = submission_counts.get(sid, 0) + 1

    assessed: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            assessed.append({
                "submission_id": None, "status": "REASSESSMENT_BLOCKED",
                "issues": ["SUBMISSION_ROW_MUST_BE_OBJECT"], "automatically_closed": False,
            })
            continue
        item = _assess_one(
            raw, b69=b69_audit, b71=b71_review,
            requirements=requirements, duplicate_requirements=dup_req,
            records=records, duplicate_records=dup_records,
            reviews=reviews, duplicate_reviews=dup_reviews,
            all_record_ids=all_record_ids, all_review_ids=all_review_ids,
        )
        sid = item.get("submission_id")
        if sid and submission_counts.get(sid, 0) > 1:
            item["status"] = "REASSESSMENT_BLOCKED"
            item["issues"] = list(dict.fromkeys([*item.get("issues", []), "DUPLICATE_SUBMISSION_ID"]))
        assessed.append(item)

    counts: dict[str, int] = {}
    for item in assessed:
        state = _txt(item.get("status")) or "UNKNOWN"
        counts[state] = counts.get(state, 0) + 1
    result["submissions"] = assessed
    result["status"] = "REMEDIATION_REASSESSMENT_RECORDED"
    result["summary"] = {
        "submission_count": len(assessed),
        "reassessment_passed_pending_formal_admission_count": counts.get("REASSESSMENT_PASSED_PENDING_FORMAL_ADMISSION", 0),
        "reassessment_failed_count": counts.get("REASSESSMENT_FAILED", 0),
        "reassessment_blocked_count": counts.get("REASSESSMENT_BLOCKED", 0) + counts.get("REASSESSMENT_BLOCKED_UPSTREAM_SCOPE_REQUIRED", 0),
        "closed_verified_count": 0,
        "status_counts": counts,
        "manual_close_authority": False,
        "formal_evidence_pit_admission_created": False,
        "all_submissions_require_fresh_b69_b70_b71_b72_reassessment": True,
    }
    return result
