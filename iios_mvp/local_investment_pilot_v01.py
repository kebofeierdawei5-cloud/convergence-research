from __future__ import annotations

"""Minimal candidate-driven, non-canonical local IIOS pilot.

This is a practical trial path, not a second canonical engine. It uses the
existing research-intake validator and the existing IIOS return/entry-price
solver. Formal admission and canonical Decision code remain unchanged.
"""

import argparse
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping

from .investment_core_contract_v03 import (
    BUY_ENTRY_RETURN_CUSHION_THRESHOLD,
    FUNDAMENTAL_TARGET_ANNUALIZED_RETURN,
    SCENARIOS,
    calculate_return_metrics,
)
from .research_intake import build_research_case

PILOT_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-0.1"
PILOT_ANALYSIS_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-ANALYSIS-0.1"
PILOT_STATUS = "PILOT_NON_CANONICAL"
PILOT_RECEIPT_SCHEMA = "IIOS-LOCAL-PILOT-RUN-RECORD-0.1"
SHANGHAI = timezone(timedelta(hours=8))
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRICE_ASSURANCE = "OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED"


class LocalInvestmentPilotError(ValueError):
    """Bad local pilot input or unavailable pilot output."""


def _number(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_NUMERIC") from exc
    if not result.is_finite():
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_FINITE")
    return result


def _positive(value: Any, field: str) -> Decimal:
    result = _number(value, field)
    if result <= 0:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_POSITIVE")
    return result


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError) as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_YYYY_MM_DD") from exc


def _datetime(value: Any, field: str, *, allow_date_only: bool = True) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise LocalInvestmentPilotError(f"{field}_REQUIRED")
    if allow_date_only and len(raw) == 10:
        return datetime.combine(_date(raw, field), time.min, tzinfo=SHANGHAI)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_ISO_DATETIME") from exc
    if parsed.tzinfo is None:
        raise LocalInvestmentPilotError(f"{field}_MUST_INCLUDE_TIMEZONE")
    return parsed.astimezone(SHANGHAI)


def _outside_repo(path: str | Path, field: str, *, must_exist: bool = False) -> Path:
    raw = Path(path).expanduser()
    if must_exist and not raw.is_file():
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_A_FILE")
    resolved = raw.resolve(strict=must_exist)
    try:
        resolved.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return resolved
    raise LocalInvestmentPilotError(f"{field}_MUST_BE_OUTSIDE_REPOSITORY")


def _private_dir(path: str | Path, field: str) -> Path:
    root = _outside_repo(path, field)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _write_local(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def _status(value: Any, allowed: set[str]) -> str:
    item = str(value or "UNKNOWN").strip().upper()
    return item if item in allowed else "UNKNOWN"


def _items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _collect_refs(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"evidence_refs", "source_refs", "evidence_ids", "source_ids"} and isinstance(item, list):
                result.update(str(row).strip() for row in item if str(row).strip())
            else:
                result.update(_collect_refs(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_collect_refs(item))
    return result


def _prepare_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != PILOT_SCHEMA:
        raise LocalInvestmentPilotError("PILOT_INPUT_SCHEMA_MISMATCH")
    case_raw = payload.get("case")
    price_raw = payload.get("price_input")
    if not isinstance(case_raw, Mapping) or not isinstance(price_raw, Mapping):
        raise LocalInvestmentPilotError("CASE_AND_PRICE_INPUT_REQUIRED")
    company = str(case_raw.get("company") or "").strip()
    if not company:
        raise LocalInvestmentPilotError("COMPANY_REQUIRED")
    market = str(case_raw.get("market") or "CN-A")
    symbol = str(case_raw.get("symbol") or "").strip()
    cutoff = _date(case_raw.get("as_of_date"), "AS_OF_DATE")
    position_raw = str(case_raw.get("current_position_pct", "0"))
    case = build_research_case(symbol, cutoff.isoformat(), position_raw, market=market)
    position = str(case["request"]["current_position_pct"])
    normalized_market = case["request"]["market"]
    currency = str(case_raw.get("currency") or ("CNY" if normalized_market == "CN-A" else "HKD")).upper()
    if currency != ("CNY" if normalized_market == "CN-A" else "HKD"):
        raise LocalInvestmentPilotError("CURRENCY_DOES_NOT_MATCH_MARKET")

    price = _positive(price_raw.get("price"), "CURRENT_PRICE")
    observation = _date(price_raw.get("observation_date"), "PRICE_OBSERVATION_DATE")
    known_at = _datetime(price_raw.get("known_at"), "PRICE_KNOWN_AT", allow_date_only=False)
    cutoff_start = datetime.combine(cutoff, time.min, tzinfo=SHANGHAI)
    price_issues: list[str] = []
    if known_at.date() != observation:
        price_issues.append("PRICE_KNOWN_AT_DATE_MISMATCH")
    if observation > cutoff:
        price_issues.append("PRICE_OBSERVATION_AFTER_CUTOFF")
    if known_at > cutoff_start:
        price_issues.append("PRICE_KNOWN_AFTER_DATE_ONLY_CUTOFF")
    if str(price_raw.get("assurance_label") or "") != PRICE_ASSURANCE:
        raise LocalInvestmentPilotError("PRICE_MUST_REMAIN_OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED")
    claims = _items(price_raw.get("sources_claimed"))
    if not claims:
        raise LocalInvestmentPilotError("PRICE_SOURCE_CLAIM_REQUIRED")

    sources: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for row in payload.get("evidence_register") or []:
        if not isinstance(row, Mapping):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if not source_id or source_id in source_ids:
            continue
        source_ids.add(source_id)
        known_text = str(row.get("known_at") or "")
        source_time_status = "UNKNOWN"
        if known_text:
            try:
                source_time = _datetime(known_text, f"{source_id}_KNOWN_AT")
                source_time_status = (
                    "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
                    if source_time <= cutoff_start else "AFTER_CUTOFF"
                )
            except LocalInvestmentPilotError:
                source_time_status = "KNOWN_AT_INVALID"
        sources.append({
            "source_id": source_id,
            "title": str(row.get("title") or "未提供标题"),
            "source_class": str(row.get("source_class") or "UNKNOWN"),
            "source_ref": str(row.get("source_ref") or "UNKNOWN"),
            "known_at": known_text or None,
            "time_status": source_time_status,
            "summary": str(row.get("summary") or "未提供事实摘要"),
            "raw_sha256_claimed": row.get("raw_sha256_claimed"),
            "formal_evidence_pit_admission": False,
        })

    raw_assessment = payload.get("assessment") if isinstance(payload.get("assessment"), Mapping) else {}
    allowed_assessment = {
        "trust": {"PASS", "REVALIDATION", "FAIL", "UNKNOWN"},
        "reality": {"PASS", "CONDITIONAL", "BLOCKED", "UNKNOWN"},
        "quality": {"PASS", "CONDITIONAL", "BLOCKED", "UNKNOWN"},
        "thesis": {"INTACT", "WATCH", "BROKEN", "UNKNOWN"},
        "market_implied_expectation": {"PASS", "NOT_IDENTIFIABLE", "OUTSIDE_HISTORICAL_SUPPORT", "UNKNOWN", "BLOCKED", "AMBIGUOUS", "INCOMPATIBLE"},
        "expectation_gap": {"PASS", "UNKNOWN", "BLOCKED", "AMBIGUOUS", "INCOMPATIBLE"},
        "risk": {"PASS", "FAIL", "UNKNOWN"},
    }
    assessment: dict[str, Any] = {}
    for name, states in allowed_assessment.items():
        raw = raw_assessment.get(name) if isinstance(raw_assessment.get(name), Mapping) else {}
        assessment[name] = dict(raw)
        assessment[name]["status"] = _status(raw.get("status"), states)
        assessment[name]["summary"] = str(raw.get("summary") or "")
    assessment["expectation_gap"]["direction"] = _status(
        assessment["expectation_gap"].get("direction"),
        {"POSITIVE", "NEUTRAL", "NEGATIVE", "UNKNOWN"},
    )
    assessment["thesis"]["break_conditions"] = _items(assessment["thesis"].get("break_conditions"))
    assessment["thesis"]["reassessment_triggers"] = _items(assessment["thesis"].get("reassessment_triggers"))
    assessment["risk"]["items"] = _items(assessment["risk"].get("items"))
    value_drivers = raw_assessment.get("value_drivers") or []
    assessment["value_drivers"] = [
        {
            "rank": int(item.get("rank", index)),
            "driver": str(item.get("driver") or "未命名价值驱动因素"),
            "impact": _status(item.get("impact"), {"POSITIVE", "NEGATIVE", "MIXED", "UNKNOWN"}),
            "rationale": str(item.get("rationale") or ""),
            "evidence_refs": _items(item.get("evidence_refs")),
        }
        for index, item in enumerate(value_drivers, start=1) if isinstance(item, Mapping)
    ]
    assessment["thesis"]["core_statement"] = str(assessment["thesis"].get("core_statement") or "")
    assessment["thesis"]["drivers"] = assessment["thesis"].get("drivers") if isinstance(assessment["thesis"].get("drivers"), list) else []

    forecast_raw = payload.get("forecast_valuation") if isinstance(payload.get("forecast_valuation"), Mapping) else {}
    forecast = {
        "model": str(forecast_raw.get("model") or "UNKNOWN"),
        "model_rationale": str(forecast_raw.get("model_rationale") or ""),
        "entry_value_reference_per_share": forecast_raw.get("entry_value_reference_per_share"),
        "probabilities_calibrated": forecast_raw.get("probabilities_calibrated") is True,
        "assumptions": _items(forecast_raw.get("assumptions")),
        "scenarios": forecast_raw.get("scenarios") if isinstance(forecast_raw.get("scenarios"), Mapping) else {},
    }
    parameters_raw = payload.get("decision_parameters") if isinstance(payload.get("decision_parameters"), Mapping) else {}
    try:
        horizon = int(parameters_raw.get("horizon_years", 1))
    except (TypeError, ValueError):
        horizon = 1
    if horizon not in (1, 2, 3):
        horizon = 1
    override = parameters_raw.get("horizon_override", False)
    override_basis = parameters_raw.get("horizon_override_basis") if isinstance(parameters_raw.get("horizon_override_basis"), list) else []
    rationale = str(parameters_raw.get("horizon_selection_rationale") or "默认以 1 年作为年化回报参考期限。")
    if horizon == 3:
        allowed_basis = {"MAJOR_INDUSTRY_LEADER", "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX"}
        if override is not True or not override_basis or any(item not in allowed_basis for item in override_basis):
            horizon = 1
            override = False
            override_basis = []
            rationale += " 3 年覆盖条件不足，已退回默认 1 年。"
    elif override is not False or override_basis:
        override = False
        override_basis = []
        rationale += " 期限覆盖未通过条件检查，已使用默认期限规则。"
    try:
        required_return = max(
            FUNDAMENTAL_TARGET_ANNUALIZED_RETURN,
            _number(parameters_raw.get("required_return_annualized", "0.15"), "REQUIRED_RETURN"),
        )
    except LocalInvestmentPilotError:
        required_return = FUNDAMENTAL_TARGET_ANNUALIZED_RETURN
    try:
        max_loss = _number(parameters_raw.get("max_loss_pct", "25"), "MAX_LOSS_PCT")
        if max_loss < 0 or max_loss >= 100:
            max_loss = Decimal("25")
    except LocalInvestmentPilotError:
        max_loss = Decimal("25")

    references = _collect_refs(assessment)
    unknown_refs = sorted(references - source_ids)
    after_cutoff_refs = [
        source["source_id"] for source in sources
        if source["source_id"] in references and source["time_status"] == "AFTER_CUTOFF"
    ]
    return {
        "case": {
            "case_id": case["case_id"], "company": company, "market": normalized_market,
            "symbol": case["request"]["symbol"], "currency": currency, "as_of_date": cutoff.isoformat(),
            "current_position_pct": position, "venue_hint": case["security_identity"]["venue_hint"],
            "venue_hint_is_evidence": False,
        },
        "price_input": {
            "price": format(price, "f"), "currency": currency, "observation_date": observation.isoformat(),
            "known_at": known_at.isoformat(), "assurance_label": PRICE_ASSURANCE, "sources_claimed": claims,
            "pit_time_status": "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY" if not price_issues else "PRICE_NOT_PIT_QUALIFIED",
            "pit_issues": price_issues, "source_origin_verified": False, "source_use_rights_verified": False,
            "canonical_price_admission": False,
        },
        "evidence_register": sources,
        "assessment": assessment,
        "forecast_valuation": forecast,
        "decision_parameters": {
            "horizon_years": horizon, "horizon_override": override, "horizon_override_basis": override_basis,
            "horizon_selection_rationale": rationale, "required_return_annualized": format(required_return, "f"),
            "fundamental_target_annualized_return": format(FUNDAMENTAL_TARGET_ANNUALIZED_RETURN, "f"),
            "entry_return_cushion_threshold": format(BUY_ENTRY_RETURN_CUSHION_THRESHOLD, "f"),
            "max_loss_pct": format(max_loss, "f"),
        },
        "unresolved_evidence_references": unknown_refs,
        "after_cutoff_evidence_references": after_cutoff_refs,
        "notes": str(payload.get("notes") or ""),
    }


def _return_metrics(prepared: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if prepared["price_input"]["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        return None, "PRICE_NOT_PIT_QUALIFIED"
    forecast = prepared["forecast_valuation"]
    anchor = forecast.get("entry_value_reference_per_share")
    scenarios = forecast.get("scenarios") or {}
    if anchor in (None, "") or not isinstance(scenarios, Mapping) or set(scenarios) != set(SCENARIOS):
        return None, "ENTRY_REFERENCE_OR_BEAR_BASE_BULL_SCENARIOS_MISSING"
    rows: dict[str, Any] = {}
    for name in SCENARIOS:
        row = scenarios.get(name)
        if not isinstance(row, Mapping):
            return None, f"{name.upper()}_SCENARIO_MISSING"
        if row.get("probability") in (None, "") or row.get("terminal_value_per_share") in (None, "") or not str(row.get("rationale") or "").strip():
            return None, f"{name.upper()}_SCENARIO_INPUTS_INCOMPLETE"
        rows[name] = {
            "probability": str(row["probability"]),
            "terminal_value_per_share": str(row["terminal_value_per_share"]),
            "cash_distributions_per_share": str(row.get("cash_distributions_per_share", "0")),
            "probability_rationale": str(row["rationale"]),
        }
    params = prepared["decision_parameters"]
    gate = {
        "entry_price": prepared["price_input"]["price"],
        "entry_value_reference": str(anchor),
        "horizon_years": str(params["horizon_years"]),
        "horizon_override": params["horizon_override"],
        "horizon_override_basis": params["horizon_override_basis"],
        "horizon_selection_rationale": params["horizon_selection_rationale"],
        "buy_entry_return_cushion_threshold": params["entry_return_cushion_threshold"],
        "fundamental_target_annualized_return": params["fundamental_target_annualized_return"],
        "required_return_annualized": params["required_return_annualized"],
        "lineage_version": "PILOT_NON_CANONICAL_MODEL_INPUTS",
        "canonical_forecast_ref": {"status": "PILOT_NON_CANONICAL"},
        "canonical_valuation_ref": {"status": "PILOT_NON_CANONICAL"},
        "scenarios": rows,
    }
    try:
        result = calculate_return_metrics(gate, max_loss_pct=params["max_loss_pct"])
        return _safe(result), None
    except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
        return None, f"SCENARIO_CALCULATION_INCOMPLETE:{exc}"


def _decision(prepared: Mapping[str, Any], metrics: Mapping[str, Any] | None, reason: str | None) -> dict[str, Any]:
    a = prepared["assessment"]
    c = prepared["case"]
    p = prepared["price_input"]
    issues: list[str] = []
    for name in ("trust", "reality", "quality", "thesis", "market_implied_expectation", "expectation_gap", "risk"):
        valid = "INTACT" if name == "thesis" else "PASS"
        if a[name]["status"] != valid:
            issues.append(f"{name.upper()}_{a[name]['status']}")
    if a["expectation_gap"]["direction"] != "POSITIVE":
        issues.append(f"EXPECTATION_GAP_DIRECTION_{a['expectation_gap']['direction']}")
    if not prepared["evidence_register"]:
        issues.append("EVIDENCE_REGISTER_EMPTY")
    if prepared["unresolved_evidence_references"]:
        issues.append("UNRESOLVED_EVIDENCE_REFERENCES")
    if prepared["after_cutoff_evidence_references"]:
        issues.append("REFERENCED_EVIDENCE_AFTER_CUTOFF")
    if p["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        issues.append("PRICE_NOT_PIT_QUALIFIED")
    if a["trust"]["status"] == "FAIL":
        action, why = "NO-BUY", "信任审查失败，禁止新增风险；不表示自动卖出。"
    elif a["thesis"]["status"] == "BROKEN":
        action, why = "REVIEW_REQUIRED", "投资论点被标记为失效，现有持仓需要人工重新评估。"
    elif metrics is None:
        action, why = "REVIEW_REQUIRED", f"当前不能计算有效的价格/回报筛选：{reason or '输入不足'}。"
    elif not metrics.get("return_gate_pass", False):
        action = "NO-BUY" if Decimal(c["current_position_pct"]) == 0 else "REVIEW_REQUIRED"
        why = "当前价未通过回报、安全边际或 Bear 损失约束；持仓不会被自动卖出。"
    elif issues:
        action, why = "REVIEW_REQUIRED", "价格情景通过，但核心模块或证据引用仍有未解决问题。"
    else:
        action = "BUY" if Decimal(c["current_position_pct"]) == 0 else "ADD"
        why = "所提供的试运行条件通过；仍需人工复核假设与原始来源。"
    current_price_eligible = (
        metrics is not None and Decimal(p["price"]) <= Decimal(str(metrics["target_entry_price"]))
    )
    return {
        "status": PILOT_STATUS,
        "provisional_action": action,
        "reason": why,
        "gating_issues": issues,
        "price_screen_status": (
            "CURRENT_PRICE_AT_OR_BELOW_RETURN_RISK_CEILING" if current_price_eligible
            else "CURRENT_PRICE_ABOVE_RETURN_RISK_CEILING" if metrics is not None
            else "UNKNOWN"
        ),
        "human_approval_required": True,
        "formal_decision_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }


def _render_report(analysis: Mapping[str, Any]) -> str:
    c, p = analysis["case"], analysis["price_input"]
    a, f, calc, d = analysis["assessment"], analysis["forecast_valuation"], analysis["return_metrics"], analysis["decision"]
    params = analysis["decision_parameters"]
    lines = [
        f"# IIOS 本地投资研究试运行：{c['company']}（{c['symbol']}）",
        "",
        f"- 运行等级：**{PILOT_STATUS}**",
        f"- 分析截止：{c['as_of_date']}；当前价：{p['price']} {c['currency']}（观察日 {p['observation_date']}）",
        f"- 当前持仓：{c['current_position_pct']}%",
        "",
        "> 这是个人使用的本地试运行报告，不是正式 canonical Decision。人工价格/AI 分析/来源摘要未完成正式证据准入；建议只供人工审阅，不会自动下单。",
        "",
        "## 一、建议与回报筛选",
        "",
        f"- 试运行建议：**{d['provisional_action']}**",
        f"- 理由：{d['reason']}",
        f"- 当前价筛选：{d['price_screen_status']}",
        f"- 预期年化回报：{calc['expected_annualized_return'] if calc else 'UNKNOWN'}",
        f"- 15% 年化门槛：{calc['fundamental_target_pass'] if calc else 'UNKNOWN'}",
        f"- Required Return：{params['required_return_annualized']}；结果：{calc['required_return_pass'] if calc else 'UNKNOWN'}",
        f"- 共同约束下目标入场价上限：{calc['target_entry_price'] if calc else 'UNKNOWN'}",
        f"- 最大 Bear 损失约束：{params['max_loss_pct']}%",
        "",
        "## 二、Trust / Reality / Quality",
        "",
        f"- Trust：{a['trust']['status']} — {a['trust'].get('summary') or '未知'}",
        f"- Reality：{a['reality']['status']} — {a['reality'].get('summary') or '未知'}",
        f"- Quality：{a['quality']['status']} — {a['quality'].get('summary') or '未知'}",
        "",
        "## 三、Thesis 与价值驱动因素",
        "",
        f"- Thesis 状态：{a['thesis']['status']}",
        f"- 核心论点：{a['thesis'].get('core_statement') or '未知'}",
        "",
    ]
    drivers = sorted(a["value_drivers"], key=lambda x: x["rank"])
    lines.extend(
        f"{x['rank']}. {x['driver']}（{x['impact']}）：{x['rationale'] or '未提供'}"
        for x in drivers
    ) if drivers else lines.append("价值驱动因素未提供。")
    lines.extend(["", "### Thesis 失效条件"])
    lines.extend(f"- {x}" for x in a["thesis"]["break_conditions"]) if a["thesis"]["break_conditions"] else lines.append("- 未提供。")
    lines.extend(["", "### 重新评估触发器"])
    lines.extend(f"- {x}" for x in a["thesis"]["reassessment_triggers"]) if a["thesis"]["reassessment_triggers"] else lines.append("- 未提供。")
    lines.extend([
        "",
        "## 四、Forecast / Valuation",
        "",
        f"- 模型：{f['model']}；选择理由：{f['model_rationale'] or '未提供'}",
        f"- 安全边际参考价值：{f.get('entry_value_reference_per_share') or 'UNKNOWN'} {c['currency']}/股",
        f"- 情景概率是否校准：{'是' if f['probabilities_calibrated'] else '否 / 未校准'}",
        "",
        "| 情景 | 概率 | 期末每股价值 | 每股现金分配 | 理由 |",
        "|---|---:|---:|---:|---|",
    ])
    scenarios = f.get("scenarios") if isinstance(f.get("scenarios"), Mapping) else {}
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        lines.append(f"| {label} | {row.get('probability', 'UNKNOWN')} | {row.get('terminal_value_per_share', 'UNKNOWN')} | {row.get('cash_distributions_per_share', '0')} | {row.get('rationale', '未提供')} |")
    if calc:
        lines.extend([
            "",
            f"- 概率加权终值：{calc['expected_terminal_wealth']} {c['currency']}/股",
            f"- 预期总回报：{calc['expected_total_return']}",
            f"- 入场安全边际：{calc['margin_of_safety']}",
            f"- Bear 情景回报：{calc['bear_return']}",
            f"- 回报门槛入场上限：{calc['target_entry_price_for_return']}",
            f"- 风险约束入场上限：{calc.get('target_entry_price_for_risk')}",
        ])
    else:
        lines.append(f"回报计算尚未完成：{analysis['return_metrics_reason'] or '情景输入不足'}。")
    lines.extend(["", "### 估值假设"])
    lines.extend(f"- {x}" for x in f["assumptions"]) if f["assumptions"] else lines.append("- 未提供；不得将其解释为市场一致预期。")
    lines.extend([
        "",
        "## 五、MIE 与预期差",
        "",
        f"- MIE：{a['market_implied_expectation']['status']} — {a['market_implied_expectation'].get('summary') or '未知'}",
        f"- 预期差：{a['expectation_gap']['status']} / {a['expectation_gap']['direction']} — {a['expectation_gap'].get('summary') or '未知'}",
        "- 若 MIE 无法识别或缺乏历史支持，不以内部估值代替市场隐含预期。",
        "",
        "## 六、风险与来源",
        "",
        f"- 风险：{a['risk']['status']} — {a['risk'].get('summary') or '未知'}",
    ])
    lines.extend(f"- {x}" for x in a["risk"]["items"]) if a["risk"]["items"] else lines.append("- 具体风险清单未提供。")
    lines.extend([
        "",
        f"- 价格 assurance：{p['assurance_label']}；截止时点：{p['pit_time_status']}",
        "- 来源时间校验只说明日期字段与 cutoff 的关系，不证明来源真实性、原始字节或使用权。",
        "",
        "| 来源 ID | 类型 | 标题 | known_at | 时间状态 | 摘要 |",
        "|---|---|---|---|---|---|",
    ])
    if analysis["evidence_register"]:
        for row in analysis["evidence_register"]:
            lines.append(f"| {row['source_id']} | {row['source_class']} | {row['title']} | {row['known_at'] or 'UNKNOWN'} | {row['time_status']} | {row['summary']} |")
    else:
        lines.append("| — | — | 未提供来源清单 | UNKNOWN | UNKNOWN | 结论应保持审慎 |")
    lines.extend(["", "## 七、需人工处理的问题"])
    lines.extend(f"- {x}" for x in d["gating_issues"]) if d["gating_issues"] else lines.append("- 所提供的试运行门槛均通过；仍需检查原始来源和估值假设。")
    lines.extend([
        "",
        "## 八、治理边界",
        "",
        "- 不创建正式 Evidence/PIT、Forecast/Valuation Admission、Decision Admission 或 Machine Publication。",
        "- 本地 run-record 不等同于 canonical IIOS_RUN_RECEIPT。",
        "- 人工最终审批必需；自动执行关闭。",
        "",
    ])
    if analysis.get("notes"):
        lines.extend(["## 操作者备注", "", analysis["notes"], ""])
    return "\n".join(lines)


def _analyse(payload: Mapping[str, Any], run_id: str) -> tuple[dict[str, Any], str]:
    prepared = _prepare_input(payload)
    metrics, reason = _return_metrics(prepared)
    decision = _decision(prepared, metrics, reason)
    analysis = {
        "schema_version": PILOT_ANALYSIS_SCHEMA,
        "runner_version": "IIOS-LOCAL-PILOT-0.1",
        "pilot_id": run_id,
        "status": PILOT_STATUS,
        "case": prepared["case"],
        "price_input": prepared["price_input"],
        "evidence_register": prepared["evidence_register"],
        "assessment": prepared["assessment"],
        "forecast_valuation": prepared["forecast_valuation"],
        "decision_parameters": prepared["decision_parameters"],
        "return_metrics": metrics,
        "return_metrics_reason": reason,
        "decision": decision,
        "governance": {
            "status": PILOT_STATUS, "source_origin_verified": False,
            "source_use_rights_verified": False, "formal_evidence_pit_admission": False,
            "formal_forecast_created": False, "formal_valuation_admission": False,
            "formal_decision_created": False, "canonical_publication_created": False,
            "canonical_run_receipt_created": False, "human_approval_required": True,
            "execution_authorized": False, "auto_execution": False,
        },
        "notes": prepared["notes"],
    }
    return analysis, _render_report(analysis)


def _write_run(
    input_path: Path, output_root: Path, *, replay_of: str | None = None
) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    symbol = str((payload.get("case") or {}).get("symbol") or "candidate").replace(".", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"local-pilot-{symbol}-{stamp}"
    analysis, report = _analyse(payload, run_id)
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    _write_local(run_dir / "input.json", input_path.read_text(encoding="utf-8"))
    _write_local(run_dir / "analysis.json", json.dumps(_safe(analysis), ensure_ascii=False, indent=2, allow_nan=False))
    _write_local(run_dir / "report.md", report)
    receipt = {
        "receipt_schema": PILOT_RECEIPT_SCHEMA,
        "status": PILOT_STATUS,
        "pilot_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "replay_of": replay_of,
        "input_file": "input.json",
        "analysis_file": "analysis.json",
        "report_file": "report.md",
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }
    _write_local(run_dir / "pilot_receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2))
    if os.name != "nt":
        run_dir.chmod(0o700)
    return {
        "status": "PILOT_REPLAY_RECOMPUTED" if replay_of else "PILOT_CREATED",
        "pilot_id": run_id,
        "provisional_action": analysis["decision"]["provisional_action"],
        "replay_of": replay_of,
        "run_dir": str(run_dir),
        "report_path": str(run_dir / "report.md"),
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "auto_execution": False,
    }


def run_local_investment_pilot(*, input_path: str | Path, output_root: str | Path, replay_of: str | None = None) -> dict[str, Any]:
    source = _outside_repo(input_path, "PILOT_INPUT_PATH", must_exist=True)
    root = _private_dir(output_root, "PILOT_OUTPUT_ROOT")
    return _write_run(source, root, replay_of=replay_of)


def _template(
    *, company: str, symbol: str, market: str, as_of_date: str, current_position_pct: str,
    price: str, price_observation_date: str, price_known_at: str, price_source_claim: str,
) -> dict[str, Any]:
    seed = build_research_case(symbol, as_of_date, current_position_pct, market=market)
    currency = "CNY" if seed["request"]["market"] == "CN-A" else "HKD"
    _positive(price, "CURRENT_PRICE")
    observation = _date(price_observation_date, "PRICE_OBSERVATION_DATE")
    known_at = _datetime(price_known_at, "PRICE_KNOWN_AT", allow_date_only=False)
    if known_at.date() != observation:
        raise LocalInvestmentPilotError("PRICE_KNOWN_AT_DATE_MUST_MATCH_OBSERVATION_DATE")
    if not str(price_source_claim or "").strip():
        raise LocalInvestmentPilotError("PRICE_SOURCE_CLAIM_REQUIRED")
    return {
        "schema_version": PILOT_SCHEMA,
        "case": {
            "company": company, "market": seed["request"]["market"], "symbol": seed["request"]["symbol"],
            "currency": currency, "as_of_date": seed["temporal_scope"]["cutoff_date"],
            "current_position_pct": seed["decision_context"]["current_position_pct"],
        },
        "price_input": {
            "price": str(price), "currency": currency, "observation_date": observation.isoformat(),
            "known_at": known_at.isoformat(), "assurance_label": PRICE_ASSURANCE,
            "sources_claimed": [str(price_source_claim).strip()],
        },
        "evidence_register": [],
        "assessment": {
            "trust": {"status": "UNKNOWN", "summary": "尚未完成信任审查", "evidence_refs": []},
            "reality": {"status": "UNKNOWN", "summary": "尚未完成经营现实审查", "evidence_refs": []},
            "quality": {"status": "UNKNOWN", "summary": "尚未完成经济质量审查", "evidence_refs": []},
            "thesis": {"status": "UNKNOWN", "core_statement": "", "drivers": [], "break_conditions": [], "reassessment_triggers": [], "evidence_refs": []},
            "value_drivers": [],
            "market_implied_expectation": {"status": "NOT_IDENTIFIABLE", "summary": "尚未足够识别市场隐含预期", "evidence_refs": []},
            "expectation_gap": {"status": "UNKNOWN", "direction": "UNKNOWN", "summary": "尚未验证预期差", "evidence_refs": []},
            "risk": {"status": "UNKNOWN", "summary": "尚未完成风险审查", "items": []},
        },
        "forecast_valuation": {
            "model": "UNKNOWN", "model_rationale": "", "entry_value_reference_per_share": None,
            "probabilities_calibrated": False, "assumptions": [],
            "scenarios": {
                "bear": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
                "base": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
                "bull": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
            },
        },
        "decision_parameters": {
            "horizon_years": 1, "horizon_override": False, "horizon_override_basis": [],
            "horizon_selection_rationale": "默认使用 1 年年化回报；符合例外条件时才显式切换为 3 年。",
            "required_return_annualized": "0.15", "max_loss_pct": "25",
        },
        "notes": "缺失信息保留 UNKNOWN / NOT_IDENTIFIABLE，不要编造。请在截止时点内优先引用公告、财报和交易所资料。",
    }


def create_pilot_template(
    *, company: str, symbol: str, market: str, as_of_date: str, current_position_pct: str,
    price: str, price_observation_date: str, price_known_at: str, price_source_claim: str,
    template_root: str | Path,
) -> dict[str, Any]:
    root = _private_dir(template_root, "PILOT_TEMPLATE_ROOT")
    payload = _template(
        company=company, symbol=symbol, market=market, as_of_date=as_of_date,
        current_position_pct=current_position_pct, price=price, price_observation_date=price_observation_date,
        price_known_at=price_known_at, price_source_claim=price_source_claim,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    token = str(payload["case"]["symbol"]).replace(".", "-")
    input_path = root / f"pilot-input-{token}-{stamp}.json"
    prompt_path = root / f"pilot-prompt-{token}-{stamp}.md"
    _write_local(input_path, json.dumps(payload, ensure_ascii=False, indent=2))
    prompt = (
        "请依据我提供的公司原始公告/财报事实摘要与来源链接，填写这份 IIOS 试运行 JSON。"
        "保留 schema_version、case、price_input 不变，只补齐 evidence_register、assessment、forecast_valuation 和 decision_parameters。"
        "不要编造未知事实；未知写 UNKNOWN，MIE 不可识别时写 NOT_IDENTIFIABLE；情景概率若未校准请明确说明。"
        "至少覆盖 Trust、Reality、Quality、Thesis、价值驱动排序、Bear/Base/Bull 估值情景、MIE/预期差和风险/失效条件。"
        "当前价已经由人工输入，不能把 assurance_label 改成来源已验证。"
        "输出只允许完整 JSON。AI/操作者判断属于试运行输入，不是正式证据准入。"
    )
    _write_local(prompt_path, prompt + "\n\n本地输入文件：" + str(input_path) + "\n")
    return {
        "status": "PILOT_TEMPLATE_CREATED", "input_template": str(input_path),
        "analysis_prompt": str(prompt_path), "private_local_storage": True,
        "formal_decision_created": False,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local candidate-driven IIOS pilot; non-canonical.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--create-template", action="store_true")
    modes.add_argument("--input", help="run a completed private pilot input JSON")
    modes.add_argument("--replay-run", help="re-run a previous local pilot's input.json")
    parser.add_argument("--template-root", default=str(Path.home() / ".iios-private" / "local-pilot" / "inputs"))
    parser.add_argument("--output-root", default=str(Path.home() / ".iios-private" / "local-pilot" / "runs"))
    parser.add_argument("--company")
    parser.add_argument("--symbol")
    parser.add_argument("--market", default="CN-A")
    parser.add_argument("--as-of")
    parser.add_argument("--position", default="0")
    parser.add_argument("--price")
    parser.add_argument("--price-date")
    parser.add_argument("--price-known-at")
    parser.add_argument("--price-source-claim")
    args = parser.parse_args(argv)
    try:
        if args.create_template:
            required = {
                "--company": args.company, "--symbol": args.symbol, "--as-of": args.as_of,
                "--price": args.price, "--price-date": args.price_date,
                "--price-known-at": args.price_known_at, "--price-source-claim": args.price_source_claim,
            }
            missing = [key for key, value in required.items() if not value]
            if missing:
                parser.error("--create-template requires " + ", ".join(missing))
            result = create_pilot_template(
                company=args.company, symbol=args.symbol, market=args.market, as_of_date=args.as_of,
                current_position_pct=args.position, price=args.price, price_observation_date=args.price_date,
                price_known_at=args.price_known_at, price_source_claim=args.price_source_claim,
                template_root=args.template_root,
            )
        elif args.input:
            result = run_local_investment_pilot(input_path=args.input, output_root=args.output_root)
        else:
            prior = Path(args.replay_run).expanduser()
            if not prior.is_dir():
                raise LocalInvestmentPilotError("REPLAY_RUN_DIRECTORY_REQUIRED")
            result = run_local_investment_pilot(
                input_path=prior / "input.json", output_root=args.output_root, replay_of=prior.name
            )
        print(json.dumps(_safe(result), ensure_ascii=False, indent=2))
        return 0
    except (LocalInvestmentPilotError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
