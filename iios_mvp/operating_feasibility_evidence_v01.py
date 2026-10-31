from __future__ import annotations

"""B70: typed, cutoff-aware evidence linkage for operating feasibility claims.

Evidence records are matched to B69 product/scenario/period requirements.
They are never treated as formal evidence admission or source-content verification.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping

B70_SCHEMA = "IIOS-OPERATING-FEASIBILITY-EVIDENCE-ASSESSMENT-0.1"
INPUT_SCHEMA = "IIOS-OPERATING-FEASIBILITY-EVIDENCE-0.1"
_SCENARIOS = ("bear", "base", "bull")
_PRIMARY_SOURCE_CLASSES = {"ISSUER_PRIMARY", "EXCHANGE_PRIMARY", "REGULATOR_PRIMARY"}
_VALID_DATA_CLASSES = {"OBSERVED_ACTUAL", "ISSUER_FORECAST", "ANALYST_ASSUMPTION"}
_CLAIMS = {
    "SUPPORTED_SALES_VOLUME": "tonnes",
    "SUPPORTED_NET_ASP": "CNY/tonne",
    "SUPPORTED_UNIT_VARIABLE_COST": "CNY/tonne",
    "EFFECTIVE_CAPACITY_AVAILABLE": "tonnes/year",
    "CAPACITY_AVAILABLE_DATE": "date",
    "INCREMENTAL_CAPEX_REQUIRED": "CNY",
    "INCREMENTAL_CAPEX_FUNDED": "CNY",
    "INCREMENTAL_WORKING_CAPITAL_REQUIRED": "CNY",
    "INCREMENTAL_WORKING_CAPITAL_FUNDED": "CNY",
}
_COMPARISON_BASIS_REQUIRED = {
    "INCREMENTAL_CAPEX_REQUIRED": "INCREMENTAL_TO_B4_FORWARD_PLAN",
    "INCREMENTAL_CAPEX_FUNDED": "INCREMENTAL_TO_B4_FORWARD_PLAN",
    "INCREMENTAL_WORKING_CAPITAL_REQUIRED": "INCREMENTAL_TO_B4_FORWARD_PLAN",
    "INCREMENTAL_WORKING_CAPITAL_FUNDED": "INCREMENTAL_TO_B4_FORWARD_PLAN",
}
_TOL = Decimal("0.01")


def _txt(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _num(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed.is_finite() else None


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _full_year_end(period: Any) -> str | None:
    label = "".join(str(period or "").upper().split())
    match = re.fullmatch(r"(?:FY(\d{4})|(\d{4})FY|(\d{4})年度|(\d{4})全年)", label)
    if not match:
        return None
    year = next(group for group in match.groups() if group)
    return f"{year}-12-31"


def _index_sources(rows: Any) -> tuple[dict[str, Mapping[str, Any]], set[str]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    duplicates: set[str] = set()
    if not isinstance(rows, list):
        return indexed, duplicates
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        source_id = _txt(row.get("source_id"))
        if not source_id:
            continue
        if source_id in indexed:
            duplicates.add(source_id)
        else:
            indexed[source_id] = row
    return indexed, duplicates


def _validate_record(
    raw: Any,
    *,
    source_by_id: Mapping[str, Mapping[str, Any]],
    duplicate_source_ids: set[str],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_timing_refs: set[str],
) -> dict[str, Any]:
    row = raw if isinstance(raw, Mapping) else {}
    record_id = _txt(row.get("record_id"))
    claim_type = _txt(row.get("claim_type")).upper()
    product_id = _txt(row.get("product_id"))
    scenario = _txt(row.get("scenario")).lower()
    period = _txt(row.get("forecast_period"))
    unit = _txt(row.get("unit"))
    data_class = _txt(row.get("data_class")).upper()
    basis = _txt(row.get("basis"))
    comparison_basis = _txt(row.get("comparison_basis")).upper()
    evidence_refs = [
        str(item).strip()
        for item in (row.get("evidence_refs") if isinstance(row.get("evidence_refs"), list) else [])
        if str(item).strip()
    ]
    issues: list[str] = []
    if not record_id:
        issues.append("RECORD_ID_REQUIRED")
    if claim_type not in _CLAIMS:
        issues.append("CLAIM_TYPE_UNSUPPORTED")
    if not product_id:
        issues.append("PRODUCT_ID_REQUIRED")
    if scenario not in _SCENARIOS:
        issues.append("SCENARIO_MUST_BE_BEAR_BASE_OR_BULL")
    if not period:
        issues.append("FORECAST_PERIOD_REQUIRED")
    if unit != _CLAIMS.get(claim_type):
        issues.append("CLAIM_UNIT_MISMATCH")
    if data_class not in _VALID_DATA_CLASSES:
        issues.append("DATA_CLASS_INVALID")
    if not basis or basis.upper() in {"UNKNOWN", "N/A", "NONE"}:
        issues.append("BASIS_NOT_IDENTIFIABLE")
    if claim_type in _COMPARISON_BASIS_REQUIRED and comparison_basis != _COMPARISON_BASIS_REQUIRED[claim_type]:
        issues.append("INCREMENTAL_COMPARISON_BASIS_REQUIRED")
    if not evidence_refs:
        issues.append("EVIDENCE_REFERENCES_REQUIRED")

    value = row.get("value")
    parsed_value: Decimal | None = None
    if claim_type == "CAPACITY_AVAILABLE_DATE":
        try:
            parsed_date = date.fromisoformat(str(value))
            normalized_value = parsed_date.isoformat()
        except (TypeError, ValueError):
            normalized_value = None
            issues.append("CAPACITY_AVAILABLE_DATE_INVALID")
    else:
        parsed_value = _num(value)
        normalized_value = _fmt(parsed_value)
        if parsed_value is None:
            issues.append("CLAIM_VALUE_MUST_BE_FINITE_NUMERIC")
        elif parsed_value < 0:
            issues.append("CLAIM_VALUE_MUST_BE_NONNEGATIVE")
        elif claim_type in {"SUPPORTED_SALES_VOLUME", "SUPPORTED_NET_ASP", "EFFECTIVE_CAPACITY_AVAILABLE"} and parsed_value <= 0:
            issues.append("CLAIM_VALUE_MUST_BE_POSITIVE")

    source_rows: list[dict[str, Any]] = []
    for ref in evidence_refs:
        source = source_by_id.get(ref)
        if source is None or ref in unresolved_refs:
            issues.append(f"EVIDENCE_REFERENCE_UNRESOLVED:{ref}")
            source_rows.append({"source_id": ref, "status": "UNRESOLVED"})
            continue
        if ref in duplicate_source_ids:
            issues.append(f"EVIDENCE_REFERENCE_DUPLICATE_SOURCE_ID:{ref}")
            source_rows.append({"source_id": ref, "status": "DUPLICATE_SOURCE_ID"})
            continue
        time_status = _txt(source.get("time_status")).upper()
        if ref in after_cutoff_refs or time_status == "AFTER_CUTOFF":
            issues.append(f"EVIDENCE_REFERENCE_AFTER_CUTOFF:{ref}")
            source_rows.append({
                "source_id": ref,
                "source_class": _txt(source.get("source_class")).upper() or "UNKNOWN",
                "time_status": time_status,
                "status": "AFTER_CUTOFF",
            })
            continue
        if ref in uncertain_timing_refs or time_status != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED":
            issues.append(f"EVIDENCE_REFERENCE_TIME_NOT_PIT_COMPATIBLE:{ref}")
            source_rows.append({
                "source_id": ref,
                "source_class": _txt(source.get("source_class")).upper() or "UNKNOWN",
                "time_status": time_status or "UNKNOWN",
                "status": "TIME_NOT_PIT_COMPATIBLE",
            })
            continue
        source_class = _txt(source.get("source_class")).upper() or "UNKNOWN"
        domain_status = _txt(source.get("source_domain_class_status")).upper() or "UNKNOWN"
        if source_class not in _PRIMARY_SOURCE_CLASSES:
            issues.append(f"EVIDENCE_REFERENCE_NOT_PRIMARY_SOURCE_CLASS:{ref}")
            source_rows.append({
                "source_id": ref,
                "source_class": source_class,
                "time_status": time_status,
                "source_domain_class_status": domain_status,
                "status": "NON_PRIMARY_SOURCE_CLASS",
            })
            continue
        if domain_status == "SOURCE_CLASS_DOMAIN_MISMATCH":
            issues.append(f"EVIDENCE_REFERENCE_SOURCE_DOMAIN_CLASS_MISMATCH:{ref}")
            source_rows.append({
                "source_id": ref,
                "source_class": source_class,
                "time_status": time_status,
                "source_domain_class_status": domain_status,
                "status": "SOURCE_DOMAIN_CLASS_MISMATCH",
            })
            continue
        source_rows.append({
            "source_id": ref,
            "source_class": source_class,
            "time_status": time_status,
            "source_domain_class_status": domain_status,
            "status": "PIT_COMPATIBLE_PRIMARY_CLASS_DECLARED_NOT_ADMITTED",
            "formal_evidence_pit_admission": False,
        })

    if data_class == "ANALYST_ASSUMPTION":
        issues.append("ANALYST_ASSUMPTION_CANNOT_CORROBORATE_OPERATING_FEASIBILITY")
    status = "PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED" if not issues else "NOT_IDENTIFIABLE"
    return {
        "record_id": record_id or None,
        "claim_type": claim_type or "UNKNOWN",
        "product_id": product_id or "UNKNOWN",
        "scenario": scenario or "UNKNOWN",
        "forecast_period": period or "UNKNOWN",
        "value": normalized_value,
        "unit": unit or "UNKNOWN",
        "data_class": data_class or "UNKNOWN",
        "basis": basis or "UNKNOWN",
        "comparison_basis": comparison_basis or None,
        "evidence_refs": evidence_refs,
        "source_linkage": source_rows,
        "status": status,
        "issues": list(dict.fromkeys(issues)),
        "formal_evidence_pit_admission": False,
        "source_content_semantically_verified": False,
    }


def _claim_map(records: list[dict[str, Any]]) -> tuple[dict[tuple[str, str, str, str], dict[str, Any]], set[tuple[str, str, str, str]]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (
            record["scenario"],
            record["product_id"],
            record["forecast_period"],
            record["claim_type"],
        )
        grouped.setdefault(key, []).append(record)
    indexed: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    duplicates: set[tuple[str, str, str, str]] = set()
    for key, rows in grouped.items():
        if len(rows) > 1:
            duplicates.add(key)
            indexed[key] = {
                "status": "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED",
                "records": rows,
                "value": None,
            }
        else:
            indexed[key] = rows[0]
    return indexed, duplicates


def _compare_claim(
    indexed: Mapping[tuple[str, str, str, str], Mapping[str, Any]],
    duplicates: set[tuple[str, str, str, str]],
    *,
    scenario: str,
    product_id: str,
    period: str,
    claim_type: str,
    required_value: Any,
    direction: str,
) -> dict[str, Any]:
    key = (scenario, product_id, period, claim_type)
    record = indexed.get(key)
    required = _num(required_value)
    if key in duplicates:
        return {
            "claim_type": claim_type,
            "status": "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED",
            "required_value": _fmt(required),
            "evidence_value": None,
        }
    if record is None:
        return {
            "claim_type": claim_type,
            "status": "EVIDENCE_NOT_PROVIDED",
            "required_value": _fmt(required),
            "evidence_value": None,
        }
    if record.get("status") != "PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED":
        return {
            "claim_type": claim_type,
            "status": "CLAIM_NOT_ELIGIBLE_FOR_COMPARISON",
            "required_value": _fmt(required),
            "evidence_value": record.get("value"),
            "record_status": record.get("status"),
            "record_issues": record.get("issues") or [],
            "record_id": record.get("record_id"),
        }
    evidence_value = _num(record.get("value"))
    if required is None or evidence_value is None:
        return {
            "claim_type": claim_type,
            "status": "REQUIRED_OR_EVIDENCE_VALUE_NOT_IDENTIFIABLE",
            "required_value": _fmt(required),
            "evidence_value": record.get("value"),
            "record_id": record.get("record_id"),
        }
    meets = evidence_value + _TOL >= required if direction == "AT_LEAST" else evidence_value - _TOL <= required
    return {
        "claim_type": claim_type,
        "status": (
            "LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT"
            if meets else "LINKED_CLAIM_NUMERICALLY_BELOW_REQUIREMENT"
            if direction == "AT_LEAST" else "LINKED_CLAIM_NUMERICALLY_ABOVE_ALLOWED_COST"
        ),
        "required_value": _fmt(required),
        "evidence_value": _fmt(evidence_value),
        "record_id": record.get("record_id"),
        "comparison_direction": direction,
        "basis": "NUMERICAL_COMPARISON_ONLY_SOURCE_CONTENT_NOT_SEMANTICALLY_VERIFIED",
    }


def build_operating_feasibility_evidence_assessment(
    *,
    raw_evidence: Any,
    b69_audit: Mapping[str, Any],
    evidence_register: Any,
    unresolved_evidence_refs: Any = None,
    after_cutoff_evidence_refs: Any = None,
    uncertain_timing_evidence_refs: Any = None,
) -> dict[str, Any]:
    """Validate evidence-linked operating claims against B69 scenario requirements."""
    result: dict[str, Any] = {
        "schema_version": B70_SCHEMA,
        "status": "EVIDENCE_NOT_PROVIDED",
        "input_schema": INPUT_SCHEMA,
        "records": [],
        "scenarios": {},
        "overall_operational_feasibility_status": "NOT_IDENTIFIABLE",
        "formal_evidence_pit_admission_created": False,
        "source_content_semantically_verified": False,
        "decision_authority": False,
        "limitations": [
            "证据记录仅声明一个与产品/情景/期间绑定的经营数值及其来源引用；引用可解析和 PIT 时间兼容不等于原始材料语义已经核实。",
            "同一产品/情景/期间/claim_type 只允许一条汇总记录；重复记录不得自动求和，避免重叠订单或同一合同重复计算。",
            "ANALYST_ASSUMPTION 不作为经营可行性证据；仅 OBSERVED_ACTUAL / ISSUER_FORECAST 且引用 PIT 时间兼容的 primary-class 来源可进入条件数值比较。",
            "数值比较不建模价格与销量弹性、客户流失、产品替代、产线切换、成本曲线、扩建爬坡或现金流时序。",
            "本节点不自动完成正式 Evidence/PIT admission、预测准入、估值准入或投资决策。",
        ],
    }
    if not isinstance(raw_evidence, Mapping):
        return result
    if _txt(raw_evidence.get("schema_version")) != INPUT_SCHEMA:
        result["status"] = "INVALID_INPUT_SCHEMA"
        result["issues"] = ["OPERATING_FEASIBILITY_EVIDENCE_SCHEMA_MISMATCH"]
        return result
    raw_records = raw_evidence.get("records")
    if not isinstance(raw_records, list):
        result["status"] = "INVALID_RECORDS"
        result["issues"] = ["OPERATING_FEASIBILITY_EVIDENCE_RECORDS_MUST_BE_LIST"]
        return result

    source_by_id, duplicate_sources_from_register = _index_sources(evidence_register)
    duplicate_refs = set(str(item).strip() for item in (duplicate_sources_from_register | set()) if str(item).strip())
    unresolved = set(str(item).strip() for item in (unresolved_evidence_refs or []) if str(item).strip())
    after_cutoff = set(str(item).strip() for item in (after_cutoff_evidence_refs or []) if str(item).strip())
    uncertain = set(str(item).strip() for item in (uncertain_timing_evidence_refs or []) if str(item).strip())

    records = [
        _validate_record(
            row,
            source_by_id=source_by_id,
            duplicate_source_ids=duplicate_refs,
            unresolved_refs=unresolved,
            after_cutoff_refs=after_cutoff,
            uncertain_timing_refs=uncertain,
        )
        for row in raw_records
    ]
    record_ids: set[str] = set()
    duplicate_record_ids: set[str] = set()
    for record in records:
        record_id = record.get("record_id")
        if record_id:
            if record_id in record_ids:
                duplicate_record_ids.add(record_id)
            record_ids.add(record_id)
    if duplicate_record_ids:
        for record in records:
            if record.get("record_id") in duplicate_record_ids:
                record["status"] = "NOT_IDENTIFIABLE"
                record["issues"] = list(dict.fromkeys((record.get("issues") or []) + ["DUPLICATE_RECORD_ID"]))
    result["records"] = records
    indexed, duplicate_claims = _claim_map(records)

    forecast_period = _txt(b69_audit.get("forecast_period")) or "UNKNOWN"
    scenarios_raw = _map(b69_audit.get("scenarios"))
    any_records = bool(records)
    all_scenario_comparisons: list[str] = []
    for scenario in _SCENARIOS:
        scenario_b69 = _map(scenarios_raw.get(scenario))
        lenses_out: list[dict[str, Any]] = []
        for lens in (scenario_b69.get("requirement_lenses") or []):
            if not isinstance(lens, Mapping):
                continue
            lens_name = _txt(lens.get("lens")) or "UNKNOWN"
            products_out: list[dict[str, Any]] = []
            for product in (lens.get("products") or []):
                if not isinstance(product, Mapping):
                    continue
                product_id = _txt(product.get("product_id")) or "UNKNOWN"
                comparisons = [
                    _compare_claim(
                        indexed, duplicate_claims,
                        scenario=scenario, product_id=product_id, period=forecast_period,
                        claim_type="SUPPORTED_SALES_VOLUME",
                        required_value=product.get("required_sales_volume_tonnes"),
                        direction="AT_LEAST",
                    ),
                    _compare_claim(
                        indexed, duplicate_claims,
                        scenario=scenario, product_id=product_id, period=forecast_period,
                        claim_type="SUPPORTED_NET_ASP",
                        required_value=product.get("required_net_asp_cny_per_tonne"),
                        direction="AT_LEAST",
                    ),
                    _compare_claim(
                        indexed, duplicate_claims,
                        scenario=scenario, product_id=product_id, period=forecast_period,
                        claim_type="SUPPORTED_UNIT_VARIABLE_COST",
                        required_value=product.get("required_unit_variable_cost_cny_per_tonne"),
                        direction="AT_MOST",
                    ),
                    _compare_claim(
                        indexed, duplicate_claims,
                        scenario=scenario, product_id=product_id, period=forecast_period,
                        claim_type="EFFECTIVE_CAPACITY_AVAILABLE",
                        required_value=product.get("required_production_tonnes_under_unchanged_inventory_movement"),
                        direction="AT_LEAST",
                    ),
                ]
                required_date = _full_year_end(forecast_period)
                date_record = indexed.get((scenario, product_id, forecast_period, "CAPACITY_AVAILABLE_DATE"))
                if date_record is None:
                    date_comparison = {"claim_type": "CAPACITY_AVAILABLE_DATE", "status": "EVIDENCE_NOT_PROVIDED"}
                elif date_record.get("status") != "PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED":
                    date_comparison = {"claim_type": "CAPACITY_AVAILABLE_DATE", "status": "CLAIM_NOT_ELIGIBLE_FOR_COMPARISON"}
                elif required_date and date_record.get("value"):
                    date_comparison = {
                        "claim_type": "CAPACITY_AVAILABLE_DATE",
                        "status": "LINKED_CLAIM_AVAILABLE_BY_FORECAST_END" if date_record["value"] <= required_date else "LINKED_CLAIM_AVAILABLE_AFTER_FORECAST_END",
                        "required_by_date": required_date,
                        "evidence_value": date_record["value"],
                        "record_id": date_record.get("record_id"),
                    }
                else:
                    date_comparison = {"claim_type": "CAPACITY_AVAILABLE_DATE", "status": "FORECAST_PERIOD_END_NOT_IDENTIFIABLE"}

                funding_comparisons = []
                for required_claim, funded_claim in (
                    ("INCREMENTAL_CAPEX_REQUIRED", "INCREMENTAL_CAPEX_FUNDED"),
                    ("INCREMENTAL_WORKING_CAPITAL_REQUIRED", "INCREMENTAL_WORKING_CAPITAL_FUNDED"),
                ):
                    required_record = indexed.get((scenario, product_id, forecast_period, required_claim))
                    funded_record = indexed.get((scenario, product_id, forecast_period, funded_claim))
                    if required_record is None or funded_record is None:
                        funding_comparisons.append({
                            "funding_type": required_claim,
                            "status": "FUNDING_REQUIREMENT_OR_AVAILABLE_AMOUNT_NOT_IDENTIFIABLE",
                        })
                    elif any(row.get("status") != "PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED" for row in (required_record, funded_record)):
                        funding_comparisons.append({
                            "funding_type": required_claim,
                            "status": "FUNDING_CLAIM_NOT_ELIGIBLE_FOR_COMPARISON",
                        })
                    else:
                        required_amount = _num(required_record.get("value"))
                        funded_amount = _num(funded_record.get("value"))
                        funding_comparisons.append({
                            "funding_type": required_claim,
                            "status": (
                                "LINKED_FUNDING_CLAIM_COVERS_REQUIREMENT"
                                if required_amount is not None and funded_amount is not None and funded_amount + _TOL >= required_amount
                                else "LINKED_FUNDING_CLAIM_SHORTFALL"
                                if required_amount is not None and funded_amount is not None
                                else "FUNDING_AMOUNT_NOT_IDENTIFIABLE"
                            ),
                            "required_amount_cny": _fmt(required_amount),
                            "funded_amount_cny": _fmt(funded_amount),
                            "required_record_id": required_record.get("record_id"),
                            "funded_record_id": funded_record.get("record_id"),
                        })
                products_out.append({
                    "product_id": product_id,
                    "comparisons": comparisons,
                    "capacity_available_date_comparison": date_comparison,
                    "incremental_funding_comparisons": funding_comparisons,
                    "all_claims_are_non_additive": True,
                })
            lenses_out.append({
                "lens": lens_name,
                "non_additive": True,
                "products": products_out,
            })
        statuses = [
            comparison.get("status")
            for lens in lenses_out for product in lens.get("products", [])
            for comparison in (
                product.get("comparisons", [])
                + [product.get("capacity_available_date_comparison", {})]
                + product.get("incremental_funding_comparisons", [])
            )
        ]
        all_scenario_comparisons.extend(statuses)
        result["scenarios"][scenario] = {
            "scenario": scenario,
            "status": "CONDITIONAL_EVIDENCE_COMPARISON_AVAILABLE" if any(
                status.startswith("LINKED_") for status in statuses
            ) else "EVIDENCE_NOT_PROVIDED_OR_NOT_ELIGIBLE",
            "requirement_lenses": lenses_out,
        }

    has_eligible = any(row.get("status") == "PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED" for row in records)
    if not any_records:
        result["status"] = "EVIDENCE_NOT_PROVIDED"
    elif not has_eligible:
        result["status"] = "EVIDENCE_LINKAGE_NOT_ELIGIBLE"
    elif any(status in {
        "LINKED_CLAIM_NUMERICALLY_BELOW_REQUIREMENT",
        "LINKED_CLAIM_NUMERICALLY_ABOVE_ALLOWED_COST",
        "LINKED_CLAIM_AVAILABLE_AFTER_FORECAST_END",
        "LINKED_FUNDING_CLAIM_SHORTFALL",
    } for status in all_scenario_comparisons):
        result["status"] = "LINKED_EVIDENCE_IDENTIFIES_CONDITION_GAP"
    else:
        result["status"] = "PARTIAL_EVIDENCE_LINKAGE"

    result["overall_operational_feasibility_status"] = (
        "NOT_IDENTIFIABLE_PENDING_HUMAN_SOURCE_CONTENT_REVIEW_AND_COMPLETE_COVERAGE"
    )
    result["summary"] = (
        "B70 将经营可行性主张绑定到现有证据登记簿，并按产品、情景和期间与 B69 要求比较。"
        "数值命中只表示引用来源链接下的数值覆盖关系，不代表来源内容已核实或经营计划可执行。"
    )
    result["input_record_count"] = len(records)
    result["eligible_linked_record_count"] = sum(
        1 for row in records if row.get("status") == "PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED"
    )
    result["duplicate_claim_keys"] = [
        {
            "scenario": key[0],
            "product_id": key[1],
            "forecast_period": key[2],
            "claim_type": key[3],
        }
        for key in sorted(duplicate_claims)
    ]
    result["duplicate_record_ids"] = sorted(duplicate_record_ids)
    return result
