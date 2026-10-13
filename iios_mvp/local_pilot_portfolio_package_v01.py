from __future__ import annotations

"""Conservative, non-canonical portfolio-package preview for the local pilot.

This module does not make a formal IIOS Decision or authorize a trade. It
validates an operator-supplied personal portfolio package with the existing
risk/portfolio contract and computes an explicitly conditional stress-budget
position ceiling. Formal admission and human approval remain separate gates.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .risk_portfolio_production_contract import build_risk_portfolio_contract

PACKAGE_VERSION = "IIOS-LOCAL-PILOT-PORTFOLIO-PACKAGE-0.1"
_ALLOWED_CONSTRAINTS = {"PASS", "BLOCKED", "UNKNOWN"}


def _decimal(value: Any, field: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field}_MUST_BE_NUMERIC") from exc
    if not out.is_finite():
        raise ValueError(f"{field}_MUST_BE_FINITE")
    return out


def _pct(value: Any, field: str) -> Decimal:
    out = _decimal(value, field)
    if out < 0 or out > 100:
        raise ValueError(f"{field}_MUST_BE_WITHIN_0_100")
    return out


def _money(value: Any, field: str) -> Decimal:
    out = _decimal(value, field)
    if out <= 0:
        raise ValueError(f"{field}_MUST_BE_POSITIVE")
    return out


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _base(status: str, reason: str) -> dict[str, Any]:
    return {
        "package_version": PACKAGE_VERSION,
        "status": status,
        "input_class": "OPERATOR_ATTESTED_NON_CANONICAL",
        "reason": reason,
        "constraint_status": "UNKNOWN",
        "can_add": False,
        "current_position_pct": None,
        "portfolio_risk_budget_pct_nav": None,
        "entry_zone": None,
        "current_price_zone_status": "UNKNOWN",
        "stress_terminal_wealth_per_share": None,
        "stress_loss_at_entry_zone_high_pct": None,
        "risk_budget_max_position_pct": None,
        "policy_max_position_pct": None,
        "effective_max_position_pct": None,
        "conditional_initial_position_pct": None,
        "conditional_target_position_pct": None,
        "current_position_over_effective_max": None,
        "conditional_proposed_position_pct": None,
        "authorized_new_position_pct": "0",
        "risk_portfolio_contract_status": "NOT_CREATED",
        "risk_portfolio_contract_audit_sha256": None,
        "contract_readiness": {
            "risk_ready": False,
            "portfolio_constraint_ready": False,
            "package_ready": False,
        },
        "formal_decision_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }


def build_local_pilot_portfolio_package(
    *,
    operator_context: Mapping[str, Any] | None,
    case: Mapping[str, Any],
    price_input: Mapping[str, Any],
    decision_parameters: Mapping[str, Any],
    assessment: Mapping[str, Any],
    forecast_valuation: Mapping[str, Any],
    return_metrics: Mapping[str, Any] | None,
    stress_review: Mapping[str, Any] | None,
    evidence_register: list[Mapping[str, Any]],
    unresolved_evidence_ids: list[str] | None = None,
    after_cutoff_evidence_ids: list[str] | None = None,
    uncertain_timing_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Validate manual portfolio limits and compute a conditional stress cap.

    The stress cap uses the separately specified thesis-break stress case, not
    the probability-weighted expected-return case. Any missing admission,
    timing, risk, or decision gate prevents this from being action permission.
    """
    if not isinstance(operator_context, Mapping):
        return _base(
            "NOT_PROVIDED",
            "未提供个人组合风险预算和仓位限制；组合约束为 UNKNOWN，不授予仓位建议或新增资金权限。",
        )

    constraint_status = str(operator_context.get("constraint_status", "UNKNOWN")).strip().upper()
    if constraint_status not in _ALLOWED_CONSTRAINTS:
        return _base("BLOCKED_INVALID_OPERATOR_CONTEXT", "组合约束状态只能是 PASS、BLOCKED 或 UNKNOWN。")

    current_position = _pct(case.get("current_position_pct", "0"), "CURRENT_POSITION_PCT")
    out = _base("REVIEW_REQUIRED", "该仓位包仅供人工复核，当前不构成交易授权。")
    out["constraint_status"] = constraint_status
    out["current_position_pct"] = str(current_position)

    if constraint_status != "PASS":
        out["status"] = "PORTFOLIO_CONSTRAINT_NOT_PASS"
        out["reason"] = "操作者尚未确认组合约束 PASS；不能形成条件仓位或新增资金建议。"
        return out

    if not isinstance(operator_context.get("can_add"), bool):
        out["status"] = "BLOCKED_INVALID_OPERATOR_CONTEXT"
        out["reason"] = "can_add 必须由操作者明确填写为 true 或 false。"
        return out
    operator_can_add = bool(operator_context["can_add"])
    try:
        risk_budget = _pct(operator_context.get("risk_budget_pct_nav"), "RISK_BUDGET_PCT_NAV")
        low = _money(operator_context.get("entry_zone_low"), "ENTRY_ZONE_LOW")
        high = _money(operator_context.get("entry_zone_high"), "ENTRY_ZONE_HIGH")
        initial = _pct(operator_context.get("initial_position_pct"), "INITIAL_POSITION_PCT")
        target = _pct(operator_context.get("target_position_pct"), "TARGET_POSITION_PCT")
        maximum = _pct(operator_context.get("max_position_pct"), "MAX_POSITION_PCT")
        if low > high:
            raise ValueError("ENTRY_ZONE_LOW_MUST_NOT_EXCEED_HIGH")
        if not (initial <= target <= maximum):
            raise ValueError("POSITION_BOUNDS_MUST_SATISFY_INITIAL_LE_TARGET_LE_MAX")
    except ValueError as exc:
        out["status"] = "BLOCKED_INVALID_OPERATOR_CONTEXT"
        out["reason"] = str(exc)
        return out

    current_price = _money(price_input.get("price"), "CURRENT_PRICE")
    zone_status = (
        "BELOW_ENTRY_ZONE" if current_price < low else
        "ABOVE_ENTRY_ZONE" if current_price > high else
        "WITHIN_ENTRY_ZONE"
    )
    out.update({
        "can_add": operator_can_add,
        "portfolio_risk_budget_pct_nav": str(risk_budget),
        "entry_zone": [str(low), str(high)],
        "current_price_zone_status": zone_status,
        "policy_max_position_pct": str(maximum),
    })

    stress_wealth: Decimal | None = None
    try:
        raw_wealth = (stress_review or {}).get("stress_terminal_wealth")
        if raw_wealth in (None, "") or (stress_review or {}).get("status") != "PASS":
            raise ValueError("THESIS_BREAK_STRESS_REVIEW_NOT_PASS")
        stress_wealth = _decimal(raw_wealth, "STRESS_TERMINAL_WEALTH")
        if stress_wealth < 0:
            raise ValueError("STRESS_TERMINAL_WEALTH_MUST_BE_NONNEGATIVE")
        stress_loss = max(Decimal("0"), (high - stress_wealth) / high * Decimal("100"))
        risk_cap = None if stress_loss == 0 else risk_budget / (stress_loss / Decimal("100"))
        effective_max = maximum if risk_cap is None else min(maximum, risk_cap)
        conditional_initial = min(initial, effective_max)
        conditional_target = min(target, effective_max)
        over_limit = current_position > effective_max
        out.update({
            "stress_terminal_wealth_per_share": str(stress_wealth),
            "stress_loss_at_entry_zone_high_pct": str(stress_loss),
            "risk_budget_max_position_pct": None if risk_cap is None else str(risk_cap),
            "effective_max_position_pct": str(effective_max),
            "conditional_initial_position_pct": str(conditional_initial),
            "conditional_target_position_pct": str(conditional_target),
            "current_position_over_effective_max": over_limit,
        })
    except ValueError as exc:
        out["status"] = "REVIEW_REQUIRED"
        out["reason"] = str(exc)
        return out

    # Require risk references to resolve to a registered, cutoff-usable source
    # before the existing risk/portfolio contract can mark its structure ready.
    risk = assessment.get("risk") if isinstance(assessment.get("risk"), Mapping) else {}
    thesis = assessment.get("thesis") if isinstance(assessment.get("thesis"), Mapping) else {}
    risk_refs = set(_strings(risk.get("evidence_refs")))
    for item in risk.get("items") or []:
        if isinstance(item, Mapping):
            risk_refs.update(_strings(item.get("evidence_refs")))
    source_map = {
        str(row.get("source_id")): str(row.get("time_status", "UNKNOWN"))
        for row in evidence_register if isinstance(row, Mapping) and str(row.get("source_id") or "").strip()
    }
    unresolved = set(unresolved_evidence_ids or [])
    after_cutoff = set(after_cutoff_evidence_ids or [])
    uncertain = set(uncertain_timing_evidence_ids or [])
    risk_ref_problem = (
        not risk_refs
        or bool(risk_refs - set(source_map))
        or bool(risk_refs & unresolved)
        or bool(risk_refs & after_cutoff)
        or bool(risk_refs & uncertain)
        or any(source_map.get(ref) not in {"PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"} for ref in risk_refs)
    )

    contract_record: dict[str, Any] | None = None
    contract_error: str | None = None
    if risk_ref_problem:
        contract_error = "风险证据引用缺失、无法解析、时点未知或超过分析截止；未构建可用的风险/组合合同。"
    else:
        try:
            breaks = _strings(thesis.get("break_conditions"))
            reassessment = _strings(thesis.get("reassessment_triggers"))
            if not breaks or not reassessment:
                raise ValueError("THESIS_BREAK_AND_MONITORING_TRIGGERS_REQUIRED")
            contract_record = build_risk_portfolio_contract(
                case_id=str(case.get("case_id") or ""),
                cutoff_date=str(case.get("as_of_date") or ""),
                risk={
                    "status": str(risk.get("status") or "UNKNOWN"),
                    "max_loss_pct": decision_parameters.get("max_loss_pct", "25"),
                    "thesis_breaks": breaks,
                    "evidence_ids": sorted(risk_refs),
                },
                portfolio={
                    "position_pct": str(current_position),
                    "constraint_status": constraint_status,
                    "can_add": operator_can_add,
                    "buy_add_package": {
                        "entry_zone": [str(low), str(high)],
                        "initial_position_pct": str(initial),
                        "target_position_pct": str(target),
                        "max_position_pct": str(maximum),
                        "thesis_break_triggers": breaks,
                        "monitoring_triggers": reassessment,
                    },
                },
            )
        except (ValueError, TypeError, KeyError) as exc:
            contract_error = str(exc)

    if contract_record:
        readiness = contract_record["readiness"]
        out["risk_portfolio_contract_status"] = "STRUCTURAL_VALIDATION_PASS_NOT_ADMITTED"
        out["risk_portfolio_contract_audit_sha256"] = contract_record["audit_sha256"]
        out["contract_readiness"] = dict(readiness)
    else:
        out["risk_portfolio_contract_status"] = "BLOCKED"
        out["contract_readiness"] = {
            "risk_ready": False,
            "portfolio_constraint_ready": False,
            "package_ready": False,
        }

    metrics_pass = bool(return_metrics and return_metrics.get("return_gate_pass", False))
    risk_pass = str(risk.get("status") or "UNKNOWN").upper() == "PASS"
    stress_pass = bool(stress_review and stress_review.get("status") == "PASS")
    package_structurally_ready = bool(
        contract_record
        and contract_record["readiness"]["portfolio_constraint_ready"]
        and contract_record["readiness"]["package_ready"]
    )
    conditional_ready = bool(
        package_structurally_ready
        and contract_record["readiness"]["risk_ready"]
        and operator_can_add
        and constraint_status == "PASS"
        and risk_pass
        and stress_pass
        and metrics_pass
        and zone_status == "WITHIN_ENTRY_ZONE"
        and not out["current_position_over_effective_max"]
        and not (stress_review or {}).get("issues")
    )
    if conditional_ready:
        out["status"] = "CONDITIONAL_PACKAGE_READY_NOT_AUTHORIZED"
        out["reason"] = (
            "组合合同结构检查与条件计算通过；但研究仍为非正式试运行，Trust/正式准入/人工审批等门槛"
            "未完成，条件仓位不是可执行买入指令。"
        )
        out["conditional_proposed_position_pct"] = str(out["conditional_target_position_pct"])
    else:
        out["status"] = "REVIEW_REQUIRED"
        reasons = []
        if not package_structurally_ready:
            reasons.append(contract_error or "风险/组合合同结构检查未完成")
        if not risk_pass:
            reasons.append("Risk 未达到 PASS")
        if not stress_pass:
            reasons.append("论点失效压力情景未通过")
        if not metrics_pass:
            reasons.append("当前价回报/风险门槛未通过")
        if zone_status != "WITHIN_ENTRY_ZONE":
            reasons.append("当前价格不在操作者指定的入场区间内")
        if not operator_can_add:
            reasons.append("操作者未允许新增资金")
        if out["current_position_over_effective_max"]:
            reasons.append("当前仓位已超过风险预算推导上限，仅提醒人工复核")
        out["reason"] = "；".join(dict.fromkeys(reasons)) or "条件仓位包尚有未满足门槛。"

    # Even the conditional result above never grants actual investment authority.
    out["formal_decision_created"] = False
    out["execution_authorized"] = False
    out["auto_execution"] = False
    out["authorized_new_position_pct"] = "0"
    return out


__all__ = ["PACKAGE_VERSION", "build_local_pilot_portfolio_package"]
