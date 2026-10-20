from __future__ import annotations

"""Auditable SOTP valuation adapter for the non-canonical local IIOS pilot.

Version 0.1 supports one deliberately narrow method:
sum(segment attributable net profit × segment P/E), subtract capitalized
parent-level after-tax costs, add signed net cash/debt and other explicit equity
adjustments, then divide by diluted shares. Minority effects already reflected in
attributable segment profit must not be deducted a second time.

It does not infer missing values, does not reuse the EPS_MULTIPLE B5 formula,
and does not create formal valuation admission or decision authority.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

SOTP_VALUATION_SCHEMA = "IIOS-SOTP-VALUATION-0.1"
SOTP_METHOD = "SEGMENT_ATTRIBUTABLE_NET_PROFIT_X_SEGMENT_PE"
SCENARIOS = ("bear", "base", "bull")
ALLOWED_DATA_CLASSES = {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}
UNIDENTIFIABLE_TEXT = {
    "", "UNKNOWN", "N/A", "NA", "NONE", "NULL", "TBD", "NOT_IDENTIFIABLE",
    "UNIDENTIFIABLE", "UNSPECIFIED", "NOT_PROVIDED", "NOT_AVAILABLE",
    "未提供", "未提供依据", "未知", "不详", "无法识别", "待补充", "待确认",
}


def _text_identifiable(value: Any) -> bool:
    text = " ".join(str(value or "").split()).strip()
    return bool(text) and text.upper() not in UNIDENTIFIABLE_TEXT


def _decimal(value: Any, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field}_NOT_NUMERIC") from exc
    if not number.is_finite():
        raise ValueError(f"{field}_NOT_FINITE")
    return number


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _blocked(status: str, summary: str, issues: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": SOTP_VALUATION_SCHEMA,
        "status": status,
        "method": SOTP_METHOD,
        "summary": summary,
        "forecast_period": None,
        "valuation_terminal_date": None,
        "scenarios": {},
        "issues": list(issues or []),
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    }


def _measure(
    raw: Any,
    *,
    field: str,
    unit: str,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_evidence_ids: set[str],
    after_cutoff_evidence_ids: set[str],
    uncertain_timing_evidence_ids: set[str],
    allow_negative: bool,
    allow_zero: bool,
) -> tuple[Decimal, dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{field}:MEASURE_OBJECT_REQUIRED")
    if str(raw.get("unit") or "").strip().lower() != unit.lower():
        raise ValueError(f"{field}:UNIT_MISMATCH_EXPECTED_{unit}")
    data_class = str(raw.get("data_class") or "").strip().upper()
    if data_class not in ALLOWED_DATA_CLASSES:
        raise ValueError(f"{field}:DATA_CLASS_NOT_ALLOWED")
    basis = str(raw.get("basis") or "").strip()
    if not _text_identifiable(basis):
        raise ValueError(f"{field}:BASIS_NOT_IDENTIFIABLE")
    value = _decimal(raw.get("value"), field)
    if not allow_negative and value < 0:
        raise ValueError(f"{field}:NEGATIVE_VALUE_NOT_ALLOWED")
    if not allow_zero and value == 0:
        raise ValueError(f"{field}:ZERO_VALUE_NOT_ALLOWED")
    refs_raw = raw.get("evidence_refs") or []
    if not isinstance(refs_raw, list):
        raise ValueError(f"{field}:EVIDENCE_REFS_MUST_BE_LIST")
    refs = list(dict.fromkeys(str(ref).strip() for ref in refs_raw if str(ref).strip()))
    if data_class == "ISSUER_FORECAST" and not refs:
        raise ValueError(f"{field}:ISSUER_FORECAST_EVIDENCE_REQUIRED")
    for ref in refs:
        source = evidence_by_id.get(ref)
        if source is None or ref in unresolved_evidence_ids:
            raise ValueError(f"{field}:EVIDENCE_REFERENCE_UNRESOLVED:{ref}")
        if ref in after_cutoff_evidence_ids:
            raise ValueError(f"{field}:EVIDENCE_REFERENCE_AFTER_CUTOFF:{ref}")
        if ref in uncertain_timing_evidence_ids or source.get("time_status") in {
            "UNKNOWN", "KNOWN_AT_INVALID", "KNOWN_AT_PRECISION_INSUFFICIENT", "AFTER_CUTOFF",
        }:
            raise ValueError(f"{field}:EVIDENCE_TIMING_UNRESOLVED:{ref}")
        if source.get("time_status") != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED":
            raise ValueError(f"{field}:EVIDENCE_NOT_CUTOFF_COMPATIBLE:{ref}")
    normalized = {
        "value": _fmt(value),
        "unit": unit,
        "data_class": data_class,
        "basis": basis,
        "evidence_refs": refs,
        "note": str(raw.get("note") or ""),
        "formal_evidence_pit_admission": False,
    }
    return value, normalized


def evaluate_sotp_valuation(
    raw: Any,
    *,
    selected_model_family: Any,
    expected_forecast_period: Any,
    expected_terminal_date: Any,
    evidence_register: list[dict[str, Any]],
    unresolved_evidence_ids: list[str] | set[str] | None = None,
    after_cutoff_evidence_ids: list[str] | set[str] | None = None,
    uncertain_timing_evidence_ids: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Compute Bear/Base/Bull SOTP per-share terminal values or fail closed."""
    if str(selected_model_family or "UNKNOWN").strip().upper() != "SOTP":
        return {
            **_blocked("NOT_SELECTED", "操作者未选择 SOTP；本适配器不参与主估值计算。"),
            "selected_for_primary_model": False,
        }
    if not isinstance(raw, Mapping):
        return _blocked(
            "SOTP_INPUT_MISSING",
            "操作者已选择 SOTP，但没有提供分部估值输入；不得使用其他模型值冒充 SOTP。",
            ["SOTP_INPUT_OBJECT_REQUIRED"],
        )
    if raw.get("schema_version") != SOTP_VALUATION_SCHEMA:
        return _blocked(
            "SOTP_SCHEMA_MISMATCH",
            "SOTP 输入版本不匹配；不得把未经验证的情景终值用于回报计算。",
            ["SOTP_SCHEMA_VERSION_MISMATCH"],
        )
    method = str(raw.get("calculation_method") or "").strip().upper()
    if method != SOTP_METHOD:
        return _blocked(
            "SOTP_METHOD_UNSUPPORTED",
            "当前版本只支持“分部归母净利润 × 分部 P/E”并进行母公司调整的 SOTP 方法。",
            ["SOTP_CALCULATION_METHOD_UNSUPPORTED"],
        )
    summary = str(raw.get("summary") or "").strip()
    if not _text_identifiable(summary):
        return _blocked(
            "SOTP_RATIONALE_NOT_IDENTIFIABLE",
            "SOTP 缺少可识别的模型适用理由。",
            ["SOTP_SUMMARY_NOT_IDENTIFIABLE"],
        )
    period = str(raw.get("forecast_period") or "").strip().upper()
    terminal_date = str(raw.get("valuation_terminal_date") or "").strip()
    expected_period = str(expected_forecast_period or "").strip().upper()
    expected_date = str(expected_terminal_date or "").strip()
    issues: list[str] = []
    if not period or period != expected_period:
        issues.append("SOTP_FORECAST_PERIOD_MISMATCH")
    if not terminal_date or terminal_date != expected_date:
        issues.append("SOTP_TERMINAL_DATE_MISMATCH")
    if issues:
        return _blocked(
            "SOTP_PERIOD_OR_TERMINAL_DATE_MISMATCH",
            "SOTP 预测期间/估值终点与主报告期间契约不一致。",
            issues,
        )

    evidence_by_id = {
        str(row.get("source_id")): row
        for row in evidence_register
        if isinstance(row, Mapping) and row.get("source_id")
    }
    unresolved = set(unresolved_evidence_ids or [])
    after_cutoff = set(after_cutoff_evidence_ids or [])
    uncertain = set(uncertain_timing_evidence_ids or [])
    scenario_inputs = raw.get("scenarios")
    if not isinstance(scenario_inputs, Mapping) or set(scenario_inputs) != set(SCENARIOS):
        return _blocked(
            "SOTP_SCENARIOS_INCOMPLETE",
            "SOTP 必须同时提供 Bear/Base/Bull 三种完整分部估值情景。",
            ["SOTP_REQUIRES_BEAR_BASE_BULL"],
        )

    outputs: dict[str, Any] = {}
    segment_ids_by_scenario: dict[str, list[str]] = {}
    try:
        for scenario_name in SCENARIOS:
            scenario = scenario_inputs.get(scenario_name)
            if not isinstance(scenario, Mapping):
                raise ValueError(f"{scenario_name.upper()}:SCENARIO_OBJECT_REQUIRED")
            scenario_rationale = str(scenario.get("rationale") or "").strip()
            if not _text_identifiable(scenario_rationale):
                raise ValueError(f"{scenario_name.upper()}:SCENARIO_RATIONALE_NOT_IDENTIFIABLE")
            raw_segments = scenario.get("segments")
            if not isinstance(raw_segments, list) or not raw_segments:
                raise ValueError(f"{scenario_name.upper()}:SEGMENTS_REQUIRED")
            normalized_segments: list[dict[str, Any]] = []
            segment_ids: list[str] = []
            segment_equity_value = Decimal("0")
            for index, segment in enumerate(raw_segments, start=1):
                if not isinstance(segment, Mapping):
                    raise ValueError(f"{scenario_name.upper()}:SEGMENT_{index}_OBJECT_REQUIRED")
                segment_id = str(segment.get("segment_id") or "").strip()
                segment_name = str(segment.get("segment_name") or "").strip()
                if not _text_identifiable(segment_id) or not _text_identifiable(segment_name):
                    raise ValueError(f"{scenario_name.upper()}:SEGMENT_{index}_IDENTITY_NOT_IDENTIFIABLE")
                if segment_id in segment_ids:
                    raise ValueError(f"{scenario_name.upper()}:DUPLICATE_SEGMENT_ID:{segment_id}")
                segment_ids.append(segment_id)
                profit, profit_norm = _measure(
                    segment.get("attributable_net_profit_cny"),
                    field=f"{scenario_name}.{segment_id}.attributable_net_profit_cny",
                    unit="CNY",
                    evidence_by_id=evidence_by_id,
                    unresolved_evidence_ids=unresolved,
                    after_cutoff_evidence_ids=after_cutoff,
                    uncertain_timing_evidence_ids=uncertain,
                    allow_negative=False,
                    allow_zero=True,
                )
                multiple, multiple_norm = _measure(
                    segment.get("pe_multiple_x"),
                    field=f"{scenario_name}.{segment_id}.pe_multiple_x",
                    unit="x",
                    evidence_by_id=evidence_by_id,
                    unresolved_evidence_ids=unresolved,
                    after_cutoff_evidence_ids=after_cutoff,
                    uncertain_timing_evidence_ids=uncertain,
                    allow_negative=False,
                    allow_zero=False,
                )
                value = profit * multiple
                segment_equity_value += value
                normalized_segments.append({
                    "segment_id": segment_id,
                    "segment_name": segment_name,
                    "attributable_net_profit_cny": profit_norm,
                    "pe_multiple_x": multiple_norm,
                    "segment_equity_value_cny": _fmt(value),
                })
            segment_ids_by_scenario[scenario_name] = sorted(segment_ids)

            parent = scenario.get("parent_level_adjustments")
            if not isinstance(parent, Mapping):
                raise ValueError(f"{scenario_name.upper()}:PARENT_LEVEL_ADJUSTMENTS_REQUIRED")
            central_cost, central_cost_norm = _measure(
                parent.get("central_cost_after_tax_cny"),
                field=f"{scenario_name}.central_cost_after_tax_cny",
                unit="CNY",
                evidence_by_id=evidence_by_id,
                unresolved_evidence_ids=unresolved,
                after_cutoff_evidence_ids=after_cutoff,
                uncertain_timing_evidence_ids=uncertain,
                allow_negative=False,
                allow_zero=True,
            )
            central_multiple, central_multiple_norm = _measure(
                parent.get("central_cost_multiple_x"),
                field=f"{scenario_name}.central_cost_multiple_x",
                unit="x",
                evidence_by_id=evidence_by_id,
                unresolved_evidence_ids=unresolved,
                after_cutoff_evidence_ids=after_cutoff,
                uncertain_timing_evidence_ids=uncertain,
                allow_negative=False,
                allow_zero=True,
            )
            net_cash_debt, net_cash_debt_norm = _measure(
                parent.get("net_cash_debt_cny"),
                field=f"{scenario_name}.net_cash_debt_cny",
                unit="CNY",
                evidence_by_id=evidence_by_id,
                unresolved_evidence_ids=unresolved,
                after_cutoff_evidence_ids=after_cutoff,
                uncertain_timing_evidence_ids=uncertain,
                allow_negative=True,
                allow_zero=True,
            )
            if "minority_interests_cny" in parent:
                raise ValueError(
                    f"{scenario_name.upper()}:SEPARATE_MINORITY_INTERESTS_ADJUSTMENT_CONFLICTS_WITH_ATTRIBUTABLE_SEGMENT_PROFIT"
                )
                        diluted_shares, diluted_shares_norm = _measure(
                scenario.get("diluted_shares"),
                field=f"{scenario_name}.diluted_shares",
                unit="shares",
                evidence_by_id=evidence_by_id,
                unresolved_evidence_ids=unresolved,
                after_cutoff_evidence_ids=after_cutoff,
                uncertain_timing_evidence_ids=uncertain,
                allow_negative=False,
                allow_zero=False,
            )
            if diluted_shares != diluted_shares.to_integral_value():
                raise ValueError(f"{scenario_name.upper()}:DILUTED_SHARES_MUST_BE_INTEGER")
            if central_cost > 0 and central_multiple <= 0:
                raise ValueError(f"{scenario_name.upper()}:CENTRAL_COST_MULTIPLE_REQUIRED")
            central_cost_value = central_cost * central_multiple
            equity_value = (
                segment_equity_value
                - central_cost_value
                + net_cash_debt
                + other_adjustments
            )
            if equity_value <= 0:
                raise ValueError(f"{scenario_name.upper()}:TOTAL_EQUITY_VALUE_NOT_POSITIVE")
            per_share = equity_value / diluted_shares
            outputs[scenario_name] = {
                "rationale": scenario_rationale,
                "segments": normalized_segments,
                "segment_equity_value_cny": _fmt(segment_equity_value),
                "parent_level_adjustments": {
                    "central_cost_after_tax_cny": central_cost_norm,
                    "central_cost_multiple_x": central_multiple_norm,
                    "capitalized_central_cost_value_cny": _fmt(central_cost_value),
                    "net_cash_debt_cny": net_cash_debt_norm,
                    "other_adjustments_cny": other_norm,
                },
                "diluted_shares": diluted_shares_norm,
                "total_equity_value_cny": _fmt(equity_value),
                "terminal_value_per_share": _fmt(per_share),
            }
    except ValueError as exc:
        issue = str(exc)
        return _blocked(
            "SOTP_INPUT_INCOMPLETE_OR_INVALID",
            "SOTP 某个分部、母公司调整、股数或证据引用无法审计复算；不输出可用于回报计算的部分估值。",
            [issue],
        )

    segment_sets = list(segment_ids_by_scenario.values())
    if any(ids != segment_sets[0] for ids in segment_sets[1:]):
        return _blocked(
            "SOTP_SEGMENT_UNIVERSE_MISMATCH",
            "Bear/Base/Bull 的分部集合不一致；必须在相同分部结构下比较不同经营情景。",
            ["SOTP_SEGMENT_IDS_MUST_MATCH_ACROSS_SCENARIOS"],
        )
    name_lookup: dict[str, str] = {}
    for row in outputs.values():
        for segment in row["segments"]:
            prior = name_lookup.setdefault(segment["segment_id"], segment["segment_name"])
            if prior != segment["segment_name"]:
                return _blocked(
                    "SOTP_SEGMENT_UNIVERSE_MISMATCH",
                    "同一个分部 ID 在不同情景中使用了不同分部名称。",
                    ["SOTP_SEGMENT_NAME_MISMATCH_ACROSS_SCENARIOS"],
                )

    wealth = {name: _decimal(outputs[name]["terminal_value_per_share"], name) for name in SCENARIOS}
    if not (wealth["bear"] <= wealth["base"] <= wealth["bull"]):
        return _blocked(
            "SOTP_SCENARIO_ORDERING_INCONSISTENT",
            "计算后的 SOTP 每股终值未满足 Bear ≤ Base ≤ Bull；不将该组终值用于回报或价格敏感性。",
            ["SOTP_SCENARIO_ORDERING_INCONSISTENT"],
        )
    return {
        "schema_version": SOTP_VALUATION_SCHEMA,
        "status": "CALCULATED",
        "method": SOTP_METHOD,
        "selected_for_primary_model": True,
        "summary": (
            "按分部归属净利润分别乘以各自 P/E 倍数求和，再减去资本化母公司税后成本，"
            "加减不重复计价的净现金/净负债及其他显式调整，最后除以稀释后股数。分部利润须已按上市公司股东口径计量；"
            "不会对已反映于归母利润的同一批少数股东权益再次扣减。所有金额与倍数均为显式输入；"
            "模型未自动补零，结果仍属非正式研究测算。"
        ),
        "analyst_supplied_summary": summary,
        "forecast_period": period,
        "valuation_terminal_date": terminal_date,
        "scenarios": outputs,
        "issues": [],
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    }


def render_sotp_valuation_section(result: Mapping[str, Any], currency: str) -> list[str]:
    """Render inputs, arithmetic and blockers for independent human review."""
    data = result if isinstance(result, Mapping) else {}
    lines = [
        "",
        "### SOTP：分部估值到每股终值的计算链",
        "",
        f"- 计算状态：**{data.get('status', 'UNKNOWN')}**；方法：{data.get('method', SOTP_METHOD)}",
        f"- 是否选为主估值模型：{data.get('selected_for_primary_model', False)}",
        f"- 预测期间 / 估值终点：{data.get('forecast_period') or 'UNKNOWN'} / {data.get('valuation_terminal_date') or 'UNKNOWN'}",
        f"- 公式：Σ（已归属于上市公司股东的分部净利润 × 分部 P/E）−（母公司税后成本 × 母公司成本倍数）+ 不重复计价的净现金/净负债 + 其他显式调整；再除以稀释后股数。",
        f"- 说明：{data.get('summary') or '未计算'}",
        "- 适用边界：B5 的 EPS_MULTIPLE 增量适配器不能用于 SOTP；不将项目 EPS 倍数增量套到 SOTP 分部估值。",
        "- 正式估值准入：未创建；本结果不创建 Decision 或交易授权。",
        "",
    ]
    scenarios = data.get("scenarios") if isinstance(data.get("scenarios"), Mapping) else {}
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        lines.extend([
            f"**{label} 情景**",
            f"- 情景理由：{row.get('rationale') or 'UNKNOWN'}",
        ])
        for segment in row.get("segments") or []:
            if not isinstance(segment, Mapping):
                continue
            profit = (segment.get("attributable_net_profit_cny") or {}).get("value", "UNKNOWN")
            multiple = (segment.get("pe_multiple_x") or {}).get("value", "UNKNOWN")
            lines.append(
                f"- 分部 {segment.get('segment_id', 'UNKNOWN')} / {segment.get('segment_name', 'UNKNOWN')}："
                f"归属净利润 {profit} CNY × P/E {multiple} = {segment.get('segment_equity_value_cny', 'UNKNOWN')} CNY"
            )
        parent = row.get("parent_level_adjustments") if isinstance(row.get("parent_level_adjustments"), Mapping) else {}
        lines.extend([
            f"- 分部权益价值合计：{row.get('segment_equity_value_cny') or 'UNKNOWN'} CNY",
            f"- 资本化母公司税后成本：{parent.get('capitalized_central_cost_value_cny') or 'UNKNOWN'} CNY",
            f"- 净现金/净负债：{(parent.get('net_cash_debt_cny') or {}).get('value', 'UNKNOWN')} CNY",
            f"- 其他调整：{(parent.get('other_adjustments_cny') or {}).get('value', 'UNKNOWN')} CNY",
            f"- 总股权价值 / 稀释后股数：{row.get('total_equity_value_cny') or 'UNKNOWN'} CNY / {(row.get('diluted_shares') or {}).get('value', 'UNKNOWN')}",
            f"- SOTP 每股终值：{row.get('terminal_value_per_share') or 'UNKNOWN'} {currency}",
            "",
        ])
    if data.get("issues"):
        lines.extend(["#### SOTP 未解决问题", ""])
        lines.extend(f"- {issue}" for issue in data.get("issues") or [])
    return lines
