from __future__ import annotations

from iios_mvp.value_core import scan_company_value_core


def attrs(**overrides):
    base = {
        "earnings_stability": "HIGH",
        "cash_flow_visibility": "HIGH",
        "capital_intensity": "LOW",
        "cyclicality": "LOW",
        "asset_intensity": "LOW",
        "reinvestment_intensity": "MEDIUM",
        "payout_characteristic": "MEDIUM",
        "pipeline_optionality": "NONE",
        "maturity": "MATURE",
    }
    base.update(overrides)
    return base


def test_tencent_value_core_is_mixed_and_scans_capital_intensive_ai_growth():
    result = scan_company_value_core({
        "version": "1.0",
        "nodes": [
            {"id": "core_cash", "name": "Core cash-generating businesses", "node_type": "operating_business", "materiality": "HIGH",
             "economic_attributes": attrs()},
            {"id": "growth", "name": "Cloud / AI growth", "node_type": "operating_business", "materiality": "HIGH",
             "economic_attributes": attrs(cash_flow_visibility="MEDIUM", capital_intensity="HIGH", reinvestment_intensity="HIGH")},
            {"id": "investments", "name": "Investment portfolio", "node_type": "investment_asset", "materiality": "HIGH",
             "economic_attributes": attrs(cash_flow_visibility="LOW", asset_intensity="HIGH", payout_characteristic="LOW")},
        ],
    })
    assert result["status"] == "PASS"
    assert result["overall_economic_profile"] == "mixed_segments"
    assert result["value_structure"]["core_asset_count"] == 3
    growth = next(x for x in result["nodes"] if x["id"] == "growth")
    assert growth["derived_economic_profile"] == "enterprise_operating_business"
    assert growth["recommended_primary_model"] == "ev_ebitda"


def test_catl_value_core_is_mature_cash_earning_with_capex_reinvestment_visible():
    result = scan_company_value_core({
        "version": "1.0",
        "nodes": [
            {"id": "battery", "name": "Battery / energy storage", "node_type": "operating_business", "materiality": "HIGH",
             "economic_attributes": attrs(capital_intensity="HIGH", reinvestment_intensity="HIGH", cyclicality="MEDIUM")},
        ],
    })
    assert result["status"] == "PASS"
    assert result["overall_economic_profile"] == "enterprise_operating_business"
    assert result["model_route"]["recommended_primary_model"] == "ev_ebitda"


def test_kolun_value_core_is_mixed_and_requires_independent_pipeline_valuation():
    result = scan_company_value_core({
        "version": "1.0",
        "nodes": [
            {"id": "mature_pharma", "name": "Mature pharmaceutical business", "node_type": "operating_business", "materiality": "HIGH",
             "economic_attributes": attrs()},
            {"id": "pipeline", "name": "Innovative drug pipeline", "node_type": "pipeline", "materiality": "HIGH",
             "economic_attributes": attrs(earnings_stability="LOW", cash_flow_visibility="LOW", capital_intensity="MEDIUM",
                                           asset_intensity="MEDIUM", reinvestment_intensity="HIGH",
                                           payout_characteristic="LOW", pipeline_optionality="HIGH", maturity="DEVELOPMENT")},
            {"id": "subsidiary", "name": "Material subsidiary", "node_type": "subsidiary", "materiality": "MEDIUM",
             "economic_attributes": attrs(earnings_stability="MEDIUM", cash_flow_visibility="MEDIUM", capital_intensity="MEDIUM")},
        ],
    })
    assert result["status"] == "PASS"
    assert result["overall_economic_profile"] == "mixed_segments"
    pipeline = next(x for x in result["core_assets"] if x["id"] == "pipeline")
    assert pipeline["derived_economic_profile"] == "innovative_drug_pipeline"
    assert pipeline["recommended_primary_model"] == "rnpv"
    assert pipeline["independent_valuation_required"] is True


def test_value_core_fails_closed_on_missing_economic_attribute():
    node_attrs = attrs()
    del node_attrs["cyclicality"]
    try:
        scan_company_value_core({
            "version": "1.0",
            "nodes": [{"id": "x", "name": "x", "node_type": "operating_business", "materiality": "HIGH",
                       "economic_attributes": node_attrs}],
        })
    except ValueError as exc:
        assert "cyclicality" in str(exc)
    else:
        raise AssertionError("missing economic attribute did not fail closed")
