from __future__ import annotations

"""B5 incremental earnings-to-per-share valuation adapter for the local IIOS pilot.

Only the explicitly supported EPS-multiple adapter can change per-share scenarios.
The adapter is non-canonical: it preserves the existing valuation whenever a required
link, operator model choice, period match, source-aware input or baseline scope is unknown.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .operating_driver_forecast_v01 import _normalise_measure, _value

VALUATION_TRANSMISSION_SCHEMA = "IIOS-VALUATION-TRANSMISSION-0.1"
SUPPORTED_MODEL_FAMILY = "EPS_MULTIPLE"
SCENARIOS = ("bear", "base", "bull")
ALLOWED_FORWARD_CLASSES = {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}
ALLOWED_ATTRIBUTION_CLASSES = {"OBSERVED_ACTUAL", "ISSUER_FORECAST", "ANALYST_ASSUMPTION"}

FIELDS = {
    "ownership_ratio": "ratio",
    "displaced_existing_after_tax_profit_cny": "CNY",
    "basic_shares": "shares",
    "convertible_bond_incremental_shares": "shares",
    "other_dilution_shares": "shares",
    "pe_multiple_x": "x",
}


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field}_MUST_BE_NUMERIC") from exc
    if not result.is_finite():
        raise ValueError(f"{field}_MUST_BE_FINITE")
    return result


def _format(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _blocked(status: str, reason: str, issues: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": VALUATION_TRANSMISSION_SCHEMA,
        "status": status,
        "method": "EPS_MULTIPLE_INCREMENTAL",
        "applied_to_per_share_scenarios": False,
        "operator_model_family": "UNKNOWN",
        "baseline_includes_project": None,
        "earnings_period": "UNKNOWN",
        "valuation_model_name": "UNKNOWN",
        "summary": reason,
        "scenarios": {
            name: {
                "scenario": name,
                "status": "NOT_LINKED",
                "issues": [],
                "applied_to_per_share_value": False,
                "project_net_profit_cny": None,
                "incremental_attributable_profit_cny": None,
                "basic_eps_delta": None,
                "diluted_eps_delta": None,
                "value_delta_per_share_basic": None,
                "value_delta_per_share_diluted": None,
                "baseline_terminal_value_per_share": None,
                "adjusted_terminal_value_per_share": None,
            }
            for name in SCENARIOS
        },
        "entry_value_reference_baseline_per_share": None,
        "entry_value_reference_adjustment_per_share": None,
        "entry_value_reference_adjusted_per_share": None,
        "input_issues": list(issues or []),
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    }


def _normalise_b5_measure(
    raw: Any,
    *,
    field: str,
    expected_unit: str,
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
    allowed_data_classes: set[str],
) -> dict[str, Any]:
    result = _normalise_measure(
        raw,
        field=field,
        expected_unit=expected_unit,
        sources_by_id=sources_by_id,
        unresolved_refs=unresolved_refs,
        after_cutoff_refs=after_cutoff_refs,
        uncertain_refs=uncertain_refs,
    )
    data_class = str(result.get("data_class") or "UNKNOWN")
    if data_class != "UNKNOWN" and data_class not in allowed_data_classes:
        result["value"] = None
        result["calculation_usable"] = False
        result["evidence_status"] = "DATA_CLASS_NOT_ALLOWED_FOR_CONTEXT"
        result.setdefault("issues", []).append(f"{field}:DATA_CLASS_NOT_ALLOWED_FOR_CONTEXT")
    if _value(result) is None:
        if not result.get("issues"):
            result.setdefault("issues", []).append(f"{field}:REQUIRED_VALUE_UNKNOWN")
    return result


def _is_integer_shares(value: Decimal) -> bool:
    return value > 0 and value == value.to_integral_value()


def evaluate_valuation_transmission(
    raw: Any,
    *,
    operating_driver_forecast: Mapping[str, Any],
    forecast_valuation: Mapping[str, Any],
    operator_context: Mapping[str, Any] | None,
    evidence_register: list[Mapping[str, Any]] | None = None,
    unresolved_evidence_ids: list[str] | None = None,
    after_cutoff_evidence_ids: list[str] | None = None,
    uncertain_timing_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate a project-to-per-share bridge and apply it only on a complete valid path."""
    if not isinstance(raw, Mapping):
        return _blocked("NOT_LINKED_INPUT_MISSING", "未提供 B5 估值传导输入；现有每股估值与价格筛选保持不变。")
    if raw.get("schema_version") != VALUATION_TRANSMISSION_SCHEMA:
        return _blocked("NOT_LINKED_INVALID_SCHEMA", "B5 传导 schema 缺失或版本不兼容；现有每股估值保持不变。", [
            "VALUATION_TRANSMISSION_SCHEMA_MISMATCH"
        ])

    operator = operator_context if isinstance(operator_context, Mapping) else {}
    selected_family = str(operator.get("selected_model_family") or "UNKNOWN").strip().upper()
    baseline_includes_raw = operator.get("baseline_includes_project")
    baseline_includes = baseline_includes_raw if isinstance(baseline_includes_raw, bool) else None
    model_name = str(forecast_valuation.get("model") or "").strip()
    reported_model_name = str(raw.get("valuation_model_name") or "").strip()
    input_family = str(raw.get("model_family") or "UNKNOWN").strip().upper()
    earnings_period = str(raw.get("earnings_period") or "UNKNOWN").strip()
    operating_period = str(operating_driver_forecast.get("forecast_period") or "UNKNOWN").strip()
    input_issues: list[str] = []
    # Diagnostics about a hypothetical second application must not be confused
    # with blockers when the operator confirms the existing baseline already
    # includes the project and no adjustment will be applied.
    counterfactual_issues: list[str] = []

    result = _blocked("NOT_LINKED", "B5 估值传导尚未建立；现有每股估值与价格筛选保持不变。")
    result.update({
        "operator_model_family": selected_family,
        "baseline_includes_project": baseline_includes,
        "earnings_period": earnings_period,
        "valuation_model_name": model_name or "UNKNOWN",
        "input_issues": input_issues,
        "counterfactual_issues": counterfactual_issues,
    })

    if selected_family == "UNKNOWN":
        result.update({
            "status": "NOT_LINKED_OPERATOR_MODEL_UNKNOWN",
            "summary": "未由操作者独立确认主估值模型类别；不能让 AI 自行选择或更换估值模型，现有估值保持不变。",
        })
        return result
    if selected_family != SUPPORTED_MODEL_FAMILY:
        result.update({
            "status": "NOT_LINKED_UNSUPPORTED_MODEL_FAMILY",
            "summary": f"操作者选择的模型类别为 {selected_family}；B5 本批只实现 EPS_MULTIPLE 传导，不用该公式冒充 DCF、DDM、SOTP 或 RNPV。",
        })
        return result
    if input_family != selected_family:
        result.update({
            "status": "NOT_LINKED_MODEL_FAMILY_MISMATCH",
            "summary": "研究回答中的传导模型类别与操作者选择不一致；没有修改原估值。",
            "input_issues": ["MODEL_FAMILY_MISMATCH"],
        })
        return result
    if not model_name or not reported_model_name or reported_model_name != model_name:
        result.update({
            "status": "NOT_LINKED_MODEL_NAME_MISMATCH",
            "summary": "B5 声明的估值模型名称与现有主估值输入不完全一致；防止使用另一套模型计算增量价值。",
            "input_issues": ["VALUATION_MODEL_NAME_MISMATCH"],
        })
        return result
    if str(operating_driver_forecast.get("scope") or "UNKNOWN").upper() != "PROJECT_INCREMENTAL":
        result.update({
            "status": "NOT_LINKED_SCOPE_NOT_INCREMENTAL",
            "summary": "经营驱动范围不是已明确的 PROJECT_INCREMENTAL；不能把公司整体利润重复加到既有每股估值。",
            "input_issues": ["OPERATING_SCOPE_NOT_PROJECT_INCREMENTAL"],
        })
        return result
    if not earnings_period or earnings_period.upper() == "UNKNOWN" or earnings_period != operating_period:
        result.update({
            "status": "NOT_LINKED_PERIOD_MISMATCH",
            "summary": "估值盈利期间与 B4 经营情景期间不完全一致；没有进行跨期间的利润/倍数传导。",
            "input_issues": [f"EARNINGS_PERIOD_MISMATCH:valuation={earnings_period or 'UNKNOWN'};operating={operating_period or 'UNKNOWN'}"],
        })
        return result
    if not isinstance(baseline_includes_raw, bool):
        result.update({
            "status": "NOT_LINKED_BASELINE_SCOPE_UNKNOWN",
            "summary": "操作者尚未确认现有每股估值及入场价值锚是否已经包含该项目；为避免重复计算，不增加项目价值。",
        })
        # Continue with an explicit calculation-only view when possible, but never apply.
    if not isinstance(operating_driver_forecast.get("scenarios"), Mapping):
        result.update({
            "status": "NOT_LINKED_OPERATING_SCENARIOS_MISSING",
            "summary": "B4 没有可用的经营情景，未建立每股估值传导。",
            "input_issues": ["OPERATING_SCENARIOS_MISSING"],
        })
        return result

    sources_by_id = {
        str(row.get("source_id")): row
        for row in evidence_register or []
        if isinstance(row, Mapping) and str(row.get("source_id") or "").strip()
    }
    unresolved_refs = set(unresolved_evidence_ids or [])
    after_cutoff_refs = set(after_cutoff_evidence_ids or [])
    uncertain_refs = set(uncertain_timing_evidence_ids or [])
    raw_scenarios = raw.get("scenarios") if isinstance(raw.get("scenarios"), Mapping) else {}
    normalized: dict[str, dict[str, Any]] = {}
    scenario_results: dict[str, dict[str, Any]] = {}
    all_scenarios_valid = set(raw_scenarios) >= set(SCENARIOS)

    for name in SCENARIOS:
        issues: list[str] = []
        driver_row = operating_driver_forecast.get("scenarios", {}).get(name, {})
        project_profit_raw = driver_row.get("net_profit_cny") if isinstance(driver_row, Mapping) else None
        project_profit: Decimal | None = None
        if project_profit_raw in (None, ""):
            issues.append(f"{name.upper()}:OPERATING_NET_PROFIT_UNKNOWN")
        else:
            try:
                project_profit = _decimal(project_profit_raw, f"{name}.project_net_profit_cny")
            except ValueError:
                issues.append(f"{name.upper()}:OPERATING_NET_PROFIT_INVALID")

        row = raw_scenarios.get(name)
        row = row if isinstance(row, Mapping) else {}
        if not isinstance(raw_scenarios.get(name), Mapping):
            issues.append(f"{name.upper()}:TRANSMISSION_SCENARIO_MISSING")

        measures: dict[str, dict[str, Any]] = {}
        for key, unit in FIELDS.items():
            allowed = ALLOWED_FORWARD_CLASSES if key in {
                "displaced_existing_after_tax_profit_cny", "pe_multiple_x"
            } else ALLOWED_ATTRIBUTION_CLASSES
            measure = _normalise_b5_measure(
                row.get(key),
                field=f"valuation_transmission.{name}.{key}",
                expected_unit=unit,
                sources_by_id=sources_by_id,
                unresolved_refs=unresolved_refs,
                after_cutoff_refs=after_cutoff_refs,
                uncertain_refs=uncertain_refs,
                allowed_data_classes=allowed,
            )
            measures[key] = measure
            issues.extend(measure.get("issues") or [])

        values = {key: _value(value) for key, value in measures.items()}
        ownership = values["ownership_ratio"]
        displaced = values["displaced_existing_after_tax_profit_cny"]
        basic_shares = values["basic_shares"]
        convertible_shares = values["convertible_bond_incremental_shares"]
        other_dilution_shares = values["other_dilution_shares"]
        pe_multiple = values["pe_multiple_x"]

        if ownership is not None and not (Decimal("0") <= ownership <= Decimal("1")):
            issues.append(f"{name.upper()}:OWNERSHIP_RATIO_OUT_OF_RANGE")
        if basic_shares is not None and not _is_integer_shares(basic_shares):
            issues.append(f"{name.upper()}:BASIC_SHARES_MUST_BE_POSITIVE_INTEGER")
        if convertible_shares is not None and convertible_shares != convertible_shares.to_integral_value():
            issues.append(f"{name.upper()}:CONVERTIBLE_INCREMENTAL_SHARES_MUST_BE_INTEGER")
        if other_dilution_shares is not None and other_dilution_shares != other_dilution_shares.to_integral_value():
            issues.append(f"{name.upper()}:OTHER_DILUTION_SHARES_MUST_BE_INTEGER")
        if convertible_shares is not None and convertible_shares < 0:
            issues.append(f"{name.upper()}:CONVERTIBLE_INCREMENTAL_SHARES_NEGATIVE")
        if other_dilution_shares is not None and other_dilution_shares < 0:
            issues.append(f"{name.upper()}:OTHER_DILUTION_SHARES_NEGATIVE")
        if pe_multiple is not None and pe_multiple <= 0:
            issues.append(f"{name.upper()}:PE_MULTIPLE_MUST_BE_POSITIVE")

        # The displaced-profit input is the annual after-tax profit lost from
        # existing products, already measured at listed-company attribution.
        if displaced is not None and displaced < 0:
            issues.append(f"{name.upper()}:DISPLACED_PROFIT_MUST_BE_NONNEGATIVE")

        diluted_shares = None
        incremental_profit = None
        eps_basic = None
        eps_diluted = None
        value_delta_basic = None
        value_delta_diluted = None
        if (
            project_profit is not None
            and ownership is not None and Decimal("0") <= ownership <= Decimal("1")
            and displaced is not None and displaced >= 0
            and basic_shares is not None and _is_integer_shares(basic_shares)
            and convertible_shares is not None and convertible_shares >= 0
            and convertible_shares == convertible_shares.to_integral_value()
            and other_dilution_shares is not None and other_dilution_shares >= 0
            and other_dilution_shares == other_dilution_shares.to_integral_value()
            and pe_multiple is not None and pe_multiple > 0
        ):
            diluted_shares = basic_shares + convertible_shares + other_dilution_shares
            if diluted_shares <= 0:
                issues.append(f"{name.upper()}:DILUTED_SHARES_NOT_POSITIVE")
                diluted_shares = None
            else:
                incremental_profit = project_profit * ownership - displaced
                eps_basic = incremental_profit / basic_shares
                eps_diluted = incremental_profit / diluted_shares
                value_delta_basic = eps_basic * pe_multiple
                value_delta_diluted = eps_diluted * pe_multiple

        # The bridge's input value and resulting delta remain visible even if
        # another scenario fails; however, application is atomic across all three.
        baseline_terminal = None
        base_row = forecast_valuation.get("scenarios", {}).get(name, {})
        base_terminal_raw = base_row.get("terminal_value_per_share") if isinstance(base_row, Mapping) else None
        if base_terminal_raw not in (None, ""):
            try:
                baseline_terminal = _decimal(base_terminal_raw, f"forecast_valuation.{name}.terminal_value_per_share")
                if baseline_terminal < 0:
                    issues.append(f"{name.upper()}:BASELINE_TERMINAL_VALUE_NEGATIVE")
            except ValueError:
                issues.append(f"{name.upper()}:BASELINE_TERMINAL_VALUE_INVALID")
        else:
            issues.append(f"{name.upper()}:BASELINE_TERMINAL_VALUE_MISSING")

        distributions = None
        if not isinstance(base_row, Mapping):
            dist_raw = None
        elif "cash_distributions_per_share" not in base_row:
            # An omitted field is unknown, not a zero-distribution claim.
            dist_raw = None
        else:
            # An explicit null/empty value is UNKNOWN, not evidence of zero.
            dist_raw = base_row.get("cash_distributions_per_share")
        if dist_raw in (None, ""):
            issues.append(f"{name.upper()}:CASH_DISTRIBUTIONS_UNKNOWN")
        else:
            try:
                distributions = _decimal(dist_raw, f"forecast_valuation.{name}.cash_distributions_per_share")
                if distributions < 0:
                    issues.append(f"{name.upper()}:CASH_DISTRIBUTIONS_NEGATIVE")
            except ValueError:
                issues.append(f"{name.upper()}:CASH_DISTRIBUTIONS_INVALID")

        hypothetically_adjusted = (
            baseline_terminal + value_delta_diluted
            if baseline_terminal is not None and value_delta_diluted is not None
            else None
        )
        if (
            hypothetically_adjusted is not None
            and hypothetically_adjusted < 0
            and baseline_includes is not True
        ):
            # A negative counterfactual terminal value blocks an application that
            # would add the project twice or introduce that value into the baseline.
            # When the operator has confirmed that the existing baseline already
            # includes the project, this hypothetical is not applied; keep it visible
            # as a counterfactual without blocking return metrics on the unchanged baseline.
            issues.append(f"{name.upper()}:ADJUSTED_TERMINAL_VALUE_NEGATIVE")

        normalized[name] = {
            "project_profit": project_profit,
            "ownership": ownership,
            "displaced_profit": displaced,
            "basic_shares": basic_shares,
            "convertible_shares": convertible_shares,
            "other_dilution_shares": other_dilution_shares,
            "diluted_shares": diluted_shares,
            "pe_multiple": pe_multiple,
            "incremental_profit": incremental_profit,
            "eps_basic": eps_basic,
            "eps_diluted": eps_diluted,
            "value_delta_basic": value_delta_basic,
            "value_delta_diluted": value_delta_diluted,
            "baseline_terminal": baseline_terminal,
            "distributions": distributions,
            "hypothetically_adjusted_terminal": hypothetically_adjusted,
            "issues": sorted(set(issues)),
        }
        if issues:
            all_scenarios_valid = False

    # An incomplete bridge never modifies any scenario. This avoids mixed-model
    # outputs where one scenario contains project value and another does not.
    if not all_scenarios_valid:
        result.update({
            "status": "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID",
            "summary": "至少一个经营情景、归属/蚕食/股数/倍数输入或基准估值不可计算；保留原每股估值，不做部分传导。",
            "input_issues": sorted({
                issue
                for row in normalized.values()
                for issue in row.get("issues", [])
            }),
        })
    else:
        anchor_raw = forecast_valuation.get("entry_value_reference_per_share")
        try:
            anchor = _decimal(anchor_raw, "entry_value_reference_per_share")
            if anchor <= 0:
                raise ValueError("ENTRY_VALUE_REFERENCE_MUST_BE_POSITIVE")
        except ValueError:
            anchor = None
            input_issues.append("ENTRY_VALUE_REFERENCE_INVALID_OR_UNKNOWN")
            all_scenarios_valid = False

        if anchor is None:
            result.update({
                "status": "NOT_LINKED_ENTRY_REFERENCE_INVALID",
                "summary": "缺少正数的每股估值锚，不能同步更新安全边际参考值；保留全部原有估值。",
                "input_issues": sorted(set(input_issues)),
            })
        else:
            adjusted_wealth = {
                name: normalized[name]["hypothetically_adjusted_terminal"]
                + (normalized[name]["distributions"] or Decimal("0"))
                for name in SCENARIOS
            }
            adjusted_ordering_valid = (
                adjusted_wealth["bear"] <= adjusted_wealth["base"] <= adjusted_wealth["bull"]
            )
            if not adjusted_ordering_valid and baseline_includes is True:
                # This is a counterfactual "add the project again" view. The
                # confirmed, unchanged baseline is not priced from these values.
                # Preserve the anomaly for transparency without blocking the
                # baseline's return/entry-price/B6 calculations.
                counterfactual_issues.append(
                    "COUNTERFACTUAL_ADJUSTED_SCENARIO_WEALTH_ORDERING_INCONSISTENT"
                )
            if not adjusted_ordering_valid and baseline_includes is not True:
                result.update({
                    "status": "NOT_LINKED_ADJUSTED_SCENARIO_ORDERING_INCONSISTENT",
                    "summary": "传导后的 Bear/Base/Bull 总财富次序不一致；为避免把错序概率加权，原估值保持不变。",
                    "input_issues": ["ADJUSTED_SCENARIO_WEALTH_ORDERING_INCONSISTENT"],
                })
                all_scenarios_valid = False
            elif baseline_includes is True:
                result.update({
                    "status": "CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT",
                    "summary": "传导算术可计算，但操作者确认现有估值已经包含该项目；只展示增量敏感性，不重复叠加项目价值。",
                    "input_issues": [],
                })
            elif baseline_includes is None:
                result.update({
                    "status": "CALCULATED_NOT_APPLIED_BASELINE_SCOPE_UNKNOWN",
                    "summary": "传导算术可计算，但操作者未确认现有每股估值是否已包含该项目；不叠加、不修改入场锚。",
                    "input_issues": [],
                })
            else:
                adjusted_anchor = anchor + (normalized["base"]["value_delta_diluted"] or Decimal("0"))
                if adjusted_anchor <= 0:
                    result.update({
                        "status": "NOT_LINKED_ADJUSTED_ENTRY_REFERENCE_NONPOSITIVE",
                        "summary": "增量传导后的安全边际估值锚非正数；保留原每股估值。",
                        "input_issues": ["ADJUSTED_ENTRY_VALUE_REFERENCE_NONPOSITIVE"],
                    })
                    all_scenarios_valid = False
                else:
                    result.update({
                        "status": "APPLIED_TO_PER_SHARE_SCENARIOS",
                        "summary": "已按项目税后利润 × 所有权比例 − 存量业务被替代的税后归属利润，除以稀释后股数并乘以同模型 EPS 倍数计算增量每股价值；原估值明确不含该项目，故将增量对称传导至 Bear/Base/Bull 终值及 Base 安全边际锚。",
                        "applied_to_per_share_scenarios": True,
                        "entry_value_reference_adjustment_per_share": _format(normalized["base"]["value_delta_diluted"]),
                        "entry_value_reference_adjusted_per_share": _format(adjusted_anchor),
                        "input_issues": [],
                    })

    # Render complete per-scenario details and only populate an adjusted value
    # when a global apply decision was made.
    result_scenarios: dict[str, dict[str, Any]] = {}
    applied = result.get("status") == "APPLIED_TO_PER_SHARE_SCENARIOS"
    for name in SCENARIOS:
        row = normalized.get(name, {})
        valid = not row.get("issues") and row.get("value_delta_diluted") is not None
        adjusted_terminal = (
            row.get("hypothetically_adjusted_terminal")
            if applied and valid else None
        )
        scenario_result = {
            "scenario": name,
            "status": "CALCULATED" if valid else "NOT_LINKED",
            "issues": row.get("issues", []),
            "project_net_profit_cny": _format(row.get("project_profit")),
            "ownership_ratio": _format(row.get("ownership")),
            "displaced_existing_after_tax_profit_cny": _format(row.get("displaced_profit")),
            "incremental_attributable_profit_cny": _format(row.get("incremental_profit")),
            "basic_shares": _format(row.get("basic_shares")),
            "convertible_bond_incremental_shares": _format(row.get("convertible_shares")),
            "other_dilution_shares": _format(row.get("other_dilution_shares")),
            "diluted_shares": _format(row.get("diluted_shares")),
            "pe_multiple_x": _format(row.get("pe_multiple")),
            "basic_eps_delta": _format(row.get("eps_basic")),
            "diluted_eps_delta": _format(row.get("eps_diluted")),
            "value_delta_per_share_basic": _format(row.get("value_delta_basic")),
            "value_delta_per_share_diluted": _format(row.get("value_delta_diluted")),
            "baseline_terminal_value_per_share": _format(row.get("baseline_terminal")),
            "hypothetical_terminal_value_if_added_per_share": _format(row.get("hypothetically_adjusted_terminal")),
            "adjusted_terminal_value_per_share": _format(adjusted_terminal),
            "applied_to_per_share_value": applied and valid,
        }
        result_scenarios[name] = scenario_result

    result.update({
        "schema_version": VALUATION_TRANSMISSION_SCHEMA,
        "method": "EPS_MULTIPLE_INCREMENTAL",
        "operator_model_family": selected_family,
        "baseline_includes_project": baseline_includes,
        "earnings_period": earnings_period,
        "valuation_model_name": model_name or "UNKNOWN",
        "scenarios": result_scenarios,
        "counterfactual_issues": sorted(set(counterfactual_issues)),
        "entry_value_reference_baseline_per_share": (
            str(forecast_valuation.get("entry_value_reference_per_share"))
            if forecast_valuation.get("entry_value_reference_per_share") not in (None, "") else None
        ),
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    })
    # Preserve errors accumulated before the scenario loop, as well as post-loop checks.
    result["input_issues"] = sorted(set(
        list(result.get("input_issues") or []) + input_issues
    ))
    if not result["input_issues"] and result["status"] == "NOT_LINKED":
        result["status"] = "CALCULATED_NOT_APPLIED"
    return result


def render_valuation_transmission_section(transmission: Mapping[str, Any], currency: str) -> list[str]:
    """Render the B5 bridge, its dilution math and any unresolved links in Chinese."""
    result = transmission if isinstance(transmission, Mapping) else {}
    lines = [
        "",
        "### B5：经营结果到每股估值的传导",
        "",
        f"- 传导状态：**{result.get('status', 'NOT_LINKED')}**",
        f"- 操作者选择的主估值模型类别：{result.get('operator_model_family', 'UNKNOWN')}",
        f"- 主估值模型：{result.get('valuation_model_name', 'UNKNOWN')}",
        f"- 经营/估值盈利期间：{result.get('earnings_period', 'UNKNOWN')}",
        f"- 现有每股估值是否已包含该项目：{result.get('baseline_includes_project') if result.get('baseline_includes_project') is not None else 'UNKNOWN'}",
        f"- 结论：{result.get('summary', '未建立估值传导。')}",
        "",
        "- 计算路径：项目税后净利润 × 上市公司所有权比例 − 被替代存量业务税后归属利润；再分别除以基础股数和稀释后股数，乘以同一 EPS 倍数。只有原估值明确不含项目且三种情景完整时，才将稀释口径增量分别加到每股终值和 Base 入场估值锚。",
        "- 稀释后股数 = 基础股数 + 可转债潜在新增股数 + 其他潜在稀释股数。稀释处理是显式情景输入，不以当前股数冒充完全稀释股数。",
        "",
    ]
    if (
        result.get("baseline_includes_project") is True
        and result.get("status") == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    ):
        lines.extend([
            "- 非阻断性说明：操作者已确认现有估值基准包含该项目；本次 B5 增量反事实因输入缺项而未计算/未应用。该未应用桥接缺项不应单独阻断未修改主估值的回报、入场价与 B6 计算，但仍需保留并审阅下方缺项诊断。",
        ])
    scenarios = result.get("scenarios") if isinstance(result.get("scenarios"), Mapping) else {}
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        lines.extend([
            f"**{label} 情景**",
            f"- B4 项目税后净利润：{row.get('project_net_profit_cny') or 'UNKNOWN'} CNY",
            f"- 所有权比例 / 被替代存量税后利润：{row.get('ownership_ratio') if row.get('ownership_ratio') is not None else 'UNKNOWN'} / {row.get('displaced_existing_after_tax_profit_cny') or 'UNKNOWN'} CNY",
            f"- 增量归属利润：{row.get('incremental_attributable_profit_cny') or 'UNKNOWN'} CNY",
            f"- 基础股数 / 可转债新增股数 / 其他稀释：{row.get('basic_shares') or 'UNKNOWN'} / {row.get('convertible_bond_incremental_shares') or 'UNKNOWN'} / {row.get('other_dilution_shares') or 'UNKNOWN'}",
            f"- 稀释后股数 / P/E 倍数：{row.get('diluted_shares') or 'UNKNOWN'} / {row.get('pe_multiple_x') or 'UNKNOWN'}x",
            f"- EPS 增量（基础 / 稀释）：{row.get('basic_eps_delta') or 'UNKNOWN'} / {row.get('diluted_eps_delta') or 'UNKNOWN'} {currency}/股",
            f"- 增量每股价值（基础 / 稀释）：{row.get('value_delta_per_share_basic') or 'UNKNOWN'} / {row.get('value_delta_per_share_diluted') or 'UNKNOWN'} {currency}/股",
            f"- 原每股终值 / 假设叠加后的终值 / 实际采用的终值：{row.get('baseline_terminal_value_per_share') or 'UNKNOWN'} / {row.get('hypothetical_terminal_value_if_added_per_share') or 'UNKNOWN'} / {row.get('adjusted_terminal_value_per_share') or '未传导'} {currency}/股",
        ])
        if row.get("issues"):
            lines.extend(f"- 未解决：{issue}" for issue in row["issues"])
        lines.append("")
    if result.get("entry_value_reference_adjustment_per_share") is not None:
        lines.append(
            f"- Base 安全边际估值锚：原值 {result.get('entry_value_reference_baseline_per_share', 'UNKNOWN')}，"
            f"增量 {result.get('entry_value_reference_adjustment_per_share')}，"
            f"调整后 {result.get('entry_value_reference_adjusted_per_share')} {currency}/股。"
        )
    elif result.get("entry_value_reference_baseline_per_share") is not None:
        lines.append(f"- Base 安全边际估值锚保持原值 {result['entry_value_reference_baseline_per_share']} {currency}/股。")
    if result.get("input_issues"):
        lines.extend(["", "#### B5 传导未解决问题", ""])
        lines.extend(f"- {issue}" for issue in result["input_issues"])
    counterfactual_explanations = {
        "COUNTERFACTUAL_ADJUSTED_SCENARIO_WEALTH_ORDERING_INCONSISTENT": (
            "“假设再加一次项目”的反事实 Bear/Base/Bull 总财富顺序不符合 Bear ≤ Base ≤ Bull；"
            "由于操作者确认现有基准已含项目，该反事实未用于回报、目标入场价或 B6 计算。"
        ),
    }
    if result.get("counterfactual_issues"):
        lines.extend(["", "#### 非阻断性反事实诊断（未参与价格计算）", ""])
        lines.extend(
            f"- {counterfactual_explanations.get(issue, issue)}"
            for issue in result["counterfactual_issues"]
        )
    lines.extend([
        "",
        "- 适用范围：本批只实现 EPS_MULTIPLE 增量传导。DCF/FCF、DDM、SOTP、RNPV 等必须有各自可验证的模型公式/桥接，不能套用 EPS 倍数公式。",
        "- 此结果仍为 PILOT_NON_CANONICAL；不会建立正式估值准入、Decision 或执行授权。论点失效压力测试不自动加回项目价值。",
        "",
    ])
    return lines
