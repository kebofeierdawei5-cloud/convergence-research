import json
from pathlib import Path

import pytest

from iios_mvp.core03_market_expectation import build_core03_package, validate_core03_package


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "examples" / "real_cases" / "RC-CN-A-300750-20261004_core03_input.json"


def _input():
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def test_real_300750_core03_full_path_is_executable():
    payload = _input()
    result = build_core03_package(
        payload["core02_input"],
        payload["forecast"],
        payload["valuation_assumptions"],
        payload["market_evidence"],
        payload["forecast_evidence"],
    )
    assert result["case_id"] == "RC-CN-A-300750-20261004"
    assert result["status"] == "CONDITIONAL"
    assert result["core02_status"] == "CONDITIONAL"
    assert result["independent_forecast"]["method"] == "BOTTOM_UP_DRIVER_SCENARIO"
    assert result["company_valuation"]["primary_model"] == "dcf"
    assert result["company_valuation"]["selection_authority"] == "HUMAN"
    assert result["p4f_market_implied_expectation"]["status"] == "BLOCKED"
    assert result["p4f_market_implied_expectation"]["qualification"] == "BLOCKED"
    assert result["expectation_gap"]["status"] == "BLOCKED"
    assert result["expectation_gap"]["not_substituted_by_intrinsic_upside"] is True
    assert validate_core03_package(result) == []


def test_real_300750_valuation_outputs_are_deterministic_and_ordered():
    payload = _input()
    result = build_core03_package(
        payload["core02_input"],
        payload["forecast"],
        payload["valuation_assumptions"],
        payload["market_evidence"],
        payload["forecast_evidence"],
    )
    valuation = result["company_valuation"]
    bear = float(valuation["intrinsic_value_range"]["bear"])
    base = float(valuation["intrinsic_value_range"]["base"])
    bull = float(valuation["intrinsic_value_range"]["bull"])
    expected = float(valuation["probability_weighted_value_per_share"])
    cagr = float(valuation["expected_3y_cagr_at_current_price"])
    assert bear < base < bull
    assert expected > base * 0.99
    assert expected < bull
    assert 0.13 < cagr < 0.15


def test_p4f_blocked_snapshot_replays():
    payload = _input()
    result = build_core03_package(
        payload["core02_input"],
        payload["forecast"],
        payload["valuation_assumptions"],
        payload["market_evidence"],
        payload["forecast_evidence"],
    )
    replay = result["p4f_market_implied_expectation"]["replay"]
    assert replay["replay_status"] == "PASS"
    assert replay["integrity_status"] == "PASS"
    assert replay["pit_status"] == "PASS"
    assert replay["provenance_status"] == "PASS"
    assert replay["semantic_status"] == "PASS"


def test_forecast_does_not_use_fm01_blocked_dataset():
    payload = _input()
    result = build_core03_package(
        payload["core02_input"],
        payload["forecast"],
        payload["valuation_assumptions"],
        payload["market_evidence"],
        payload["forecast_evidence"],
    )
    assert result["independent_forecast"]["method"] != "FM01_PRODUCTION_ROUTER"
    assert set(result["independent_forecast"]["scenarios"]["base"]["evidence_ids"]) >= {"E004", "E005", "E009"}


def test_future_forecast_evidence_fails_closed():
    payload = _input()
    bad = dict(payload["forecast_evidence"][0])
    bad["known_at"] = "2026-10-05T00:00:00+08:00"
    payload["forecast_evidence"] = [bad]
    with pytest.raises(ValueError, match="violates PIT"):
        build_core03_package(
            payload["core02_input"],
            payload["forecast"],
            payload["valuation_assumptions"],
            payload["market_evidence"],
            payload["forecast_evidence"],
        )


def test_corrupt_core03_audit_hash_is_rejected():
    payload = _input()
    result = build_core03_package(
        payload["core02_input"],
        payload["forecast"],
        payload["valuation_assumptions"],
        payload["market_evidence"],
        payload["forecast_evidence"],
    )
    result["company_valuation"]["primary_model"] = "ev_ebitda"
    assert "CORE03_HASH_MISMATCH" in validate_core03_package(result)
