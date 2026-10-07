from __future__ import annotations

import json
import math
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
    import hashlib
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


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
        raise AuditError("PIT_INPUT_UNAVAILABLE")
    return vis[period]


def forecast(model, vis, origin, horizon):
    h = HORIZONS[horizon]
    target = qadd(origin, h)
    base_period = qadd(target, -4)
    if model == "SEASONAL_NAIVE":
        r = req(vis, base_period)
        return float(r["value"])
    if model == "PERSISTENCE_YOY":
        cur = req(vis, origin)
        prev = req(vis, qadd(origin, -4))
        base = req(vis, base_period)
        growth = float(cur["value"]) / float(prev["value"]) - 1.0
        return float(base["value"]) * (1.0 + growth)
    if model == "TREND_LOG_LINEAR_8Q":
        values = []
        for i in range(8):
            r = req(vis, qadd(origin, -7 + i))
            value = float(r["value"])
            if value <= 0:
                raise AuditError("NON_POSITIVE_TREND_INPUT")
            values.append(math.log(value))
        xbar = 3.5
        ybar = mean(values)
        denom = sum((i - xbar) ** 2 for i in range(8))
        slope = sum((i - xbar) * (y - ybar) for i, y in enumerate(values)) / denom
        intercept = ybar - slope * xbar
        return math.exp(intercept + slope * (7 + h))
    if model == "MEAN_REVERSION_YOY_8":
        base = req(vis, base_period)
        growths = []
        for offset in range(-7, 1):
            cur = req(vis, qadd(origin, offset))
            prev = req(vis, qadd(origin, offset - 4))
            if float(prev["value"]) == 0:
                raise AuditError("ZERO_YOY_DENOMINATOR")
            growths.append(float(cur["value"]) / float(prev["value"]) - 1.0)
        return float(base["value"]) * (1.0 + mean(growths))
    raise AuditError("UNKNOWN_MODEL")


def metrics(pred, actual):
    error = abs(pred - actual)
    return {
        "MAE": error,
        "RMSE": error,
        "sMAPE": 0.0 if abs(pred) + abs(actual) == 0 else 200.0 * error / (abs(pred) + abs(actual)),
    }


def main() -> int:
    root = Path("research")
    contract = json.loads((root / "fm04/FM04_CONDITIONAL_BACKTEST_CONTRACT.json").read_text())
    result = json.loads((root / "fm04/FM04_BACKTEST_RESULT.json").read_text())
    states = load_ndjson(root / "fm03/FM03_STATE_SNAPSHOT.ndjson")
    records = load_ndjson(root / "fm01/CATL_DRIVER_HISTORY.ndjson")
    lock = json.loads((root / "fm00/OU-M12-FM00-CATL-001.json").read_text())

    assert result["schema_version"] == "IIOS-FM04-CONDITIONAL-BACKTEST-RESULT-0.1"
    assert result["status"] == "PASS"
    assert result["confirmatory_eligible"] is False
    assert result["summary"]["significance_claim_allowed"] is False
    assert result["summary"]["current_price_used"] is False
    assert result["summary"]["automatic_execution"] is False
    assert result["input_bindings"]["state_snapshot_sha256"] == sha(states)

    state_by_key = {(r["origin_id"], r["driver_id"]): r for r in states}
    by_driver = {"REVENUE": {}, "NET_PROFIT": {}}
    for r in records:
        by_driver[r["driver_id"]].setdefault(r["period"], []).append(r)

    expected_units = sum(len(o["scheduled_horizons"]) for o in lock["origins"]) * 2 * len(STATE_DIMENSIONS)
    if len(result["outer_selection_evaluations"]) != expected_units:
        raise AuditError("SELECTION_UNIT_COUNT_MISMATCH")

    for item in result["outer_selection_evaluations"]:
        outer = item["outer_origin_id"]
        driver = item["driver_id"]
        horizon = item["horizon"]
        state_row = state_by_key[(outer, driver)]
        state = state_row["states"][item["state_dimension"]]
        assert item["state_status"] == state["status"]
        assert item["state_value"] == state.get("state")
        assert item["state_row_id"] == state_row["state_row_id"]

        inner = item["provenance"]["inner"]
        for obs in inner:
            inner_origin = obs["inner_origin_id"]
            assert qkey(inner_origin) < qkey(outer)
            target = qadd(inner_origin, HORIZONS[horizon])
            assert qkey(target) <= qkey(outer)
            actual = by_driver[driver][target]
            assert len(actual) == 1
            actual = actual[0]
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
                predicted = forecast(model, vis, inner_origin, horizon)
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
                vals.append(metrics(forecast(model, visible(by_driver[driver], inner_origin), inner_origin, horizon), float(actual["value"]))["MAE"])
            recomputed[model] = mean(vals)
        assert all(abs(recomputed[m] - item["inner_model_mae"][m]) < 1e-12 for m in MODELS)
        selected = min(MODELS, key=lambda m: (recomputed[m], MODELS.index(m)))
        assert selected == item["selected_model"]

        target = qadd(outer, HORIZONS[horizon])
        actual = by_driver[driver][target][0]
        pred = forecast(item["selected_model"], visible(by_driver[driver], outer), outer, horizon)
        expected_metrics = metrics(pred, float(actual["value"]))
        for metric in ("MAE", "RMSE", "sMAPE"):
            assert abs(expected_metrics[metric] - item["outer_metrics"][metric]) < 1e-12
        assert item["outer_actual_record_id"] == actual["record_id"]
        assert all(qkey(r["period"]) <= qkey(outer) for r in [
            next(rr for rs in by_driver[driver].values() for rr in rs if rr["record_id"] == rid)
            for rid in item["provenance"]["outer_model_input_record_ids"]
        ])

    if result["summary"]["selected_count"] != sum(
        x["status"] != "NO_SELECTION" for x in result["outer_selection_evaluations"]
    ):
        raise AuditError("SELECTED_COUNT_MISMATCH")
    if result["summary"]["no_selection_count"] != sum(
        x["status"] == "NO_SELECTION" for x in result["outer_selection_evaluations"]
    ):
        raise AuditError("NO_SELECTION_COUNT_MISMATCH")

    print("FM04 independent PIT/nested-selection/blind-scoring audit: PASS")
    print(json.dumps({
        "outer_selection_units": len(result["outer_selection_evaluations"]),
        "selected": result["summary"]["selected_count"],
        "no_selection": result["summary"]["no_selection_count"],
        "conditional_groups": result["summary"]["conditional_group_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
