from datetime import date

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.canonical_investment_admission_v01 import (
    CANONICAL_INVESTMENT_ADMISSION_VERSION,
    InMemoryCanonicalInvestmentAdmissionRegistry,
    build_canonical_investment_admission,
)


CASE = {
    "case_id": "RC-CN-A-300750-20261004",
    "market": "CN-A",
    "symbol": "300750",
    "company": "CATL",
    "cutoff_date": "2026-10-04",
}


def _record(domain: str = "FORECAST"):
    return build_canonical_investment_admission(
        admission_id=f"B02-{domain}-001",
        domain=domain,
        **CASE,
        domain_status="PASS",
        source_record_id=f"{domain}-SOURCE-001",
        source_record_hash="1" * 64,
        output_hash="2" * 64,
        producer_version=f"{domain}-0.1",
        evidence_ids=["E1"],
        admitted_at="2026-10-06T15:00:00+00:00",
    )


def test_reference_contains_identity_but_not_self_declared_domain_status():
    record = _record()
    ref = record.reference().to_dict()
    assert set(ref) == {
        "admission_id",
        "admission_record_hash",
        "contract_version",
        "domain",
        "case_id",
        "market",
        "symbol",
        "company",
        "cutoff_date",
    }
    assert "domain_status" not in ref
    assert "PASS" not in ref.values()


def test_unknown_hash_cannot_be_resolved_even_when_reference_identity_is_valid():
    record = _record()
    registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    forged = record.reference().to_dict()
    forged["admission_record_hash"] = "3" * 64
    with pytest.raises(ValueError, match="unknown or not admitted"):
        registry.resolve(
            forged,
            expected_domain="FORECAST",
            **{**CASE, "cutoff_date": date(2026, 10, 4)},
        )


def test_wrong_domain_reference_is_rejected():
    record = _record()
    registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    ref = registry.admit(record).to_dict()
    with pytest.raises(ValueError, match="domain mismatch"):
        registry.resolve(
            ref,
            expected_domain="VALUATION",
            **CASE,
            cutoff_date=date(2026, 10, 4),
        )


@pytest.mark.parametrize("field,value", [
    ("case_id", "RC-CN-A-002422-20261004"),
    ("market", "HK"),
    ("symbol", "002422"),
    ("company", "四川科伦药业股份有限公司"),
    ("cutoff_date", date(2026, 10, 5)),
])
def test_identity_mismatch_is_rejected(field, value):
    record = _record()
    registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    ref = registry.admit(record).to_dict()
    kwargs = {
        **CASE,
        "cutoff_date": date.fromisoformat(CASE["cutoff_date"]),
    }
    if field == "cutoff_date":
        kwargs[field] = value
    else:
        kwargs[field] = value
    with pytest.raises(ValueError, match=f"canonical admission {field} mismatch"):
        registry.resolve(
            ref,
            expected_domain="FORECAST",
            **kwargs,
        )


def test_admitted_record_tampering_is_rejected():
    record = _record()
    registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    registry.admit(record)
    tampered = record.to_dict()
    tampered["output_hash"] = "4" * 64
    with pytest.raises(ValueError, match="record hash mismatch"):
        from iios_mvp.canonical_investment_admission_v01 import validate_canonical_investment_admission_record
        validate_canonical_investment_admission_record(tampered)


def test_reference_tampering_is_rejected_by_record_binding():
    record = _record()
    registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    ref = registry.admit(record).to_dict()
    ref["admission_id"] = "B02-FORECAST-999"
    with pytest.raises(ValueError, match="reference does not match"):
        registry.resolve(
            ref,
            expected_domain="FORECAST",
            **CASE,
            cutoff_date=date(2026, 10, 4),
        )


def test_schema_is_strict_and_versioned():
    import json
    from pathlib import Path
    schema = json.loads(
        (Path(__file__).parents[1] / "schemas/canonical_investment_admission_reference_v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    ref = _record().reference().to_dict()
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(ref)
    bad = {**ref, "domain_status": "PASS"}
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(bad))
    assert errors


def test_all_decision_critical_domains_are_enumerated():
    from iios_mvp.canonical_investment_admission_v01 import ADMISSION_DOMAINS
    assert ADMISSION_DOMAINS == {
        "REALITY",
        "QUALITY",
        "VALUE_DRIVER",
        "VALUATION",
        "FORECAST",
        "THESIS",
        "RETURN",
        "RISK",
        "PORTFOLIO",
    }
