from decimal import Decimal

from iios_mvp.engine import decide
from iios_mvp.price_dependent_expectation_gap import (
    P2_PRICE_GAP_REVALIDATION_VERSION,
    combine_target_entry_price_v2,
    revalidate_expectation_gap_at_price,
)
from tests.test_investment_core_v03 import (
    EVIDENCE_ROOT_REGISTRY,
    INDEPENDENT_FORECAST_REGISTRY,
    CURRENT_PRICE_REGISTRY,
    case,
)


def test_p2_revalidation_changes_market_expectation_with_candidate_price():
    c = case()
    snapshot = EVIDENCE_ROOT_REGISTRY.resolve_p4f_snapshot(
        c["market_implied_expectation_snapshot_ref"],
        case_id=c["case_id"],
        cutoff_date=__import__("datetime").date.fromisoformat(c["cutoff_date"]),
    )
    result = revalidate_expectation_gap_at_price(
        market_implied_expectation_snapshot=snapshot,
        current_price_observation=c["current_price_observation"],
        candidate_price="80",
        cutoff_date=c["cutoff_date"],
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        market_expectation_id=c["expectation_gap"]["market_expectation_id"],
        independent_forecast_ref=c["expectation_gap"]["independent_forecast_ref"],
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert result["status"] == "PASS"
    assert result["reference_price"] == "100"
    assert result["candidate_price"] == "80"
    assert result["reference_market_value"] == "10"
    assert result["candidate_market_value"] == "8"
    assert result["independent_value"] == "12"
    assert result["gap_positive"] is True
    assert Decimal(result["gap_relative"]) == Decimal("0.5")
    assert result["price_response_semantics"] == "PRICE_PROPORTIONAL_MODEL_WITH_ASSUMPTIONS_FROZEN"


def test_p2_revalidation_detects_gap_failure_at_higher_candidate_price():
    c = case()
    snapshot = EVIDENCE_ROOT_REGISTRY.resolve_p4f_snapshot(
        c["market_implied_expectation_snapshot_ref"],
        case_id=c["case_id"],
        cutoff_date=__import__("datetime").date.fromisoformat(c["cutoff_date"]),
    )
    result = revalidate_expectation_gap_at_price(
        market_implied_expectation_snapshot=snapshot,
        current_price_observation=c["current_price_observation"],
        candidate_price="130",
        cutoff_date=c["cutoff_date"],
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        market_expectation_id=c["expectation_gap"]["market_expectation_id"],
        independent_forecast_ref=c["expectation_gap"]["independent_forecast_ref"],
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert result["status"] == "NON_POSITIVE"
    assert result["gap_positive"] is False
    assert Decimal(result["candidate_market_value"]) == Decimal("13")
    assert Decimal(result["expectation_gap_price_boundary"]) == Decimal("120")


def test_p2_combines_return_target_with_expectation_gap_ceiling():
    revalidation = {
        "status": "PASS",
        "comparison_direction": "HIGHER_IS_BETTER",
        "expectation_gap_price_boundary": "120",
    }
    result = combine_target_entry_price_v2(
        return_target_entry_price="130",
        revalidation=revalidation,
    )
    assert result["status"] == "PASS"
    assert result["target_entry_price"] == Decimal("120")
    assert result["binding"] == "EXPECTATION_GAP_UPPER_BOUND"
    assert result["price_constraint_type"] == "UPPER_BOUND_STRICT"
    assert result["target_entry_price_inclusive"] is False


def test_p2_target_entry_price_2_is_integrated_into_decision_output():
    c = case()
    c["return_gate"]["entry_value_reference"] = "150"
    c["return_gate"]["scenarios"] = {
        "bear": {"probability": "0.2", "terminal_value_per_share": "180", "cash_distributions_per_share": "0", "probability_rationale": "P2 bear"},
        "base": {"probability": "0.5", "terminal_value_per_share": "220", "cash_distributions_per_share": "0", "probability_rationale": "P2 base"},
        "bull": {"probability": "0.3", "terminal_value_per_share": "260", "cash_distributions_per_share": "0", "probability_rationale": "P2 bull"},
    }
    result = decide(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert result["decision"]["action"] == "BUY"
    assert result["decision"]["target_entry_price_return_only"] is not None
    assert Decimal(result["decision"]["target_entry_price_return_only"]) > Decimal("120")
    assert result["decision"]["target_entry_price"] == "120"
    assert result["decision"]["target_entry_price_v2_version"] == P2_PRICE_GAP_REVALIDATION_VERSION
    assert result["decision"]["target_entry_price_v2"]["status"] == "PASS"
    assert result["decision"]["target_entry_price_v2"]["binding"] == "EXPECTATION_GAP_UPPER_BOUND"
    assert result["decision"]["target_entry_price_v2"]["target_entry_price_inclusive"] is False
    assert result["decision"]["target_entry_price_gap_revalidation"]["status"] == "NON_POSITIVE"
    assert Decimal(result["decision"]["target_entry_price_gap_revalidation"]["expectation_gap_price_boundary"]) == Decimal("120")
    assert result["gates"]["target_entry_price_v2_status"] == "PASS"
    assert result["gates"]["target_entry_price_for_expectation_gap"] == "120"


def test_p2_unsupported_price_response_fails_closed_for_target_price_only():
    result = combine_target_entry_price_v2(
        return_target_entry_price="100",
        revalidation={
            "status": "REVIEW_REQUIRED",
            "comparison_direction": "HIGHER_IS_BETTER",
        },
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["target_entry_price"] is None


def test_p2_revalidation_does_not_mutate_canonical_current_price():
    c = case()
    original = c["current_price_observation"]["price"]
    snapshot = EVIDENCE_ROOT_REGISTRY.resolve_p4f_snapshot(
        c["market_implied_expectation_snapshot_ref"],
        case_id=c["case_id"],
        cutoff_date=__import__("datetime").date.fromisoformat(c["cutoff_date"]),
    )
    revalidate_expectation_gap_at_price(
        market_implied_expectation_snapshot=snapshot,
        current_price_observation=c["current_price_observation"],
        candidate_price="80",
        cutoff_date=c["cutoff_date"],
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        market_expectation_id=c["expectation_gap"]["market_expectation_id"],
        independent_forecast_ref=c["expectation_gap"]["independent_forecast_ref"],
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert c["current_price_observation"]["price"] == original
