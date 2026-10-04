from __future__ import annotations

import json
from pathlib import Path

from iios_mvp.engine import decide, replay, run_case
from iios_mvp.store import read_snapshot, write_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "iios_mvp_demo.json"


def load_demo():
    return json.loads(DEMO.read_text(encoding="utf-8"))


def test_demo_decision_is_buy_without_human_approval():
    result = decide(load_demo())
    assert result["decision"]["action"] == "BUY"
    assert result["decision"]["human_approval_required"] is True
    assert result["decision"]["auto_execution"] is False
    assert result["gates"]["new_buy_add_allowed"] is True


def test_future_evidence_blocks_new_buy():
    case = load_demo()
    case["evidence"] = list(case["evidence"]) + [{"source": "future-test", "known_at": "2026-11-01", "claim": "future fact"}]
    result = decide(case)
    assert result["validation"]["status"] == "BLOCKED"
    assert result["decision"]["action"] == "NO-BUY"
    assert any(x.startswith("PIT_LEAK_EVIDENCE_") for x in result["validation"]["blockers"])


def test_trust_fail_blocks_buy_but_does_not_force_exit():
    case = load_demo()
    case["trust"]["status"] = "FAIL"
    case["portfolio"]["position_pct"] = 5
    result = decide(case)
    assert result["decision"]["action"] == "HOLD"
    assert result["decision"]["primary_reason"] == "TRUST_GATES_NEW_BUY_ADD_ONLY"


def test_snapshot_is_immutable_and_replayable(tmp_path):
    snapshot, snapshot_hash = run_case(load_demo())
    path = write_snapshot(tmp_path, snapshot)
    loaded = read_snapshot(path)
    assert loaded["snapshot_hash"] == snapshot_hash
    assert replay(loaded)["replay_status"] == "PASS"


def test_missing_forecast_inputs_fail_closed():
    case = load_demo()
    case["forecast"]["base"]["net_profit"] = None
    result = decide(case)
    assert result["validation"]["status"] == "BLOCKED"
    assert result["decision"]["action"] == "NO-BUY"



def test_multiple_revisions_preserve_history_and_advance_current(tmp_path):
    from iios_mvp.store import (
        approve_revision, create_or_load_series, next_revision,
        write_decision_revision, write_snapshot,
    )

    case1 = load_demo()
    case1["cutoff_date"] = "2026-10-04"
    snap1, h1 = run_case(case1)
    write_snapshot(tmp_path, snap1)
    series = create_or_load_series(tmp_path, "CN-A", case1["symbol"], case1["company"], "2026-10-04T00:00:00Z")
    r1 = next_revision(tmp_path, series["decision_series_id"])
    write_decision_revision(tmp_path, series["decision_series_id"], r1, snap1, h1[:16])
    (tmp_path / f"{series['decision_series_id']}.index.json").write_text(json.dumps({"next_revision": 2}), encoding="utf-8")
    d1 = f"{series['decision_series_id']}-r001"
    assert approve_revision(tmp_path, d1, snap1, True, "approve r1")["current"] is True

    case2 = load_demo()
    case2["cutoff_date"] = "2026-10-05"
    case2["valuation"]["current_price"] = 380
    snap2, h2 = run_case(case2)
    write_snapshot(tmp_path, snap2)
    r2 = next_revision(tmp_path, series["decision_series_id"])
    write_decision_revision(tmp_path, series["decision_series_id"], r2, snap2, h2[:16])
    (tmp_path / f"{series['decision_series_id']}.index.json").write_text(json.dumps({"next_revision": 3}), encoding="utf-8")
    d2 = f"{series['decision_series_id']}-r002"
    assert approve_revision(tmp_path, d2, snap2, True, "approve r2")["current"] is True

    current = json.loads((tmp_path / f"{series['decision_series_id']}.current.json").read_text())
    assert current["current_approved_decision_id"] == d2
    assert (tmp_path / f"{d1}.decision.json").exists()
    assert (tmp_path / f"{d2}.decision.json").exists()
    assert read_snapshot(tmp_path / f"{h1}.json")["snapshot_hash"] == h1
    assert read_snapshot(tmp_path / f"{h2}.json")["snapshot_hash"] == h2


def test_approval_cannot_bind_wrong_snapshot(tmp_path):
    from iios_mvp.store import approve_revision, create_or_load_series, write_decision_revision, write_snapshot

    snap1, h1 = run_case(load_demo())
    snap2, h2 = run_case({**load_demo(), "cutoff_date": "2026-10-06"})
    write_snapshot(tmp_path, snap1)
    write_snapshot(tmp_path, snap2)
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-04T00:00:00Z")
    did = f"{series['decision_series_id']}-r001"
    write_decision_revision(tmp_path, series["decision_series_id"], 1, snap1, h1[:16])
    try:
        approve_revision(tmp_path, did, snap2, True, "wrong snapshot")
    except ValueError as exc:
        assert "same snapshot" in str(exc)
    else:
        raise AssertionError("wrong snapshot approval was accepted")


def test_trigger_contract_and_event_are_hashed_and_immutable(tmp_path):
    from iios_mvp.store import write_trigger_contract, write_trigger_event

    contract = {"trigger_id": "t1", "trigger_type": "PRICE", "metric": "market_price", "operator": "<=", "threshold": 350}
    event = {"trigger_event_id": "e1", "event_type": "PRICE", "metric": "market_price", "value": 349.5}
    cp = write_trigger_contract(tmp_path, "CN-A-300750-r001", contract)
    ep = write_trigger_event(tmp_path, event)
    assert cp.exists() and ep.exists()
    c = json.loads(cp.read_text())
    e = json.loads(ep.read_text())
    assert len(c["trigger_hash"]) == 64
    assert len(e["trigger_event_hash"]) == 64
    write_trigger_contract(tmp_path, "CN-A-300750-r001", contract)
    write_trigger_event(tmp_path, event)


def test_valuation_model_selection_is_not_pe_only():
    from iios_mvp.valuation import select_model
    selection = select_model({
        "model_selection": {
            "primary_model": "dcf",
            "economic_profile": "cash_flow_business",
            "rationale": "cash flow is the principal economic value driver",
            "alternatives": ["forward_pe"],
        }
    })
    assert selection["primary_model"] == "dcf"


def test_dcf_intrinsic_value_is_deterministic():
    from decimal import Decimal
    from iios_mvp.valuation import value_scenario
    forecast = {s: {"net_profit": 1} for s in ("bear", "base", "bull")}
    valuation = {
        "model_selection": {
            "primary_model": "dcf",
            "economic_profile": "cash_flow_business",
            "rationale": "cash flow is the principal economic value driver",
        },
        "model_inputs": {
            "dcf": {
                "base": {
                    "fcf": [100, 110, 121],
                    "discount_rate": 0.10,
                    "terminal_growth": 0.03,
                },
                "net_debt": 0,
            }
        },
    }
    a = value_scenario(forecast, valuation, "base", Decimal("10"))
    b = value_scenario(forecast, valuation, "base", Decimal("10"))
    assert a == b
    assert a["model"] == "dcf"
    assert a["value_per_share"] > 0


def test_sotp_values_segments_independently():
    from decimal import Decimal
    from iios_mvp.valuation import value_scenario
    forecast = {s: {"net_profit": 1} for s in ("bear", "base", "bull")}
    valuation = {
        "model_selection": {
            "primary_model": "sotp",
            "economic_profile": "mixed_businesses",
            "rationale": "material businesses have different value drivers",
        },
        "model_inputs": {
            "sotp": {
                "base": [
                    {"name": "mature", "model": "forward_pe", "net_profit": 100, "multiple": 10},
                    {"name": "growth", "model": "forward_pe", "net_profit": 50, "multiple": 20},
                ],
                "net_debt": 50,
                "other_assets": 100,
            }
        },
    }
    result = value_scenario(forecast, valuation, "base", Decimal("10"))
    assert result["model"] == "sotp"
    assert result["drivers"]["segment_count"] == 2
    assert result["equity_value"] == 2050.0


def test_extended_valuation_models():
    from decimal import Decimal
    from iios_mvp.valuation import route_model, value_scenario

    assert route_model("innovative_drug_commercial")["recommended_primary_model"] == "ps"
    assert route_model("cyclical")["recommended_primary_model"] == "pb"
    assert route_model("innovative_drug_pipeline")["recommended_primary_model"] == "rnpv"

    forecast = {s: {"net_profit": 1, "revenue": 100} for s in ("bear", "base", "bull")}

    ps = {
        "model_selection": {
            "primary_model": "ps",
            "economic_profile": "innovative_drug_commercial",
            "rationale": "commercial-stage revenue is the current observable value driver",
        },
        "model_inputs": {"ps": {"base": {"revenue": 100, "multiple": 8}}},
    }
    assert value_scenario(forecast, ps, "base", Decimal("10"))["value_per_share"] == 80.0

    pb = {
        "model_selection": {
            "primary_model": "pb",
            "economic_profile": "cyclical",
            "rationale": "cycle-normalized earnings are unstable and asset value is a key anchor",
        },
        "model_inputs": {"pb": {"base": {"book_equity": 500, "multiple": 1.2}}},
    }
    assert value_scenario(forecast, pb, "base", Decimal("10"))["value_per_share"] == 60.0

    ev = {
        "model_selection": {
            "primary_model": "ev_ebitda",
            "economic_profile": "enterprise_operating_business",
            "rationale": "capital structure-neutral operating earnings are the comparison basis",
        },
        "model_inputs": {"ev_ebitda": {"base": {"ebitda": 100, "multiple": 10, "net_debt": 200}}},
    }
    assert value_scenario(forecast, ev, "base", Decimal("10"))["value_per_share"] == 80.0

    rnpv = {
        "model_selection": {
            "primary_model": "rnpv",
            "economic_profile": "innovative_drug_pipeline",
            "rationale": "pipeline value depends on risk-adjusted future cash flows",
        },
        "model_inputs": {
            "rnpv": {
                "base": {
                    "cash_flows": [100, 200],
                    "probability_of_success": [0.5, 0.25],
                    "discount_rate": 0.1,
                }
            }
        },
    }
    result = value_scenario(forecast, rnpv, "base", Decimal("10"))
    assert result["model"] == "rnpv"
    assert result["value_per_share"] > 0
