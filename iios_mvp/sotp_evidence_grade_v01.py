from __future__ import annotations

"""B64 evidence grading for SOTP segment earnings and terminal multiples.

This is a read-only, structural evidence-linkage diagnostic. It does not verify
source-document contents, admit PIT evidence, validate a forecast, or select a
fair multiple.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

B64_SCHEMA = "IIOS-B64-SOTP-EVIDENCE-GRADE-0.1"
_ALLOWED_B63_SCENARIO_STATUSES = {
    "CONDITIONAL_ATTRIBUTION_CALCULATED",
    "PARTIAL",
}
_PLACEHOLDERS = {
    "", "UNKNOWN", "N/A", "NA", "NONE", "NULL", "TBD",
    "NOT_IDENTIFIABLE", "UNSPECIFIED", "NOT_PROVIDED",
    "未提供", "未知", "不详", "待补充", "待确认",
}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _identifiable(value: Any) -> bool:
    candidate = _text(value)
    return bool(candidate) and candidate.upper() not in _PLACEHOLDERS


def _string_list(value: Any) -> tuple[list[str], bool]:
    if value is None:
        return [], True
    if not isinstance(value, list):
        return [], False
    rows = list(dict.fromkeys(_text(item) for item in value if _text(item)))
    return rows, True


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _date_is_valid(value: Any) -> bool:
    raw = _text(value)
    try:
        return len(raw) == 10 and date.fromisoformat(raw).isoformat() == raw
    except ValueError:
        return False


def _measure_refs(measure: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    refs, valid_shape = _string_list(measure.get("evidence_refs"))
    issues = [] if valid_shape else ["MEASURE_EVIDENCE_REFS_MUST_BE_LIST"]
    return refs, issues


def _audit_refs(
    refs: list[str],
    *,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    allowed_refs: set[str] | None = None,
) -> dict[str, Any]:
    audited: list[dict[str, Any]] = []
    issues: list[str] = []
    for ref in refs:
        if allowed_refs is not None and ref not in allowed_refs:
            issues.append(f"SUPPORT_REFERENCE_NOT_ATTACHED_TO_MEASURE:{ref}")
            continue
        source = evidence_by_id.get(ref)
        if source is None:
            issues.append(f"EVIDENCE_REFERENCE_UNRESOLVED:{ref}")
            continue
        time_status = str(source.get("time_status") or "UNKNOWN").upper()
        if time_status != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED":
            issues.append(f"EVIDENCE_REFERENCE_NOT_CUTOFF_COMPATIBLE:{ref}:{time_status}")
            continue
        audited.append({
            "source_id": ref,
            "title": source.get("title") or "UNKNOWN",
            "source_class": str(source.get("source_class") or "UNKNOWN").upper(),
            "source_domain_class_status": source.get("source_domain_class_status") or "UNKNOWN",
            "time_status": time_status,
            "known_at": source.get("known_at") or "UNKNOWN",
            "summary": source.get("summary") or "UNKNOWN",
        })
    return {
        "status": "RESOLVED_TIME_COMPATIBLE_ONLY_NOT_ADMITTED" if not issues and refs else (
            "NO_REFERENCES" if not refs else "UNRESOLVED_OR_NOT_CUTOFF_COMPATIBLE"
        ),
        "sources": audited,
        "issues": sorted(set(issues)),
    }


def _is_primary_disclosure_source(source: Mapping[str, Any]) -> bool:
    source_class = str(source.get("source_class") or "").strip().upper()
    domain_status = str(source.get("source_domain_class_status") or "").strip().upper()
    if source_class == "EXCHANGE_PRIMARY":
        return domain_status == "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    if source_class == "REGULATOR_PRIMARY":
        return domain_status == "OFFICIAL_REGULATOR_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    if source_class == "ISSUER_PRIMARY":
        # The pilot does not independently verify issuer domains; accept only
        # the declared class with no exchange/regulator class conflict and
        # disclose that domain limitation in the returned source audit.
        return domain_status == "ISSUER_DOMAIN_NOT_INDEPENDENTLY_VERIFIED"
    return False


def _grade_profit_measure(
    measure: Any,
    *,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    segment_id: str,
    scenario_name: str,
) -> dict[str, Any]:
    if not isinstance(measure, Mapping) or _decimal(measure) is None:
        return {
            "grade": "G5_UNKNOWN",
            "grade_label": "UNKNOWN / 未能识别",
            "status": "NOT_IDENTIFIABLE",
            "issues": ["NORMALIZED_SEGMENT_PROFIT_MEASURE_MISSING_OR_NONNUMERIC"],
            "data_class": "UNKNOWN",
            "basis": "UNKNOWN",
            "measure_evidence_refs": [],
            "support_type": "UNKNOWN",
            "support_summary": "UNKNOWN",
            "support_evidence_audit": {"status": "NO_REFERENCES", "sources": [], "issues": []},
            "counter_evidence_audit": {"status": "NO_REFERENCES", "sources": [], "issues": []},
            "mechanism_chain": [],
            "key_operating_indicators": [],
            "derivation_steps": [],
            "reversal_signals": [],
            "limitations": ["没有可识别的分部归母正常化利润数值；不推定为零。"],
        }

    data_class = str(measure.get("data_class") or "UNKNOWN").strip().upper()
    basis = _text(measure.get("basis")) or "UNKNOWN"
    measure_refs, ref_issues = _measure_refs(measure)
    support = measure.get("support_assessment") if isinstance(measure.get("support_assessment"), Mapping) else {}
    support_type = str(support.get("support_type") or "UNKNOWN").strip().upper()
    support_summary = _text(support.get("support_summary")) or "UNKNOWN"
    support_refs, support_refs_shape_ok = _string_list(support.get("support_evidence_refs"))
    counter_refs, counter_refs_shape_ok = _string_list(support.get("counter_evidence_refs"))
    mechanism_chain, mechanism_shape_ok = _string_list(support.get("mechanism_chain"))
    indicators, indicators_shape_ok = _string_list(support.get("key_operating_indicators"))
    derivation_steps, derivation_shape_ok = _string_list(support.get("derivation_steps"))
    reversal_signals, reversal_shape_ok = _string_list(support.get("reversal_signals"))

    support_audit = _audit_refs(
        support_refs,
        evidence_by_id=evidence_by_id,
        allowed_refs=set(measure_refs),
    )
    counter_audit = _audit_refs(counter_refs, evidence_by_id=evidence_by_id)
    issues = list(ref_issues)
    for ok, code in (
        (support_refs_shape_ok, "SUPPORT_EVIDENCE_REFS_MUST_BE_LIST"),
        (counter_refs_shape_ok, "COUNTER_EVIDENCE_REFS_MUST_BE_LIST"),
        (mechanism_shape_ok, "MECHANISM_CHAIN_MUST_BE_LIST"),
        (indicators_shape_ok, "KEY_OPERATING_INDICATORS_MUST_BE_LIST"),
        (derivation_shape_ok, "DERIVATION_STEPS_MUST_BE_LIST"),
        (reversal_shape_ok, "REVERSAL_SIGNALS_MUST_BE_LIST"),
    ):
        if not ok:
            issues.append(code)
    issues.extend(support_audit["issues"])
    issues.extend(counter_audit["issues"])

    grade = "G5_UNKNOWN"
    grade_label = "UNKNOWN / 未能识别"
    grade_reason = "PROFIT_SUPPORT_LINKAGE_NOT_IDENTIFIABLE"
    assessment_status = "PARTIAL"
    valid_support_refs = bool(support_refs) and not support_audit["issues"]
    has_primary_disclosure_source = any(
        _is_primary_disclosure_source(source)
        for source in support_audit["sources"]
    )

    if support_type in {"DISCLOSED_FACTS", "ISSUER_GUIDANCE"}:
        guidance_class_ok = support_type != "ISSUER_GUIDANCE" or data_class == "ISSUER_FORECAST"
        if (
            _identifiable(support_summary)
            and valid_support_refs
            and has_primary_disclosure_source
            and guidance_class_ok
        ):
            grade = "G1_DISCLOSURE_LINKED_TO_PROFIT"
            grade_label = "一级：披露事实/指引与利润输入建立引用关联"
            grade_reason = "PRIMARY_DISCLOSURE_REFERENCE_AND_EXPLICIT_SUPPORT_CLAIM_PRESENT"
            assessment_status = "STRUCTURAL_LINKAGE_PRESENT_NOT_SEMANTICALLY_VERIFIED"
        else:
            issues.append("DISCLOSURE_SUPPORT_CLAIM_LACKS_VALID_PRIMARY_REFERENCE_OR_SUMMARY")
    elif support_type == "BUSINESS_MECHANISM":
        if (
            _identifiable(support_summary)
            and valid_support_refs
            and len(mechanism_chain) >= 2
            and len(indicators) >= 1
            and len(reversal_signals) >= 1
        ):
            grade = "G2_BUSINESS_MECHANISM_AND_EVIDENCE_LINKED"
            grade_label = "二级：业务机制、经营指标与证据链可追踪"
            grade_reason = "MECHANISM_CHAIN_INDICATORS_AND_REVERSAL_SIGNALS_PRESENT"
            assessment_status = "STRUCTURAL_LINKAGE_PRESENT_NOT_SEMANTICALLY_VERIFIED"
        else:
            issues.append("BUSINESS_MECHANISM_SUPPORT_INCOMPLETE")
    elif data_class == "ANALYST_ASSUMPTION":
        grade = "G3_ANALYST_ASSUMPTION_ONLY"
        grade_label = "三级：分析师假设 / 需要独立推演"
        grade_reason = (
            "EXPLICIT_ANALYST_DERIVATION_PRESENT"
            if support_type == "ANALYST_DERIVATION" and derivation_steps
            else "ANALYST_ASSUMPTION_WITHOUT_VERIFIABLE_SUPPORT_CHAIN"
        )
        assessment_status = (
            "ANALYST_DERIVATION_RECORDED_NOT_VERIFIED"
            if support_type == "ANALYST_DERIVATION" and derivation_steps
            else "ANALYST_ASSUMPTION_ONLY"
        )
    elif data_class == "ISSUER_FORECAST":
        grade_reason = "ISSUER_FORECAST_WITHOUT_A_VALIDATED_SUPPORT_LINKAGE"
        issues.append("ISSUER_FORECAST_SUPPORT_LINKAGE_NOT_ESTABLISHED")
    else:
        grade_reason = "PROFIT_DATA_CLASS_UNKNOWN_OR_UNSUPPORTED"
        issues.append(f"PROFIT_DATA_CLASS_NOT_IDENTIFIABLE:{data_class}")

    if grade == "G5_UNKNOWN" and data_class == "ANALYST_ASSUMPTION":
        # The profit's analyst-assumption class is still identifiable even when
        # a stronger claimed support path is incomplete or cannot be resolved.
        grade = "G3_ANALYST_ASSUMPTION_ONLY"
        grade_label = "三级：分析师假设 / 需要独立推演"
        grade_reason = "ANALYST_ASSUMPTION_WITH_UNRESOLVED_OR_INCOMPLETE_SUPPORT_CLAIM"
        assessment_status = "ANALYST_ASSUMPTION_ONLY_SUPPORT_CLAIM_NOT_VALIDATED"

    limitations = [
        "等级只检查结构化声明、引用 ID、来源类别标签和截止时点状态；不会读取原始文件内容，也不证明来源中的事实确实支持本分部利润数值。",
        "ISSUER_FORECAST 代表发行人预测/指引，不是已实现利润；历史披露事实与前瞻预测之间仍需要经营机制连接。",
        "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED 只表示时间兼容检查通过，不代表正式证据准入、来源真实性或原始字节完整性通过。",
    ]
    return {
        "grade": grade,
        "grade_label": grade_label,
        "status": assessment_status,
        "grade_reason": grade_reason,
        "data_class": data_class,
        "basis": basis,
        "measure_evidence_refs": measure_refs,
        "support_type": support_type,
        "support_summary": support_summary,
        "support_evidence_refs": support_refs,
        "support_evidence_audit": support_audit,
        "counter_evidence_refs": counter_refs,
        "counter_evidence_audit": counter_audit,
        "mechanism_chain": mechanism_chain,
        "key_operating_indicators": indicators,
        "derivation_steps": derivation_steps,
        "reversal_signals": reversal_signals,
        "issues": sorted(set(issues)),
        "limitations": limitations,
    }


def _grade_multiple_measure(
    measure: Any,
    *,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(measure, Mapping) or _decimal(measure) is None or _decimal(measure) <= 0:
        return {
            "grade": "G5_UNKNOWN",
            "grade_label": "UNKNOWN / P/E 假设不可识别",
            "status": "NOT_IDENTIFIABLE",
            "data_class": "UNKNOWN",
            "basis": "UNKNOWN",
            "measure_evidence_refs": [],
            "comparable_set_status": "NOT_PROVIDED",
            "comparable_observations": [],
            "issues": ["SEGMENT_PE_MEASURE_MISSING_OR_NONPOSITIVE"],
            "limitations": ["P/E 缺失或非正数；不推定合理倍数。"],
        }

    data_class = str(measure.get("data_class") or "UNKNOWN").strip().upper()
    basis = _text(measure.get("basis")) or "UNKNOWN"
    measure_refs, ref_issues = _measure_refs(measure)
    support = measure.get("support_assessment") if isinstance(measure.get("support_assessment"), Mapping) else {}
    comparable_rows = support.get("comparable_observations")
    issues = list(ref_issues)
    validated_comparables: list[dict[str, Any]] = []
    comparable_status = "NOT_PROVIDED"

    if comparable_rows is not None:
        if not isinstance(comparable_rows, list):
            issues.append("COMPARABLE_OBSERVATIONS_MUST_BE_LIST")
            comparable_status = "INVALID_OR_INCOMPLETE"
        else:
            seen_entities: set[str] = set()
            for index, row in enumerate(comparable_rows, start=1):
                if not isinstance(row, Mapping):
                    issues.append(f"COMPARABLE_ROW_NOT_OBJECT:{index}")
                    continue
                entity = _text(row.get("entity"))
                as_of = _text(row.get("as_of_date"))
                multiple = _decimal(row.get("observed_pe_x"))
                evidence_ref = _text(row.get("evidence_ref"))
                adjustment = _text(row.get("comparability_adjustment"))
                if (
                    not _identifiable(entity)
                    or entity in seen_entities
                    or not _date_is_valid(as_of)
                    or multiple is None
                    or multiple <= 0
                    or not evidence_ref
                    or evidence_ref not in set(measure_refs)
                    or not _identifiable(adjustment)
                ):
                    issues.append(f"COMPARABLE_ROW_INCOMPLETE_OR_NOT_LINKED:{index}")
                    continue
                audit = _audit_refs([evidence_ref], evidence_by_id=evidence_by_id, allowed_refs=set(measure_refs))
                if audit["issues"]:
                    issues.extend(audit["issues"])
                    issues.append(f"COMPARABLE_REFERENCE_NOT_CUTOFF_COMPATIBLE:{index}")
                    continue
                seen_entities.add(entity)
                peer_profile = row.get("peer_comparability_profile")
                dimensions = row.get("dimension_assessments")
                validated_comparables.append({
                    "entity": entity,
                    "as_of_date": as_of,
                    "observed_pe_x": format(multiple, "f"),
                    "evidence_ref": evidence_ref,
                    "comparability_adjustment": adjustment,
                    "date_alignment_rationale": _text(row.get("date_alignment_rationale")) or None,
                    "peer_comparability_profile": dict(peer_profile) if isinstance(peer_profile, Mapping) else None,
                    "dimension_assessments": dict(dimensions) if isinstance(dimensions, Mapping) else None,
                })
            if len(validated_comparables) >= 2 and len(seen_entities) >= 2:
                comparable_status = "COMPARABLE_SET_CAPTURED_NOT_INDEPENDENTLY_VERIFIED"
            else:
                comparable_status = "INVALID_OR_INCOMPLETE"

    # A selected terminal P/E remains an analyst valuation assumption even when
    # peer observations are recorded; comparisons do not mechanically prove
    # the selected multiple or establish fair value.
    if data_class == "ANALYST_ASSUMPTION":
        grade = "G4_MULTIPLE_ASSUMPTION_ONLY"
        grade_label = "四级：终值倍数假设（可有可比样本，但非公允价值证明）"
        status = "MULTIPLE_ASSUMPTION"
    else:
        grade = "G5_UNKNOWN"
        grade_label = "UNKNOWN / P/E 数据分类不适配"
        status = "NOT_IDENTIFIABLE"
        issues.append(f"PE_DATA_CLASS_NOT_ANALYST_ASSUMPTION:{data_class}")

    support_refs, support_shape_ok = _string_list(support.get("support_evidence_refs"))
    if not support_shape_ok:
        issues.append("PE_SUPPORT_EVIDENCE_REFS_MUST_BE_LIST")
    support_audit = _audit_refs(
        support_refs,
        evidence_by_id=evidence_by_id,
        allowed_refs=set(measure_refs),
    )
    issues.extend(support_audit["issues"])
    limitations = [
        "选择的终值 P/E 本质上仍是分析师估值假设；即使记录可比公司，也不能自动证明所选倍数公允。",
        "可比样本必须由人工核查业务结构、增长/周期阶段、利润质量、资本回报、杠杆、会计口径和估值日期；本模块不自动做可比公司调整。",
        "倍数输入的 evidence_refs 可能只是来源引用；只有逐项列出的可比观察值才会被记录为候选可比样本，仍未完成独立核验。",
    ]
    return {
        "grade": grade,
        "grade_label": grade_label,
        "status": status,
        "data_class": data_class,
        "basis": basis,
        "measure_evidence_refs": measure_refs,
        "support_type": str(support.get("support_type") or "UNKNOWN").strip().upper(),
        "support_summary": _text(support.get("support_summary")) or "UNKNOWN",
        "support_evidence_refs": support_refs,
        "support_evidence_audit": support_audit,
        "target_comparability_profile": (
            dict(support.get("target_comparability_profile"))
            if isinstance(support.get("target_comparability_profile"), Mapping) else None
        ),
        "comparable_set_status": comparable_status,
        "comparable_observations": validated_comparables,
        "issues": sorted(set(issues)),
        "limitations": limitations,
    }


def build_sotp_evidence_grade_assessment(
    *,
    sotp_valuation: Mapping[str, Any],
    evidence_register: list[dict[str, Any]],
    valuation_gap_attribution: Mapping[str, Any],
) -> dict[str, Any]:
    """Grade SOTP profit-support claims and P/E assumptions without changing values."""
    result: dict[str, Any] = {
        "schema_version": B64_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "qualification": "STRUCTURAL_EVIDENCE_LINKAGE_DIAGNOSTIC_ONLY",
        "grade_definitions": {
            "G1_DISCLOSURE_LINKED_TO_PROFIT": "披露事实/发行人指引与具体分部利润输入建立结构化引用关联；来源内容与数值的语义关系仍需人工核验。",
            "G2_BUSINESS_MECHANISM_AND_EVIDENCE_LINKED": "已声明经营因果链、关键可观测指标、证据引用和反转信号；机制真实性与量化弹性仍需人工核验。",
            "G3_ANALYST_ASSUMPTION_ONLY": "利润明确属于分析师假设；即使有背景来源引用，也未达到披露事实或机制证据链标准。",
            "G4_MULTIPLE_ASSUMPTION_ONLY": "终值 P/E 是独立估值假设；可比样本只能提供参照，不自动证明倍数公允。",
            "G5_UNKNOWN": "缺少必要输入、证据引用无法解析、来源时间不兼容或支持关系无法识别。",
        },
        "forecast_period": sotp_valuation.get("forecast_period") or "UNKNOWN",
        "scenarios": {},
        "limitations": [
            "B64 是结构化自述和来源登记的审计辅助，不是文档内容理解、事实核实、因果识别或正式 Evidence/PIT Admission。",
            "引用 ID 存在、来源类别被标记为 primary、时间状态兼容，均不等同于来源内容确实支撑相应利润或估值倍数。",
            "G1/G2 不是系统自动证明；它们表示必要的结构化关联字段和基础校验已具备，仍需人工查看原始来源、口径和反证。",
            "G3/G4 不是自动否决；它们要求投资者知道价值中有多少来自分析判断或终值倍数假设。",
            "等级不参与估值加权、不调整 B4/B61/B62/B63、不改变 SOTP、MIE、expectation_gap、15% 年化回报门槛、目标价、组合约束、Decision 或执行权限。",
        ],
        "sotp_input_modified": False,
        "valuation_values_modified": False,
        "external_mie_modified": False,
        "decision_authority": False,
    }

    if (
        str(sotp_valuation.get("status") or "").upper() != "CALCULATED"
        or sotp_valuation.get("selected_for_primary_model") is not True
    ):
        result["status"] = "NOT_APPLICABLE_OR_SOTP_NOT_CALCULATED"
        return result

    b63_status = str(valuation_gap_attribution.get("status") or "UNKNOWN").upper()
    if b63_status not in {"CONDITIONAL_ATTRIBUTION_CALCULATED", "PARTIAL"}:
        result["status"] = "BLOCKED_BY_B63"
        result["b63_status"] = b63_status
        return result

    evidence_by_id = {
        str(row.get("source_id")): row
        for row in evidence_register
        if isinstance(row, Mapping) and row.get("source_id")
    }
    sotp_scenarios = sotp_valuation.get("scenarios") if isinstance(sotp_valuation.get("scenarios"), Mapping) else {}
    b63_scenarios = valuation_gap_attribution.get("scenarios") if isinstance(valuation_gap_attribution.get("scenarios"), Mapping) else {}
    scenario_statuses: list[str] = []

    for scenario_name in ("bear", "base", "bull"):
        sotp_row = sotp_scenarios.get(scenario_name) if isinstance(sotp_scenarios.get(scenario_name), Mapping) else {}
        b63_row = b63_scenarios.get(scenario_name) if isinstance(b63_scenarios.get(scenario_name), Mapping) else {}
        row: dict[str, Any] = {
            "scenario": scenario_name,
            "status": "NOT_IDENTIFIABLE",
            "segments": [],
            "issues": [],
            "profit_grade_distribution": {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0},
            "multiple_grade_distribution": {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0},
        }
        b63_row_status = str(b63_row.get("status") or "UNKNOWN").upper()
        if b63_row_status not in _ALLOWED_B63_SCENARIO_STATUSES:
            row["status"] = "BLOCKED_BY_B63_SCENARIO"
            row["issues"] = [f"B63_SCENARIO_NOT_RECONCILED:{b63_row_status}"]
            result["scenarios"][scenario_name] = row
            scenario_statuses.append(row["status"])
            continue
        sotp_segments = sotp_row.get("segments") if isinstance(sotp_row.get("segments"), list) else []
        b63_segments = b63_row.get("earnings_effect_by_segment") if isinstance(b63_row.get("earnings_effect_by_segment"), list) else []
        sotp_ids = {
            str(segment.get("segment_id") or "").strip()
            for segment in sotp_segments if isinstance(segment, Mapping)
        }
        b63_ids = {
            str(segment.get("segment_id") or "").strip()
            for segment in b63_segments if isinstance(segment, Mapping)
        }
        if not sotp_ids or sotp_ids != b63_ids:
            row["status"] = "SEGMENT_UNIVERSE_NOT_RECONCILED"
            row["issues"] = ["B63_VS_SOTP_SEGMENT_UNIVERSE_MISMATCH"]
            result["scenarios"][scenario_name] = row
            scenario_statuses.append(row["status"])
            continue

        for segment in sotp_segments:
            if not isinstance(segment, Mapping):
                continue
            segment_id = str(segment.get("segment_id") or "").strip()
            profit_assessment = _grade_profit_measure(
                segment.get("attributable_net_profit_cny"),
                evidence_by_id=evidence_by_id,
                segment_id=segment_id,
                scenario_name=scenario_name,
            )
            multiple_assessment = _grade_multiple_measure(
                segment.get("pe_multiple_x"),
                evidence_by_id=evidence_by_id,
            )
            row["profit_grade_distribution"][profit_assessment["grade"][:2]] += 1
            row["multiple_grade_distribution"][multiple_assessment["grade"][:2]] += 1
            row["segments"].append({
                "segment_id": segment_id,
                "segment_name": segment.get("segment_name") or "UNKNOWN",
                "earnings_basis": segment.get("earnings_basis") or "UNKNOWN",
                "sotp_selected_attributable_profit_cny": (
                    (segment.get("attributable_net_profit_cny") or {}).get("value")
                    if isinstance(segment.get("attributable_net_profit_cny"), Mapping) else None
                ),
                "profit_evidence_assessment": profit_assessment,
                "selected_terminal_pe_x": (
                    (segment.get("pe_multiple_x") or {}).get("value")
                    if isinstance(segment.get("pe_multiple_x"), Mapping) else None
                ),
                "multiple_evidence_assessment": multiple_assessment,
            })

        grade5_measure_count = sum(
            1 for segment in row["segments"]
            if (
                segment["profit_evidence_assessment"]["grade"] == "G5_UNKNOWN"
                or segment["multiple_evidence_assessment"]["grade"] == "G5_UNKNOWN"
            )
        )
        row["status"] = "PARTIAL" if grade5_measure_count or not row["segments"] else "ASSESSED_DIAGNOSTIC_ONLY"
        row["summary"] = (
            "分部盈利输入与终值倍数分别评级；G3 表示分析师盈利假设，G4 表示终值倍数假设。"
            "不得将两者合并成一个看似精确的总分。"
        )
        if grade5_measure_count:
            row["issues"].append(f"SOTP_MEASURE_EVIDENCE_GRADE_UNKNOWN_COUNT:{grade5_measure_count}")
        result["scenarios"][scenario_name] = row
        scenario_statuses.append(row["status"])

    if scenario_statuses and all(status == "ASSESSED_DIAGNOSTIC_ONLY" for status in scenario_statuses):
        result["status"] = "ASSESSED_DIAGNOSTIC_ONLY"
    elif any(status in {"BLOCKED_BY_B63_SCENARIO", "SEGMENT_UNIVERSE_NOT_RECONCILED"} for status in scenario_statuses):
        result["status"] = "PARTIAL"
    elif any(status in {"ASSESSED_DIAGNOSTIC_ONLY", "PARTIAL"} for status in scenario_statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "NOT_IDENTIFIABLE"

    result["summary"] = (
        "B64 将分部归母盈利输入的披露事实关联、业务机制关联、分析师假设和 UNKNOWN，"
        "与终值 P/E 假设单独分级；只展示证据链成熟度，不替代原始文件审阅和投资判断。"
    )
    return result
