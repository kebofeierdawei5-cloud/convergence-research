from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .canonical_expectation_gap import evaluate_canonical_expectation_gap
from .canonical_independent_forecast import (
    CanonicalIndependentForecastResolver,
    canonical_independent_expectation_from_record,
)
from .p4f_mie_snapshot import validate_p4f_snapshot

C4_EXPECTATION_GAP_VERSION = "IIOS-C4-EXPECTATION-GAP-0.1"
C4_POLICY_EFFECT = "ADVISORY_ONLY_NO_ADDITIVE_RETURN_THRESHOLD"
_STATUS_VALUES = {
    "PASS",
    "BLOCKED",
    "AMBIGUOUS",
    "INCOMPATIBLE",
    "NO_FEASIBLE_SOLUTION",
}
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_HORIZON_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)(Y|M)$")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_obj(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date") from exc


def _horizon_years(value: Any, field: str) -> Decimal:
    match = _HORIZON_RE.fullmatch(str(value).strip().upper())
    if not match:
        raise ValueError(f"{field} must use canonical Y/M notation")
    amount = _decimal(match.group(1), field)
    years = amount if match.group(2) == "Y" else amount / Decimal("12")
    if years <= 0:
        raise ValueError(f"{field} must be > 0")
    return years


def _strict_gap_payload(case: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = case.get("expectation_gap")
    if not isinstance(payload, Mapping):
        raise ValueError("expectation_gap must be an object")
    required = {
        "gap_id",
        "evaluator_version",
        "price",
        "price_observation_id",
        "cutoff_date",
        "mie_snapshot_hash",
        "market_expectation_id",
        "independent_forecast_ref",
    }
    if set(payload) != required:
        raise ValueError("expectation_gap fields are not canonical")
    return payload


def _resolve_snapshot(case: Mapping[str, Any], evidence_root_resolver: Any) -> dict[str, Any]:
    reference = case.get("market_implied_expectation_snapshot_ref")
    if not isinstance(reference, Mapping):
        raise ValueError("market_implied_expectation_snapshot_ref is required")
    snapshot = evidence_root_resolver.resolve_p4f_snapshot(
        reference,
        case_id=str(case["case_id"]),
        cutoff_date=_date(case["cutoff_date"], "case.cutoff_date"),
    )
    if not isinstance(snapshot, Mapping):
        raise ValueError("resolved P4-F snapshot must be an object")
    validate_p4f_snapshot(snapshot)
    return dict(snapshot)


def _resolve_forecast(
    case: Mapping[str, Any],
    payload: Mapping[str, Any],
    resolver: CanonicalIndependentForecastResolver,
) -> dict[str, Any]:
    reference = payload["independent_forecast_ref"]
    if not isinstance(reference, Mapping):
        raise ValueError("expectation_gap.independent_forecast_ref must be an object")
    record = resolver.resolve_independent_forecast(
        reference,
        case_id=str(case["case_id"]),
        market=str(case["market"]),
        symbol=str(case["symbol"]),
        cutoff_date=_date(case["cutoff_date"], "case.cutoff_date"),
    )
    if not isinstance(record, Mapping):
        raise ValueError("resolved canonical independent forecast must be an object")
    return dict(record)


def _materialized_expectation(snapshot: Mapping[str, Any], expectation_id: str) -> Mapping[str, Any] | None:
    mie_set = snapshot.get("mie_set")
    if not isinstance(mie_set, Mapping):
        raise ValueError("P4-F snapshot mie_set is invalid")
    matches = []
    for evaluation in mie_set.get("model_evaluations") or []:
        if not isinstance(evaluation, Mapping) or evaluation.get("state") != "MATERIALIZED":
            continue
        expectation = evaluation.get("expectation")
        if isinstance(expectation, Mapping) and expectation.get("expectation_id") == expectation_id:
            matches.append(expectation)
    if len(matches) != 1:
        return None
    return matches[0]


def _qualification_state(snapshot: Mapping[str, Any]) -> tuple[str, str]:
    mie_set = snapshot.get("mie_set") or {}
    return str(mie_set.get("resolution_state", "")), str(mie_set.get("qualification", ""))


def _comparison_context(
    expectation: Mapping[str, Any],
    independent_record: Mapping[str, Any],
) -> tuple[dict[str, Any], Mapping[str, Any] | None]:
    independent = canonical_independent_expectation_from_record(independent_record)
    variable_id = str(independent["variable_id"])
    unit = str(independent["unit"])
    basis = str(independent["basis"])
    horizon = _decimal(independent["horizon_years"], "independent forecast horizon_years")
    matches = []
    for requirement in expectation.get("economic_requirements") or []:
        if not isinstance(requirement, Mapping):
            continue
        try:
            requirement_horizon = _horizon_years(requirement.get("horizon"), "market requirement horizon")
        except ValueError:
            continue
        if (
            requirement.get("economic_variable") == variable_id
            and requirement.get("unit") == unit
            and requirement.get("basis") == basis
            and requirement_horizon == horizon
        ):
            matches.append(requirement)
    context = {
        "variable_id": variable_id,
        "unit": unit,
        "basis": basis,
        "horizon_years": str(horizon),
        "comparison_direction": None,
    }
    if len(matches) == 1:
        context["comparison_direction"] = str(matches[0].get("comparison_direction", ""))
    return context, matches[0] if len(matches) == 1 else None


def _record(
    *,
    case: Mapping[str, Any],
    payload: Mapping[str, Any],
    snapshot: Mapping[str, Any] | None,
    status: str,
    resolution_state: str,
    qualification: str,
    reason: str,
    comparison: Mapping[str, Any] | None = None,
    independent_value: Decimal | None = None,
    market_required_value: Decimal | None = None,
    gap_absolute: Decimal | None = None,
    gap_relative: Decimal | None = None,
    independent_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in _STATUS_VALUES:
        raise ValueError("unsupported C4 expectation-gap status")
    comparison_payload = {
        "variable_id": None,
        "unit": None,
        "basis": None,
        "horizon_years": None,
        "comparison_direction": None,
    }
    if comparison:
        comparison_payload.update(comparison)
    core = {
        "evaluation_version": C4_EXPECTATION_GAP_VERSION,
        "case_id": str(case["case_id"]),
        "cutoff_date": str(case["cutoff_date"]),
        "price": str(payload.get("price")),
        "price_observation_id": str(payload.get("price_observation_id")),
        "mie_snapshot_hash": (
            str(snapshot.get("snapshot_hash"))
            if snapshot is not None
            else str(payload.get("mie_snapshot_hash"))
        ),
        "mie_set_hash": str(snapshot.get("mie_set_hash")) if snapshot is not None else None,
        "provenance_hash": str(snapshot.get("provenance_hash")) if snapshot is not None else None,
        "market_expectation_id": str(payload.get("market_expectation_id")),
        "independent_forecast_ref": payload.get("independent_forecast_ref"),
        "independent_forecast_id": (
            str(independent_record.get("forecast_id"))
            if independent_record is not None
            else None
        ),
        "independent_forecast_version": (
            str(independent_record.get("forecast_version"))
            if independent_record is not None
            else None
        ),
        "independent_forecast_model_version": (
            str(independent_record.get("model_version"))
            if independent_record is not None
            else None
        ),
        "status": status,
        "resolution_state": resolution_state or None,
        "qualification": qualification or None,
        "comparison": comparison_payload,
        "independent_value": None if independent_value is None else str(independent_value),
        "market_required_value": None if market_required_value is None else str(market_required_value),
        "gap_absolute": None if gap_absolute is None else str(gap_absolute),
        "gap_relative": None if gap_relative is None else str(gap_relative),
        "reason": reason,
        "policy_effect": C4_POLICY_EFFECT,
        "evidence_ids": sorted(
            set(
                str(item)
                for item in (
                    (independent_record or {}).get("evidence_ids") or []
                )
            )
            | set((snapshot or {}).get("mie_set", {}).get("evidence_ids") or []),
        ),
    }
    evaluation_hash = _sha256_obj(core)
    return {
        **core,
        "evaluation_id": f"c4-gap-{evaluation_hash[:16]}",
        "evaluation_hash": evaluation_hash,
    }


def build_expectation_gap_evaluation(
    *,
    case: Mapping[str, Any],
    evidence_root_resolver: Any,
    independent_forecast_resolver: CanonicalIndependentForecastResolver,
) -> dict[str, Any]:
    payload = _strict_gap_payload(case)
    snapshot = _resolve_snapshot(case, evidence_root_resolver)

    if snapshot.get("snapshot_hash") != payload.get("mie_snapshot_hash"):
        raise ValueError("expectation_gap.mie_snapshot_hash does not match canonical P4-F snapshot")

    resolution_state, qualification = _qualification_state(snapshot)
    if resolution_state == "AMBIGUOUS":
        return _record(
            case=case,
            payload=payload,
            snapshot=snapshot,
            status="AMBIGUOUS",
            resolution_state=resolution_state,
            qualification=qualification,
            reason="market-implied expectation is not uniquely identifiable",
        )
    if resolution_state in {"NO_FEASIBLE_MODEL", "NO_DECISION_GRADE_MODEL"}:
        return _record(
            case=case,
            payload=payload,
            snapshot=snapshot,
            status="NO_FEASIBLE_SOLUTION",
            resolution_state=resolution_state,
            qualification=qualification,
            reason="no decision-grade feasible market-implied expectation exists",
        )
    if resolution_state != "UNIQUE_MODEL" or qualification != "DECISION_GRADE":
        return _record(
            case=case,
            payload=payload,
            snapshot=snapshot,
            status="BLOCKED",
            resolution_state=resolution_state,
            qualification=qualification,
            reason="market-implied expectation is not decision-grade and uniquely resolved",
        )

    independent_record = _resolve_forecast(case, payload, independent_forecast_resolver)
    expectation = _materialized_expectation(snapshot, str(payload["market_expectation_id"]))
    if expectation is None:
        return _record(
            case=case,
            payload=payload,
            snapshot=snapshot,
            status="INCOMPATIBLE",
            resolution_state=resolution_state,
            qualification=qualification,
            reason="market_expectation_id does not resolve to exactly one materialized MIE",
            independent_record=independent_record,
        )

    comparison, requirement = _comparison_context(expectation, independent_record)
    independent_value = _decimal(
        independent_record["value"], "independent forecast value"
    )
    if requirement is None or not comparison["comparison_direction"]:
        return _record(
            case=case,
            payload=payload,
            snapshot=snapshot,
            status="INCOMPATIBLE",
            resolution_state=resolution_state,
            qualification=qualification,
            reason="market and independent expectation semantics do not match exactly",
            comparison=comparison,
            independent_value=independent_value,
            independent_record=independent_record,
        )
    if "value" not in requirement or any(
        key in requirement for key in ("range_low", "range_high")
    ):
        return _record(
            case=case,
            payload=payload,
            snapshot=snapshot,
            status="INCOMPATIBLE",
            resolution_state=resolution_state,
            qualification=qualification,
            reason="market-implied requirement is not a point value and cannot generate a scalar expectation gap",
            comparison=comparison,
            independent_value=independent_value,
            independent_record=independent_record,
        )

    evaluated = evaluate_canonical_expectation_gap(
        payload,
        market_implied_expectation_snapshot=snapshot,
        current_price=case["current_price_observation"]["price"],
        current_price_observation=case["current_price_observation"],
        cutoff_date=case["cutoff_date"],
        case_id=str(case["case_id"]),
        market=str(case["market"]),
        symbol=str(case["symbol"]),
        independent_forecast_resolver=independent_forecast_resolver,
    )

    status = str(evaluated["status"]).upper()
    return _record(
        case=case,
        payload=payload,
        snapshot=snapshot,
        status=status,
        resolution_state=resolution_state,
        qualification=qualification,
        reason=str(evaluated["reason"]),
        comparison={
            **comparison,
            "comparison_direction": str(evaluated["comparison_direction"]),
        },
        independent_value=(
            evaluated.get("independent_value")
            if isinstance(evaluated.get("independent_value"), Decimal)
            else _decimal(evaluated["independent_value"], "evaluated independent value")
        ),
        market_required_value=(
            evaluated.get("market_required_value")
            if isinstance(evaluated.get("market_required_value"), Decimal)
            else _decimal(evaluated["market_required_value"], "evaluated market value")
        ),
        gap_absolute=(
            evaluated.get("gap_absolute")
            if isinstance(evaluated.get("gap_absolute"), Decimal)
            else _decimal(evaluated["gap_absolute"], "evaluated gap")
        ),
        gap_relative=(
            evaluated.get("gap_relative")
            if isinstance(evaluated.get("gap_relative"), Decimal)
            else _decimal(evaluated["gap_relative"], "evaluated relative gap")
        ),
        independent_record=independent_record,
    )


def validate_expectation_gap_evaluation(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("expectation_gap_evaluation must be an object")
    required = {
        "evaluation_version",
        "evaluation_id",
        "evaluation_hash",
        "case_id",
        "cutoff_date",
        "price",
        "price_observation_id",
        "mie_snapshot_hash",
        "mie_set_hash",
        "provenance_hash",
        "market_expectation_id",
        "independent_forecast_ref",
        "independent_forecast_id",
        "independent_forecast_version",
        "independent_forecast_model_version",
        "status",
        "resolution_state",
        "qualification",
        "comparison",
        "independent_value",
        "market_required_value",
        "gap_absolute",
        "gap_relative",
        "reason",
        "policy_effect",
        "evidence_ids",
    }
    if set(record) != required:
        raise ValueError("expectation_gap_evaluation fields are invalid")
    if record["evaluation_version"] != C4_EXPECTATION_GAP_VERSION:
        raise ValueError("expectation_gap_evaluation version mismatch")
    if record["status"] not in _STATUS_VALUES:
        raise ValueError("expectation_gap_evaluation status invalid")
    if record["policy_effect"] != C4_POLICY_EFFECT:
        raise ValueError("expectation_gap_evaluation policy effect invalid")
    for field in ("mie_snapshot_hash", "mie_set_hash", "provenance_hash", "evaluation_hash"):
        value = record[field]
        if value is not None and not _HASH_RE.fullmatch(str(value)):
            raise ValueError(f"{field} must be a lowercase SHA-256")
    if record["status"] == "PASS":
        if record["resolution_state"] != "UNIQUE_MODEL" or record["qualification"] != "DECISION_GRADE":
            raise ValueError("PASS expectation gap requires UNIQUE_MODEL / DECISION_GRADE")
        for field in ("independent_value", "market_required_value", "gap_absolute", "gap_relative"):
            if record[field] is None:
                raise ValueError(f"PASS expectation gap requires {field}")
    else:
        if any(record[field] is not None for field in ("market_required_value", "gap_absolute", "gap_relative")):
            raise ValueError("non-PASS expectation gap cannot contain scalar gap values")
    comparison = record["comparison"]
    if not isinstance(comparison, Mapping):
        raise ValueError("expectation_gap_evaluation comparison must be an object")
    direction = comparison.get("comparison_direction")
    if direction not in {None, "HIGHER_IS_BETTER", "LOWER_IS_BETTER"}:
        raise ValueError("expectation_gap_evaluation comparison direction invalid")
    evidence_ids = record["evidence_ids"]
    if not isinstance(evidence_ids, list) or not evidence_ids or len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("expectation_gap_evaluation evidence_ids must be a unique non-empty list")

    core = {k: record[k] for k in required if k not in {"evaluation_id", "evaluation_hash"}}
    expected_hash = _sha256_obj(core)
    if record["evaluation_hash"] != expected_hash:
        raise ValueError("expectation_gap_evaluation hash mismatch")
    if record["evaluation_id"] != f"c4-gap-{expected_hash[:16]}":
        raise ValueError("expectation_gap_evaluation id mismatch")


def replay_expectation_gap_evaluation(record: Mapping[str, Any]) -> dict[str, Any]:
    validate_expectation_gap_evaluation(record)
    core = {
        k: record[k]
        for k in record
        if k not in {"evaluation_id", "evaluation_hash"}
    }
    return {
        "evaluation_hash": record["evaluation_hash"],
        "replay_hash": _sha256_obj(core),
        "replay_status": "PASS",
        "deterministic_replay": _sha256_obj(core) == record["evaluation_hash"],
    }


def evaluation_path(root: str | Path, evaluation_hash: str) -> Path:
    return Path(root) / f"{evaluation_hash}.expectation-gap.json"


__all__ = [
    "C4_EXPECTATION_GAP_VERSION",
    "C4_POLICY_EFFECT",
    "build_expectation_gap_evaluation",
    "validate_expectation_gap_evaluation",
    "replay_expectation_gap_evaluation",
    "evaluation_path",
]
