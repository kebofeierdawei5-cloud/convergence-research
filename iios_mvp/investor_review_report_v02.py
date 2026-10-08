from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .engine import canonical_json, sha256_obj
from .machine_publication import validate_machine_publication

INVESTOR_REPORT_VERSION = "IIOS-INVESTOR-REVIEW-0.2"
INVESTOR_QA_VERSION = "IIOS-INVESTOR-REVIEW-QA-0.2"
LANGUAGE = "zh-CN"

MODULE_ORDER = (
    ("candidate", "Candidate / 标的"),
    ("trust", "Trust / 可信度"),
    ("quality", "Quality / 经济质量"),
    ("reality", "Reality / 经营现实"),
    ("thesis", "Thesis / 投资论点"),
    ("value_drivers", "Value Drivers / 价值驱动"),
    ("forecast", "Independent Forecast / 独立预测"),
    ("valuation", "Valuation / 估值"),
    ("mie", "Market Implied Expectation / 市场隐含预期"),
    ("expectation_gap", "Expectation Gap / 预期差"),
    ("risk", "Risk / 风险"),
    ("positioning", "Market / Positioning / 市场与筹码"),
    ("decision", "Decision / 决策"),
    ("position", "Position / 仓位"),
    ("monitoring", "Monitoring / 监控"),
    ("validation", "Validation / 验证"),
)

REQUIRED_SECTIONS = tuple(label for _, label in MODULE_ORDER) + (
    "一页决策摘要", "完整投资决策链", "人工判断边界", "数据血缘与完整性", "明确非授权"
)

ALLOWED_STATUS = {
    "PASS", "FAIL", "CONDITIONAL", "UNKNOWN", "NOT_PROVIDED",
    "NOT_RUN", "NOT_IDENTIFIABLE", "BLOCKED", "N/A", "REVIEW_REQUIRED",
    "REVALIDATION", "ADMITTED"
}

def _timestamp(value: Any, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601 timestamp") from exc
    return text

def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value

def _fmt(value: Any) -> str:
    if value is None:
        return "NOT_PROVIDED（未提供）"
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)

def _first_mapping(payload: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            return value
    return {}

def _status(node: Any, gates: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = gates.get(key)
        if value not in (None, ""):
            return str(value)
    if isinstance(node, Mapping):
        for key in keys:
            value = node.get(key)
            if value not in (None, ""):
                return str(value)
        value = node.get("status")
        if value not in (None, ""):
            return str(value)
    return "NOT_PROVIDED"

def _pretty_key(key: Any) -> str:
    return str(key).replace("_", " ")

def _render_mapping(mapping: Mapping[str, Any], indent: int = 0, max_depth: int = 2) -> list[str]:
    lines: list[str] = []
    prefix = "  " * indent
    for key, value in mapping.items():
        label = _pretty_key(key)
        if isinstance(value, Mapping) and indent < max_depth:
            lines.append(f"{prefix}- {label}:")
            lines.extend(_render_mapping(value, indent + 1, max_depth))
        elif isinstance(value, list) and indent < max_depth:
            lines.append(f"{prefix}- {label}:")
            for item in value:
                if isinstance(item, Mapping):
                    lines.append(f"{prefix}  -")
                    lines.extend(_render_mapping(item, indent + 2, max_depth))
                else:
                    lines.append(f"{prefix}  - {_fmt(item)}")
        else:
            lines.append(f"{prefix}- {label}: {_fmt(value)}")
    return lines

def _evidence_rows(chain: Any) -> list[dict[str, Any]]:
    if not isinstance(chain, list):
        return []
    rows = []
    for item in chain:
        if not isinstance(item, Mapping):
            continue
        rows.append({
            "evidence_id": item.get("evidence_id"),
            "claim_type": item.get("claim_type"),
            "source": item.get("source") or item.get("source_name") or item.get("source_id"),
            "period": item.get("period") or item.get("as_of_date"),
            "known_at": item.get("known_at") or item.get("knowledge_timestamp"),
            "purpose": item.get("purpose"),
            "provenance": item.get("provenance"),
        })
    return rows

def _scenario_summary(scenarios: Any) -> dict[str, Any]:
    if not isinstance(scenarios, Mapping):
        return {}
    result = {}
    for name in ("bear", "base", "bull"):
        item = scenarios.get(name)
        if isinstance(item, Mapping):
            result[name] = {
                "normalized_eps_cny": item.get("normalized_eps_cny"),
                "valuation_multiple": item.get("valuation_multiple"),
                "probability": item.get("probability") or item.get("prob"),
                "value_per_share": item.get("value_per_share"),
            }
    return result

def _module(name: str, label: str, status: str, source_path: str, data: Any) -> dict[str, Any]:
    return {
        "module": name,
        "label": label,
        "status": status if status in ALLOWED_STATUS else str(status),
        "source_path": source_path,
        "present": bool(data),
        "data": data if isinstance(data, (Mapping, list)) else {},
    }

def build_machine_surface(publication: Mapping[str, Any]) -> dict[str, Any]:
    validate_machine_publication(publication)
    case = publication["case"]
    payload = publication["decision_payload"]
    decision = publication["ai_decision"]
    gates = payload.get("gates") if isinstance(payload.get("gates"), Mapping) else {}
    returns = payload.get("return_metrics") if isinstance(payload.get("return_metrics"), Mapping) else {}
    trust = _first_mapping(payload, "trust", "evidence_trust")
    quality = _first_mapping(payload, "quality", "quality_gate")
    reality = _first_mapping(payload, "reality", "economic_reality", "economic_structure")
    thesis = _first_mapping(payload, "thesis", "investment_thesis")
    drivers = _first_mapping(payload, "value_driver_ranking", "value_drivers", "value_core")
    forecast = _first_mapping(payload, "forecast", "independent_forecast")
    valuation = _first_mapping(payload, "valuation", "primary_valuation")
    mie = _first_mapping(payload, "p4f_market_implied_expectation", "market_implied_expectation", "mie")
    gap = _first_mapping(payload, "expectation_gap", "expectation_gap_evaluation")
    if not gap and gates.get("expectation_gap_status") not in (None, ""):
        gap = {
            "status": gates.get("expectation_gap_status"),
            "resolution_state": gates.get("expectation_gap_resolution_state"),
            "qualification": gates.get("expectation_gap_qualification"),
        }
    risk = _first_mapping(payload, "risk")
    positioning = _first_mapping(payload, "positioning", "positioning_sizing", "market_positioning")
    rpc = decision.get("risk_portfolio_contract")
    rpc = rpc if isinstance(rpc, Mapping) else {}
    portfolio = rpc.get("portfolio") if isinstance(rpc.get("portfolio"), Mapping) else {}
    monitoring = payload.get("monitoring") if isinstance(payload.get("monitoring"), list) else []
    lifecycle = publication["lifecycle_refs"]
    validations = lifecycle.get("validation_records") if isinstance(lifecycle.get("validation_records"), list) else []

    modules = {
        "candidate": _module("candidate", "Candidate / 标的", "PASS", "case", case),
        "trust": _module("trust", "Trust / 可信度", _status(trust, gates, "trust"), "decision_payload.trust / gates.trust", trust),
        "quality": _module("quality", "Quality / 经济质量", _status(quality, gates, "quality"), "decision_payload.quality / gates.quality", quality),
        "reality": _module("reality", "Reality / 经营现实", _status(reality, gates, "reality"), "decision_payload.reality / gates.reality", reality),
        "thesis": _module("thesis", "Thesis / 投资论点", _status(thesis, gates, "thesis"), "decision_payload.thesis / gates.thesis", thesis),
        "value_drivers": _module("value_drivers", "Value Drivers / 价值驱动", _status(drivers, gates, "value_driver", "value_drivers"), "decision_payload.value_driver_ranking / value_drivers / value_core", drivers),
        "forecast": _module("forecast", "Independent Forecast / 独立预测", _status(forecast, gates, "forecast_ready", "forecast"), "decision_payload.forecast / gates.forecast", forecast),
        "valuation": _module("valuation", "Valuation / 估值", _status(valuation, gates, "valuation_ready", "valuation"), "decision_payload.valuation / gates.valuation", valuation),
        "mie": _module("mie", "Market Implied Expectation / 市场隐含预期", _status(mie, gates, "mie", "mie_status"), "decision_payload.p4f_market_implied_expectation / market_implied_expectation / mie", mie),
        "expectation_gap": _module("expectation_gap", "Expectation Gap / 预期差", _status(gap, gates, "expectation_gap"), "decision_payload.expectation_gap / gates.expectation_gap", gap),
        "risk": _module("risk", "Risk / 风险", _status(risk, gates, "risk"), "decision_payload.risk / gates.risk", risk),
        "positioning": _module("positioning", "Market / Positioning / 市场与筹码", _status(positioning, gates, "positioning", "positioning_sizing"), "decision_payload.positioning / positioning_sizing", positioning),
        "decision": _module("decision", "Decision / 决策", _status(decision, gates, "decision_status"), "ai_decision", decision),
        "position": _module("position", "Position / 仓位", "PASS" if portfolio else "NOT_PROVIDED", "ai_decision.risk_portfolio_contract.portfolio", portfolio),
        "monitoring": _module("monitoring", "Monitoring / 监控", "PASS" if monitoring or lifecycle.get("monitoring_states") else "NOT_PROVIDED", "decision_payload.monitoring / lifecycle_refs.monitoring_states", monitoring),
        "validation": _module("validation", "Validation / 验证", "PASS" if validations else "NOT_PROVIDED", "lifecycle_refs.validation_records", validations),
    }
    semantic_matrix = {name: modules[name] for name, _ in MODULE_ORDER}
    core_missing = [
        name for name in ("trust", "quality", "reality", "thesis", "value_drivers", "forecast", "valuation", "mie", "expectation_gap", "risk", "positioning")
        if (
            semantic_matrix[name]["status"] == "NOT_PROVIDED"
            or not semantic_matrix[name]["present"]
        )
    ]
    return {
        "surface_version": "IIOS-INVESTOR-SEMANTIC-SURFACE-0.2",
        "language": LANGUAGE,
        "publication_id": publication["publication_id"],
        "publication_hash": publication["publication_hash"],
        "case": case,
        "decision": {
            "action": decision.get("action"),
            "decision_status": decision.get("decision_status"),
            "investability_status": decision.get("investability_status"),
            "primary_reason": decision.get("primary_reason"),
            "current_price": decision.get("current_price"),
            "target_entry_price": decision.get("target_entry_price"),
            "human_approval_required": decision.get("human_approval_required"),
            "auto_execution": decision.get("auto_execution"),
        },
        "returns": returns,
        "scenarios": _scenario_summary(forecast.get("scenarios")),
        "evidence": _evidence_rows(payload.get("evidence_chain")),
        "semantic_matrix": semantic_matrix,
        "missing_core_modules": core_missing,
        "human_review_readiness": "READY" if not core_missing else "HUMAN_REVIEW_NOT_READY",
        "current_projection": publication["current_projection"],
        "human_approval": publication["human_approval"],
        "lifecycle_refs": publication["lifecycle_refs"],
    }

def _decision_wording(decision: Mapping[str, Any]) -> str:
    action = str(decision.get("action", ""))
    if decision.get("decision_status") == "REVIEW_REQUIRED" or action == "REVIEW_REQUIRED":
        return "进入人工复核；本报告不形成新的资金投入授权。"
    if action in {"BUY", "ADD"}:
        return "形成买入/加仓方向建议，但仍必须经过人工批准后才能进入实际执行边界。"
    if action in {"HOLD", "WATCH"}:
        return "维持持有/观察方向；本报告不产生新增资金执行授权。"
    if action in {"SELL", "REDUCE", "EXIT", "CLEAR"}:
        return "形成减仓/退出方向建议，但仍必须经过人工批准后才能实际执行。"
    return f"当前动作={_fmt(action)}；实际资金执行仍受人工批准边界约束。"

def render_investor_review_v02(publication: Mapping[str, Any], surface: Mapping[str, Any]) -> str:
    validate_machine_publication(publication)
    case = publication["case"]
    ref = publication["decision_ref"]
    decision = publication["ai_decision"]
    approval = publication["human_approval"]
    modules = surface["semantic_matrix"]
    returns = surface["returns"]
    lines = [
        f"# IIOS 投资决策人审报告 v0.2｜{case['company']}（{case['symbol']}）",
        "",
        f"> 分析截止日：{case['cutoff_date']}｜数据时点：{case['as_of_date']}｜Decision Revision：r{ref['revision']:03d}",
        "",
        "## 一页决策摘要",
        "",
        f"**当前动作：{_fmt(decision.get('action'))}。** {_decision_wording(decision)}",
        f"- Decision status：**{_fmt(decision.get('decision_status'))}**；Investability：**{_fmt(decision.get('investability_status'))}**。",
        f"- Current price：**{_fmt(decision.get('current_price'))}**；Actionable target entry：**{_fmt(decision.get('target_entry_price'))}**。",
        f"- Expected annualized return：**{_fmt(returns.get('expected_annualized_return'))}**；Required return：**{_fmt(returns.get('required_return'))}**。",
        f"- New capital allowed：**{_fmt((publication['decision_payload'].get('gates') or {}).get('new_capital_allowed'))}**；Human Approval：**{_fmt(approval.get('approval_status'))}**。",
        f"- Human-review readiness：**{surface['human_review_readiness']}**。",
        "",
        "核心原则：模块缺失不会被默认成 PASS；价格阈值、仓位包和报告本身都不能替代 canonical Decision 与 Human Approval。",
        "",
        "## 完整投资决策链",
        "",
        "Candidate → Trust → Quality → Reality → Thesis → Value Drivers → Independent Forecast → Valuation → Market Implied Expectation → Expectation Gap → Risk → Market/Positioning → Decision → Position → Monitoring → Validation",
        "",
    ]
    for name, label in MODULE_ORDER:
        lines.append(f"- **{label}**：{modules[name]['status']}")
    lines.append("")
    lines.append("这是受控阅读投影。NOT_PROVIDED / NOT_RUN / NOT_IDENTIFIABLE / BLOCKED 均明确保留，不被隐式填充。")
    lines.append("")

    def add_module(title: str, name: str, notes: list[str] | None = None) -> None:
        mod = modules[name]
        lines.extend([f"## {title}", "", f"状态：**{mod['status']}**", f"来源路径：{mod['source_path']}"])
        if mod["present"] and isinstance(mod["data"], Mapping):
            lines.extend(_render_mapping(mod["data"]))
        elif mod["present"] and isinstance(mod["data"], list):
            for item in mod["data"]:
                lines.append(f"- {_fmt(item)}")
        else:
            lines.append("- NOT_PROVIDED（canonical publication 未提供该模块的结构化数据）")
        if notes:
            lines.extend(notes)
        lines.append("")

    add_module("Candidate / 标的", "candidate")
    add_module("Trust / 可信度", "trust", ["- Trust 优先于估值与仓位；Trust 不足时，下游结果不能越权。"])
    add_module("Quality / 经济质量", "quality", ["- 应回答商业模式、竞争优势、资本回报、现金流质量和资本配置；估值不能替代 Quality。"])
    add_module("Reality / 经营现实", "reality", ["- 关键事实应能追溯 source / period / known_at / cutoff / provenance；缺失时不补写。"])
    add_module("Thesis / 投资论点", "thesis", ["- Thesis 回答为什么值得持有；Falsifiers 回答什么会证明 Thesis 错误。"])
    add_module("Value Drivers / 价值驱动", "value_drivers", ["- 明确周期、成长、资本回报和估值因素分别怎样影响价值。"])
    add_module("Independent Forecast / 独立预测", "forecast")
    scenarios = surface["scenarios"]
    lines.extend(["### Bear / Base / Bull", ""])
    if scenarios:
        for name in ("bear", "base", "bull"):
            item = scenarios.get(name, {})
            lines.append(f"- {name.upper()}：EPS={_fmt(item.get('normalized_eps_cny'))}；Multiple={_fmt(item.get('valuation_multiple'))}；Probability={_fmt(item.get('probability'))}；Value/Share={_fmt(item.get('value_per_share'))}")
    else:
        lines.append("- NOT_PROVIDED")
    lines.append("")
    add_module("Valuation / 估值", "valuation", ["- 估值需要让投资者看见模型、关键假设、正常化逻辑与敏感性；本报告不重新计算另一套价格。"])
    add_module("Market Implied Expectation / 市场隐含预期", "mie", ["- 市场价格已知不等于 MIE 可识别；识别性、稳定性和 decision-grade 必须由上游语义明确提供。"])
    add_module("Expectation Gap / 预期差", "expectation_gap", ["- 需要明确市场隐含假设、Independent Forecast 与差异来源；缺失即保留缺失。"])
    add_module("Risk / 风险", "risk", [f"- Expected annualized return={_fmt(returns.get('expected_annualized_return'))}；Required return={_fmt(returns.get('required_return'))}；Margin of safety={_fmt(returns.get('margin_of_safety'))}。"])
    add_module("Market / Positioning / 市场与筹码", "positioning", ["- 筹码只影响 timing、sizing 和风险预算，不得改写基本面 Decision。"])
    add_module("Decision / 决策", "decision", [f"- Primary reason：**{_fmt(decision.get('primary_reason'))}**。"])
    add_module("Position / 仓位", "position", ["- 仓位包不能覆盖 Trust、Decision Status 或 Human Approval。"])
    add_module("Monitoring / 监控", "monitoring", ["- 触发关键经营偏离、Trust/Evidence 失效或 Thesis Break 时，应重新进入 Decision Revision。"])
    add_module("Validation / 验证", "validation", ["- Validation 应复核 Forecast、Valuation、Decision 与 Thesis 的兑现情况，而不是只看股价。"])

    lines += [
        "## 人工判断边界", "",
        f"- Human Approval：**{_fmt(approval.get('approval_status'))}**；Approved：**{_fmt(approval.get('approved'))}**。",
        "- Report PASS / CI PASS / Publication PASS 都不等于 Human Approval。",
        "- AI/系统提供结构化建议，Human 负责最终批准与执行。",
        "",
        "## 数据血缘与完整性", "",
        f"- Machine Publication：{publication['publication_id']}。",
        f"- Publication Hash：{publication['publication_hash']}。",
        f"- Decision Revision：{ref['decision_id']} / r{ref['revision']:03d}。",
        f"- Snapshot Hash：{ref['snapshot_hash']}。",
        f"- Revision Hash：{ref['revision_hash']}。",
        f"- Evidence observations：{len(surface['evidence'])} 条。",
        "",
        "### Evidence / PIT provenance", "",
    ]
    if surface["evidence"]:
        for row in surface["evidence"]:
            lines.append(f"- {_fmt(row.get('evidence_id'))}｜claim={_fmt(row.get('claim_type'))}｜source={_fmt(row.get('source'))}｜period={_fmt(row.get('period'))}｜known_at={_fmt(row.get('known_at'))}｜purpose={_fmt(row.get('purpose'))}")
    else:
        lines.append("- NOT_PROVIDED")
    lines += [
        "",
        "## 明确非授权", "",
        "本报告是 Machine Publication 的投资者阅读投影，不是第二个 Decision Source。",
        "",
        "不存在“到价即可自动买入”的隐含授权。BUY/ADD/REDUCE/EXIT 必须受 canonical Decision、Risk/Portfolio 与 Human Approval 约束。",
        "",
        "本报告不会把缺失的 Quality、Reality、MIE、Expectation Gap、Positioning 或其他模块补写成结论。",
        "",
    ]
    return "\\n".join(lines)

def build_investor_review_report_v02(*, publication: Mapping[str, Any], generated_at: str) -> dict[str, Any]:
    validate_machine_publication(publication)
    generated_at = _timestamp(generated_at, "generated_at")
    surface = build_machine_surface(publication)
    markdown = render_investor_review_v02(publication, surface)
    machine_core = {
        "report_version": INVESTOR_REPORT_VERSION,
        "generated_at": generated_at,
        "publication_id": publication["publication_id"],
        "publication_hash": publication["publication_hash"],
        "decision_id": publication["decision_ref"]["decision_id"],
        "revision": publication["decision_ref"]["revision"],
        "case_id": publication["decision_ref"]["case_id"],
        "cutoff_date": publication["decision_ref"]["cutoff_date"],
        "language": LANGUAGE,
        "semantic_surface": surface,
    }
    machine_hash = sha256_obj(machine_core)
    machine_report = {**machine_core, "machine_report_id": f'{publication["publication_id"]}-machine-{machine_hash[:16]}', "machine_report_hash": machine_hash}
    human_core = {**machine_core, "machine_report_hash": machine_hash, "markdown": markdown}
    human_hash = sha256_obj(human_core)
    return {
        "report_version": INVESTOR_REPORT_VERSION,
        "generated_at": generated_at,
        "publication_id": publication["publication_id"],
        "publication_hash": publication["publication_hash"],
        "decision_id": publication["decision_ref"]["decision_id"],
        "revision": publication["decision_ref"]["revision"],
        "case_id": publication["decision_ref"]["case_id"],
        "cutoff_date": publication["decision_ref"]["cutoff_date"],
        "language": LANGUAGE,
        "machine_report_hash": machine_hash,
        "human_report_hash": human_hash,
        "machine_report": machine_report,
        "markdown": markdown,
        "report_id": f'{publication["publication_id"]}-investor-v02-{human_hash[:16]}',
        "report_hash": human_hash,
    }

def validate_investor_review_report_v02(record: Any) -> None:
    required = {
        "report_version", "generated_at", "publication_id", "publication_hash",
        "decision_id", "revision", "case_id", "cutoff_date", "language",
        "machine_report_hash", "human_report_hash", "machine_report",
        "markdown", "report_id", "report_hash",
    }
    if not isinstance(record, Mapping) or set(record) != required:
        raise ValueError("investor_review_report_v02 fields are invalid")
    if record["report_version"] != INVESTOR_REPORT_VERSION or record["language"] != LANGUAGE:
        raise ValueError("investor_review_report_v02 version/language mismatch")
    _timestamp(record["generated_at"], "generated_at")
    if any(not isinstance(record[k], str) or len(record[k]) != 64 for k in ("publication_hash", "machine_report_hash", "human_report_hash", "report_hash")):
        raise ValueError("investor_review_report_v02 hash invalid")
    if not isinstance(record["machine_report"], Mapping):
        raise ValueError("machine_report must be an object")
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in record["markdown"]:
            raise ValueError(f"investor_review_report_v02 missing required section: {section}")
    machine_core = {k: record["machine_report"][k] for k in record["machine_report"] if k not in {"machine_report_id", "machine_report_hash"}}
    expected_machine_hash = sha256_obj(machine_core)
    if record["machine_report_hash"] != expected_machine_hash or record["machine_report"]["machine_report_hash"] != record["machine_report_hash"]:
        raise ValueError("machine_report hash mismatch")
    human_core = {
        "report_version": record["report_version"], "generated_at": record["generated_at"],
        "publication_id": record["publication_id"], "publication_hash": record["publication_hash"],
        "decision_id": record["decision_id"], "revision": record["revision"],
        "case_id": record["case_id"], "cutoff_date": record["cutoff_date"],
        "language": record["language"], "machine_report_hash": record["machine_report_hash"],
        "markdown": record["markdown"],
    }
    if record["report_hash"] != sha256_obj(human_core) or record["human_report_hash"] != record["report_hash"]:
        raise ValueError("human report hash mismatch")

def qa_investor_review_v02(*, publication: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "publication_integrity": "PASS", "publication_binding": "PASS",
        "machine_surface_integrity": "PASS", "human_surface_integrity": "PASS",
        "deterministic_render_replay": "PASS", "required_sections": "PASS",
        "semantic_matrix_complete": "PASS", "explicit_absence_handling": "PASS",
        "decision_fidelity": "PASS", "human_boundary": "PASS", "non_authority": "PASS",
    }
    issues: list[str] = []
    try:
        validate_machine_publication(publication)
    except Exception as exc:
        checks["publication_integrity"] = "FAIL"; issues.append(f"publication_integrity: {exc}")
    try:
        machine = report.get("machine_report")
        if not isinstance(machine, Mapping):
            raise ValueError("machine_report missing")
        machine_core = {k: machine[k] for k in machine if k not in {"machine_report_id", "machine_report_hash"}}
        expected = sha256_obj(machine_core)
        if machine.get("machine_report_hash") != expected or report.get("machine_report_hash") != expected:
            raise ValueError("machine surface hash mismatch")
    except Exception as exc:
        checks["machine_surface_integrity"] = "FAIL"; issues.append(f"machine_surface_integrity: {exc}")
    try:
        validate_investor_review_report_v02(report)
    except Exception as exc:
        checks["human_surface_integrity"] = "FAIL"; issues.append(f"human_surface_integrity: {exc}")
    ref = publication.get("decision_ref") or {}
    bindings = {
        "publication_id": publication.get("publication_id"), "publication_hash": publication.get("publication_hash"),
        "decision_id": ref.get("decision_id"), "revision": ref.get("revision"),
        "case_id": ref.get("case_id"), "cutoff_date": ref.get("cutoff_date"),
    }
    if any(report.get(k) != v for k, v in bindings.items()):
        checks["publication_binding"] = "FAIL"; issues.append("publication_binding: exact Machine Publication mismatch")
    try:
        regenerated = build_investor_review_report_v02(publication=publication, generated_at=report["generated_at"])
        if canonical_json(regenerated) != canonical_json(report):
            checks["deterministic_render_replay"] = "FAIL"; issues.append("deterministic_render_replay: regenerated report differs")
    except Exception as exc:
        checks["deterministic_render_replay"] = "FAIL"; issues.append(f"deterministic_render_replay: {exc}")
    markdown = str(report.get("markdown", ""))
    missing_sections = [section for section in REQUIRED_SECTIONS if f"## {section}" not in markdown]
    if missing_sections:
        checks["required_sections"] = "FAIL"; issues.append("required_sections: " + ", ".join(missing_sections))
    surface = report.get("machine_report", {}).get("semantic_surface", {})
    matrix = surface.get("semantic_matrix", {}) if isinstance(surface, Mapping) else {}
    expected_names = [name for name, _ in MODULE_ORDER]
    if set(matrix) != set(expected_names):
        checks["semantic_matrix_complete"] = "FAIL"; issues.append("semantic_matrix_complete: required module set mismatch")
    elif any(matrix[name].get("status") not in ALLOWED_STATUS for name in expected_names):
        checks["semantic_matrix_complete"] = "FAIL"; issues.append("semantic_matrix_complete: invalid status")
    if surface.get("missing_core_modules") and "NOT_PROVIDED" not in str(report.get("markdown", "")):
        checks["explicit_absence_handling"] = "FAIL"; issues.append("explicit_absence_handling: missing modules are silent")
    decision = publication.get("ai_decision") or {}
    markdown = str(report.get("markdown", ""))
    if str(decision.get("action", "")) not in markdown or str(decision.get("primary_reason", "")) not in markdown:
        checks["decision_fidelity"] = "FAIL"; issues.append("decision_fidelity: canonical action/reason missing")
    approval = publication.get("human_approval") or {}
    if str(approval.get("approval_status", "")) not in markdown:
        checks["human_boundary"] = "FAIL"; issues.append("human_boundary: approval status missing")
    if "不能下单" not in markdown or "Human Approval" not in markdown:
        checks["non_authority"] = "FAIL"; issues.append("non_authority: explicit non-authority missing")
    status = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"
    core = {
        "qa_version": INVESTOR_QA_VERSION, "qa_id": f'{report["report_id"]}-qa',
        "report_id": report["report_id"], "report_hash": report["report_hash"],
        "publication_id": publication["publication_id"], "publication_hash": publication["publication_hash"],
        "qa_status": status, "checks": checks, "issues": issues,
        "policy_effect": "REPORT_ONLY_PROJECTION",
    }
    return {**core, "qa_hash": sha256_obj(core)}

def validate_investor_review_qa_v02(record: Any) -> None:
    required = {"qa_version", "qa_id", "report_id", "report_hash", "publication_id", "publication_hash", "qa_status", "checks", "issues", "policy_effect", "qa_hash"}
    if not isinstance(record, Mapping) or set(record) != required:
        raise ValueError("investor_review_qa_v02 fields are invalid")
    if record["qa_version"] != INVESTOR_QA_VERSION or record["qa_status"] not in {"PASS", "FAIL"}:
        raise ValueError("investor_review_qa_v02 version/status invalid")
    expected_checks = {"publication_integrity", "publication_binding", "machine_surface_integrity", "human_surface_integrity", "deterministic_render_replay", "required_sections", "semantic_matrix_complete", "explicit_absence_handling", "decision_fidelity", "human_boundary", "non_authority"}
    if not isinstance(record["checks"], Mapping) or set(record["checks"]) != expected_checks:
        raise ValueError("investor_review_qa_v02 checks invalid")
    if any(v not in {"PASS", "FAIL"} for v in record["checks"].values()):
        raise ValueError("investor_review_qa_v02 check status invalid")
    expected_status = "PASS" if all(v == "PASS" for v in record["checks"].values()) else "FAIL"
    if record["qa_status"] != expected_status or record["policy_effect"] != "REPORT_ONLY_PROJECTION":
        raise ValueError("investor_review_qa_v02 status/policy mismatch")
    core = {k: record[k] for k in required if k != "qa_hash"}
    if record["qa_hash"] != sha256_obj(core):
        raise ValueError("investor_review_qa_v02 hash mismatch")

def _write_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"immutable artifact collision: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

def write_investor_review_report_v02(root: str | Path, *, publication_path: str | Path, generated_at: str) -> tuple[Path, Path, Path, Path]:
    publication = _load_json(publication_path)
    validate_machine_publication(publication)
    report = build_investor_review_report_v02(publication=publication, generated_at=generated_at)
    validate_investor_review_report_v02(report)
    qa = qa_investor_review_v02(publication=publication, report=report)
    validate_investor_review_qa_v02(qa)
    if qa["qa_status"] != "PASS":
        raise ValueError("investor review v0.2 quality gate failed: " + "; ".join(qa["issues"]))
    root_path = Path(root)
    rp = root_path / f'{report["report_hash"]}.investor-review-v02.json'
    mp = root_path / f'{report["machine_report_hash"]}.investor-review-v02.machine.json'
    hp = root_path / f'{report["human_report_hash"]}.investor-review-v02.md'
    qp = root_path / f'{qa["qa_hash"]}.investor-review-v02-qa.json'
    _write_immutable(rp, json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8") + b"\\n")
    _write_immutable(mp, json.dumps(report["machine_report"], ensure_ascii=False, indent=2).encode("utf-8") + b"\\n")
    _write_immutable(hp, report["markdown"].encode("utf-8"))
    _write_immutable(qp, json.dumps(qa, ensure_ascii=False, indent=2).encode("utf-8") + b"\\n")
    return rp, mp, hp, qp
