from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Mapping

from .price_dependent_expectation_gap import (
    P2_PRICE_GAP_REVALIDATION_VERSION,
    combine_target_entry_price_v2,
)
from .p2_1_canonical_price_response import PRICE_RESPONSE_VERSION

CANONICAL_ENTRY_EVALUATION_VERSION = "IIOS-P2.2-CANONICAL-ENTRY-EVALUATION-0.1"
DECISION_ADMISSION_VERSION = "IIOS-P2.2-DECISION-ADMISSION-0.1"

_FINAL_INCREASE_ACTIONS = frozenset({"BUY", "ADD"})
_ADMISSION_REVIEW_STATES = frozenset(
    {
        "BLOCKED",
        "AMBIGUOUS",
        "INCOMPATIBLE",
        "UNKNOWN",
        "UNSUPPORTED",
        "REVIEW_REQUIRED",
        "NO_FEASIBLE_PRICE",
    }
)


def _dec(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{path} must be finite")
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _evaluation_id(
    *,
    current_price: Decimal,
    return_target_entry_price: Decimal,
    price_response: Mapping[str, Any] | None,
    price_response_source: str,
    entry_reference_source: str,
) -> str:
    return "p22-entry-evaluation-" + _hash(
        {
            "version": CANONICAL_ENTRY_EVALUATION_VERSION,
            "current_price": str(current_price),
            "return_target_entry_price": str(return_target_entry_price),
            "price_response_hash": (
                None if price_response is None else _hash(price_response)
            ),
            "price_response_source": price_response_source,
            "entry_reference_source": entry_reference_source,
        }
    )


def _price_eligible(
    *,
    current_price: Decimal,
    target_entry_price: Decimal,
    price_constraint_type: str | None,
    target_entry_price_inclusive: bool,
) -> bool:
    if price_constraint_type in {
        "UPPER_BOUND_STRICT",
        "UPPER_BOUND_INCLUSIVE",
        "RETURN_TARGET_ENTRY_PRICE",
    }:
        return (
            current_price <= target_entry_price
            if target_entry_price_inclusive
            else current_price < target_entry_price
        )
    if price_constraint_type in {
        "LOWER_BOUND_STRICT",
        "LOWER_BOUND_INCLUSIVE",
    }:
        return (
            current_price >= target_entry_price
            if target_entry_price_inclusive
            else current_price > target_entry_price
        )
    raise ValueError(
        "unsupported canonical entry price constraint type: "
        f"{price_constraint_type}"
    )


def build_canonical_entry_evaluation(
    *,
    current_price: Any,
    return_target_entry_price: Any,
    price_response: Mapping[str, Any] | None,
    price_response_source: str = "P2.1_CANONICAL",
    entry_reference_source: str = "EXPECTATION_GAP",
    market_expectation_id: str | None = None,
    independent_forecast_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize the canonical target-entry object consumed by decision admission."""
    current = _dec(current_price, "current_price")
    return_target = _dec(
        return_target_entry_price,
        "return_target_entry_price",
    )
    if current <= 0:
        raise ValueError("current_price must be > 0")
    if return_target <= 0:
        raise ValueError("return_target_entry_price must be > 0")

    entry_source = str(entry_reference_source or "NONE").upper()
    response_source = str(
        price_response_source or "P2.1_CANONICAL"
    ).upper()
    if response_source not in {
        "P2.1_CANONICAL",
        "P2_LEGACY_COMPAT",
    }:
        raise ValueError(
            "unsupported canonical price-response source: "
            f"{response_source}"
        )

    common = {
        "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
        "current_price": str(current),
        "return_target_entry_price": str(return_target),
        "entry_reference_source": entry_source,
        "market_expectation_id": market_expectation_id,
        "independent_forecast_ref": independent_forecast_ref,
        "price_response_source": response_source,
        "price_response_version": (
            str(price_response.get("response_version"))
            if isinstance(price_response, Mapping)
            and price_response.get("response_version") is not None
            else None
        ),
        "price_response_id": (
            str(price_response.get("response_id") or price_response.get("revalidation_id"))
            if isinstance(price_response, Mapping)
            and (
                price_response.get("response_id")
                or price_response.get("revalidation_id")
            )
            is not None
            else None
        ),
        "price_response_hash": (
            _hash(price_response)
            if isinstance(price_response, Mapping)
            else None
        ),
        "snapshot_hash": (
            str(
                price_response.get("snapshot_hash")
                or price_response.get("reference_snapshot_hash")
            )
            if isinstance(price_response, Mapping)
            and (
                price_response.get("snapshot_hash")
                or price_response.get("reference_snapshot_hash")
            )
            is not None
            else None
        ),
        "model_id": (
            str(
                price_response.get("model_id")
                or price_response.get("market_model")
            )
            if isinstance(price_response, Mapping)
            and (
                price_response.get("model_id")
                or price_response.get("market_model")
            )
            is not None
            else None
        ),
        "expectation_id": (
            str(price_response.get("expectation_id"))
            if isinstance(price_response, Mapping)
            and price_response.get("expectation_id") is not None
            else None
        ),
    }

    if not isinstance(price_response, Mapping):
        return {
            **common,
            "evaluation_id": _evaluation_id(
                current_price=current,
                return_target_entry_price=return_target,
                price_response=None,
                price_response_source=response_source,
                entry_reference_source=entry_source,
            ),
            "status": "REVIEW_REQUIRED",
            "qualification": "UNKNOWN",
            "effective_target_entry_price": None,
            "price_constraint_type": None,
            "target_entry_price_inclusive": False,
            "current_price_eligible": False,
            "binding": "ENTRY_EVALUATION_MISSING_PRICE_RESPONSE",
            "binding_components": [],
            "reason": (
                "canonical price response is required for "
                "decision-grade entry admission"
            ),
        }

    response = dict(price_response)
    response_version = str(response.get("response_version", ""))
    if response_source == "P2.1_CANONICAL":
        if response_version != PRICE_RESPONSE_VERSION:
            raise ValueError(
                "canonical entry evaluation requires exact P2.1 response version "
                f"{PRICE_RESPONSE_VERSION}"
            )
    elif response_version != P2_PRICE_GAP_REVALIDATION_VERSION:
        raise ValueError(
            "P2 legacy compatibility requires exact P2 response version "
            f"{P2_PRICE_GAP_REVALIDATION_VERSION}"
        )

    candidate = _dec(
        response.get("candidate_price"),
        "price_response.candidate_price",
    )
    if candidate != return_target:
        raise ValueError(
            "canonical price-response candidate_price must equal "
            "the canonical return target-entry price"
        )

    reference_price = _dec(
        response.get("reference_price"),
        "price_response.reference_price",
    )
    if reference_price != current:
        raise ValueError(
            "P2.2 canonical current price must equal "
            "price-response reference_price"
        )

    qualification = (
        str(response.get("qualification", "DECISION_GRADE")).upper()
        if response_source == "P2.1_CANONICAL"
        else "DECISION_GRADE"
    )
    if qualification not in {
        "DECISION_GRADE",
        "CONDITIONAL_ONLY",
    }:
        raise ValueError(
            "canonical price response qualification must be "
            "DECISION_GRADE or CONDITIONAL_ONLY"
        )

    combined = combine_target_entry_price_v2(
        return_target_entry_price=return_target,
        revalidation=response,
    )
    combined_status = str(combined.get("status", "")).upper()

    if combined_status == "PASS":
        target = _dec(
            combined["target_entry_price"],
            "combined.target_entry_price",
        )
        constraint_type = str(
            combined.get("price_constraint_type") or ""
        )
        inclusive = bool(
            combined.get("target_entry_price_inclusive", False)
        )
        eligible = _price_eligible(
            current_price=current,
            target_entry_price=target,
            price_constraint_type=constraint_type,
            target_entry_price_inclusive=inclusive,
        )
        binding = str(combined.get("binding") or "")
        status = (
            "PASS"
            if qualification == "DECISION_GRADE"
            else "CONDITIONAL_ONLY"
        )
        return {
            **common,
            "evaluation_id": _evaluation_id(
                current_price=current,
                return_target_entry_price=return_target,
                price_response=response,
                price_response_source=response_source,
                entry_reference_source=entry_source,
            ),
            "status": status,
            "qualification": qualification,
            "effective_target_entry_price": str(target),
            "price_constraint_type": constraint_type,
            "target_entry_price_inclusive": inclusive,
            "current_price_eligible": (
                eligible
                if qualification == "DECISION_GRADE"
                else None
            ),
            "binding": binding,
            "binding_components": [
                binding,
                "RETURN_REQUIRED_RETURN_ENTRY_CUSHION_RISK",
                "PRICE_DEPENDENT_EXPECTATION_GAP",
            ],
            "reason": (
                "canonical decision-grade entry boundary is satisfied "
                "at current price"
                if qualification == "DECISION_GRADE" and eligible
                else "canonical decision-grade entry boundary rejects "
                "current price"
                if qualification == "DECISION_GRADE"
                else "conditional-only price boundary is advisory "
                "and cannot admit capital"
            ),
        }

    if combined_status == "NO_FEASIBLE_PRICE":
        return {
            **common,
            "evaluation_id": _evaluation_id(
                current_price=current,
                return_target_entry_price=return_target,
                price_response=response,
                price_response_source=response_source,
                entry_reference_source=entry_source,
            ),
            "status": "NO_FEASIBLE_PRICE",
            "qualification": qualification,
            "effective_target_entry_price": None,
            "price_constraint_type": combined.get(
                "price_constraint_type"
            ),
            "target_entry_price_inclusive": False,
            "current_price_eligible": False,
            "binding": combined.get("binding"),
            "binding_components": [
                str(combined.get("binding") or ""),
                "PRICE_DEPENDENT_EXPECTATION_GAP",
            ],
            "reason": str(
                combined.get("reason")
                or "no feasible price satisfies the canonical entry constraints"
            ),
        }

    return {
        **common,
        "evaluation_id": _evaluation_id(
            current_price=current,
            return_target_entry_price=return_target,
            price_response=response,
            price_response_source=response_source,
            entry_reference_source=entry_source,
        ),
        "status": "REVIEW_REQUIRED",
        "qualification": qualification,
        "effective_target_entry_price": None,
        "price_constraint_type": combined.get("price_constraint_type"),
        "target_entry_price_inclusive": False,
        "current_price_eligible": False,
        "binding": combined.get("binding"),
        "binding_components": [
            "PRICE_DEPENDENT_EXPECTATION_GAP"
        ],
        "reason": str(
            combined.get("reason")
            or "canonical target-entry evaluation is unresolved"
        ),
    }


def admit_decision(
    *,
    pre_admission_action: str,
    pre_admission_status: str,
    pre_admission_reason: str,
    pre_admission_capital_effect: str,
    position_pct: Any,
    entry_evaluation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Apply P2.2 after P1.4 without weakening higher-protection actions."""
    action = str(pre_admission_action).upper()
    base_status = str(pre_admission_status).upper()
    base_reason = str(pre_admission_reason)
    base_capital_effect = str(pre_admission_capital_effect).upper()
    _dec(position_pct, "position_pct")

    if action not in _FINAL_INCREASE_ACTIONS:
        return {
            "admission_version": DECISION_ADMISSION_VERSION,
            "status": "NOT_APPLICABLE",
            "rule_id": "DA00_NOT_CAPITAL_INCREASING_ACTION",
            "pre_admission_action": action,
            "action": action,
            "decision_status": base_status,
            "primary_reason": base_reason,
            "capital_effect": base_capital_effect,
            "new_capital_allowed": False,
            "evaluation_id": (
                entry_evaluation.get("evaluation_id")
                if isinstance(entry_evaluation, Mapping)
                else None
            ),
        }

    if not isinstance(entry_evaluation, Mapping):
        return {
            "admission_version": DECISION_ADMISSION_VERSION,
            "status": "REVIEW_REQUIRED",
            "rule_id": "DA10_ENTRY_EVALUATION_MISSING",
            "pre_admission_action": action,
            "action": "REVIEW_REQUIRED",
            "decision_status": "REVIEW_REQUIRED",
            "primary_reason": "CANONICAL_ENTRY_EVALUATION_MISSING",
            "capital_effect": "REVIEW",
            "new_capital_allowed": False,
            "evaluation_id": None,
        }

    evaluation_version = str(
        entry_evaluation.get("evaluation_version", "")
    )
    if evaluation_version != CANONICAL_ENTRY_EVALUATION_VERSION:
        return {
            "admission_version": DECISION_ADMISSION_VERSION,
            "status": "REVIEW_REQUIRED",
            "rule_id": "DA11_ENTRY_EVALUATION_VERSION_MISMATCH",
            "pre_admission_action": action,
            "action": "REVIEW_REQUIRED",
            "decision_status": "REVIEW_REQUIRED",
            "primary_reason": "CANONICAL_ENTRY_EVALUATION_VERSION_MISMATCH",
            "capital_effect": "REVIEW",
            "new_capital_allowed": False,
            "evaluation_id": entry_evaluation.get("evaluation_id"),
        }

    qualification = str(
        entry_evaluation.get("qualification", "UNKNOWN")
    ).upper()
    evaluation_status = str(
        entry_evaluation.get("status", "UNKNOWN")
    ).upper()

    if qualification == "CONDITIONAL_ONLY":
        return {
            "admission_version": DECISION_ADMISSION_VERSION,
            "status": "PASS_ADVISORY_ONLY",
            "rule_id": "DA20_CONDITIONAL_ONLY_NO_ADMISSION",
            "pre_admission_action": action,
            "action": action,
            "decision_status": base_status,
            "primary_reason": base_reason,
            "capital_effect": base_capital_effect,
            "new_capital_allowed": action in _FINAL_INCREASE_ACTIONS,
            "evaluation_id": entry_evaluation.get("evaluation_id"),
        }

    if evaluation_status in _ADMISSION_REVIEW_STATES or qualification != "DECISION_GRADE":
        return {
            "admission_version": DECISION_ADMISSION_VERSION,
            "status": "REVIEW_REQUIRED",
            "rule_id": "DA30_DECISION_GRADE_ENTRY_UNRESOLVED",
            "pre_admission_action": action,
            "action": "REVIEW_REQUIRED",
            "decision_status": "REVIEW_REQUIRED",
            "primary_reason": "CANONICAL_ENTRY_EVALUATION_UNRESOLVED",
            "capital_effect": "REVIEW",
            "new_capital_allowed": False,
            "evaluation_id": entry_evaluation.get("evaluation_id"),
        }

    eligible = entry_evaluation.get("current_price_eligible")
    if eligible is not True:
        admitted_action = "WATCH" if action == "BUY" else "HOLD"
        return {
            "admission_version": DECISION_ADMISSION_VERSION,
            "status": "BLOCKED",
            "rule_id": (
                "DA40_NEW_CAPITAL_PRICE_INELIGIBLE"
                if action == "BUY"
                else "DA41_EXISTING_POSITION_PRICE_INELIGIBLE"
            ),
            "pre_admission_action": action,
            "action": admitted_action,
            "decision_status": "READY",
            "primary_reason": "CURRENT_PRICE_OUTSIDE_CANONICAL_ENTRY_BOUNDARY",
            "capital_effect": "UNCHANGED",
            "new_capital_allowed": False,
            "evaluation_id": entry_evaluation.get("evaluation_id"),
        }

    return {
        "admission_version": DECISION_ADMISSION_VERSION,
        "status": "PASS",
        "rule_id": "DA50_CANONICAL_ENTRY_ADMITTED",
        "pre_admission_action": action,
        "action": action,
        "decision_status": base_status,
        "primary_reason": base_reason,
        "capital_effect": base_capital_effect,
        "new_capital_allowed": action in _FINAL_INCREASE_ACTIONS,
        "evaluation_id": entry_evaluation.get("evaluation_id"),
    }


def replay_canonical_entry_evaluation(
    *,
    evaluation: Mapping[str, Any],
    current_price: Any,
    return_target_entry_price: Any,
    price_response: Mapping[str, Any] | None,
    price_response_source: str = "P2.1_CANONICAL",
    entry_reference_source: str = "EXPECTATION_GAP",
    market_expectation_id: str | None = None,
    independent_forecast_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    regenerated = build_canonical_entry_evaluation(
        current_price=current_price,
        return_target_entry_price=return_target_entry_price,
        price_response=price_response,
        price_response_source=price_response_source,
        entry_reference_source=entry_reference_source,
        market_expectation_id=market_expectation_id,
        independent_forecast_ref=independent_forecast_ref,
    )
    return {
        "replay_status": (
            "PASS"
            if _canonical_json(dict(evaluation))
            == _canonical_json(regenerated)
            else "FAIL"
        ),
        "evaluation_id": evaluation.get("evaluation_id"),
        "regenerated_evaluation_id": regenerated.get("evaluation_id"),
    }


def replay_decision_admission(
    *,
    admission: Mapping[str, Any],
    pre_admission_action: str,
    pre_admission_status: str,
    pre_admission_reason: str,
    pre_admission_capital_effect: str,
    position_pct: Any,
    entry_evaluation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    regenerated = admit_decision(
        pre_admission_action=pre_admission_action,
        pre_admission_status=pre_admission_status,
        pre_admission_reason=pre_admission_reason,
        pre_admission_capital_effect=pre_admission_capital_effect,
        position_pct=position_pct,
        entry_evaluation=entry_evaluation,
    )
    return {
        "replay_status": (
            "PASS"
            if _canonical_json(dict(admission))
            == _canonical_json(regenerated)
            else "FAIL"
        ),
        "admission_rule_id": admission.get("rule_id"),
        "regenerated_admission_rule_id": regenerated.get("rule_id"),
    }


__all__ = [
    "CANONICAL_ENTRY_EVALUATION_VERSION",
    "DECISION_ADMISSION_VERSION",
    "build_canonical_entry_evaluation",
    "admit_decision",
    "replay_canonical_entry_evaluation",
    "replay_decision_admission",
]
