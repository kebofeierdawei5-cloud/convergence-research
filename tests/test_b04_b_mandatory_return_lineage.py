from __future__ import annotations

from copy import deepcopy

from iios_mvp.investment_core_contract_v03 import (
    REQUIRED_RUNTIME_RETURN_LINEAGE_VERSION,
    validate_case_v03,
)
from tests.test_investment_core_v03 import (
    CURRENT_PRICE_REGISTRY,
    EVIDENCE_ROOT_REGISTRY,
    INDEPENDENT_FORECAST_REGISTRY,
    UPSTREAM_AUTHORITY_REGISTRY,
    VALUATION_OUTPUT_RESOLVER,
    case,
)


def _validate(c: dict, *, valuation_resolver=True):
    kwargs = {
        "evidence_root_resolver": EVIDENCE_ROOT_REGISTRY,
        "current_price_resolver": CURRENT_PRICE_REGISTRY,
        "independent_forecast_resolver": INDEPENDENT_FORECAST_REGISTRY,
        "upstream_authority_resolver": UPSTREAM_AUTHORITY_REGISTRY,
    }
    if valuation_resolver:
        kwargs["valuation_output_resolver"] = VALUATION_OUTPUT_RESOLVER
    return validate_case_v03(c, **kwargs)


def test_b04_b_runtime_requires_exact_lineage_version():
    c = case()
    c["return_gate"]["lineage_version"] = "IIOS-FORECAST-VALUATION-RETURN-LINEAGE-0.0"
    result = _validate(c)
    assert result["status"] == "BLOCKED"
    assert any(error["code"] == "V03-RETURN-LINEAGE-REQUIRED" for error in result["errors"])


def test_b04_b_runtime_requires_canonical_valuation_resolver():
    result = _validate(case(), valuation_resolver=False)
    assert result["status"] == "BLOCKED"
    assert any(
        error["code"] == "V03-RETURN-LINEAGE-VALUATION-RESOLVER"
        for error in result["errors"]
    )


def test_b04_b_entry_price_cannot_diverge_from_current_price():
    c = case()
    c["return_gate"]["entry_price"] = "101"
    result = _validate(c)
    assert result["status"] == "BLOCKED"
    assert any(error["code"] == "V03-CURRENT-PRICE-BIND" for error in result["errors"])


def test_b04_b_return_scenario_substitution_fails_closed():
    c = case()
    c["return_gate"]["scenarios"]["base"]["terminal_value_per_share"] = "999"
    result = _validate(c)
    assert result["status"] == "BLOCKED"
    assert any(
        error["code"] == "V03-RETURN-LINEAGE-CANONICAL"
        for error in result["errors"]
    )


def test_b04_b_canonical_lineage_matches_runtime_version():
    c = case()
    assert c["return_gate"]["lineage_version"] == REQUIRED_RUNTIME_RETURN_LINEAGE_VERSION
    result = _validate(c)
    assert result["status"] == "PASS", result
