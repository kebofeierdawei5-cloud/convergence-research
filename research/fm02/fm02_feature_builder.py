from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, pstdev
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

HORIZON_OFFSETS = {"3M": 1, "6M": 2, "12M": 4}


class FM02FeatureError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def qkey(period: str) -> tuple[int, int]:
    if len(period) != 6 or period[4] != "Q" or period[-1] not in "1234":
        raise FM02FeatureError(f"invalid quarter: {period}")
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
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _parse_dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FM02FeatureError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise FM02FeatureError(f"timestamp must be timezone-aware: {value}")
    return parsed


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != "IIOS-FM02-FEATURE-CONTRACT-0.1":
        raise FM02FeatureError("unsupported FM02 contract schema")
    if contract.get("status") != "FROZEN":
        raise FM02FeatureError("FM02 feature contract must be FROZEN")
    if contract.get("confirmatory_eligible") is not False:
        raise FM02FeatureError("FM02 feature contract is not confirmatory eligible")
    boundary = contract.get("capability_boundary", {})
    expected_false = (
        "state_engine",
        "conditional_backtest",
        "model_selection",
        "production_router",
        "automatic_execution",
    )
    if boundary.get("feature_builder_only") is not True or any(
        boundary.get(key) is not False for key in expected_false
    ):
        raise FM02FeatureError("FM02 capability boundary was widened")


def validate_inputs(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    admission: dict[str, Any],
    contract: dict[str, Any],
) -> None:
    validate_contract(contract)
    if manifest.get("status") != "DATA_READY":
        raise FM02FeatureError("FM01_NOT_DATA_READY")
    if manifest.get("data_status", {}).get("exact_source_snapshot_present") is not True:
        raise FM02FeatureError("FM01 exact source snapshot is not admitted")
    if admission.get("status") != "PASS":
        raise FM02FeatureError("FM01_ADMISSION_NOT_PASS")

    expected_security = set(contract["input_contract"]["required_security_ids"])
    expected_drivers = set(contract["input_contract"]["required_drivers"])
    seen_record_ids: set[str] = set()

    for record in records:
        record_id = record.get("record_id")
        if not record_id or record_id in seen_record_ids:
            raise FM02FeatureError("duplicate_or_missing_record_id")
        seen_record_ids.add(record_id)

        if record.get("security_id") not in expected_security:
            raise FM02FeatureError("OUTSIDE_SECURITY_SCOPE")
        if record.get("driver_id") not in expected_drivers:
            raise FM02FeatureError("OUTSIDE_DRIVER_SCOPE")

        required = (
            "value",
            "known_at",
            "published_at",
            "provenance",
            "source_ref",
            "revision",
            "period",
        )
        if any(field not in record for field in required):
            raise FM02FeatureError("MISSING_PIT_FIELD")

        known_at = _parse_dt(record["known_at"])
        published_at = _parse_dt(record["published_at"])
        if known_at < published_at:
            raise FM02FeatureError("known_at_before_published_at")
        qkey(record["period"])

        if record.get("status") != "VALID":
            raise FM02FeatureError("non_valid_driver_record")
        if not isinstance(record.get("value"), (int, float)) or isinstance(
            record.get("value"), bool
        ):
            raise FM02FeatureError("driver_value_must_be_numeric")


def resolve_visible(
    records: list[dict[str, Any]], driver_id: str, cutoff: datetime
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["driver_id"] != driver_id:
            continue
        if _parse_dt(record["known_at"]) <= cutoff:
            grouped[record["period"]].append(record)

    resolved: dict[str, dict[str, Any]] = {}
    for period, candidates in grouped.items():
        by_known_at: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for candidate in candidates:
            by_known_at[candidate["known_at"]].append(candidate)

        if any(len(items) > 1 for items in by_known_at.values()):
            raise FM02FeatureError(
                f"AMBIGUOUS_VISIBLE_REVISION:{driver_id}:{period}"
            )

        resolved[period] = max(
            candidates,
            key=lambda item: (
                _parse_dt(item["known_at"]),
                int(item["revision"]["sequence"]),
            ),
        )
    return resolved


def yoy_series(
    values: dict[str, dict[str, Any]]
) -> dict[str, tuple[float, list[str]]]:
    out: dict[str, tuple[float, list[str]]] = {}
    periods = sorted(values, key=qkey)
    for period in periods:
        prior = qadd(period, -4)
        if prior not in values:
            continue
        denominator = values[prior]["value"]
        numerator = values[period]["value"]
        if denominator == 0:
            continue
        out[period] = (
            numerator / denominator - 1.0,
            [values[period]["record_id"], values[prior]["record_id"]],
        )
    return out


def ols_log_slope(window: list[float]) -> float:
    if len(window) < 2 or any(x <= 0 for x in window):
        raise FM02FeatureError("NON_POSITIVE_VALUE")
    xs = list(range(len(window)))
    ys = [math.log(x) for x in window]
    xbar = mean(xs)
    ybar = mean(ys)
    denominator = sum((x - xbar) ** 2 for x in xs)
    return sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / denominator


def unknown(reason: str) -> dict[str, Any]:
    return {
        "value": None,
        "status": "UNKNOWN",
        "unknown_reason": reason,
        "input_record_ids": [],
    }


def available(
    value: float, input_record_ids: list[str]
) -> dict[str, Any]:
    return {
        "value": float(value),
        "status": "AVAILABLE",
        "unknown_reason": None,
        "input_record_ids": sorted(set(input_record_ids)),
    }


def build_features(
    values: dict[str, dict[str, Any]], current_period: str
) -> dict[str, dict[str, Any]]:
    yoy = yoy_series(values)
    features: dict[str, dict[str, Any]] = {}

    current = yoy.get(current_period)
    if current is None:
        reason = (
            "ZERO_DENOMINATOR"
            if qadd(current_period, -4) in values
            and values[qadd(current_period, -4)]["value"] == 0
            else "INSUFFICIENT_LOOKBACK"
        )
        for feature_id in FEATURE_IDS:
            features[feature_id] = unknown(reason)
        return features

    current_growth, current_ids = current
    features["YOY_GROWTH"] = available(current_growth, current_ids)

    previous_period = qadd(current_period, -1)
    if previous_period not in yoy:
        features["GROWTH_ACCELERATION"] = unknown("INSUFFICIENT_LOOKBACK")
    else:
        features["GROWTH_ACCELERATION"] = available(
            current_growth - yoy[previous_period][0],
            current_ids + yoy[previous_period][1],
        )

    yoy_periods = sorted(yoy, key=qkey)
    trailing = [p for p in yoy_periods if qkey(p) <= qkey(current_period)]
    if len(trailing) < 8:
        features["ROLLING_GROWTH_VOL"] = unknown("INSUFFICIENT_LOOKBACK")
    else:
        last8 = trailing[-8:]
        features["ROLLING_GROWTH_VOL"] = available(
            pstdev([yoy[p][0] for p in last8]),
            [record_id for p in last8 for record_id in yoy[p][1]],
        )

    same_quarter_prior = [
        p
        for p in yoy_periods
        if qkey(p) < qkey(current_period) and qkey(p)[1] == qkey(current_period)[1]
    ]
    if len(same_quarter_prior) < 2:
        features["SEASONAL_DEVIATION"] = unknown(
            "INSUFFICIENT_SAME_QUARTER_HISTORY"
        )
    else:
        features["SEASONAL_DEVIATION"] = available(
            current_growth - mean(yoy[p][0] for p in same_quarter_prior),
            current_ids
            + [record_id for p in same_quarter_prior for record_id in yoy[p][1]],
        )

    prior8 = [p for p in trailing if qkey(p) < qkey(current_period)]
    if len(prior8) < 8:
        features["MEAN_REVERSION_GAP"] = unknown("INSUFFICIENT_FIT_HISTORY")
    else:
        window = prior8[-8:]
        features["MEAN_REVERSION_GAP"] = available(
            current_growth - mean(yoy[p][0] for p in window),
            current_ids + [record_id for p in window for record_id in yoy[p][1]],
        )

    raw_periods = sorted(
        [p for p in values if qkey(p) <= qkey(current_period)], key=qkey
    )
    if len(raw_periods) < 9:
        features["SLOPE_STABILITY"] = unknown("INSUFFICIENT_HISTORY")
    else:
        slopes: list[float] = []
        used_ids: list[str] = []
        for end_index in range(7, len(raw_periods)):
            window_periods = raw_periods[end_index - 7 : end_index + 1]
            window_values = [values[p]["value"] for p in window_periods]
            try:
                slope = ols_log_slope(window_values)
            except FM02FeatureError:
                features["SLOPE_STABILITY"] = unknown("NON_POSITIVE_VALUE")
                break
            slopes.append(slope)
            used_ids.extend(values[p]["record_id"] for p in window_periods)
        else:
            if len(slopes) < 2:
                features["SLOPE_STABILITY"] = unknown("INSUFFICIENT_HISTORY")
            else:
                features["SLOPE_STABILITY"] = available(
                    pstdev(slopes), used_ids
                )

    return features


def build_feature_snapshot(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    admission: dict[str, Any],
    contract: dict[str, Any],
    outer_lock: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_inputs(records, manifest, admission, contract)

    rows: list[dict[str, Any]] = []
    for origin in outer_lock["origins"]:
        origin_id = origin["origin_id"]
        cutoff = qcutoff(origin_id)
        origin_features: dict[str, dict[str, Any]] = {}

        for driver_id in contract["input_contract"]["required_drivers"]:
            visible = resolve_visible(records, driver_id, cutoff)
            if not visible:
                raise FM02FeatureError(
                    f"no_visible_data:{origin_id}:{driver_id}"
                )
            current_period = max(visible, key=qkey)
            feature_values = build_features(visible, current_period)

            feature_asof_known_at = visible[current_period]["known_at"]
            provenance_periods = sorted(
                {
                    qkey(period)
                    for feature in feature_values.values()
                    for record_id in feature["input_record_ids"]
                    for period, record in visible.items()
                    if record["record_id"] == record_id
                }
            )
            max_input_period = (
                f"{provenance_periods[-1][0]}Q{provenance_periods[-1][1]}"
                if provenance_periods
                else current_period
            )

            for horizon, offset in HORIZON_OFFSETS.items():
                target_period = qadd(origin_id, offset)
                if qkey(current_period) >= qkey(target_period):
                    raise FM02FeatureError(
                        f"TARGET_PERIOD_VISIBLE_AS_FEATURE_ASOF:{origin_id}:{driver_id}:{horizon}"
                    )

            row_id = f"FM02-{outer_lock.get('lock_id', 'OUTER')}-{origin_id}-{driver_id}"
            all_input_ids = sorted(
                {
                    record_id
                    for feature in feature_values.values()
                    for record_id in feature["input_record_ids"]
                }
            )
            origin_features[driver_id] = {
                "row_id": row_id,
                "security_id": visible[current_period]["security_id"],
                "driver_id": driver_id,
                "origin_id": origin_id,
                "origin_cutoff": cutoff.isoformat(),
                "feature_asof_period": current_period,
                "feature_asof_known_at": feature_asof_known_at,
                "max_feature_input_period": max_input_period,
                "visible_record_count": len(visible),
                "input_record_ids": all_input_ids,
                "features": feature_values,
            }

        rows.extend(origin_features.values())

    rows.sort(key=lambda row: (qkey(row["origin_id"]), row["driver_id"]))
    summary = {
        "schema_version": "IIOS-FM02-FEATURE-BUILD-0.1",
        "status": "PASS",
        "contract_id": contract["contract_id"],
        "research_epoch_id": contract["research_epoch_id"],
        "security_ids": sorted({row["security_id"] for row in rows}),
        "drivers": sorted({row["driver_id"] for row in rows}),
        "origin_count": len(outer_lock["origins"]),
        "row_count": len(rows),
        "feature_ids": list(FEATURE_IDS),
        "unknown_counts": {
            feature_id: sum(
                row["features"][feature_id]["status"] == "UNKNOWN"
                for row in rows
            )
            for feature_id in FEATURE_IDS
        },
        "snapshot_sha256": canonical_sha(rows),
        "confirmatory_eligible": False,
    }
    return rows, summary


def write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in rows
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="IIOS FM02 PIT feature builder")
    parser.add_argument(
        "--dataset", default="research/fm01/CATL_DRIVER_HISTORY.ndjson"
    )
    parser.add_argument(
        "--manifest", default="research/fm01/dataset_manifest.json"
    )
    parser.add_argument(
        "--admission", default="research/fm01/M1_1_SOURCE_ADMISSION.json"
    )
    parser.add_argument(
        "--contract", default="research/fm02/FM02_FEATURE_CONTRACT.json"
    )
    parser.add_argument(
        "--outer-lock", default="research/fm00/OU-M12-FM00-CATL-001.json"
    )
    parser.add_argument(
        "--output", default="research/fm02/FM02_FEATURE_SNAPSHOT.ndjson"
    )
    parser.add_argument(
        "--receipt", default="research/fm02/FM02_FEATURE_BUILD_RECEIPT.json"
    )
    args = parser.parse_args()

    rows, summary = build_feature_snapshot(
        load_ndjson(Path(args.dataset)),
        load_json(Path(args.manifest)),
        load_json(Path(args.admission)),
        load_json(Path(args.contract)),
        load_json(Path(args.outer_lock)),
    )
    write_ndjson(Path(args.output), rows)
    Path(args.receipt).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
