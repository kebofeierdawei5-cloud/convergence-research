from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ8 = timezone(timedelta(hours=8))

FEATURE_IDS = (
    "YOY_GROWTH",
    "GROWTH_ACCELERATION",
    "ROLLING_GROWTH_VOL",
    "SEASONAL_DEVIATION",
    "MEAN_REVERSION_GAP",
    "SLOPE_STABILITY",
)

STATE_DIMENSIONS = (
    "DIRECTION",
    "MOMENTUM",
    "VOLATILITY",
    "SEASONALITY",
    "MEAN_REVERSION_PRESSURE",
    "STRUCTURAL_STABILITY",
    "DATA_QUALITY",
)

HORIZON_OFFSETS = {"3M": 1, "6M": 2, "12M": 4}
DOWNSTREAM_FORBIDDEN = {
    "m1.2.fm04.conditional_backtest",
    "m1.2.model_selection",
    "production.forecast_router",
    "production.automatic_execution",
}


class FM03StateError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FM03StateError(f"expected JSON object: {path}")
    return value


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FM03StateError(f"invalid JSON at {path}:{line_no}") from exc
        if not isinstance(value, dict):
            raise FM03StateError(f"expected JSON object at {path}:{line_no}")
        rows.append(value)
    return rows


def qkey(period: str) -> tuple[int, int]:
    if len(period) != 6 or period[4] != "Q" or period[-1] not in "1234":
        raise FM03StateError(f"invalid quarter: {period}")
    return int(period[:4]), int(period[-1])


def qadd(period: str, offset: int) -> str:
    year, quarter = qkey(period)
    serial = year * 4 + quarter - 1 + offset
    return f"{serial // 4}Q{serial % 4 + 1}"


def qcutoff(period: str) -> datetime:
    year, quarter = qkey(period)
    month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
    day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
    return datetime(year, month, day, 23, 59, 59, tzinfo=TZ8)


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_dt(value: Any) -> datetime:
    if not isinstance(value, str):
        raise FM03StateError("INVALID_TIMESTAMP")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FM03StateError("INVALID_TIMESTAMP") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise FM03StateError("INVALID_TIMESTAMP")
    return result


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != "IIOS-FM03-STATE-CONTRACT-0.1":
        raise FM03StateError("FM03_CONTRACT_SCHEMA_MISMATCH")
    if contract.get("status") != "FROZEN":
        raise FM03StateError("FM03_CONTRACT_NOT_FROZEN")
    if contract.get("confirmatory_eligible") is not False:
        raise FM03StateError("FM03_MUST_BE_NON_CONFIRMATORY")
    boundary = contract.get("capability_boundary", {})
    if boundary != {
        "state_engine_only": True,
        "conditional_backtest": False,
        "model_selection": False,
        "production_router": False,
        "automatic_execution": False,
    }:
        raise FM03StateError("FM03_CAPABILITY_BOUNDARY_WIDENED")
    capability = contract.get("capability_contract", {})
    if capability.get("required_principal") != "iios_research":
        raise FM03StateError("FM03_PRINCIPAL_MISMATCH")
    if capability.get("required_grant") != "m1.2.fm03.state_engine":
        raise FM03StateError("FM03_GRANT_MISMATCH")
    if set(capability.get("forbidden_grants", [])) != DOWNSTREAM_FORBIDDEN:
        raise FM03StateError("FM03_FORBIDDEN_GRANTS_MISMATCH")


def validate_capability_context(context: dict[str, Any], contract: dict[str, Any]) -> None:
    if set(context) != {"schema_version", "principal", "grants"}:
        raise FM03StateError("INVALID_CAPABILITY_CONTEXT")
    if context.get("schema_version") != "IIOS-CAPABILITY-CONTEXT-0.1":
        raise FM03StateError("CAPABILITY_SCHEMA_MISMATCH")
    if context.get("principal") != contract["capability_contract"]["required_principal"]:
        raise FM03StateError("CAPABILITY_PRINCIPAL_MISMATCH")
    grants = context.get("grants")
    if not isinstance(grants, list) or len(grants) != len(set(grants)):
        raise FM03StateError("INVALID_CAPABILITY_GRANTS")
    if contract["capability_contract"]["required_grant"] not in grants:
        raise FM03StateError("MISSING_FM03_GRANT")
    forbidden = DOWNSTREAM_FORBIDDEN.intersection(grants)
    if forbidden:
        raise FM03StateError("DOWNSTREAM_CAPABILITY_PRESENT")


def _state_available(value: str) -> dict[str, Any]:
    return {
        "state": value,
        "status": "AVAILABLE",
        "unknown_reason": None,
    }


def _state_unknown(reason: str) -> dict[str, Any]:
    return {
        "state": "UNKNOWN",
        "status": "UNKNOWN",
        "unknown_reason": reason,
    }


def validate_feature(feature: Any) -> None:
    if not isinstance(feature, dict):
        raise FM03StateError("INVALID_INPUT_STATE")
    if set(feature) != {"value", "status", "unknown_reason", "input_record_ids"}:
        raise FM03StateError("INVALID_INPUT_STATE")
    status = feature.get("status")
    if status == "AVAILABLE":
        value = feature.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise FM03StateError("INVALID_INPUT_STATE")
        if feature.get("unknown_reason") is not None:
            raise FM03StateError("INVALID_INPUT_STATE")
        ids = feature.get("input_record_ids")
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)) or any(not isinstance(x, str) or not x for x in ids):
            raise FM03StateError("INVALID_INPUT_STATE")
    elif status == "UNKNOWN":
        if feature.get("value") is not None:
            raise FM03StateError("INVALID_INPUT_STATE")
        if not isinstance(feature.get("unknown_reason"), str) or not feature["unknown_reason"]:
            raise FM03StateError("INVALID_INPUT_STATE")
        if feature.get("input_record_ids") != []:
            raise FM03StateError("INVALID_INPUT_STATE")
    else:
        raise FM03StateError("INVALID_INPUT_STATE")


def validate_feature_row(row: dict[str, Any], contract: dict[str, Any], lock: dict[str, Any]) -> None:
    required = {
        "row_id", "security_id", "driver_id", "origin_id", "origin_cutoff",
        "feature_asof_period", "feature_asof_known_at", "max_feature_input_period",
        "visible_record_count", "input_record_ids", "features",
    }
    if set(row) != required:
        raise FM03StateError("INVALID_INPUT_STATE")
    if row["security_id"] not in contract["input_contract"]["required_security_ids"]:
        raise FM03StateError("OUTSIDE_SECURITY_SCOPE")
    if row["driver_id"] not in contract["input_contract"]["required_drivers"]:
        raise FM03StateError("OUTSIDE_DRIVER_SCOPE")
    origin = next((item for item in lock["origins"] if item.get("origin_id") == row["origin_id"]), None)
    if origin is None or origin.get("eligibility") != "SCHEDULED":
        raise FM03StateError("ORIGIN_OUTSIDE_FROZEN_SCHEDULE")
    cutoff = qcutoff(row["origin_id"])
    if parse_dt(row["origin_cutoff"]) != cutoff:
        raise FM03StateError("PIT_BOUNDARY_FAILURE")
    feature_asof = qkey(row["feature_asof_period"])
    max_input = qkey(row["max_feature_input_period"])
    if max_input > feature_asof or feature_asof > qkey(row["origin_id"]):
        raise FM03StateError("PIT_BOUNDARY_FAILURE")
    if parse_dt(row["feature_asof_known_at"]) > cutoff:
        raise FM03StateError("PIT_BOUNDARY_FAILURE")
    if not isinstance(row["visible_record_count"], int) or row["visible_record_count"] < 1:
        raise FM03StateError("INVALID_INPUT_STATE")
    if not isinstance(row["input_record_ids"], list) or len(row["input_record_ids"]) != len(set(row["input_record_ids"])):
        raise FM03StateError("INVALID_INPUT_STATE")
    features = row["features"]
    if set(features) != set(contract["input_contract"]["required_feature_ids"]):
        raise FM03StateError("INVALID_INPUT_STATE")
    for feature_id in FEATURE_IDS:
        validate_feature(features[feature_id])
    union_ids = sorted({
        record_id
        for feature in features.values()
        for record_id in feature["input_record_ids"]
    })
    if sorted(row["input_record_ids"]) != union_ids:
        raise FM03StateError("INCOMPLETE_LINEAGE")
    for offset in HORIZON_OFFSETS.values():
        target = qkey(qadd(row["origin_id"], offset))
        if feature_asof >= target or max_input >= target:
            raise FM03StateError("PIT_BOUNDARY_FAILURE")


def validate_upstream_lock(lock: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    if lock.get("schema_version") != "IIOS-OUTER-UNIVERSE-LOCK-0.1" or lock.get("status") != "FROZEN":
        raise FM03StateError("FM03_OUTER_LOCK_NOT_FROZEN")
    if lock.get("lock_id") != "OU-M12-FM00-CATL-001":
        raise FM03StateError("FM03_OUTER_LOCK_ID_MISMATCH")
    if lock.get("eligibility_policy") != "PRE_SCHEDULED_AND_IMMUTABLE_AFTER_FREEZE":
        raise FM03StateError("FM03_OUTER_LOCK_POLICY_MISMATCH")
    expected_hash = contract["origin_contract"]["outer_universe_lock_sha256"]
    if canonical_sha(lock) != expected_hash:
        raise FM03StateError("FM03_OUTER_LOCK_HASH_MISMATCH")
    origins = lock.get("origins")
    if not isinstance(origins, list) or len(origins) != contract["origin_contract"]["exact_origin_count"]:
        raise FM03StateError("FM03_ORIGIN_COUNT_MISMATCH")
    ids = [item.get("origin_id") for item in origins]
    if len(ids) != len(set(ids)) or any(not isinstance(x, str) for x in ids):
        raise FM03StateError("FM03_ORIGIN_SET_INVALID")
    counts = {h: 0 for h in HORIZON_OFFSETS}
    for item in origins:
        if item.get("eligibility") != "SCHEDULED":
            raise FM03StateError("FM03_ORIGIN_NOT_SCHEDULED")
        if item.get("cutoff_rule") != "ORIGIN_QUARTER_END_KNOWN_AT_CUTOFF":
            raise FM03StateError("FM03_CUTOFF_RULE_MISMATCH")
        for h in HORIZON_OFFSETS:
            if h in item.get("scheduled_horizons", []):
                counts[h] += 1
    if counts != {"3M": 11, "6M": 10, "12M": 8}:
        raise FM03StateError("FM03_ORIGIN_HORIZON_COUNTS_MISMATCH")
    return origins


def _attach_provenance(base: dict[str, Any], feature_ids: list[str], current: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    row_ids = [current["row_id"]]
    record_ids: set[str] = set()
    for feature_id in feature_ids:
        record_ids.update(current["features"][feature_id]["input_record_ids"])
    if prior is not None:
        row_ids.append(prior["row_id"])
        for feature_id in feature_ids:
            record_ids.update(prior["features"][feature_id]["input_record_ids"])
    base["input_feature_ids"] = feature_ids
    base["input_feature_row_ids"] = sorted(set(row_ids))
    base["input_record_ids"] = sorted(record_ids)
    return base


def signed_state(feature_id: str, feature: dict[str, Any]) -> dict[str, Any]:
    if feature["status"] != "AVAILABLE":
        return _state_unknown("SOURCE_FEATURE_UNKNOWN")
    value = feature["value"]
    if feature_id == "YOY_GROWTH":
        return _state_available("UP" if value > 0 else "DOWN" if value < 0 else "FLAT")
    if feature_id == "GROWTH_ACCELERATION":
        return _state_available("ACCELERATING" if value > 0 else "DECELERATING" if value < 0 else "FLAT")
    if feature_id == "SEASONAL_DEVIATION":
        return _state_available("POSITIVE" if value > 0 else "NEGATIVE" if value < 0 else "NEUTRAL")
    if feature_id == "MEAN_REVERSION_GAP":
        return _state_available("DOWNWARD" if value > 0 else "UPWARD" if value < 0 else "NEUTRAL")
    raise FM03StateError("INVALID_INPUT_STATE")


def comparison_state(feature_id: str, current: dict[str, Any], prior: dict[str, Any] | None, lower_label: str, equal_label: str, higher_label: str) -> tuple[dict[str, Any], list[str]]:
    if current["status"] != "AVAILABLE" or (prior is not None and prior["status"] != "AVAILABLE"):
        reason = "NO_PRIOR_FROZEN_ORIGIN" if prior is None else "SOURCE_FEATURE_UNKNOWN"
        feature_ids = [feature_id]
        return _state_unknown(reason), feature_ids
    value = current["value"]
    previous = prior["value"]
    if value < previous:
        return _state_available(lower_label), [feature_id, feature_id]
    if value > previous:
        return _state_available(higher_label), [feature_id, feature_id]
    return _state_available(equal_label), [feature_id, feature_id]


def build_state_row(current: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    states: dict[str, dict[str, Any]] = {}
    states["DIRECTION"] = {**signed_state("YOY_GROWTH", current["features"]["YOY_GROWTH"]), **_attach_provenance({}, ["YOY_GROWTH"], current, None)}
    states["MOMENTUM"] = {**signed_state("GROWTH_ACCELERATION", current["features"]["GROWTH_ACCELERATION"]), **_attach_provenance({}, ["GROWTH_ACCELERATION"], current, None)}
    vol_state, _ = comparison_state("ROLLING_GROWTH_VOL", current["features"]["ROLLING_GROWTH_VOL"], None if prior is None else prior["features"]["ROLLING_GROWTH_VOL"], "FALLING", "FLAT", "RISING")
    states["VOLATILITY"] = {**vol_state, **_attach_provenance({}, ["ROLLING_GROWTH_VOL"], current, prior)}
    states["SEASONALITY"] = {**signed_state("SEASONAL_DEVIATION", current["features"]["SEASONAL_DEVIATION"]), **_attach_provenance({}, ["SEASONAL_DEVIATION"], current, None)}
    states["MEAN_REVERSION_PRESSURE"] = {**signed_state("MEAN_REVERSION_GAP", current["features"]["MEAN_REVERSION_GAP"]), **_attach_provenance({}, ["MEAN_REVERSION_GAP"], current, None)}
    stability_state, _ = comparison_state("SLOPE_STABILITY", current["features"]["SLOPE_STABILITY"], None if prior is None else prior["features"]["SLOPE_STABILITY"], "IMPROVING", "STABLE", "DETERIORATING")
    states["STRUCTURAL_STABILITY"] = {**stability_state, **_attach_provenance({}, ["SLOPE_STABILITY"], current, prior)}
    statuses = [current["features"][feature_id]["status"] for feature_id in FEATURE_IDS]
    if all(status == "UNKNOWN" for status in statuses):
        dq = _state_unknown("SOURCE_FEATURE_UNKNOWN")
    elif all(status == "AVAILABLE" for status in statuses):
        dq = _state_available("COMPLETE")
    else:
        dq = _state_available("PARTIAL")
    states["DATA_QUALITY"] = {**dq, **_attach_provenance({}, list(FEATURE_IDS), current, None)}
    all_feature_row_ids = sorted({
        row_id
        for state in states.values()
        for row_id in state["input_feature_row_ids"]
    })
    all_record_ids = sorted({
        record_id
        for state in states.values()
        for record_id in state["input_record_ids"]
    })
    return {
        "state_row_id": current["row_id"].replace("FM02-", "FM03-"),
        "security_id": current["security_id"],
        "driver_id": current["driver_id"],
        "origin_id": current["origin_id"],
        "origin_cutoff": current["origin_cutoff"],
        "feature_asof_period": current["feature_asof_period"],
        "feature_asof_known_at": current["feature_asof_known_at"],
        "max_feature_input_period": current["max_feature_input_period"],
        "feature_row_id": current["row_id"],
        "input_feature_row_ids": all_feature_row_ids,
        "input_record_ids": all_record_ids,
        "states": states,
    }


def validate_state_row(row: dict[str, Any]) -> None:
    if row["state_row_id"] != row["feature_row_id"].replace("FM02-", "FM03-"):
        raise FM03StateError("INVALID_INPUT_STATE")
    if qkey(row["max_feature_input_period"]) > qkey(row["feature_asof_period"]):
        raise FM03StateError("INCOMPLETE_LINEAGE")
    for state in row["states"].values():
        if state["status"] == "AVAILABLE":
            if state["state"] == "UNKNOWN" or state["unknown_reason"] is not None:
                raise FM03StateError("INVALID_INPUT_STATE")
        elif state["status"] == "UNKNOWN":
            if state["state"] != "UNKNOWN" or not state["unknown_reason"]:
                raise FM03StateError("INVALID_INPUT_STATE")
        else:
            raise FM03StateError("INVALID_INPUT_STATE")


def build_state_snapshot(feature_rows: list[dict[str, Any]], contract: dict[str, Any], outer_lock: dict[str, Any], capability_context: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_contract(contract)
    validate_capability_context(capability_context, contract)
    origins = validate_upstream_lock(outer_lock, contract)
    expected_keys = {(item["origin_id"], driver_id) for item in origins for driver_id in contract["input_contract"]["required_drivers"]}
    if len(feature_rows) != contract["origin_contract"]["exact_row_count"]:
        raise FM03StateError("FM03_FEATURE_ROW_COUNT_MISMATCH")
    seen: set[tuple[str, str]] = set()
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in feature_rows:
        validate_feature_row(row, contract, outer_lock)
        key = (row["origin_id"], row["driver_id"])
        if key in seen:
            raise FM03StateError("DUPLICATE_FEATURE_ROW")
        seen.add(key)
        by_key[key] = row
    if seen != expected_keys:
        raise FM03StateError("FROZEN_ORIGIN_OR_DRIVER_SET_MISMATCH")
    rows: list[dict[str, Any]] = []
    for index, origin in enumerate(origins):
        origin_id = origin["origin_id"]
        prior_origin = origins[index - 1]["origin_id"] if index > 0 else None
        for driver_id in contract["input_contract"]["required_drivers"]:
            current = by_key[(origin_id, driver_id)]
            prior = None if prior_origin is None else by_key[(prior_origin, driver_id)]
            row = build_state_row(current, prior)
            validate_state_row(row)
            rows.append(row)
    rows.sort(key=lambda row: (qkey(row["origin_id"]), row["driver_id"]))
    summary = {
        "schema_version": "IIOS-FM03-STATE-BUILD-0.1",
        "status": "PASS",
        "contract_id": contract["contract_id"],
        "research_epoch_id": contract["research_epoch_id"],
        "security_ids": sorted({row["security_id"] for row in rows}),
        "drivers": sorted({row["driver_id"] for row in rows}),
        "origin_count": len(origins),
        "row_count": len(rows),
        "state_dimensions": list(STATE_DIMENSIONS),
        "unknown_counts": {
            dimension: sum(row["states"][dimension]["status"] == "UNKNOWN" for row in rows)
            for dimension in STATE_DIMENSIONS
        },
        "feature_contract_sha256": contract["input_contract"]["feature_contract_sha256"],
        "outer_universe_lock_sha256": contract["origin_contract"]["outer_universe_lock_sha256"],
        "snapshot_sha256": canonical_sha(rows),
        "confirmatory_eligible": False,
        "capability_principal": capability_context["principal"],
        "capability_grant": contract["capability_contract"]["required_grant"],
    }
    return rows, summary


def write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="IIOS M1.2 FM03 PIT state engine")
    parser.add_argument("--feature-snapshot", default="research/fm02/FM02_FEATURE_SNAPSHOT.ndjson")
    parser.add_argument("--contract", default="research/fm03/FM03_STATE_CONTRACT.json")
    parser.add_argument("--outer-lock", default="research/fm00/OU-M12-FM00-CATL-001.json")
    parser.add_argument("--output", default="research/fm03/FM03_STATE_SNAPSHOT.ndjson")
    parser.add_argument("--receipt", default="research/fm03/FM03_STATE_BUILD_RECEIPT.json")
    parser.add_argument("--principal", default="iios_research")
    parser.add_argument("--grant", default="m1.2.fm03.state_engine")
    args = parser.parse_args()
    contract = load_json(Path(args.contract))
    capability = {
        "schema_version": "IIOS-CAPABILITY-CONTEXT-0.1",
        "principal": args.principal,
        "grants": [args.grant],
    }
    rows, summary = build_state_snapshot(
        load_ndjson(Path(args.feature_snapshot)),
        contract,
        load_json(Path(args.outer_lock)),
        capability,
    )
    write_ndjson(Path(args.output), rows)
    Path(args.receipt).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
