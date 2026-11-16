from __future__ import annotations

import json
from pathlib import Path

from iios_mvp.expectation_gap_comparison_v01 import build_expectation_gap_comparison
from iios_mvp.local_investment_pilot_v01 import _render_core_investment_synthesis


ROOT = Path(__file__).resolve().parents[1]
REAL_CASES = ROOT / "examples" / "real_cases"


def _load_real_case(filename: str) -> dict:
    return json.loads((REAL_CASES / filename).read_text(encoding="utf-8"))


def _legacy_case_b76_report(case: dict, *, model_family: str, price: str | None):
    """Exercise the real legacy research input without inventing missing B4/B57/B61 data."""
    local_sotp = {
        "selected_model_family": model_family,
        "currency": "CNY",
        # The legacy input does not contain a calculated B60/B61 inversion.
        "expectation_gap_comparison": None,
    }
    price_input = {"price": price, "currency": "CNY"} if price is not None else {"price": None, "currency": "CNY"}
    b76 = build_expectation_gap_comparison(
        local_sotp_recalculation=local_sotp,
        return_metrics=None,
        price_input=price_input,
        forecast_valuation={"model_family": model_family, "scenarios": {}},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=None,
    )
    local_sotp["expectation_gap_comparison"] = b76
    price_implied = {
        "local_sotp_recalculation": local_sotp,
    }
    if price is not None:
        price_implied["reference_price"] = None
    analysis = {
        "case": {
            "company": case["company"],
            "symbol": case["symbol"],
            "currency": "CNY",
        },
        "price_input": price_input,
        "assessment": {
            "trust": {"status": "UNKNOWN"},
            "reality": {"status": "UNKNOWN"},
            "quality": {"status": "UNKNOWN"},
            "thesis": {"core_statement": case.get("thesis", {}).get("statement", "UNKNOWN"), "drivers": []},
            "value_drivers": [],
            "market_implied_expectation": {
                "status": "NOT_IDENTIFIABLE",
                "summary": "Legacy case contains no admitted current-format B60/B61 inversion.",
                "price_implied_analysis": price_implied,
            },
        },
        "forecast_valuation": {"model_family": model_family, "scenarios": {}},
    }
    return b76, "\n".join(_render_core_investment_synthesis(analysis))


def test_real_xinhecheng_eps_multiple_legacy_case_is_visible_but_not_promoted_to_fake_b76_gap():
    case = _load_real_case("RC-CN-A-002001-20261007_pilot02_input.json")
    assert case["symbol"] == "002001"
    assert case["valuation"]["primary_model"] == "FORWARD_PE"
    assert case["forecast_assumptions"]["scenarios"]["base"]["normalized_eps_cny"] == "2.80"
    # The legacy case stores normalized EPS and P/E assumptions, not the modern
    # B57 all-items profit/share bridge, B58 basis reconciliation or B60 inversion.
    b76, report = _legacy_case_b76_report(case, model_family="EPS_MULTIPLE", price=None)
    assert b76["status"] == "BLOCKED_BY_B60_RESULT_MISSING"
    assert b76["eps_multiple_comparison"]["status"] == "BLOCKED_BY_B60_RESULT_MISSING"
    assert b76["eps_multiple_comparison"]["scenarios"] == {}
    assert case["company"] in report and "002001" in report
    assert "EPS_MULTIPLE" in report
    assert "BLOCKED_BY_B60_RESULT_MISSING" in report
    assert "B4/B57 all-items EPS" not in report
    assert "forecast_minus_required_cny_per_share" not in report
    assert "headroom_vs_required_pct" not in report
    assert b76["external_mie_modified"] is False


def test_real_kolun_sotp_legacy_case_is_visible_but_missing_segment_profit_bridge_stays_unknown():
    case = _load_real_case("RC-CN-A-002422-20261004_c3_input.json")
    assert case["symbol"] == "002422"
    assert case["valuation"]["primary_model"] == "SOTP"
    assert case["evidence"][-1]["value"] == 40.85
    assert case["valuation"]["scenario_values_per_share"]["base"] == "58"
    # The legacy SOTP contains per-share value components, but no B61 reference
    # inversion or B62/B63/B68 normalized segment earnings/value-pool chain.
    b76, report = _legacy_case_b76_report(case, model_family="SOTP", price="40.85")
    assert b76["status"] == "PRICE_REFERENCE_NOT_IDENTIFIABLE"
    assert b76["price_reference_status"] == "NOT_IDENTIFIABLE"
    assert b76["scenarios"] == {}
    assert b76["external_mie_modified"] is False
    assert case["company"] in report and "002422" in report
    assert "SOTP" in report
    assert "PRICE_REFERENCE_NOT_IDENTIFIABLE" in report
    assert "B4 前瞻分部价值池" not in report
    assert "价值池余量 50 CNY" not in report
    assert "B4 前瞻分部价值池 1250 CNY" not in report
    assert "40.85" in report
