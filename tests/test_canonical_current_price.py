from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json

import pytest

from iios_mvp.canonical_current_price import (
    CanonicalCurrentPriceObservationReference,
    FileSystemCanonicalCurrentPriceRegistry,
    InMemoryCanonicalCurrentPriceRegistry,
    validate_current_price_binding,
)
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    TemporalProvenance,
    VerifiedMarketEvidence,
    admit_market_valuation_observation,
)

CUTOFF = date(2026, 10, 4)
OBSERVED_AT = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)


def make_admission(price="291.11", evidence_id="E011"):
    def evidence(evidence_id, variable, value, unit):
        return VerifiedMarketEvidence(
            evidence_id=evidence_id,
            variable=variable,
            unit=unit,
            basis="historical-market-observation",
            observation_date=CUTOFF,
            known_at=OBSERVED_AT,
            source="SZSE:MARKET_DATA",
            source_location="https://example.invalid/szse",
            content_sha256="a" * 64,
            exact_bytes=True,
            status=AdmissionStatus.ADMITTED,
            temporal_provenance=TemporalProvenance.SOURCE_VINTAGE,
            value=Decimal(value),
        )
    price_evidence = evidence(evidence_id, "market_price", price, "CNY/share")
    admission = admit_market_valuation_observation(
        cutoff_date=CUTOFF,
        observation_id=f"MO-{evidence_id}",
        price_evidence=price_evidence,
        shares_evidence=evidence(f"{evidence_id}-SHARES", "shares_outstanding", "4380630342", "shares"),
        economic_evidence=evidence(f"{evidence_id}-EBITDA", "ebitda", "100000000000", "CNY/share"),
        net_debt_evidence=evidence(f"{evidence_id}-DEBT", "net_debt", "-351500000000", "CNY"),
    )
    assert admission.status is AdmissionStatus.ADMITTED
    return admission, price_evidence


def test_inmemory_round_trip_binds_exact_price():
    registry = InMemoryCanonicalCurrentPriceRegistry()
    admission, price_evidence = make_admission()
    ref = registry.admit_current_price(
        case_id="CORE-04C",
        market="CN-A",
        symbol="300750",
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=price_evidence,
        observed_at=OBSERVED_AT,
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    )
    record = registry.resolve_current_price(
        ref.to_dict(),
        case_id="CORE-04C",
        market="CN-A",
        symbol="300750",
        cutoff_date=CUTOFF,
    )
    assert record["price"] == "291.11"
    validate_current_price_binding(
        {
            "price": "291.11",
            "price_observation_id": "E011",
            "price_observation_admission_hash": ref.admission_record_hash,
            "currency": "CNY",
            "observed_at": OBSERVED_AT.isoformat(),
            "known_at": OBSERVED_AT.isoformat(),
            "source": "SZSE:MARKET_DATA",
            "adjustment_semantics": "UNADJUSTED",
        },
        record,
    )


def test_forged_price_with_same_admission_is_rejected():
    registry = InMemoryCanonicalCurrentPriceRegistry()
    admission, price_evidence = make_admission()
    ref = registry.admit_current_price(
        case_id="CORE-04C",
        market="CN-A",
        symbol="300750",
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=price_evidence,
        observed_at=OBSERVED_AT,
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    )
    forged = {
        "price": "999.99",
        "price_observation_id": "E011",
        "price_observation_admission_hash": ref.admission_record_hash,
        "currency": "CNY",
        "observed_at": OBSERVED_AT.isoformat(),
        "known_at": OBSERVED_AT.isoformat(),
        "source": "SZSE:MARKET_DATA",
        "adjustment_semantics": "UNADJUSTED",
    }
    with pytest.raises(ValueError, match="does not match canonical admitted price"):
        validate_current_price_binding(forged, registry.resolve_current_price(
            ref.to_dict(), case_id="CORE-04C", market="CN-A", symbol="300750", cutoff_date=CUTOFF
        ))


def test_wrong_admission_hash_is_rejected():
    registry = InMemoryCanonicalCurrentPriceRegistry()
    admission, price_evidence = make_admission()
    ref = registry.admit_current_price(
        case_id="CORE-04C", market="CN-A", symbol="300750", cutoff_date=CUTOFF,
        admission=admission, price_evidence=price_evidence, observed_at=OBSERVED_AT,
        currency="CNY", adjustment_semantics="UNADJUSTED",
    )
    with pytest.raises(ValueError, match="admission hash mismatch"):
        registry.resolve_current_price(
            {"price_observation_id": "E011", "admission_record_hash": "0" * 64},
            case_id="CORE-04C", market="CN-A", symbol="300750", cutoff_date=CUTOFF,
        )


def test_cross_instrument_reuse_is_rejected():
    registry = InMemoryCanonicalCurrentPriceRegistry()
    admission, price_evidence = make_admission()
    ref = registry.admit_current_price(
        case_id="CORE-04C", market="CN-A", symbol="300750", cutoff_date=CUTOFF,
        admission=admission, price_evidence=price_evidence, observed_at=OBSERVED_AT,
        currency="CNY", adjustment_semantics="UNADJUSTED",
    )
    with pytest.raises(ValueError, match="instrument identity mismatch"):
        registry.resolve_current_price(
            ref.to_dict(), case_id="CORE-04C", market="CN-A", symbol="000001", cutoff_date=CUTOFF
        )


def test_filesystem_tampering_is_fail_closed(tmp_path):
    registry = FileSystemCanonicalCurrentPriceRegistry(tmp_path)
    admission, price_evidence = make_admission()
    ref = registry.admit_current_price(
        case_id="CORE-04C", market="CN-A", symbol="300750", cutoff_date=CUTOFF,
        admission=admission, price_evidence=price_evidence, observed_at=OBSERVED_AT,
        currency="CNY", adjustment_semantics="UNADJUSTED",
    )
    path = registry._path("E011")
    value = json.loads(path.read_text(encoding="utf-8"))
    value["price"] = "999.99"
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="admission record hash mismatch"):
        registry.resolve_current_price(
            ref.to_dict(), case_id="CORE-04C", market="CN-A", symbol="300750", cutoff_date=CUTOFF
        )


def test_reference_rejects_extra_fields():
    with pytest.raises(ValueError, match="unsupported fields"):
        CanonicalCurrentPriceObservationReference.from_mapping({
            "price_observation_id": "E011",
            "admission_record_hash": "a" * 64,
            "price": "291.11",
        })


def test_partial_upstream_market_admission_cannot_be_registered():
    registry = InMemoryCanonicalCurrentPriceRegistry()
    admission, price_evidence = make_admission()
    blocked = admission.__class__(
        status=AdmissionStatus.BLOCKED,
        observation=None,
        evidence_ids=admission.evidence_ids,
        blockers=("upstream blocked",),
    )
    with pytest.raises(ValueError, match="ADMITTED market observation"):
        registry.admit_current_price(
            case_id="CORE-04C", market="CN-A", symbol="300750", cutoff_date=CUTOFF,
            admission=blocked, price_evidence=price_evidence, observed_at=OBSERVED_AT,
            currency="CNY", adjustment_semantics="UNADJUSTED",
        )
