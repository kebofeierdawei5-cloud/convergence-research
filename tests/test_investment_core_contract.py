from __future__ import annotations

from copy import deepcopy

from iios_mvp.investment_core_contract import validate_investment_core_case


def valid_case():
    return {
        "contract_version": "IIOS-INVESTMENT-CORE-0.2",
        "case_id": "P2A-001",
        "market": "CN-A",
        "symbol": "300750",
        "company": "CATL",
        "as_of_date": "2026-10-04",
        "cutoff_date": "2026-10-04",
        "company_evidence_manifest": {"manifest_id": "company-test-001"},
        "market_evidence_manifest": {"manifest_id": "market-test-001"},
        "current_price_observation": {
            "price": "400",
            "currency": "CNY",
            "observed_at": "2026-10-04T10:00:00+08:00",
            "known_at": "2026-10-04T10:00:00+08:00",
            "source": "test",
            "adjustment_semantics": "UNADJUSTED",
        },
        "trust": {"status": "PASS"},
        "reality": {},
        "forecast": {},
        "valuation": {},
        "market_implied_expectation": {
            "market_model": "forward_pe",
            "identifiability": "IDENTIFIABLE",
            "stability": "STABLE",
            "economic_variables": [{"name": "forward_eps", "unit": "CNY/share", "basis": "forward"}],
            "observation_basis": {"price_observation_date": "2026-10-04", "cutoff_date": "2026-10-04"},
            "assumption_set": {},
            "evidence_sufficiency": True,
            "selected_market_model": "forward_pe",
        },
        "expectation_gap": {
            "status": "PASS",
            "economic_variable": "forward_eps",
            "unit": "CNY/share",
            "model": "forward_pe",
            "independent_value": {"value": "20", "unit": "CNY/share", "economic_variable": "forward_eps"},
            "market_implied_value": {"value": "15", "unit": "CNY/share", "economic_variable": "forward_eps"},
            "gap_direction": "POSITIVE",
        },
        "return_gate": {
            "entry_price": "400",
            "scenario_values": {"bear": "360", "base": "500", "bull": "700"},
            "scenarios": {
                "bear": {"probability": "0.2"},
                "base": {"probability": "0.5"},
                "bull": {"probability": "0.3"},
            },
            "expected_value": "530",
            "expected_return_pct": "32.5",
            "hurdle_pct": "15",
            "hurdle_pass": True,
        },
        "risk": {"status": "PASS", "max_loss_pct": "20"},
        "portfolio": {"position_pct": "0"},
        "thesis": {"status": "INTACT"},
        "decision": {"action": "BUY"},
    }


def codes(result):
    return {e["code"] for e in result["errors"]}


def test_valid_v02_case_passes():
    assert validate_investment_core_case(valid_case())["status"] == "PASS"


def test_wrong_contract_version_blocks():
    case = valid_case()
    case["contract_version"] = "IIOS-INVESTMENT-CORE-0.1"
    assert "CORE-VERSION-EXACT" in codes(validate_investment_core_case(case))


def test_price_known_after_cutoff_blocks():
    case = valid_case()
    case["current_price_observation"]["known_at"] = "2026-10-05T09:00:00+08:00"
    assert "CORE-PIT-PRICE-KNOWN-AT" in codes(validate_investment_core_case(case))


def test_gap_variable_mismatch_blocks():
    case = valid_case()
    case["expectation_gap"]["market_implied_value"]["economic_variable"] = "revenue"
    assert "CORE-INVARIANT-GAP-VARIABLE-MISMATCH" in codes(validate_investment_core_case(case))


def test_ambiguous_market_cannot_select_winner():
    case = valid_case()
    case["market_implied_expectation"]["identifiability"] = "AMBIGUOUS"
    assert "CORE-INVARIANT-NO-FORCED-WINNER" in codes(validate_investment_core_case(case))


def test_probability_sum_must_equal_one():
    case = valid_case()
    case["return_gate"]["scenarios"]["bull"]["probability"] = "0.2"
    assert "CORE-INVARIANT-PROBABILITY-SUM" in codes(validate_investment_core_case(case))


def test_expected_return_is_recomputed():
    case = valid_case()
    case["return_gate"]["expected_return_pct"] = "15"
    assert "CORE-INVARIANT-EXPECTED-RETURN" in codes(validate_investment_core_case(case))


def test_exact_15_percent_fails_hurdle():
    case = valid_case()
    case["return_gate"]["scenario_values"] = {"bear": "400", "base": "460", "bull": "520"}
    case["return_gate"]["expected_value"] = "460"
    case["return_gate"]["expected_return_pct"] = "15"
    case["return_gate"]["hurdle_pass"] = False
    assert validate_investment_core_case(case)["status"] == "PASS"


def test_buy_requires_identifiable_and_stable_market_view():
    case = valid_case()
    case["market_implied_expectation"]["stability"] = "UNSTABLE"
    result = validate_investment_core_case(case)
    assert "CORE-GATE-BUY-MARKET-STABILITY" in codes(result)


def test_buy_cannot_bypass_trust():
    case = valid_case()
    case["trust"]["status"] = "FAIL"
    assert "CORE-GATE-BUY-TRUST" in codes(validate_investment_core_case(case))


def test_v02_case_cannot_fall_back_to_legacy_engine_path():
    from iios_mvp.engine import validate_case
    case = valid_case()
    case["valuation"]["market_implied_multiple"] = "20"
    blockers = validate_case(case)
    assert not any(item.startswith("MISSING_FIELD:") for item in blockers)
    assert "CORE-INVARIANT-NO-LEGACY-MARKET-SEMANTICS:valuation.market_implied_multiple:legacy v0.1.1 market/return field is forbidden in a v0.2 case" in blockers


def test_v02_requires_evidence_manifests():
    case = valid_case()
    del case["company_evidence_manifest"]
    result = validate_investment_core_case(case)
    assert "CORE-SCHEMA-REQUIRED" in codes(result)


def test_v02_buy_requires_risk_pass():
    case = valid_case()
    case["risk"]["status"] = "UNKNOWN"
    result = validate_investment_core_case(case)
    assert "CORE-GATE-BUY-RISK" in codes(result)
