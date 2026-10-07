from __future__ import annotations

from copy import deepcopy

from iios_mvp.engine import decide, validate_case
from iios_mvp.investment_core_contract_v03 import REQUIRED_RUNTIME_UPSTREAM_ADMISSION_VERSION, validate_case_v03
from tests.test_investment_core_v03 import (
    CURRENT_PRICE_REGISTRY,
    EVIDENCE_ROOT_REGISTRY,
    INDEPENDENT_FORECAST_REGISTRY,
    UPSTREAM_AUTHORITY_REGISTRY,
    VALUATION_OUTPUT_RESOLVER,
    case,
)


def _runtime_case():
    return case()


def test_b03_b_canonical_v02_upstream_is_required_and_passes_with_trusted_resolver():
    c = _runtime_case()
    result = validate_case_v03(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
    )
    assert result["status"] == "PASS"
    assert c["decision_upstream_admission"]["schema_version"] == REQUIRED_RUNTIME_UPSTREAM_ADMISSION_VERSION


def test_b03_b_legacy_v01_upstream_authority_is_blocked_at_decision_runtime():
    c = _runtime_case()
    legacy = deepcopy(c["decision_upstream_admission"])
    legacy["schema_version"] = "IIOS-CORE-04-UPSTREAM-ADMISSION-0.1"
    legacy.pop("canonical_admission_refs", None)
    # The legacy record's own hash is intentionally recomputed so this test
    # isolates the runtime-version boundary rather than hash validation.
    from iios_mvp.decision_upstream_admission_v03 import _sha
    legacy["admission_record_hash"] = _sha({
        k: legacy[k] for k in legacy if k != "admission_record_hash"
    })
    c["decision_upstream_admission"] = legacy

    result = validate_case_v03(
        c,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert result["status"] == "BLOCKED"
    assert any(
        "legacy v0.1 authority path is disabled" in error["message"]
        for error in result["errors"]
    )

    decision = decide(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert decision["decision"]["action"] != "BUY"
    assert decision["gates"]["new_capital_allowed"] is False


def test_b03_b_forged_v02_reference_without_matching_canonical_record_fails_closed():
    c = _runtime_case()
    refs = c["decision_upstream_admission"]["canonical_admission_refs"]
    forged = deepcopy(refs)
    forged["VALUATION"]["admission_record_hash"] = "0" * 64
    c["decision_upstream_admission"]["canonical_admission_refs"] = forged

    result = validate_case_v03(
        c,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert result["status"] == "BLOCKED"
    assert any(
        "unknown or not admitted" in error["message"]
        or "admission hash" in error["message"]
        for error in result["errors"]
    )


def test_b03_b_engine_propagates_upstream_authority_resolver():
    c = _runtime_case()
    errors = validate_case(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert errors == []

    decision = decide(
        c,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert decision["decision"]["auto_execution"] is False
