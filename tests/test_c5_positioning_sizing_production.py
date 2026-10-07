from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.engine import decide
from iios_mvp.positioning_sizing_production import (
    C5_POLICY_EFFECT,
    C5_POLICY_VERSION,
    C5_POSITIONING_SIZING_VERSION,
    build_positioning_sizing,
    replay_positioning_sizing,
    validate_positioning_sizing,
)
from tests.test_investment_core_v03 import (
    CURRENT_PRICE_REGISTRY,
    EVIDENCE_ROOT_REGISTRY,
    INDEPENDENT_FORECAST_REGISTRY,
    UPSTREAM_AUTHORITY_REGISTRY,
    VALUATION_OUTPUT_RESOLVER,
    case,
)

ROOT = Path(__file__).resolve().parents[1]


def positioning(**overrides):
    value = {
        "observation_id": "pos-300750-20261004",
        "price_zones": {
            "entry_zone": ["95", "100"],
            "add_zone": ["90", "95"],
            "reduce_zone": ["110", "120"],
        },
        "observation_as_of_date": "2026-10-04",
        "known_at": "2026-10-04T15:30:00+00:00",
        "source": "fixture-positioning-source",
        "source_bundle_sha256": "c" * 64,
        "evidence_ids": ["pos-market-1", "pos-industry-1", "pos-stock-1", "pos-holder-1", "pos-crowding-1"],
        "market_regime": "BULL",
        "industry_sentiment": "POSITIVE",
        "stock_structure": "UP",
        "holder_capital_structure": "SUPPORTIVE",
        "crowding_supply_pressure": "LOW",
    }
    value.update(overrides)
    return value


def test_c5_favorable_snapshot_produces_target_sizing_band():
    record = build_positioning_sizing(case=case(), positioning=positioning())
    assert record["evaluation_version"] == C5_POSITIONING_SIZING_VERSION
    assert record["policy_version"] == C5_POLICY_VERSION
    assert record["status"] == "PASS"
    assert record["composite_score"] == 5
    assert record["timing_bias"] == "FAVORABLE"
    assert record["sizing_band"] == "TARGET"
    assert record["sizing_permission"] == "ALLOW_UP_TO_TARGET"
    assert record["permitted_position_pct"] == "10"
    assert record["entry_zone"] == ["95", "100"]
    assert record["add_zone"] == ["90", "95"]
    assert record["reduce_zone"] == ["110", "120"]
    assert record["hard_exposure_limit"] == "10"
    assert record["policy_effect"] == C5_POLICY_EFFECT


def test_c5_neutral_snapshot_limits_new_sizing_to_initial():
    p = positioning(
        market_regime="NEUTRAL",
        industry_sentiment="NEUTRAL",
        stock_structure="RANGE",
        holder_capital_structure="NEUTRAL",
        crowding_supply_pressure="MEDIUM",
    )
    record = build_positioning_sizing(case=case(), positioning=p)
    assert record["status"] == "PASS"
    assert record["composite_score"] == 0
    assert record["timing_bias"] == "NEUTRAL"
    assert record["sizing_band"] == "INITIAL"
    assert record["sizing_permission"] == "ALLOW_UP_TO_INITIAL"
    assert record["permitted_position_pct"] == "5"


def test_c5_unfavorable_snapshot_stops_adds_but_does_not_rewrite_decision():
    p = positioning(
        market_regime="BEAR",
        industry_sentiment="NEGATIVE",
        stock_structure="DOWN",
        holder_capital_structure="OVERHANG",
        crowding_supply_pressure="HIGH",
    )
    record = build_positioning_sizing(case=case(), positioning=p)
    assert record["status"] == "PASS"
    assert record["composite_score"] == -5
    assert record["timing_bias"] == "UNFAVORABLE"
    assert record["sizing_band"] == "CURRENT"
    assert record["sizing_permission"] == "HOLD_CURRENT_NO_ADD"
    assert record["permitted_position_pct"] == "0"

    c = case()
    c["positioning"] = p
    result = decide(
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert result["decision"]["action"] == "BUY"
    assert result["decision"]["positioning_sizing"]["timing_bias"] == "UNFAVORABLE"
    assert result["decision"]["positioning_sizing"]["sizing_permission"] == "HOLD_CURRENT_NO_ADD"
    assert result["gates"]["positioning_sizing_status"] == "PASS"


def test_c5_unknown_or_ambiguous_positioning_fails_closed_for_sizing():
    record = build_positioning_sizing(
        case=case(),
        positioning=positioning(stock_structure="AMBIGUOUS"),
    )
    assert record["status"] == "BLOCKED"
    assert record["sizing_permission"] == "NO_SIZING_PERMISSION"
    assert record["composite_score"] is None
    assert record["permitted_position_pct"] is None


def test_c5_stale_positioning_known_at_is_fail_closed():
    record = build_positioning_sizing(
        case=case(),
        positioning=positioning(known_at="2026-10-05T09:00:00+00:00"),
    )
    assert record["status"] == "BLOCKED"
    assert record["reason"] == "positioning evidence became known after case cutoff"
    assert record["sizing_permission"] == "NO_SIZING_PERMISSION"


def test_c5_missing_positioning_is_explicitly_blocked():
    record = build_positioning_sizing(case=case(), positioning=None)
    assert record["status"] == "BLOCKED"
    assert record["sizing_band"] == "NONE"
    assert record["sizing_permission"] == "NO_SIZING_PERMISSION"
    validate_positioning_sizing(record)


def test_c5_missing_portfolio_package_blocks_sizing_without_affecting_factors():
    c = case()
    c["portfolio"] = {
        "position_pct": "0",
        "constraint_status": "PASS",
        "can_add": True,
    }
    record = build_positioning_sizing(case=c, positioning=positioning())
    assert record["status"] == "BLOCKED"
    assert "buy_add_package" in record["reason"]
    assert record["composite_score"] is None
    assert record["sizing_permission"] == "NO_SIZING_PERMISSION"


def test_c5_deterministic_replay_and_tamper_detection():
    record = build_positioning_sizing(case=case(), positioning=positioning())
    validate_positioning_sizing(record)
    replay = replay_positioning_sizing(record)
    assert replay["replay_status"] == "PASS"
    assert replay["deterministic_replay"] is True

    tampered = deepcopy(record)
    tampered["reason"] = "tampered"
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_positioning_sizing(tampered)


def test_c5_schema_accepts_record():
    record = build_positioning_sizing(case=case(), positioning=positioning())
    schema = json.loads(
        (ROOT / "schemas/c5_positioning_sizing_v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record)
    ) == []


def test_c5_projection_is_optional_and_action_stays_fundamental():
    c = case()
    result_without = decide(
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert "positioning_sizing" in result_without["decision"]

    c["positioning"] = positioning(industry_sentiment="NEGATIVE")
    result_with = decide(
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert result_with["decision"]["action"] == result_without["decision"]["action"]
    assert result_with["gates"]["positioning_sizing_status"] == "PASS"
    assert result_with["gates"]["positioning_sizing_permission"] in {
        "ALLOW_UP_TO_TARGET",
        "ALLOW_UP_TO_INITIAL",
        "HOLD_CURRENT_NO_ADD",
    }
