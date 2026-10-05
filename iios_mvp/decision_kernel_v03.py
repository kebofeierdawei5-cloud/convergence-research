from __future__ import annotations

from decimal import Decimal
from typing import Any

from .decision_state_machine_v01 import (
    DECISION_PRECEDENCE_VERSION,
    DecisionStateInputs,
    MIE_POLICY_MANDATORY,
    MIE_POLICY_OPTIONAL_EXPLANATORY,
    evaluate_decision_state,
)

DECISION_KERNEL_VERSION = "IIOS-CORE-04-DECISION-KERNEL-0.2"
DECISION_KERNEL_POLICY_VERSION = "IIOS-DECISION-POLICY-0.3"


def _investability_for_action(action: str) -> str:
    if action == "REVIEW_REQUIRED":
        return "UNKNOWN"
    if action in {"BUY", "ADD"}:
        return "INVESTABLE"
    if action in {"HOLD", "WATCH"}:
        return "WATCH"
    return "NOT_INVESTABLE"


def evaluate_production_decision(
    *,
    validation_pass: bool,
    trust_status: str,
    thesis_status: str,
    reality_status: str,
    quality_gate_status: str,
    value_driver_status: str,
    valuation_status: str,
    forecast_status: str,
    thesis_admission_status: str,
    risk_status: str,
    portfolio_status: str,
    position_pct: Decimal,
    gap_status: str,
    gap_positive: bool,
    expected_annualized_return: Decimal | None,
    return_gate_pass: bool,
    risk_gate_pass: bool,
    can_add: bool,
    package_complete: bool,
    return_metrics_ready: bool,
    mie_policy: str = MIE_POLICY_OPTIONAL_EXPLANATORY,
    mie_material_contradiction: bool = False,
) -> dict[str, Any]:
    """Canonical CORE-04 production decision boundary for Investment Core v0.3.

    MIE is optional/explanatory in v0.3. Its absence, UNKNOWN, BLOCKED or
    AMBIGUOUS state cannot by itself deny a company-side BUY/ADD opportunity.
    A future material qualified contradiction policy must be explicit; no
    hidden threshold is inferred here.
    """
    if mie_policy not in {MIE_POLICY_OPTIONAL_EXPLANATORY, MIE_POLICY_MANDATORY}:
        raise ValueError(f"unsupported mie_policy: {mie_policy}")

    state = evaluate_decision_state(
        DecisionStateInputs(
            validation_pass=bool(validation_pass),
            trust_status=str(trust_status).upper(),
            thesis_status=str(thesis_status).upper(),
            reality_status=str(reality_status).upper(),
            quality_gate_status=str(quality_gate_status).upper(),
            value_driver_status=str(value_driver_status).upper(),
            valuation_status=str(valuation_status).upper(),
            forecast_status=str(forecast_status).upper(),
            thesis_admission_status=str(thesis_admission_status).upper(),
            risk_status=str(risk_status).upper(),
            portfolio_status=str(portfolio_status).upper(),
            position_pct=Decimal(position_pct),
            gap_status=str(gap_status).upper(),
            gap_positive=bool(gap_positive),
            expected_annualized_return=(
                None if expected_annualized_return is None else Decimal(expected_annualized_return)
            ),
            return_gate_pass=bool(return_gate_pass),
            risk_gate_pass=bool(risk_gate_pass),
            can_add=bool(can_add),
            package_complete=bool(package_complete),
            return_metrics_ready=bool(return_metrics_ready),
            mie_policy=mie_policy,
            mie_material_contradiction=bool(mie_material_contradiction),
        )
    )
    action = state["action"]
    return {
        **state,
        "decision_kernel_version": DECISION_KERNEL_VERSION,
        "decision_policy_version": DECISION_KERNEL_POLICY_VERSION,
        "decision_precedence_version": DECISION_PRECEDENCE_VERSION,
        "mie_policy": mie_policy,
        "mie_material_contradiction": bool(mie_material_contradiction),
        "upstream_gate_status": {
            "reality": str(reality_status).upper(),
            "quality": str(quality_gate_status).upper(),
            "value_driver": str(value_driver_status).upper(),
            "valuation": str(valuation_status).upper(),
            "forecast": str(forecast_status).upper(),
            "thesis_admission": str(thesis_admission_status).upper(),
        },
        "investability_status": _investability_for_action(action),
    }


__all__ = [
    "DECISION_KERNEL_POLICY_VERSION",
    "DECISION_KERNEL_VERSION",
    "evaluate_production_decision",
]
