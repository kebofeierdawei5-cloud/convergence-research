from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .engine import canonical_json, sha256_obj
from .machine_publication import validate_machine_publication

INVESTOR_REPORT_VERSION = "IIOS-INVESTOR-REVIEW-0.1"
INVESTOR_QA_VERSION = "IIOS-INVESTOR-REVIEW-QA-0.1"

REQUIRED_SECTIONS = (
    "一页结论",
    "投资结论与授权状态",
    "公司与分析边界",
    "可信度与证据",
    "基本面、预测与估值",
    "收益、风险与仓位",
    "核心逻辑与反证",
    "监控与复核",
    "人工判断边界",
    "数据血缘与完整性",
    "明确非授权",
)

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
        return "暂无 / 未形成该项授权"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(", ", ": "))
    return str(value)

def _pct(value: Any) -> str:
    if value is None:
        return "暂无"
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return _fmt(value)
    if -1.5 <= number <= 1.5:
        return f"{number * 100:.2f}%"
    return f"{number:.2f}%"

def _entry_zone(value: Any) -> str:
    if isinstance(value, list) and len(value) == 2:
        return f"{_fmt(value[0])}–{_fmt(value[1])}"
    return _fmt(value)

def _decision_wording(decision: Mapping[str, Any]) -> str:
    action = str(decision.get("action", ""))
    status = str(decision.get("decision_status", ""))
    if status == "REVIEW_REQUIRED" or action == "REVIEW_REQUIRED":
        return "进入人工复核；本报告本身不形成新的资金投入授权。"
    if action in {"BUY", "ADD"}:
        return "形成买入/加仓建议，但仍必须经过人工批准后才能产生实际执行授权。"
    if action in {"HOLD", "WATCH"}:
        return "维持持有/观察建议；本报告不产生新增资金执行授权。"
    if action in {"SELL", "REDUCE", "CLEAR"}:
        return "形成减仓/清仓方向建议，但仍必须经过人工批准后才能实际执行。"
    return f"当前动作={_fmt(action)}；实际资金执行仍受人工批准边界约束。"

def render_investor_review_report(publication: Mapping[str, Any]) -> str:
    validate_machine_publication(publication)
    case = publication["case"]
    ref = publication["decision_ref"]
    decision = publication["ai_decision"]
    payload = publication["decision_payload"]
    approval = publication["human_approval"]
    current = publication["current_projection"]
    lifecycle = publication["lifecycle_refs"]
    gates = payload.get("gates") or {}
    returns = payload.get("return_metrics") or {}
    forecast = payload.get("forecast") or {}
    valuation = payload.get("valuation") or {}
    risk = payload.get("risk") or {}
    monitoring = payload.get("monitoring") or []
    rpc = decision.get("risk_portfolio_contract") or {}
    portfolio = rpc.get("portfolio") if isinstance(rpc, Mapping) else {}
    package = portfolio.get("buy_add_package") if isinstance(portfolio, Mapping) else {}
    scenarios = forecast.get("scenarios") or {}
    style = forecast.get("style_weighting") or {}
    values = valuation.get("scenario_values_per_share") or {}

    lines = [
        f"# IIOS 投资决策人审报告｜{case['company']}（{case['symbol']}）",
        "",
        f"> 分析截止日：{case['cutoff_date']}｜数据时点：{case['as_of_date']}｜决策修订：r{ref['revision']:03d}",
        "",
        "## 一页结论",
        "",
        f"**当前动作：{_fmt(decision.get('action'))}。** {_decision_wording(decision)}",
        "",
        f"- Trust Gate：**{_fmt(gates.get('trust'))}**；基本面预测：{_fmt(gates.get('forecast'))}；估值：{_fmt(gates.get('valuation'))}。",
        f"- 新资金投入授权：**{_fmt(gates.get('new_capital_allowed'))}**；仓位/择时权限：**{_fmt(gates.get('positioning_sizing_permission'))}**。",
        f"- 当前市场价格：**{_fmt(decision.get('current_price'))}**。",
        f"- 可执行目标入场价：**{_fmt(decision.get('target_entry_price'))}**。",
        f"- 收益/风险计算阈值：**{_fmt(returns.get('target_entry_price'))}**。",
        f"- 预计年化回报：**{_pct(returns.get('expected_annualized_return'))}**；Margin of Safety：**{_pct(returns.get('margin_of_safety'))}**。",
        "",
        "最重要的一句话：本次报告的阈值价格不能被理解为“到价即可买入”；只有当 canonical Decision 明确形成可执行入场授权，并经过人工批准后，才可能进入实际执行边界。",
        "",
        "## 投资结论与授权状态",
        "",
        "### 1. 为什么当前不是直接执行",
        _decision_wording(decision),
        "",
        f"- 决策状态：**{_fmt(decision.get('decision_status'))}**。",
        f"- 投资状态：**{_fmt(decision.get('investability_status'))}**。",
        f"- 首要原因：**{_fmt(decision.get('primary_reason'))}**。",
        f"- 是否要求人工批准：**{_fmt(decision.get('human_approval_required'))}**。",
        f"- 自动执行：**{_fmt(decision.get('auto_execution'))}**。",
        f"- 当前投影状态：**{_fmt(current.get('status'))}**。",
        "",
        "### 2. 价格字段必须区分",
        f"- Actionable Target Entry Price：{_fmt(decision.get('target_entry_price'))}。它才是可执行目标入场价；若为空，表示本次没有形成该授权。",
        f"- Return/Risk Threshold：{_fmt(returns.get('target_entry_price'))}。这是收益/风险条件计算出的阈值，不等于买入授权。",
        f"- Entry Zone：{_entry_zone(package.get('entry_zone') if isinstance(package, Mapping) else None)}。这是仓位包参考区间，不凌驾于 Decision 的资金授权。",
        "",
        "因此，不能把仓位包中的入场区间、收益/风险阈值或风险包建议仓位单独理解为买入许可。",
        "",
        "## 公司与分析边界",
        "",
        f"- 公司：**{case['company']}**。",
        f"- 市场/标的：**{case.get('market', 'CN-A')} / {case['symbol']}**。",
        f"- 分析截止日：**{case['cutoff_date']}**。",
        f"- 当前决策修订：**r{ref['revision']:03d}**。",
        f"- 证据链：**{len(payload.get('evidence_chain') or [])} 条 canonical observations**。",
        f"- 决策范围：**{_fmt(payload.get('decision_scope'))}**。",
        "",
        "本报告不是重新做一次独立研究，而是把已经通过 canonical admission 的 Decision、Forecast、Valuation、Return/Risk/Portfolio 结果转换成适合投资者阅读的中文解释层。它不自行改变任何经济判断。",
        "",
        "## 可信度与证据",
        "",
        f"### Trust Gate：**{_fmt(gates.get('trust'))}**",
        "",
        "Trust Gate 是本次决策最优先的边界。只要 Trust 未达到允许直接行动的状态，下游的高质量预测或漂亮估值都不能自动越过这一边界。",
        "",
        f"- Canonical evidence observations：**{len(payload.get('evidence_chain') or [])}**。",
        f"- Engine version：**{_fmt(ref.get('engine_version'))}**。",
        f"- Decision Revision Hash：{ref['revision_hash']}。",
        f"- Snapshot Hash：{ref['snapshot_hash']}。",
        "",
        "报告中的数字与结论来自 canonical Decision Publication；人审版不创造新的事实，也不替换原始证据来源。",
        "",
        "## 基本面、预测与估值",
        "",
        "### 预测",
        f"- 方法：**{_fmt(forecast.get('method'))}**。",
        f"- 预测期限：**{_fmt(forecast.get('horizon_years'))} 年**。",
        f"- 风格权重：周期 **{_fmt(style.get('cyclical'))}** / 成长 **{_fmt(style.get('growth'))}**。",
        f"- Base normalized EPS：**{_fmt((scenarios.get('base') or {}).get('normalized_eps_cny'))} 元**。",
        f"- Base valuation multiple：**{_fmt((scenarios.get('base') or {}).get('valuation_multiple'))}x**。",
        f"- Bear / Base / Bull EPS：**{_fmt((scenarios.get('bear') or {}).get('normalized_eps_cny'))} / {_fmt((scenarios.get('base') or {}).get('normalized_eps_cny'))} / {_fmt((scenarios.get('bull') or {}).get('normalized_eps_cny'))} 元**。",
        "",
        "### 估值",
        f"- 主模型：**{_fmt(valuation.get('primary_model'))}**。",
        f"- Bear / Base / Bull 每股价值：**{_fmt(values.get('bear'))} / {_fmt(values.get('base'))} / {_fmt(values.get('bull'))} 元**。",
        "",
        "这些数字属于 canonical model assumptions / outputs，不应被误写成市场一致预期，也不应在本报告里重新计算出另一个版本。",
        "",
        "### 基本面结论",
        f"- Forecast Gate：**{_fmt(gates.get('forecast'))}**。",
        f"- Valuation Gate：**{_fmt(gates.get('valuation'))}**。",
        f"- Fundamental Target：**{_fmt(returns.get('fundamental_target_pass'))}**。",
        "",
        "## 收益、风险与仓位",
        "",
        f"- Expected Total Return：**{_pct(returns.get('expected_total_return'))}**。",
        f"- Expected Annualized Return：**{_pct(returns.get('expected_annualized_return'))}**。",
        f"- Entry Return Cushion：**{_pct(returns.get('entry_return_cushion'))}**。",
        f"- Required Return：**{_pct(returns.get('required_return'))}**。",
        f"- Required Return 条件通过：**{_fmt(returns.get('required_return_pass'))}**。",
        f"- Margin of Safety：**{_pct(returns.get('margin_of_safety'))}**。",
        f"- 最大损失边界：**{_fmt(risk.get('max_loss_pct'))}%**。",
        "",
        "### 当前仓位包",
        f"- 当前仓位：**{_fmt(portfolio.get('position_pct'))}%**。",
        f"- 仓位包可加仓：**{_fmt(portfolio.get('can_add'))}**。",
        f"- 初始仓位：**{_fmt(package.get('initial_position_pct'))}%**。",
        f"- 目标仓位：**{_fmt(package.get('target_position_pct'))}%**。",
        f"- 最大仓位：**{_fmt(package.get('max_position_pct'))}%**。",
        "",
        "仓位包是 Risk/Portfolio 层的建议输入；它不能覆盖 Trust Gate、Decision Status 或 Human Approval 边界。",
        "",
        "## 核心逻辑与反证",
        "",
        "### 核心逻辑",
        "- 当前系统的首要判断链是：Trust → 基本面/Forecast → Valuation → Return/Risk → Portfolio → Decision。",
        f"- 本次首要原因：**{_fmt(decision.get('primary_reason'))}**。",
        "",
        "### Thesis Break / 反证条件",
    ]

    falsifiers = (payload.get("thesis") or {}).get("falsifiers", []) or []
    if falsifiers:
        lines.extend(f"- {item}" for item in falsifiers)
    else:
        lines.append("- 当前 canonical Decision 未提供额外反证条目；不能据此推断风险不存在。")

    lines += [
        "",
        "## 监控与复核",
        "",
    ]
    if monitoring:
        for item in monitoring:
            lines.append(f"- **{_fmt(item.get('metric'))}**：{_fmt(item.get('condition'))}")
    else:
        lines.append("- 当前没有额外的 canonical monitoring 条目。")
    lines += [
        "",
        "出现 Thesis Break、关键经营数据显著偏离预测、Trust/Evidence 失效、估值假设失真或其他 canonical trigger 时，应重新进入 Decision Revision / Review，而不是沿用旧结论。",
        "",
        "## 人工判断边界",
        "",
        f"- 当前 Human Approval：**{_fmt(approval.get('approval_status'))}**。",
        "- AI/系统提供的是标准化投资决策建议，不是最终投资授权。",
        "- 人工需要判断：事实与假设是否足够可信、当前组合约束是否满足、风险是否可接受，以及是否批准进入实际执行。",
        "- 报告发布、报告阅读、CI PASS 都不能替代 Human Approval。",
        "- 本报告不能修改 Decision Revision、Monitoring 或 Validation，也不能下单或打开自动执行。",
        "",
        "### 本次人工验收应该回答的不是“我是否同意买入”，而是：",
        "",
        "1. 我是否能在一屏内找到当前动作、不能做什么以及为什么？",
        "2. 我能否区分事实、模型假设、阈值价格与真正的执行授权？",
        "3. 我能否理解 Trust Gate、Forecast、Valuation 与最终 Decision 之间的因果关系？",
        "4. 我能否知道什么情况下必须重新审查？",
        "",
        "## 数据血缘与完整性",
        "",
        f"- Machine Publication ID：{publication['publication_id']}。",
        f"- Machine Publication Hash：{publication['publication_hash']}。",
        f"- Publication-bound Decision Revision：{ref['decision_id']} / r{ref['revision']:03d}。",
        f"- Trigger contracts referenced：{len(lifecycle['trigger_contracts'])}。",
        f"- Monitoring states referenced：{len(lifecycle['monitoring_states'])}。",
        f"- Validation records referenced：{len(lifecycle['validation_records'])}。",
        "",
        "说明：本中文人审报告只是 Machine Publication 的受控阅读投影。它没有独立的经济计算权，也没有投资执行权。",
        "",
        "## 明确非授权",
        "",
        "本报告不是订单，也不是自动交易指令。",
        "",
        "即使某个价格、估值或仓位包看起来有吸引力，只要 canonical Decision 没有形成相应授权，并且 Human Approval 尚未完成，都不能将其解释为可直接执行的买入/加仓指令。",
        "",
    ]
    return "\\n".join(lines)

def build_investor_review_report(*, publication: Mapping[str, Any], generated_at: str) -> dict[str, Any]:
    validate_machine_publication(publication)
    generated_at = _timestamp(generated_at, "generated_at")
    core = {
        "report_version": INVESTOR_REPORT_VERSION,
        "generated_at": generated_at,
        "publication_id": publication["publication_id"],
        "publication_hash": publication["publication_hash"],
        "decision_id": publication["decision_ref"]["decision_id"],
        "revision": publication["decision_ref"]["revision"],
        "case_id": publication["decision_ref"]["case_id"],
        "cutoff_date": publication["decision_ref"]["cutoff_date"],
        "language": "zh-CN",
        "markdown": render_investor_review_report(publication),
    }
    report_hash = sha256_obj(core)
    return {
        **core,
        "report_id": f'{publication["publication_id"]}-investor-review-{report_hash[:16]}',
        "report_hash": report_hash,
    }

def validate_investor_review_report(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("investor_review_report must be an object")
    required = {
        "report_version", "generated_at", "publication_id", "publication_hash",
        "decision_id", "revision", "case_id", "cutoff_date", "language",
        "markdown", "report_id", "report_hash",
    }
    if set(record) != required:
        raise ValueError("investor_review_report fields are invalid")
    if record["report_version"] != INVESTOR_REPORT_VERSION:
        raise ValueError("investor_review_report version mismatch")
    if record["language"] != "zh-CN":
        raise ValueError("investor_review_report language mismatch")
    _timestamp(record["generated_at"], "generated_at")
    for field in ("publication_hash", "report_hash"):
        if not isinstance(record[field], str) or len(record[field]) != 64:
            raise ValueError(f"investor_review_report {field} invalid")
    if not isinstance(record["revision"], int) or record["revision"] < 1:
        raise ValueError("investor_review_report revision invalid")
    if not isinstance(record["markdown"], str) or not record["markdown"].strip():
        raise ValueError("investor_review_report markdown invalid")
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in record["markdown"]:
            raise ValueError(f"investor_review_report missing required section: {section}")
    core = {k: record[k] for k in required if k not in {"report_id", "report_hash"}}
    if record["report_hash"] != sha256_obj(core):
        raise ValueError("investor_review_report hash mismatch")
    expected_id = f'{record["publication_id"]}-investor-review-{record["report_hash"][:16]}'
    if record["report_id"] != expected_id:
        raise ValueError("investor_review_report id mismatch")

def qa_investor_review_report(*, publication: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "publication_integrity": "PASS",
        "publication_binding": "PASS",
        "report_integrity": "PASS",
        "deterministic_render_replay": "PASS",
        "required_sections": "PASS",
        "decision_fidelity": "PASS",
        "human_boundary": "PASS",
        "non_authority": "PASS",
    }
    issues: list[str] = []
    try:
        validate_machine_publication(publication)
    except Exception as exc:
        checks["publication_integrity"] = "FAIL"
        issues.append(f"publication_integrity: {exc}")
    try:
        validate_investor_review_report(report)
    except Exception as exc:
        checks["report_integrity"] = "FAIL"
        issues.append(f"report_integrity: {exc}")
    ref = publication.get("decision_ref") or {}
    if (
        report.get("publication_id") != publication.get("publication_id")
        or report.get("publication_hash") != publication.get("publication_hash")
        or report.get("decision_id") != ref.get("decision_id")
        or report.get("revision") != ref.get("revision")
        or report.get("case_id") != ref.get("case_id")
        or report.get("cutoff_date") != ref.get("cutoff_date")
    ):
        checks["publication_binding"] = "FAIL"
        issues.append("publication_binding: exact Machine Publication mismatch")
    try:
        regenerated = build_investor_review_report(
            publication=publication,
            generated_at=report["generated_at"],
        )
        if canonical_json(regenerated) != canonical_json(report):
            checks["deterministic_render_replay"] = "FAIL"
            issues.append("deterministic_render_replay: regenerated report differs")
    except Exception as exc:
        checks["deterministic_render_replay"] = "FAIL"
        issues.append(f"deterministic_render_replay: {exc}")
    markdown = str(report.get("markdown", ""))
    decision = publication.get("ai_decision") or {}
    if str(decision.get("action", "")) not in markdown or str(decision.get("primary_reason", "")) not in markdown:
        checks["decision_fidelity"] = "FAIL"
        issues.append("decision_fidelity: canonical action/reason missing")
    approval = publication.get("human_approval") or {}
    if str(approval.get("approval_status", "")) not in markdown:
        checks["human_boundary"] = "FAIL"
        issues.append("human_boundary: approval status missing")
    if "不能下单" not in markdown or "Human Approval" not in markdown:
        checks["non_authority"] = "FAIL"
        issues.append("non_authority: explicit non-authority boundary missing")
    status = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"
    core = {
        "qa_version": INVESTOR_QA_VERSION,
        "qa_id": f'{report["report_id"]}-qa',
        "report_id": report["report_id"],
        "report_hash": report["report_hash"],
        "publication_id": publication["publication_id"],
        "publication_hash": publication["publication_hash"],
        "qa_status": status,
        "checks": checks,
        "issues": issues,
        "policy_effect": "REPORT_ONLY_PROJECTION",
    }
    return {**core, "qa_hash": sha256_obj(core)}

def validate_investor_review_qa(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("investor_review_qa must be an object")
    required = {
        "qa_version", "qa_id", "report_id", "report_hash",
        "publication_id", "publication_hash", "qa_status", "checks",
        "issues", "policy_effect", "qa_hash",
    }
    if set(record) != required:
        raise ValueError("investor_review_qa fields are invalid")
    if record["qa_version"] != INVESTOR_QA_VERSION:
        raise ValueError("investor_review_qa version mismatch")
    checks = record["checks"]
    expected_checks = {
        "publication_integrity", "publication_binding", "report_integrity",
        "deterministic_render_replay", "required_sections", "decision_fidelity",
        "human_boundary", "non_authority",
    }
    if not isinstance(checks, Mapping) or set(checks) != expected_checks:
        raise ValueError("investor_review_qa checks invalid")
    if any(v not in {"PASS", "FAIL"} for v in checks.values()):
        raise ValueError("investor_review_qa check status invalid")
    expected_status = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"
    if record["qa_status"] != expected_status:
        raise ValueError("investor_review_qa status/check mismatch")
    if record["policy_effect"] != "REPORT_ONLY_PROJECTION":
        raise ValueError("investor_review_qa policy effect invalid")
    core = {k: record[k] for k in required if k != "qa_hash"}
    if record["qa_hash"] != sha256_obj(core):
        raise ValueError("investor_review_qa hash mismatch")

def report_path(root: str | Path, report_hash: str) -> Path:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    return root_path / f"{report_hash}.investor-review.json"

def markdown_path(root: str | Path, report_hash: str) -> Path:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    return root_path / f"{report_hash}.investor-review.md"

def qa_path(root: str | Path, qa_hash: str) -> Path:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    return root_path / f"{qa_hash}.investor-review-qa.json"

def write_investor_review_report(
    root: str | Path,
    *,
    publication_path: str | Path,
    generated_at: str,
) -> tuple[Path, Path]:
    publication = _load_json(publication_path)
    validate_machine_publication(publication)
    report = build_investor_review_report(publication=publication, generated_at=generated_at)
    validate_investor_review_report(report)
    qa = qa_investor_review_report(publication=publication, report=report)
    validate_investor_review_qa(qa)
    if qa["qa_status"] != "PASS":
        raise ValueError("investor review quality gate failed: " + "; ".join(qa["issues"]))
    rp = report_path(root, report["report_hash"])
    if rp.exists():
        existing = _load_json(rp)
        validate_investor_review_report(existing)
        if canonical_json(existing) != canonical_json(report):
            raise ValueError("investor review report hash collision or attempted overwrite")
    else:
        rp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8", newline="\\n")
    mp = markdown_path(root, report["report_hash"])
    markdown_bytes = report["markdown"].encode("utf-8")
    if mp.exists():
        if mp.read_bytes() != markdown_bytes:
            raise ValueError("investor review markdown collision or attempted overwrite")
    else:
        mp.write_bytes(markdown_bytes)
    qp = qa_path(root, qa["qa_hash"])
    if qp.exists():
        existing = _load_json(qp)
        validate_investor_review_qa(existing)
        if canonical_json(existing) != canonical_json(qa):
            raise ValueError("investor review QA hash collision or attempted overwrite")
    else:
        qp.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8", newline="\\n")
    return rp, qp
