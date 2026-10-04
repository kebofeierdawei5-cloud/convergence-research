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
            "selection_method": "HUMAN",
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
            "selection_method": "HUMAN",
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
            "selection_method": "HUMAN",
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

    assert route_model("innovative_drug_commercial")["candidate_models"][0] == "ps"
    assert route_model("cyclical")["candidate_models"][0] == "pb"
    assert route_model("innovative_drug_pipeline")["candidate_models"][0] == "rnpv"

    forecast = {s: {"net_profit": 1, "revenue": 100} for s in ("bear", "base", "bull")}

    ps = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "ps",
            "economic_profile": "innovative_drug_commercial",
            "rationale": "commercial-stage revenue is the current observable value driver",
        },
        "model_inputs": {"ps": {"base": {"revenue": 100, "multiple": 8}}},
    }
    assert value_scenario(forecast, ps, "base", Decimal("10"))["value_per_share"] == 80.0

    pb = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "pb",
            "economic_profile": "cyclical",
            "rationale": "cycle-normalized earnings are unstable and asset value is a key anchor",
        },
        "model_inputs": {"pb": {"base": {"book_equity": 500, "multiple": 1.2}}},
    }
    assert value_scenario(forecast, pb, "base", Decimal("10"))["value_per_share"] == 60.0

    ev = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "ev_ebitda",
            "economic_profile": "enterprise_operating_business",
            "rationale": "capital structure-neutral operating earnings are the comparison basis",
        },
        "model_inputs": {"ev_ebitda": {"base": {"ebitda": 100, "multiple": 10, "net_debt": 200}}},
    }
    assert value_scenario(forecast, ev, "base", Decimal("10"))["value_per_share"] == 80.0

    rnpv = {
        "model_selection": {
            "selection_method": "HUMAN",
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


def test_model_suitability_returns_primary_secondary_and_cross_check():
    from iios_mvp.valuation import assess_model_suitability, route_model
    assessment = assess_model_suitability("cyclical")
    assert assessment["ranked_models"][0]["model"] == "pb"
    route = route_model("cyclical")
    assert route["candidate_models"][0] == "pb"
    assert route["candidate_models"][1] == "ev_ebitda"
    assert route["candidate_models"][2] == "dcf"


def test_primary_authoritative_aggregation_does_not_average_checks():
    from decimal import Decimal
    from iios_mvp.valuation import build_intrinsic_valuation
    forecast = {s: {"net_profit": 100, "revenue": 1000} for s in ("bear", "base", "bull")}
    valuation = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "forward_pe",
            "economic_profile": "mature_earnings",
            "rationale": "normalized earnings are the primary value driver",
            "secondary_models": ["dcf"],
        },
        "base_multiple": 10,
        "bear_multiple": 8,
        "bull_multiple": 12,
        "model_inputs": {
            "dcf": {
                "base": {"fcf": [200, 200], "discount_rate": 0.10, "terminal_growth": 0.02},
                "bear": {"fcf": [100, 100], "discount_rate": 0.12, "terminal_growth": 0.01},
                "bull": {"fcf": [300, 300], "discount_rate": 0.09, "terminal_growth": 0.03},
            }
        },
    }
    result = build_intrinsic_valuation(forecast, valuation, Decimal("10"))
    assert result["aggregation"]["method"] == "primary_authoritative_no_arbitrary_average"
    assert result["aggregation"]["weights"] == {"forward_pe": 1.0}
    assert result["intrinsic_value_per_share"] == 100.0
    assert result["model_cross_check_dispersion"] is not None


def test_explicit_model_weights_require_complete_models_and_sum_to_one():
    from decimal import Decimal
    from iios_mvp.valuation import build_intrinsic_valuation
    forecast = {s: {"net_profit": 100, "revenue": 1000} for s in ("bear", "base", "bull")}
    valuation = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "forward_pe",
            "economic_profile": "mature_earnings",
            "rationale": "normalized earnings are the primary value driver",
            "secondary_models": ["dcf"],
        },
        "base_multiple": 10, "bear_multiple": 8, "bull_multiple": 12,
        "aggregation": {"model_weights": {"forward_pe": 0.7, "dcf": 0.3}},
        "model_inputs": {
            "dcf": {
                "base": {"fcf": [200, 200], "discount_rate": 0.10, "terminal_growth": 0.02},
                "bear": {"fcf": [100, 100], "discount_rate": 0.12, "terminal_growth": 0.01},
                "bull": {"fcf": [300, 300], "discount_rate": 0.09, "terminal_growth": 0.03},
            }
        },
    }
    result = build_intrinsic_valuation(forecast, valuation, Decimal("10"))
    assert result["aggregation"]["method"] == "explicit_weighted_average"
    assert result["aggregation"]["weights"] == {"forward_pe": 0.7, "dcf": 0.3}


def test_rnpv_pipeline_assets_support_delay_and_asset_level_probability():
    from decimal import Decimal
    from iios_mvp.valuation import build_intrinsic_valuation
    forecast = {s: {"net_profit": 1, "revenue": 1} for s in ("bear", "base", "bull")}
    valuation = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "rnpv",
            "economic_profile": "innovative_drug_pipeline",
            "rationale": "pipeline assets require risk-adjusted valuation",
        },
        "model_inputs": {
            "rnpv": {
                "base": {
                    "discount_rate": 0.10,
                    "pipeline": [
                        {
                            "name": "Drug-A",
                            "launch_delay_periods": 1,
                            "cash_flows": [100, 100],
                            "probability_of_success": [0.5, 0.5],
                        },
                        {
                            "name": "Drug-B",
                            "cash_flows": [{"cash_flow": 50, "risk_adjust": False}],
                            "probability_of_success": [0.8],
                        },
                    ],
                },
                "bear": {"discount_rate": 0.12, "pipeline": [{"name": "A", "cash_flows": [50], "probability_of_success": [0.4]}]},
                "bull": {"discount_rate": 0.09, "pipeline": [{"name": "A", "cash_flows": [150], "probability_of_success": [0.7]}]},
            }
        },
    }
    result = build_intrinsic_valuation(forecast, valuation, Decimal("10"))
    assert result["model_selection"]["primary_model"] == "rnpv"
    assert result["model_status"]["rnpv"]["base_status"] == "PASS"
    assert result["models"]["rnpv"]["base"]["drivers"]["asset_count"] == 2


def test_sotp_supports_mixed_models_and_ownership():
    from decimal import Decimal
    from iios_mvp.valuation import build_intrinsic_valuation
    forecast = {s: {"net_profit": 100, "revenue": 1000} for s in ("bear", "base", "bull")}
    valuation = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "sotp",
            "economic_profile": "mixed_segments",
            "rationale": "segments have materially different economic drivers",
        },
        "model_inputs": {
            "sotp": {
                "base": {
                    "segments": [
                        {"name": "mature", "model": "forward_pe", "net_profit": 100, "multiple": 10},
                        {"name": "pipeline", "model": "rnpv", "cash_flows": [100], "probability_of_success": [0.5], "discount_rate": 0.1, "ownership_pct": 80},
                    ]
                },
                "bear": {"segments": [{"name": "mature", "model": "forward_pe", "net_profit": 80, "multiple": 8}]},
                "bull": {"segments": [{"name": "mature", "model": "forward_pe", "net_profit": 120, "multiple": 12}]},
            }
        },
    }
    result = build_intrinsic_valuation(forecast, valuation, Decimal("10"))
    assert result["models"]["sotp"]["base"]["drivers"]["segment_count"] == 2
    assert result["intrinsic_value_range"]["low"] < result["intrinsic_value_range"]["base"] < result["intrinsic_value_range"]["high"]


def test_intrinsic_value_gate_fails_on_bad_scenario_order():
    from iios_mvp.valuation import evaluate_intrinsic_value_gate
    result = {
        "model_selection": {"primary_model": "pb", "economic_profile": "cyclical", "rationale": "asset value"},
        "scenarios": {"bear_value_per_share": 20, "base_value_per_share": 10, "bull_value_per_share": 30},
        "model_status": {"pb": {"bear_status": "PASS", "base_status": "PASS", "bull_status": "PASS"}},
        "aggregation": {"weights": {"pb": 1.0}},
    }
    gate = evaluate_intrinsic_value_gate(result)
    assert gate["status"] == "BLOCKED"
    assert "SCENARIO_ORDER_INVALID" in gate["blockers"]


def test_intrinsic_value_gate_passes_valid_range():
    from iios_mvp.valuation import evaluate_intrinsic_value_gate
    result = {
        "model_selection": {"primary_model": "pb", "economic_profile": "cyclical", "rationale": "asset value"},
        "scenarios": {"bear_value_per_share": 8, "base_value_per_share": 12, "bull_value_per_share": 18},
        "model_status": {"pb": {"bear_status": "PASS", "base_status": "PASS", "bull_status": "PASS"}},
        "aggregation": {"weights": {"pb": 1.0}},
    }
    assert evaluate_intrinsic_value_gate(result)["status"] == "PASS"


def test_human_selection_is_required_and_router_is_advisory():
    from iios_mvp.valuation import select_model, route_model
    route = route_model("mature_cash_earning_business")
    assert route["candidate_models"][0] == "forward_pe"
    case = {"model_selection": {"primary_model": "dcf", "economic_profile": "mature_cash_earning_business", "rationale": "cash flow is the principal driver"}}
    try:
        select_model(case)
    except ValueError as exc:
        assert "selection_method" in str(exc)
    else:
        raise AssertionError("missing HUMAN selection method did not fail closed")


def test_human_selection_can_override_advisory_candidates_with_reason():
    from iios_mvp.valuation import select_model
    result = select_model({"model_selection": {"selection_method": "HUMAN", "primary_model": "rnpv", "economic_profile": "mature_cash_earning_business", "rationale": "material contingent asset requires risk-adjusted valuation", "override_reason": "company economics include a material separately valued pipeline"}})
    assert result["selection_outside_candidates"] is True
