from datetime import date
from copy import deepcopy

import pytest

from iios_mvp.canonical_investment_admission_v01 import (
    InMemoryCanonicalInvestmentAdmissionRegistry,
    build_canonical_investment_admission,
)
from iios_mvp.upstream_authority_v03 import (
    CORE_STATUS_DOMAINS,
    validate_core_upstream_authority,
)


CASE = {
    "case_id": "RC-CN-A-300750-20261004",
    "market": "CN-A",
    "symbol": "300750",
    "company": "CATL",
    "cutoff_date": date(2026, 10, 4),
}


def registry_with_states(states: dict[str, str]):
    registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    refs = {}
    for domain in CORE_STATUS_DOMAINS:
        record = build_canonical_investment_admission(
            admission_id=f"B03-{domain}-001",
            domain=domain,
            **CASE,
            domain_status=states[domain],
            source_record_id=f"{domain}-SOURCE-001",
            source_record_hash=(domain.lower().replace("_", "") + "a" * 64)[:64],
            output_hash=("b" * 64),
            producer_version=f"{domain}-0.1",
            evidence_ids=[f"E-{domain}"],
            admitted_at="2026-10-06T15:00:00+00:00",
        )
        refs[domain] = registry.admit(record).to_dict()
    return registry, refs


def test_resolver_returns_domain_owned_states_not_reference_declarations():
    states = {domain: "PASS" for domain in CORE_STATUS_DOMAINS}
    registry, refs = registry_with_states(states)
    result = validate_core_upstream_authority(
        admission_refs=refs,
        declared_states={
            "reality_status": "PASS",
            "quality_gate_status": "PASS",
            "value_driver_status": "PASS",
            "valuation_status": "PASS",
            "forecast_status": "PASS",
        },
        resolver=registry,
        **CASE,
    )
    assert result["resolved_states"] == {
        "reality_status": "PASS",
        "quality_gate_status": "PASS",
        "value_driver_status": "PASS",
        "valuation_status": "PASS",
        "forecast_status": "PASS",
    }


def test_caller_cannot_upgrade_blocked_domain_to_pass():
    states = {domain: "PASS" for domain in CORE_STATUS_DOMAINS}
    states["VALUE_DRIVER"] = "BLOCKED"
    registry, refs = registry_with_states(states)
    with pytest.raises(ValueError, match="value_driver_status drift"):
        validate_core_upstream_authority(
            admission_refs=refs,
            declared_states={
                "reality_status": "PASS",
                "quality_gate_status": "PASS",
                "value_driver_status": "PASS",
                "valuation_status": "PASS",
                "forecast_status": "PASS",
            },
            resolver=registry,
            **CASE,
        )


def test_missing_ref_fails_closed_even_when_declared_pass():
    states = {domain: "PASS" for domain in CORE_STATUS_DOMAINS}
    registry, refs = registry_with_states(states)
    missing = deepcopy(refs)
    del missing["FORECAST"]
    with pytest.raises(ValueError, match="incomplete"):
        validate_core_upstream_authority(
            admission_refs=missing,
            declared_states={
                "reality_status": "PASS",
                "quality_gate_status": "PASS",
                "value_driver_status": "PASS",
                "valuation_status": "PASS",
                "forecast_status": "PASS",
            },
            resolver=registry,
            **CASE,
        )


def test_cross_case_reference_fails_closed():
    states = {domain: "PASS" for domain in CORE_STATUS_DOMAINS}
    registry, refs = registry_with_states(states)
    with pytest.raises(ValueError, match="case_id mismatch"):
        validate_core_upstream_authority(
            admission_refs=refs,
            declared_states={
                "reality_status": "PASS",
                "quality_gate_status": "PASS",
                "value_driver_status": "PASS",
                "valuation_status": "PASS",
                "forecast_status": "PASS",
            },
            resolver=registry,
            case_id="RC-CN-A-002422-20261004",
            market=CASE["market"],
            symbol=CASE["symbol"],
            company=CASE["company"],
            cutoff_date=CASE["cutoff_date"],
        )


def test_tampered_reference_hash_fails_closed():
    states = {domain: "PASS" for domain in CORE_STATUS_DOMAINS}
    registry, refs = registry_with_states(states)
    tampered = deepcopy(refs)
    tampered["FORECAST"]["admission_record_hash"] = "f" * 64
    with pytest.raises(ValueError, match="unknown or not admitted"):
        validate_core_upstream_authority(
            admission_refs=tampered,
            declared_states={
                "reality_status": "PASS",
                "quality_gate_status": "PASS",
                "value_driver_status": "PASS",
                "valuation_status": "PASS",
                "forecast_status": "PASS",
            },
            resolver=registry,
            **CASE,
        )
