from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

TZ8 = timezone(timedelta(hours=8))

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
MODEL_ORDER = (
    "SEASONAL_NAIVE",
    "PERSISTENCE_YOY",
    "TREND_LOG_LINEAR_8Q",
    "MEAN_REVERSION_YOY_8",
)
FORBIDDEN_GRANTS = {
    "m1.2.model_selection",
    "production.forecast_router",
    "production.automatic_execution",
    "investment.decision",
}


class FM04BacktestError(ValueError):
    pass


class ForecastUnavailable(FM04BacktestError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FM04BacktestError(f"INVALID_JSON:{path}:{line_no}") from exc
        if not isinstance(value, dict):
            raise FM04BacktestError(f"INVALID_ROW:{path}:{line_no}")
        rows.append(value)
    return rows


def qkey(period: str) -> tuple[int, int]:
    if not isinstance(period, str) or len(period) != 6 or period[4] != "Q" or period[5] not in "1234":
        raise FM04BacktestError("INVALID_QUARTER")
    return int(period[:4]), int(period[5])


def qadd(period: str, offset: int) -> str:
    year, quarter = qkey(period)
    serial = year * 4 + quarter - 1 + offset
    return f"{serial // 4}Q{serial % 4 + 1}"


def qcutoff(period: str) -> datetime:
    year, quarter = qkey(period)
    month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
    day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
    return datetime(year, month, day, 23, 59, 59, tzinfo=TZ8)


def parse_dt(value: Any) -> datetime:
    if not isinstance(value, str):
        raise FM04BacktestError("INVALID_TIMESTAMP")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FM04BacktestError("INVALID_TIMESTAMP") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise FM04BacktestError("INVALID_TIMESTAMP")
    return dt


def canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_capability_context(context: dict[str, Any], contract: dict[str, Any]) -> None:
    if set(context) != {"schema_version", "principal", "grants"}:
        raise FM04BacktestError("INVALID_CAPABILITY_CONTEXT")
    if context["schema_version"] != "IIOS-CAPABILITY-CONTEXT-0.1":
        raise FM04BacktestError("CAPABILITY_SCHEMA_MISMATCH")
    capability = contract["capability_contract"]
    if context["principal"] != capability["required_principal"]:
        raise FM04BacktestError("CAPABILITY_PRINCIPAL_MISMATCH")
    grants = context["grants"]
    if not isinstance(grants, list) or len(grants) != len(set(grants)):
        raise FM04BacktestError("INVALID_CAPABILITY_GRANTS")
    if capability["required_grant"] not in grants:
        raise FM04BacktestError("MISSING_FM04_GRANT")
    if FORBIDDEN_GRANTS.intersection(grants):
        raise FM04BacktestError("DOWNSTREAM_CAPABILITY_PRESENT")


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != "IIOS-FM04-CONDITIONAL-BACKTEST-0.1":
        raise FM04BacktestError("FM04_CONTRACT_SCHEMA_MISMATCH")
    if contract.get("status") != "FROZEN":
        raise FM04BacktestError("FM04_CONTRACT_NOT_FROZEN")
    if contract.get("confirmatory_eligible") is not False:
        raise FM04BacktestError("FM04_MUST_BE_NON_CONFIRMATORY")
    boundary = contract.get("capability_boundary", {})
    expected_boundary = {
        "conditional_backtest_only": True,
        "production_router": False,
        "production_model_selection": False,
        "automatic_execution": False,
        "investment_decision": False,
    }
    if boundary != expected_boundary:
        raise FM04BacktestError("FM04_CAPABILITY_BOUNDARY_WIDENED")
    if tuple(m["model_id"] for m in sorted(contract["models"], key=lambda x: x["order"])) != MODEL_ORDER:
        raise FM04BacktestError("FM04_MODEL_UNIVERSE_MISMATCH")
    if contract["evaluation"]["primary_metric"] != "MAE":
        raise FM04BacktestError("FM04_SELECTION_METRIC_MISMATCH")
    if contract["selection_policy"]["min_common_inner_observations"] != 3:
        raise FM04BacktestError("FM04_INNER_MIN_MISMATCH")
    if contract["selection_policy"]["no_post_hoc_tuning_same_epoch"] is not True:
        raise FM04BacktestError("FM04_POST_HOC_TUNING_FORBIDDEN")
    if contract["research_boundary"]["purity"] != "CONTAMINATED":
        raise FM04BacktestError("FM04_RESEARCH_EPOCH_MISMATCH")
    if contract["research_boundary"]["confirmatory_evidence_authorized"] is not False:
        raise FM04BacktestError("FM04_CONFIRMATORY_AUTHORIZED")


def validate_lock(lock: dict[str, Any]) -> list[dict[str, Any]]:
    if lock.get("schema_version") != "IIOS-OUTER-UNIVERSE-LOCK-0.1" or lock.get("status") != "FROZEN":
        raise FM04BacktestError("OUTER_LOCK_NOT_FROZEN")
    if lock.get("lock_id") != "OU-M12-FM00-CATL-001":
        raise FM04BacktestError("OUTER_LOCK_ID_MISMATCH")
    if lock.get("eligibility_policy") != "PRE_SCHEDULED_AND_IMMUTABLE_AFTER_FREEZE":
        raise FM04BacktestError("OUTER_LOCK_POLICY_MISMATCH")
    origins = lock.get("origins")
    if not isinstance(origins, list) or len(origins) != 11:
        raise FM04BacktestError("OUTER_ORIGIN_COUNT_MISMATCH")
    ids = [o.get("origin_id") for o in origins]
    if len(ids) != len(set(ids)):
        raise FM04BacktestError("OUTER_ORIGIN_DUPLICATE")
    expected = {"3M": 11, "6M": 10, "12M": 8}
    counts = {h: sum(h in o.get("scheduled_horizons", []) for o in origins) for h in HORIZON_OFFSETS}
    if counts != expected:
        raise FM04BacktestError("OUTER_HORIZON_COUNTS_MISMATCH")
    return origins


def validate_state_rows(rows: list[dict[str, Any]], lock: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    expected = {(o["origin_id"], d) for o in lock for d in ("REVENUE", "NET_PROFIT")}
    if len(rows) != len(expected):
        raise FM04BacktestError("FM03_STATE_ROW_COUNT_MISMATCH")
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        required = {
            "state_row_id", "security_id", "driver_id", "origin_id", "origin_cutoff",
            "feature_asof_period", "feature_asof_known_at", "max_feature_input_period",
            "feature_row_id", "input_feature_row_ids", "input_record_ids", "states",
        }
        if set(row) != required:
            raise FM04BacktestError("INVALID_FM03_STATE_ROW")
        if row["security_id"] != "300750.SZ" or row["driver_id"] not in ("REVENUE", "NET_PROFIT"):
            raise FM04BacktestError("FM03_STATE_SCOPE_MISMATCH")
        key = (row["origin_id"], row["driver_id"])
        if key in by_key:
            raise FM04BacktestError("DUPLICATE_FM03_STATE_ROW")
        if key not in expected:
            raise FM04BacktestError("FM03_STATE_OUTSIDE_FROZEN_SCHEDULE")
        if parse_dt(row["origin_cutoff"]) != qcutoff(row["origin_id"]):
            raise FM04BacktestError("FM03_PIT_CUTOFF_MISMATCH")
        if not isinstance(row["states"], dict) or set(row["states"]) != set(STATE_DIMENSIONS):
            raise FM04BacktestError("FM03_STATE_DIMENSION_MISMATCH")
        for dimension in STATE_DIMENSIONS:
            state = row["states"][dimension]
            if not isinstance(state, dict):
                raise FM04BacktestError("INVALID_FM03_STATE")
            if state.get("status") not in ("AVAILABLE", "UNKNOWN"):
                raise FM04BacktestError("INVALID_FM03_STATE_STATUS")
            if state["status"] == "UNKNOWN" and state.get("state") != "UNKNOWN":
                raise FM04BacktestError("UNKNOWN_NOT_EXPLICIT")
            if state["status"] == "AVAILABLE" and state.get("state") == "UNKNOWN":
                raise FM04BacktestError("AVAILABLE_AS_UNKNOWN")
        by_key[key] = row
    if set(by_key) != expected:
        raise FM04BacktestError("FM03_STATE_ORIGIN_SET_MISMATCH")
    return by_key


def validate_driver_records(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, dict[str, Any]]], str]:
    if len(records) != 44:
        raise FM04BacktestError("DRIVER_RECORD_COUNT_MISMATCH")
    by_driver: dict[str, dict[str, dict[str, Any]]] = {"REVENUE": {}, "NET_PROFIT": {}}
    for record in records:
        required = {
            "record_id", "security_id", "driver_id", "period", "value", "known_at",
            "published_at", "provenance", "status",
        }
        if not required.issubset(record):
            raise FM04BacktestError("INVALID_DRIVER_RECORD")
        if record["security_id"] != "300750.SZ" or record["driver_id"] not in by_driver:
            raise FM04BacktestError("DRIVER_SCOPE_MISMATCH")
        qkey(record["period"])
        value = record["value"]
        if record["status"] != "VALID" or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise FM04BacktestError("INVALID_DRIVER_VALUE")
        parse_dt(record["known_at"])
        parse_dt(record["published_at"])
        if record["period"] in by_driver[record["driver_id"]]:
            raise FM04BacktestError("DUPLICATE_DRIVER_PERIOD")
        by_driver[record["driver_id"]][record["period"]] = record
    expected_periods = [qadd("2021Q1", i) for i in range(22)]
    for driver, by_period in by_driver.items():
        if sorted(by_period, key=qkey) != sorted(expected_periods, key=qkey):
            raise FM04BacktestError(f"DRIVER_PERIOD_COVERAGE_MISMATCH:{driver}")
    return by_driver, canonical_sha(records)


def visible_records(
    by_period: dict[str, dict[str, Any]],
    cutoff: datetime,
) -> dict[str, dict[str, Any]]:
    visible: dict[str, dict[str, Any]] = {}
    candidates: dict[str, list[dict[str, Any]]] = {}
    for period, record in by_period.items():
        if parse_dt(record["known_at"]) <= cutoff:
            candidates.setdefault(period, []).append(record)
    for period, records in candidates.items():
        if len(records) != 1:
            raise FM04BacktestError("AMBIGUOUS_VISIBLE_REVISION")
        visible[period] = records[0]
    return visible


def require_visible(visible: dict[str, dict[str, Any]], period: str) -> dict[str, Any]:
    record = visible.get(period)
    if record is None:
        raise ForecastUnavailable(f"UNAVAILABLE_PIT_INPUT:{period}")
    return record


def metric_bundle(pred: float, actual: float) -> dict[str, float]:
    if not math.isfinite(pred) or not math.isfinite(actual):
        raise FM04BacktestError("NON_FINITE_METRIC_INPUT")
    denominator = abs(pred) + abs(actual)
    return {
        "MAE": abs(pred - actual),
        "RMSE": math.sqrt((pred - actual) ** 2),
        "sMAPE": 0.0 if denominator == 0 else 200.0 * abs(pred - actual) / denominator,
    }


def forecast_model(
    model_id: str,
    by_period: dict[str, dict[str, Any]],
    visible: dict[str, dict[str, Any]],
    origin: str,
    horizon: str,
) -> tuple[float, list[str]]:
    h = HORIZON_OFFSETS[horizon]
    target = qadd(origin, h)
    base_period = qadd(target, -4)

    if model_id == "SEASONAL_NAIVE":
        base = require_visible(visible, base_period)
        return float(base["value"]), [base["record_id"]]

    if model_id == "PERSISTENCE_YOY":
        current = require_visible(visible, origin)
        prior = require_visible(visible, qadd(origin, -4))
        base = require_visible(visible, base_period)
        yoy = float(current["value"]) / float(prior["value"]) - 1.0
        if not math.isfinite(yoy):
            raise ForecastUnavailable("NON_FINITE_YOY")
        return float(base["value"]) * (1.0 + yoy), [
            base["record_id"], current["record_id"], prior["record_id"]
        ]

    if model_id == "TREND_LOG_LINEAR_8Q":
        periods = [qadd(origin, -7 + i) for i in range(8)]
        points = []
        ids = []
        for idx, period in enumerate(periods):
            record = require_visible(visible, period)
            value = float(record["value"])
            if value <= 0:
                raise ForecastUnavailable("NON_POSITIVE_TREND_INPUT")
            points.append((float(idx), math.log(value)))
            ids.append(record["record_id"])
        xbar = mean(x for x, _ in points)
        ybar = mean(y for _, y in points)
        denom = sum((x - xbar) ** 2 for x, _ in points)
        if denom == 0:
            raise ForecastUnavailable("DEGENERATE_TREND_FIT")
        slope = sum((x - xbar) * (y - ybar) for x, y in points) / denom
        intercept = ybar - slope * xbar
        forecast = math.exp(intercept + slope * (7 + h))
        if not math.isfinite(forecast):
            raise ForecastUnavailable("NON_FINITE_TREND_FORECAST")
        return forecast, ids

    if model_id == "MEAN_REVERSION_YOY_8":
        base = require_visible(visible, base_period)
        yoy_values = []
        ids = [base["record_id"]]
        for offset in range(-7, 1):
            period = qadd(origin, offset)
            current = require_visible(visible, period)
            prior = require_visible(visible, qadd(period, -4))
            prior_value = float(prior["value"])
            if prior_value == 0:
                raise ForecastUnavailable("ZERO_YOY_DENOMINATOR")
            yoy = float(current["value"]) / prior_value - 1.0
            if not math.isfinite(yoy):
                raise ForecastUnavailable("NON_FINITE_YOY")
            yoy_values.append(yoy)
            ids.extend([current["record_id"], prior["record_id"]])
        growth = mean(yoy_values)
        forecast = float(base["value"]) * (1.0 + growth)
        if not math.isfinite(forecast):
            raise ForecastUnavailable("NON_FINITE_MEAN_REVERSION_FORECAST")
        return forecast, sorted(set(ids))

    raise FM04BacktestError("UNKNOWN_MODEL")


def common_inner_observations(
    outer_origin: str,
    driver_id: str,
    horizon: str,
    state_dimension: str,
    state_value: str,
    origins: list[dict[str, Any]],
    state_by_key: dict[tuple[str, str], dict[str, Any]],
    by_driver: dict[str, dict[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, float]]]]:
    outer_cutoff = qcutoff(outer_origin)
    eligible: list[dict[str, Any]] = []
    per_model_metrics: dict[str, list[dict[str, float]]] = {m: [] for m in MODEL_ORDER}
    for origin_item in origins:
        inner_origin = origin_item["origin_id"]
        if qkey(inner_origin) >= qkey(outer_origin):
            continue
        if horizon not in origin_item.get("scheduled_horizons", []):
            continue
        state_row = state_by_key[(inner_origin, driver_id)]
        state = state_row["states"][state_dimension]
        if state.get("status") != "AVAILABLE" or state.get("state") != state_value:
            continue
        target = qadd(inner_origin, HORIZON_OFFSETS[horizon])
        actual = by_driver[driver_id].get(target)
        if actual is None:
            continue
        if qkey(target) > qkey(outer_origin):
            continue
        if parse_dt(actual["known_at"]) > outer_cutoff:
            continue
        visible = visible_records(by_driver[driver_id], qcutoff(inner_origin))
        forecasts: dict[str, tuple[float, list[str]]] = {}
        failed = False
        for model_id in MODEL_ORDER:
            try:
                forecasts[model_id] = forecast_model(
                    model_id, by_driver[driver_id], visible, inner_origin, horizon
                )
            except ForecastUnavailable:
                failed = True
                break
        if failed:
            continue
        metrics_by_model = {
            model_id: metric_bundle(forecasts[model_id][0], float(actual["value"]))
            for model_id in MODEL_ORDER
        }
        eligible.append({
            "inner_origin_id": inner_origin,
            "state_row_id": state_row["state_row_id"],
            "actual_record_id": actual["record_id"],
            "actual_known_at": actual["known_at"],
            "model_input_record_ids": {
                model_id: forecasts[model_id][1] for model_id in MODEL_ORDER
            },
        })
        for model_id in MODEL_ORDER:
            per_model_metrics[model_id].append(metrics_by_model[model_id])
    return eligible, per_model_metrics


def selection_record(
    outer_origin: str,
    driver_id: str,
    horizon: str,
    state_dimension: str,
    state_row: dict[str, Any],
    origins: list[dict[str, Any]],
    state_by_key: dict[tuple[str, str], dict[str, Any]],
    by_driver: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    state = state_row["states"][state_dimension]
    record: dict[str, Any] = {
        "selection_id": f"FM04-SEL-{driver_id}-{horizon}-{state_dimension}-{outer_origin}",
        "driver_id": driver_id,
        "horizon": horizon,
        "state_dimension": state_dimension,
        "outer_origin_id": outer_origin,
        "state_row_id": state_row["state_row_id"],
        "state_status": state["status"],
        "state_value": state.get("state"),
        "status": "NO_SELECTION",
        "no_selection_reason": None,
        "inner_sample_size": 0,
        "inner_candidate_origins": [],
        "inner_model_mae": {model_id: None for model_id in MODEL_ORDER},
        "selected_model": None,
        "outer_actual_record_id": None,
        "outer_actual_known_at": None,
        "outer_forecast": None,
        "outer_metrics": None,
        "provenance": {
            "state_input_feature_row_ids": state_row["input_feature_row_ids"],
            "state_input_record_ids": state_row["input_record_ids"],
            "inner": [],
            "outer_model_input_record_ids": [],
        },
    }
    if state["status"] != "AVAILABLE":
        record["no_selection_reason"] = "UNKNOWN_STATE"
        return record

    eligible, per_model_metrics = common_inner_observations(
        outer_origin, driver_id, horizon, state_dimension, state["state"],
        origins, state_by_key, by_driver,
    )
    record["inner_sample_size"] = len(eligible)
    record["inner_candidate_origins"] = [x["inner_origin_id"] for x in eligible]
    record["provenance"]["inner"] = eligible

    if len(eligible) < 3:
        record["no_selection_reason"] = "INSUFFICIENT_COMMON_INNER_OBSERVATIONS"
        return record

    means = {
        model_id: mean(item["MAE"] for item in per_model_metrics[model_id])
        for model_id in MODEL_ORDER
    }
    record["inner_model_mae"] = means
    selected = min(
        MODEL_ORDER,
        key=lambda model_id: (means[model_id], MODEL_ORDER.index(model_id)),
    )
    record["selected_model"] = selected
    record["status"] = "SELECTED"
    record["no_selection_reason"] = None

    outer_actual_period = qadd(outer_origin, HORIZON_OFFSETS[horizon])
    actual = by_driver[driver_id].get(outer_actual_period)
    if actual is None:
        record["status"] = "SELECTED_BUT_OUTER_UNAVAILABLE"
        record["no_selection_reason"] = "UNVERIFIABLE_ACTUAL"
        return record
    record["outer_actual_record_id"] = actual["record_id"]
    record["outer_actual_known_at"] = actual["known_at"]
    visible = visible_records(by_driver[driver_id], qcutoff(outer_origin))
    try:
        prediction, input_ids = forecast_model(
            selected, by_driver[driver_id], visible, outer_origin, horizon
        )
    except ForecastUnavailable as exc:
        record["status"] = "SELECTED_BUT_OUTER_UNAVAILABLE"
        record["no_selection_reason"] = str(exc)
        return record
    record["outer_forecast"] = prediction
    record["outer_metrics"] = metric_bundle(prediction, float(actual["value"]))
    record["provenance"]["outer_model_input_record_ids"] = input_ids
    record["status"] = "SELECTED_AND_EVALUATED"
    return record


def aggregate_metrics(rows: list[dict[str, float]]) -> dict[str, float | None]:
    if not rows:
        return {"MAE": None, "RMSE": None, "sMAPE": None}
    return {metric: mean(row[metric] for row in rows) for metric in ("MAE", "RMSE", "sMAPE")}


def conditional_performance(
    origins: list[dict[str, Any]],
    state_by_key: dict[tuple[str, str], dict[str, Any]],
    by_driver: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], set[str]] = {}
    for origin_item in origins:
        origin = origin_item["origin_id"]
        for horizon in origin_item.get("scheduled_horizons", []):
            for driver_id in ("REVENUE", "NET_PROFIT"):
                state_row = state_by_key[(origin, driver_id)]
                for dimension in STATE_DIMENSIONS:
                    state = state_row["states"][dimension]
                    if state["status"] == "AVAILABLE":
                        groups.setdefault((driver_id, horizon, dimension, state["state"]), set()).add(origin)

    results = []
    for (driver_id, horizon, dimension, state_value), _ in sorted(groups.items()):
        common_units = []
        per_model_metrics: dict[str, list[dict[str, float]]] = {m: [] for m in MODEL_ORDER}
        for origin_item in origins:
            origin = origin_item["origin_id"]
            if horizon not in origin_item.get("scheduled_horizons", []):
                continue
            state_row = state_by_key[(origin, driver_id)]
            state = state_row["states"][dimension]
            if state["status"] != "AVAILABLE" or state["state"] != state_value:
                continue
            target = qadd(origin, HORIZON_OFFSETS[horizon])
            actual = by_driver[driver_id].get(target)
            if actual is None:
                continue
            visible = visible_records(by_driver[driver_id], qcutoff(origin))
            forecasts = {}
            failed = False
            for model_id in MODEL_ORDER:
                try:
                    forecasts[model_id] = forecast_model(
                        model_id, by_driver[driver_id], visible, origin, horizon
                    )
                except ForecastUnavailable:
                    failed = True
                    break
            if failed:
                continue
            common_units.append({
                "outer_origin_id": origin,
                "actual_record_id": actual["record_id"],
                "state_row_id": state_row["state_row_id"],
            })
            for model_id in MODEL_ORDER:
                per_model_metrics[model_id].append(
                    metric_bundle(forecasts[model_id][0], float(actual["value"]))
                )
        results.append({
            "driver_id": driver_id,
            "horizon": horizon,
            "state_dimension": dimension,
            "state_value": state_value,
            "common_outer_sample_size": len(common_units),
            "common_outer_origins": [u["outer_origin_id"] for u in common_units],
            "models": {
                model_id: {
                    "metrics": aggregate_metrics(per_model_metrics[model_id]),
                    "evaluation_observation_count": len(per_model_metrics[model_id]),
                }
                for model_id in MODEL_ORDER
            },
            "insufficient_for_selection": len(common_units) < 3,
            "descriptive_only": True,
        })
    return results


def build_result(
    contract: dict[str, Any],
    state_rows: list[dict[str, Any]],
    lock: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    validate_contract(contract)
    capability = {
        "schema_version": "IIOS-CAPABILITY-CONTEXT-0.1",
        "principal": "iios_research",
        "grants": ["m1.2.fm04.conditional_backtest"],
    }
    validate_capability_context(capability, contract)
    origins = validate_lock(lock)
    state_by_key = validate_state_rows(state_rows, origins)
    by_driver, driver_canonical_sha = validate_driver_records(records)

    state_snapshot_sha = canonical_sha(state_rows)
    input_bindings = contract["input_contract"]
    expected_state_sha = input_bindings["state_snapshot_sha256"]
    if state_snapshot_sha != expected_state_sha:
        raise FM04BacktestError("FM03_STATE_SNAPSHOT_HASH_MISMATCH")

    selection_results: list[dict[str, Any]] = []
    for origin_item in origins:
        origin = origin_item["origin_id"]
        for horizon in origin_item.get("scheduled_horizons", []):
            for driver_id in ("REVENUE", "NET_PROFIT"):
                row = state_by_key[(origin, driver_id)]
                for dimension in STATE_DIMENSIONS:
                    selection_results.append(
                        selection_record(
                            origin, driver_id, horizon, dimension,
                            row, origins, state_by_key, by_driver,
                        )
                    )

    conditional = conditional_performance(origins, state_by_key, by_driver)
    selected_count = sum(
        result["status"] in ("SELECTED", "SELECTED_AND_EVALUATED", "SELECTED_BUT_OUTER_UNAVAILABLE")
        for result in selection_results
    )
    evaluated_count = sum(result["status"] == "SELECTED_AND_EVALUATED" for result in selection_results)
    no_selection_count = sum(result["status"] == "NO_SELECTION" for result in selection_results)
    reason_counts: dict[str, int] = {}
    model_counts = {model_id: 0 for model_id in MODEL_ORDER}
    for result in selection_results:
        reason = result["no_selection_reason"]
        if reason:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if result["selected_model"]:
            model_counts[result["selected_model"]] += 1

    result = {
        "schema_version": "IIOS-FM04-CONDITIONAL-BACKTEST-RESULT-0.1",
        "status": "PASS",
        "contract_id": contract["contract_id"],
        "research_epoch_id": contract["research_epoch_id"],
        "confirmatory_eligible": False,
        "input_bindings": {
            "state_snapshot_sha256": state_snapshot_sha,
            "driver_history_canonical_sha256": driver_canonical_sha,
            "driver_history_git_blob_sha": input_bindings["upstream_git_blob_sha"]["driver_history"],
            "state_contract_git_blob_sha": input_bindings["upstream_git_blob_sha"]["state_contract"],
            "outer_universe_lock_git_blob_sha": input_bindings["upstream_git_blob_sha"]["outer_universe_lock"],
            "research_plan_git_blob_sha": input_bindings["upstream_git_blob_sha"]["research_plan"],
            "candidate_space_git_blob_sha": input_bindings["upstream_git_blob_sha"]["candidate_space"],
            "purity_boundary_git_blob_sha": input_bindings["upstream_git_blob_sha"]["purity_boundary"],
            "outer_universe_lock_canonical_sha256": canonical_sha(lock),
        },
        "summary": {
            "outer_origins": [o["origin_id"] for o in origins],
            "outer_selection_unit_count": len(selection_results),
            "selected_count": selected_count,
            "outer_evaluated_count": evaluated_count,
            "no_selection_count": no_selection_count,
            "conditional_group_count": len(conditional),
            "model_order": list(MODEL_ORDER),
            "min_common_inner_observations": 3,
            "no_selection_reason_counts": reason_counts,
            "selected_model_counts": model_counts,
            "rolling_origins_assumed_iid": False,
            "significance_claim_allowed": False,
            "descriptive_only": True,
            "current_price_used": False,
            "automatic_execution": False,
        },
        "outer_selection_evaluations": selection_results,
        "conditional_performance": conditional,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="IIOS M1.2 FM04 Conditional Backtest")
    parser.add_argument("--state-snapshot", default="research/fm03/FM03_STATE_SNAPSHOT.ndjson")
    parser.add_argument("--driver-history", default="research/fm01/CATL_DRIVER_HISTORY.ndjson")
    parser.add_argument("--contract", default="research/fm04/FM04_CONDITIONAL_BACKTEST_CONTRACT.json")
    parser.add_argument("--outer-lock", default="research/fm00/OU-M12-FM00-CATL-001.json")
    parser.add_argument("--output", default="research/fm04/FM04_BACKTEST_RESULT.json")
    args = parser.parse_args()

    contract = load_json(Path(args.contract))
    state_rows = load_ndjson(Path(args.state_snapshot))
    records = load_ndjson(Path(args.driver_history))
    lock = load_json(Path(args.outer_lock))
    result = build_result(contract, state_rows, lock, records)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "schema_version": result["schema_version"],
        "status": result["status"],
        "outer_selection_unit_count": result["summary"]["outer_selection_unit_count"],
        "selected_count": result["summary"]["selected_count"],
        "outer_evaluated_count": result["summary"]["outer_evaluated_count"],
        "no_selection_count": result["summary"]["no_selection_count"],
        "conditional_group_count": result["summary"]["conditional_group_count"],
        "selected_model_counts": result["summary"]["selected_model_counts"],
        "input_bindings": result["input_bindings"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
