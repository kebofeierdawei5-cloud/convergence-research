from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

C5_POSITIONING_SIZING_VERSION = "IIOS-C5-POSITIONING-SIZING-0.1"
C5_POLICY_VERSION = "IIOS-C5-POSITIONING-POLICY-0.1"
C5_POLICY_EFFECT = "TIMING_AND_SIZING_ONLY_NO_FUNDAMENTAL_DECISION_MUTATION"

_STATUS_VALUES = {"PASS", "BLOCKED"}
_TIMING_VALUES = {"FAVORABLE", "NEUTRAL", "UNFAVORABLE", None}
_SIZING_BANDS = {"TARGET", "INITIAL", "CURRENT", "NONE"}
_PERMISSION_VALUES = {
    "ALLOW_UP_TO_TARGET",
    "ALLOW_UP_TO_INITIAL",
    "HOLD_CURRENT_NO_ADD",
    "NO_SIZING_PERMISSION",
}
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

FACTOR_FIELDS = (
    "market_regime",
    "industry_sentiment",
    "stock_structure",
    "holder_capital_structure",
    "crowding_supply_pressure",
)

FACTOR_SCORE_MAP = {
    "market_regime": {"BULL": 1, "NEUTRAL": 0, "BEAR": -1},
    "industry_sentiment": {"POSITIVE": 1, "NEUTRAL": 0, "NEGATIVE": -1},
    "stock_structure": {"UP": 1, "RANGE": 0, "DOWN": -1},
    "holder_capital_structure": {"SUPPORTIVE": 1, "NEUTRAL": 0, "OVERHANG": -1},
    "crowding_supply_pressure": {"LOW": 1, "MEDIUM": 0, "HIGH": -1},
}

FACTOR_ALLOWED_VALUES = {
    field: set(values) | {"UNKNOWN", "AMBIGUOUS"}
    for field, values in FACTOR_SCORE_MAP.items()
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _date(value: Any, field: str):
    from datetime import date

    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date") from exc


def _datetime(value: Any, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO datetime") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


def _hash_or_none(value: Any, field: str) -> str | None:
    if value is None:
        return None
    result = str(value)
    if not _HASH_RE.fullmatch(result):
        raise ValueError(f"{field} must be lowercase SHA-256")
    return result


def _factor_status(positioning: Mapping[str, Any]) -> tuple[str, str | None]:
    states = []
    for field in FACTOR_FIELDS:
        value = str(positioning.get(field, "")).strip().upper()
        if value not in FACTOR_ALLOWED_VALUES[field]:
            return "BLOCKED", f"{field} has unsupported state: {value}"
        states.append(value)
    if any(state in {"UNKNOWN", "AMBIGUOUS"} for state in states):
        return "BLOCKED", "one or more positioning dimensions are UNKNOWN or AMBIGUOUS"
    return "PASS", None


def _portfolio_bounds(case: Mapping[str, Any]) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    portfolio = case.get("portfolio") or {}
    current = _decimal(portfolio.get("position_pct", "0"), "portfolio.position_pct")
    package = portfolio.get("buy_add_package")
    if not isinstance(package, Mapping):
        raise ValueError("portfolio.buy_add_package is required for C5 sizing")
    initial = _decimal(package.get("initial_position_pct"), "buy_add_package.initial_position_pct")
    target = _decimal(package.get("target_position_pct"), "buy_add_package.target_position_pct")
    maximum = _decimal(package.get("max_position_pct"), "buy_add_package.max_position_pct")
    for name, value in (
        ("current", current),
        ("initial", initial),
        ("target", target),
        ("maximum", maximum),
    ):
        if value < 0 or value > 100:
            raise ValueError(f"{name} position must be within [0,100]")
    if not (initial <= target <= maximum):
        raise ValueError("buy/add position bounds must satisfy initial <= target <= maximum")
    if current > maximum:
        raise ValueError("current position exceeds declared maximum position")
    return current, initial, target, maximum


def build_positioning_sizing(
    *,
    case: Mapping[str, Any],
    positioning: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cutoff_date = _date(case["cutoff_date"], "case.cutoff_date")
    case_id = str(case["case_id"])
    evidence_ids: list[str] = []

    if positioning is None:
        core = {
            "evaluation_version": C5_POSITIONING_SIZING_VERSION,
            "policy_version": C5_POLICY_VERSION,
            "case_id": case_id,
            "cutoff_date": str(cutoff_date),
            "observation_id": None,
            "observation_as_of_date": None,
            "known_at": None,
            "source": None,
            "source_bundle_sha256": None,
            "evidence_ids": [],
            "factors": {field: None for field in FACTOR_FIELDS},
            "factor_scores": {},
            "composite_score": None,
            "timing_bias": None,
            "sizing_band": "NONE",
            "sizing_permission": "NO_SIZING_PERMISSION",
            "current_position_pct": None,
            "initial_position_pct": None,
            "target_position_pct": None,
            "max_position_pct": None,
            "permitted_position_pct": None,
            "reduce_consideration": False,
            "status": "BLOCKED",
            "reason": "positioning observation was not supplied",
            "policy_effect": C5_POLICY_EFFECT,
        }
        digest = _sha(core)
        return {**core, "evaluation_id": f"c5-positioning-{digest[:16]}", "evaluation_hash": digest}

    required = {
        "observation_id",
        "observation_as_of_date",
        "known_at",
        "source",
        "source_bundle_sha256",
        "evidence_ids",
        *FACTOR_FIELDS,
    }
    missing = sorted(required - set(positioning))
    if missing:
        reason = f"positioning observation missing required fields: {missing}"
        core = {
            "evaluation_version": C5_POSITIONING_SIZING_VERSION,
            "policy_version": C5_POLICY_VERSION,
            "case_id": case_id,
            "cutoff_date": str(cutoff_date),
            "observation_id": str(positioning.get("observation_id")) if positioning.get("observation_id") else None,
            "observation_as_of_date": None,
            "known_at": None,
            "source": str(positioning.get("source")) if positioning.get("source") else None,
            "source_bundle_sha256": None,
            "evidence_ids": [],
            "factors": {field: positioning.get(field) for field in FACTOR_FIELDS},
            "factor_scores": {},
            "composite_score": None,
            "timing_bias": None,
            "sizing_band": "NONE",
            "sizing_permission": "NO_SIZING_PERMISSION",
            "current_position_pct": None,
            "initial_position_pct": None,
            "target_position_pct": None,
            "max_position_pct": None,
            "permitted_position_pct": None,
            "reduce_consideration": False,
            "status": "BLOCKED",
            "reason": reason,
            "policy_effect": C5_POLICY_EFFECT,
        }
        digest = _sha(core)
        return {**core, "evaluation_id": f"c5-positioning-{digest[:16]}", "evaluation_hash": digest}

    observation_date = _date(positioning["observation_as_of_date"], "positioning.observation_as_of_date")
    known_at = _datetime(positioning["known_at"], "positioning.known_at")
    if observation_date > cutoff_date:
        positioning_reason = "positioning observation date is after case cutoff"
    elif known_at.astimezone(timezone.utc).date() > cutoff_date:
        positioning_reason = "positioning evidence became known after case cutoff"
    else:
        positioning_reason = None

    try:
        source_bundle_sha256 = _hash_or_none(
            positioning.get("source_bundle_sha256"),
            "positioning.source_bundle_sha256",
        )
    except ValueError as exc:
        source_bundle_sha256 = None
        positioning_reason = positioning_reason or str(exc)

    raw_evidence_ids = positioning.get("evidence_ids")
    if isinstance(raw_evidence_ids, list):
        evidence_ids = [str(x).strip() for x in raw_evidence_ids]
    if not evidence_ids or any(not x for x in evidence_ids) or len(evidence_ids) != len(set(evidence_ids)):
        positioning_reason = positioning_reason or "positioning.evidence_ids must be a unique non-empty list"

    factor_state, factor_reason = _factor_status(positioning)
    block_reason = positioning_reason or factor_reason

    common = {
        "evaluation_version": C5_POSITIONING_SIZING_VERSION,
        "policy_version": C5_POLICY_VERSION,
        "case_id": case_id,
        "cutoff_date": str(cutoff_date),
        "observation_id": str(positioning["observation_id"]),
        "observation_as_of_date": str(observation_date),
        "known_at": known_at.isoformat(),
        "source": str(positioning["source"]),
        "source_bundle_sha256": source_bundle_sha256,
        "evidence_ids": sorted(set(evidence_ids)),
        "factors": {field: str(positioning[field]).strip().upper() for field in FACTOR_FIELDS},
        "factor_scores": {},
        "composite_score": None,
        "timing_bias": None,
        "sizing_band": "NONE",
        "sizing_permission": "NO_SIZING_PERMISSION",
        "current_position_pct": None,
        "initial_position_pct": None,
        "target_position_pct": None,
        "max_position_pct": None,
        "permitted_position_pct": None,
        "reduce_consideration": False,
        "status": "BLOCKED",
        "reason": block_reason,
        "policy_effect": C5_POLICY_EFFECT,
    }
    if block_reason:
        digest = _sha(common)
        return {**common, "evaluation_id": f"c5-positioning-{digest[:16]}", "evaluation_hash": digest}

    try:
        current, initial, target, maximum = _portfolio_bounds(case)
    except ValueError as exc:
        common["reason"] = str(exc)
        digest = _sha(common)
        return {
            **common,
            "evaluation_id": f"c5-positioning-{digest[:16]}",
            "evaluation_hash": digest,
        }

    factor_scores = {
        field: FACTOR_SCORE_MAP[field][common["factors"][field]]
        for field in FACTOR_FIELDS
    }
    score = sum(factor_scores.values())

    if score >= 2:
        timing_bias = "FAVORABLE"
        sizing_band = "TARGET"
        sizing_permission = "ALLOW_UP_TO_TARGET"
        permitted = max(current, target)
    elif score >= 0:
        timing_bias = "NEUTRAL"
        sizing_band = "INITIAL"
        sizing_permission = "ALLOW_UP_TO_INITIAL"
        permitted = max(current, initial)
    else:
        timing_bias = "UNFAVORABLE"
        sizing_band = "CURRENT"
        sizing_permission = "HOLD_CURRENT_NO_ADD"
        permitted = current

    common.update(
        {
            "factor_scores": factor_scores,
            "composite_score": score,
            "timing_bias": timing_bias,
            "sizing_band": sizing_band,
            "sizing_permission": sizing_permission,
            "current_position_pct": str(current),
            "initial_position_pct": str(initial),
            "target_position_pct": str(target),
            "max_position_pct": str(maximum),
            "permitted_position_pct": str(min(permitted, maximum)),
            "reduce_consideration": timing_bias == "UNFAVORABLE" and current > 0,
            "status": "PASS",
            "reason": "positioning snapshot is complete, PIT-valid and all dimensions are identifiable",
        }
    )
    digest = _sha(common)
    return {**common, "evaluation_id": f"c5-positioning-{digest[:16]}", "evaluation_hash": digest}


def validate_positioning_sizing(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("positioning_sizing must be an object")
    required = {
        "evaluation_version",
        "evaluation_id",
        "evaluation_hash",
        "policy_version",
        "case_id",
        "cutoff_date",
        "observation_id",
        "observation_as_of_date",
        "known_at",
        "source",
        "source_bundle_sha256",
        "evidence_ids",
        "factors",
        "factor_scores",
        "composite_score",
        "timing_bias",
        "sizing_band",
        "sizing_permission",
        "current_position_pct",
        "initial_position_pct",
        "target_position_pct",
        "max_position_pct",
        "permitted_position_pct",
        "reduce_consideration",
        "status",
        "reason",
        "policy_effect",
    }
    if set(record) != required:
        raise ValueError("positioning_sizing fields are invalid")
    if record["evaluation_version"] != C5_POSITIONING_SIZING_VERSION:
        raise ValueError("positioning_sizing version mismatch")
    if record["policy_version"] != C5_POLICY_VERSION:
        raise ValueError("positioning_sizing policy version mismatch")
    if record["policy_effect"] != C5_POLICY_EFFECT:
        raise ValueError("positioning_sizing policy effect invalid")
    if record["status"] not in _STATUS_VALUES:
        raise ValueError("positioning_sizing status invalid")
    if record["timing_bias"] not in _TIMING_VALUES:
        raise ValueError("positioning_sizing timing bias invalid")
    if record["sizing_band"] not in _SIZING_BANDS:
        raise ValueError("positioning_sizing sizing band invalid")
    if record["sizing_permission"] not in _PERMISSION_VALUES:
        raise ValueError("positioning_sizing sizing permission invalid")
    for field in ("evaluation_hash", "source_bundle_sha256"):
        value = record[field]
        if value is not None and not _HASH_RE.fullmatch(str(value)):
            raise ValueError(f"{field} must be lowercase SHA-256")
    if not isinstance(record["evidence_ids"], list) or len(record["evidence_ids"]) != len(set(record["evidence_ids"])):
        raise ValueError("positioning_sizing evidence_ids must be unique")
    if record["status"] == "PASS":
        if len(record["evidence_ids"]) == 0:
            raise ValueError("PASS positioning_sizing requires evidence_ids")
        if record["timing_bias"] is None or record["sizing_band"] == "NONE":
            raise ValueError("PASS positioning_sizing requires timing/sizing outputs")
        if record["composite_score"] not in range(-5, 6):
            raise ValueError("positioning_sizing composite_score must be within [-5,5]")
        if any(record[key] is None for key in (
            "current_position_pct",
            "initial_position_pct",
            "target_position_pct",
            "max_position_pct",
            "permitted_position_pct",
        )):
            raise ValueError("PASS positioning_sizing requires position bounds")
    else:
        if record["sizing_permission"] != "NO_SIZING_PERMISSION":
            raise ValueError("BLOCKED positioning_sizing must deny sizing permission")
        if record["composite_score"] is not None or record["permitted_position_pct"] is not None:
            raise ValueError("BLOCKED positioning_sizing cannot contain computed sizing values")

    factors = record["factors"]
    if set(factors) != set(FACTOR_FIELDS):
        raise ValueError("positioning_sizing factor set mismatch")
    for field in FACTOR_FIELDS:
        value = factors[field]
        if value is not None and value not in FACTOR_ALLOWED_VALUES[field]:
            raise ValueError(f"invalid positioning factor: {field}={value}")
    factor_scores = record["factor_scores"]
    if record["status"] == "PASS":
        if any(field not in factor_scores for field in FACTOR_FIELDS):
            raise ValueError("PASS positioning_sizing requires all factor scores")
        expected_scores = {
            field: FACTOR_SCORE_MAP[field][factors[field]]
            for field in FACTOR_FIELDS
        }
        if factor_scores != expected_scores:
            raise ValueError("positioning_sizing factor score drift")
        if record["composite_score"] != sum(expected_scores.values()):
            raise ValueError("positioning_sizing composite score drift")

    core = {k: record[k] for k in required if k not in {"evaluation_id", "evaluation_hash"}}
    expected_hash = _sha(core)
    if record["evaluation_hash"] != expected_hash:
        raise ValueError("positioning_sizing hash mismatch")
    if record["evaluation_id"] != f"c5-positioning-{expected_hash[:16]}":
        raise ValueError("positioning_sizing evaluation_id mismatch")


def replay_positioning_sizing(record: Mapping[str, Any]) -> dict[str, Any]:
    validate_positioning_sizing(record)
    core = {
        k: record[k]
        for k in record
        if k not in {"evaluation_id", "evaluation_hash"}
    }
    replay_hash = _sha(core)
    return {
        "replay_status": "PASS",
        "deterministic_replay": replay_hash == record["evaluation_hash"],
        "evaluation_hash": record["evaluation_hash"],
        "replay_hash": replay_hash,
    }


def evaluation_path(root: str | Path, evaluation_hash: str) -> Path:
    return Path(root) / f"{evaluation_hash}.positioning-sizing.json"


__all__ = [
    "C5_POSITIONING_SIZING_VERSION",
    "C5_POLICY_VERSION",
    "C5_POLICY_EFFECT",
    "build_positioning_sizing",
    "validate_positioning_sizing",
    "replay_positioning_sizing",
    "evaluation_path",
]
