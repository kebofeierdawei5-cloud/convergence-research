from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

TZ8 = timezone(timedelta(hours=8))
MODELS = ("SEASONAL_NAIVE", "PERSISTENCE_YOY", "TREND_LOG_LINEAR_8Q", "MEAN_REVERSION_YOY_8")
HORIZONS = {"3M": 1, "6M": 2, "12M": 4}
STATE_DIMENSIONS = (
    "DIRECTION", "MOMENTUM", "VOLATILITY", "SEASONALITY",
    "MEAN_REVERSION_PRESSURE", "STRUCTURAL_STABILITY", "DATA_QUALITY",
)


class AuditError(AssertionError):
    pass


class ForecastUnavailable(AuditError):
    pass


def qkey(p: str) -> tuple[int, int]:
    return int(p[:4]), int(p[5])


def qadd(p: str, offset: int) -> str:
    y, q = qkey(p)
    serial = y * 4 + q - 1 + offset
    return f"{serial // 4}Q{serial % 4 + 1}"


def qcutoff(p: str) -> datetime:
    y, q = qkey(p)
    m = {1: 3, 2: 6, 3: 9, 4: 12}[q]
    d = {3: 31, 6: 30, 9: 30, 12: 31}[m]
    return datetime(y, m, d, 23, 59, 59, tzinfo=TZ8)


def dt(v: str) -> datetime:
    value = datetime.fromisoformat(v)
    if value.tzinfo is None:
        raise AuditError("NAIVE_TIMESTAMP")
    return value


def sha(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha(path: Path) -> str:
    proc = subprocess.run(
        ["git", "hash-object", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AuditError(f"GIT_HASH_OBJECT_FAILED:{path}")
    return proc.stdout.strip()


def load_ndjson(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def visible(by_period, origin):
    cutoff = qcutoff(origin)
    out = {}
    for period, rows in by_period.items():
        candidates = [r for r in rows if dt(r["known_at"]) <= cutoff]
        if len(candidates) > 1:
            raise AuditError("AMBIGUOUS_VISIBLE_REVISION")
        if candidates:
            out[period] = candidates[0]
    return out


def req(vis, period):
    if period not in vis:
        raise ForecastUnavailable("PIT_INPUT_UNAVAILABLE")
    return vis[period]


def forecast(model, vis, origin, horizon):
    h = HORIZONS[horizon]
    target = qadd(origin, h)
    base_period = qadd(target, -4)
    if model == "SEASONAL_NAIVE":
        r = req(vis, base_period)
        return float(r["value"]), [r["record_id"]]
    if model == "PERSISTENCE_YOY":
        cur = req(vis, origin)
        prev = req(vis, qadd(origin, -4))
        base = req(vis, base_period)
        growth = float(cur["value"]) / float(prev["value"]) - 1.0
        return float(base["value"]) * (1.0 + growth), [base["record_id"], cur["record_id"], prev["record_id"]]
    if model == "TREND_LOG_LINEAR_8Q":
        values = []
        ids = []
        for i in range(8):
            r = req(vis, qadd(origin, -7 + i))
            value = float(r["value"])
            if value <= 0:
                raise ForecastUnavailable("NON_POSITIVE_TREND_INPUT")
            values.append(math.log(value))
            ids.append(r["record_id"])
        xbar = 3.5
        ybar = mean(values)
        denom = sum((i - xbar) ** 2 for i in range(8))
        slope = sum((i - xbar) * (y - ybar) for i, y in enumerate(values)) / denom
        intercept = ybar - slope * xbar
        prediction = math.exp(intercept + slope * (7 + h))
        return prediction, ids
    if model == "MEAN_REVERSION_YOY_8":
        base = req(vis, base_period)
        growths = []
        ids = [base["record_id"]]
        for offset in range(-7, 1):
            cur = req(vis, qadd(origin, offset))
            prev = req(vis, qadd(origin, offset - 4))
            if float(prev["value"]) == 0:
                raise ForecastUnavailable("ZERO_YOY_DENOMINATOR")
            growths.append(float(cur["value"]) / float(prev["value"]) - 1.0)
            ids.extend([cur["record_id"], prev["record_id"]])
        return float(base["value"]) * (1.0 + mean(growths)), sorted(set(ids))
    raise AuditError("UNKNOWN_MODEL")


def metrics(pred, actual):
    error = abs(pred - actual)
    return {
        "MAE": error,
        "RMSE": error,
        "sMAPE": 0.0 if abs(pred) + abs(actual) == 0 else 200.0 * error / (abs(pred) + abs(actual)),
    }


def assert_input_bindings(root: Path, contract: dict, result: dict, states, records, lock) -> None:
    assert result["contract_id"] == contract["contract_id"]
    assert result["research_epoch_id"] == contract["research_epoch_id"]
    expected = contract["input_contract"]["upstream_git_blob_sha"]
    paths = {
        "state_contract": root / "fm03/FM03_STATE_CONTRACT.json",
        "driver_history": root / "fm01/CATL_DRIVER_HISTORY.ndjson",
        "outer_universe_lock": root / "fm00/OU-M12-FM00-CATL-001.json",
        "research_plan": root / "fm00/RP-M12-FM00-EXP-001.json",
        "candidate_space": root / "fm00/CS-M12-FM00-CATL-001.json",
        "purity_boundary": root / "fm00/EPB-M12-FM00-EXP-001.json",
    }
    for name, path in paths.items():
        actual_blob = git_blob_sha(path)
        assert actual_blob == expected[name]
        assert result["input_bindings"][f"{name}_git_blob_sha"] == expected[name]
    assert result["input_bindings"]["state_snapshot_sha256"] == sha(states)
    assert result["input_bindings"]["driver_history_canonical_sha256"] == sha(records)
    assert result["input_bindings"]["outer_universe_lock_canonical_sha256"] == sha(lock)


def expected_group_definitions(origins, state_by_key):
    groups = set()
    for origin_item in origins:
        origin = origin_item["origin_id"]
        for horizon in origin_item.get("scheduled_horizons", []):
            for driver_id in ("REVENUE", "NET_PROFIT"):
                state_row = state_by_key[(origin, driver_id)]
                for dimension in STATE_DIMENSIONS:
                    state = state_row["states"][dimension]
                    if state["status"] == "AVAILABLE":
                        groups.add((driver_id, horizon, dimension, state["state"]))
    return [
        {
            "group_id": f"FM04-GRP-{d}-{h}-{dim}-{v}",
            "driver_id": d,
            "horizon": h,
            "state_dimension": dim,
            "state_value": v,
        }
        for d, h, dim, v in sorted(groups)
    ]


def recompute_empirical_group(group, origins, state_by_key, by_driver):
    driver_id = group["driver_id"]
    horizon = group["horizon"]
    dimension = group["state_dimension"]
    state_value = group["state_value"]
    observations = []
    per_model_metrics = {m: [] for m in MODELS}

    for origin_item in origins:
        origin = origin_item["origin_id"]
        if horizon not in origin_item.get("scheduled_horizons", []):
            continue
        state_row = state_by_key[(origin, driver_id)]
        state = state_row["states"][dimension]
        if state["status"] != "AVAILABLE" or state["state"] != state_value:
            continue
        target = qadd(origin, HORIZONS[horizon])
        actual_rows = by_driver[driver_id].get(target, [])
        if not actual_rows:
            continue
        assert len(actual_rows) == 1
        actual = actual_rows[0]
        vis = visible(by_driver[driver_id], origin)
        forecasts = {}
        failed = False
        for model in MODELS:
            try:
                forecasts[model] = forecast(model, vis, origin, horizon)
            except ForecastUnavailable:
                failed = True
                break
        if failed:
            continue
        model_metrics = {
            model: metrics(forecasts[model][0], float(actual["value"]))
            for model in MODELS
        }
        observations.append({
            "outer_origin_id": origin,
            "state_row_id": state_row["state_row_id"],
            "actual_record_id": actual["record_id"],
            "model_input_record_ids": {model: forecasts[model][1] for model in MODELS},
            "model_forecasts": {model: forecasts[model][0] for model in MODELS},
            "model_metrics": model_metrics,
        })
        for model in MODELS:
            per_model_metrics[model].append(model_metrics[model])

    if not observations:
        return None

    return {
        "performance_id": f"FM04-EMP-{driver_id}-{horizon}-{dimension}-{state_value}",
        "group_id": group["group_id"],
        "driver_id": driver_id,
        "horizon": horizon,
        "state_dimension": dimension,
        "state_value": state_value,
        "common_outer_sample_size": len(observations),
        "common_outer_origins": [x["outer_origin_id"] for x in observations],
        "observations": observations,
        "models": {
            model: {
                "metrics": {
                    metric: mean(obs["model_metrics"][model][metric] for obs in observations)
                    for metric in ("MAE", "RMSE", "sMAPE")
                },
                "evaluation_observation_count": len(observations),
            }
            for model in MODELS
        },
        "selection_eligible": False,
        "descriptive_only": True,
    }


def main() -> int:
    root = Path("research")
    contract = json.loads((root / "fm04/FM04_CONDITIONAL_BACKTEST_CONTRACT.json").read_text())
    result = json.loads(Path(os.environ.get("FM04_BACKTEST_RESULT", root / "fm04/FM04_BACKTEST_RESULT.json")).read_text())
    states = load_ndjson(Path(os.environ.get("FM03_STATE_SNAPSHOT", root / "fm03/FM03_STATE_SNAPSHOT.ndjson")))
    records = load_ndjson(root / "fm01/CATL_DRIVER_HISTORY.ndjson")
    lock = json.loads((root / "fm00/OU-M12-FM00-CATL-001.json").read_text())

    assert result["schema_version"] == "IIOS-FM04-CONDITIONAL-BACKTEST-RESULT-0.2"
    assert result["status"] == "PASS"
    assert result["confirmatory_eligible"] is False
    assert result["summary"]["significance_claim_allowed"] is False
    assert result["summary"]["current_price_used"] is False
    assert result["summary"]["automatic_execution"] is False
    assert_input_bindings(root, contract, result, states, records, lock)

    state_by_key = {(r["origin_id"], r["driver_id"]): r for r in states}
    by_driver = {"REVENUE": {}, "NET_PROFIT": {}}
    for r in records:
        by_driver[r["driver_id"]].setdefault(r["period"], []).append(r)

    expected_units = sum(len(o["scheduled_horizons"]) for o in lock["origins"]) * 2 * len(STATE_DIMENSIONS)
    evaluations = result["outer_selection_evaluations"]
    assert len(evaluations) == expected_units

    eligibility = {x["selection_id"]: x for x in result["selection_eligibility"]}
    assert len(eligibility) == len(evaluations)

    for item in evaluations:
        outer = item["outer_origin_id"]
        driver = item["driver_id"]
        horizon = item["horizon"]
        state_row = state_by_key[(outer, driver)]
        state = state_row["states"][item["state_dimension"]]
        assert item["state_status"] == state["status"]
        assert item["state_value"] == state.get("state")
        assert item["state_row_id"] == state_row["state_row_id"]
        e = eligibility.get(item["selection_id"])
        assert e is not None
        assert e["driver_id"] == driver
        assert e["horizon"] == horizon
        assert e["state_dimension"] == item["state_dimension"]
        assert e["outer_origin_id"] == outer
        assert e["state_value"] == item["state_value"]
        expected_eligible = item["status"] in ("SELECTED", "SELECTED_AND_EVALUATED", "SELECTED_BUT_OUTER_UNAVAILABLE")
        assert e["eligible"] is expected_eligible
        assert e["reason"] == item["no_selection_reason"]

        inner = item["provenance"]["inner"]
        for obs in inner:
            inner_origin = obs["inner_origin_id"]
            assert qkey(inner_origin) < qkey(outer)
            target = qadd(inner_origin, HORIZONS[horizon])
            assert qkey(target) <= qkey(outer)
            actual_rows = by_driver[driver][target]
            assert len(actual_rows) == 1
            actual = actual_rows[0]
            assert obs["inner_actual_record_id"] == actual["record_id"]
            assert dt(actual["known_at"]) <= qcutoff(outer)
            inner_state = state_by_key[(inner_origin, driver)]["states"][item["state_dimension"]]
            assert inner_state["status"] == "AVAILABLE"
            assert inner_state["state"] == item["state_value"]
            vis = visible(by_driver[driver], inner_origin)
            for model in MODELS:
                for record_id in obs["inner_model_input_record_ids"][model]:
                    matching = [r for rs in by_driver[driver].values() for r in rs if r["record_id"] == record_id]
                    assert len(matching) == 1
                    assert qkey(matching[0]["period"]) <= qkey(inner_origin)
                    assert dt(matching[0]["known_at"]) <= qcutoff(inner_origin)
                predicted, _ = forecast(model, vis, inner_origin, horizon)
                assert math.isfinite(predicted)

        if item["status"] == "NO_SELECTION":
            assert item["selected_model"] is None
            assert item["outer_metrics"] is None
            if item["state_status"] == "UNKNOWN":
                assert item["no_selection_reason"] == "UNKNOWN_STATE"
            else:
                assert item["inner_sample_size"] < 3
            continue

        assert item["selected_model"] in MODELS
        assert item["inner_sample_size"] >= 3
        recomputed = {}
        for model in MODELS:
            vals = []
            for obs in inner:
                inner_origin = obs["inner_origin_id"]
                actual = by_driver[driver][qadd(inner_origin, HORIZONS[horizon])][0]
                pred, _ = forecast(model, visible(by_driver[driver], inner_origin), inner_origin, horizon)
                vals.append(metrics(pred, float(actual["value"]))["MAE"])
            recomputed[model] = mean(vals)
        for model in MODELS:
            assert abs(recomputed[model] - item["inner_model_mae"][model]) < 1e-12
        selected = min(MODELS, key=lambda m: (recomputed[m], MODELS.index(m)))
        assert selected == item["selected_model"]

        target = qadd(outer, HORIZONS[horizon])
        actual = by_driver[driver][target][0]
        pred, _ = forecast(item["selected_model"], visible(by_driver[driver], outer), outer, horizon)
        expected_metrics = metrics(pred, float(actual["value"]))
        for metric in ("MAE", "RMSE", "sMAPE"):
            assert abs(expected_metrics[metric] - item["outer_metrics"][metric]) < 1e-12
        assert item["outer_actual_record_id"] == actual["record_id"]
        input_ids = item["provenance"]["outer_model_input_record_ids"]
        for record_id in input_ids:
            matching = [r for rs in by_driver[driver].values() for r in rs if r["record_id"] == record_id]
            assert len(matching) == 1
            assert qkey(matching[0]["period"]) <= qkey(outer)
            assert dt(matching[0]["known_at"]) <= qcutoff(outer)

    assert result["summary"]["selected_count"] == sum(
        x["status"] != "NO_SELECTION" for x in evaluations
    )
    assert result["summary"]["no_selection_count"] == sum(
        x["status"] == "NO_SELECTION" for x in evaluations
    )
    selected_model_counts = {model: 0 for model in MODELS}
    for x in evaluations:
        if x["selected_model"]:
            selected_model_counts[x["selected_model"]] += 1
    assert result["summary"]["selected_model_counts"] == selected_model_counts

    expected_groups = expected_group_definitions(lock["origins"], state_by_key)
    assert result["conditional_group_definitions"] == expected_groups
    empirical = result["conditional_empirical_performance"]
    expected_empirical = []
    for group in expected_groups:
        expected = recompute_empirical_group(group, lock["origins"], state_by_key, by_driver)
        if expected is not None:
            expected_empirical.append(expected)
    assert empirical == expected_empirical
    assert result["summary"]["conditional_group_count"] == len(expected_groups)
    assert result["summary"]["empirical_conditional_group_count"] == len(expected_empirical)
    assert len(empirical) == len(expected_empirical)
    assert all(item["selection_eligible"] is False for item in empirical)
    assert all(item["descriptive_only"] is True for item in empirical)

    print("FM04 independent PIT/nested-selection/result-integrity audit: PASS")
    print(json.dumps({
        "outer_selection_units": len(evaluations),
        "selected": result["summary"]["selected_count"],
        "no_selection": result["summary"]["no_selection_count"],
        "conditional_groups": len(expected_groups),
        "empirical_conditional_groups": len(expected_empirical),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
