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
