from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

import pytest

from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    TemporalProvenance,
    VerifiedMarketEvidence,
    admit_market_valuation_observation,
)


CUTOFF = date(2026, 10, 4)
KNOWN = datetime(2026, 10, 4, 2, tzinfo=timezone.utc)


def evidence(
    evidence_id: str,
    variable: str,
    value: str,
    *,
    observed: date = date(2026, 9, 30),
    known: datetime = KNOWN,
    exact_bytes: bool = True,
    status: AdmissionStatus = AdmissionStatus.ADMITTED,
    temporal: TemporalProvenance = TemporalProvenance.SOURCE_VINTAGE,
    unit: str | None = None,
) -> VerifiedMarketEvidence:
    resolved_unit = unit or {
        "market_price": "CNY/share",
        "shares_outstanding": "shares",
        "net_debt": "CNY",
    }.get(variable, "CNY")
    return VerifiedMarketEvidence(
        evidence_id=evidence_id,
        variable=variable,
        unit=resolved_unit,
        basis="historical_market_observation",
        observation_date=observed,
        known_at=known,
        source="official-or-free-public-test-fixture",
        source_location="https://example.invalid/source",
        content_sha256="a" * 64,
        exact_bytes=exact_bytes,
        status=status,
        temporal_provenance=temporal,
        value=Decimal(value),
    )


def admitted():
    return dict(
        cutoff_date=CUTOFF,
        observation_id="mkt-2026-09-30",
        price_evidence=evidence("p1", "market_price", "291.11"),
        shares_evidence=evidence("s1", "shares_outstanding", "4380630342"),
        economic_evidence=evidence("f1", "ebitda", "100000000000"),
        net_debt_evidence=evidence("n1", "net_debt", "-351500000000"),
    )


def test_admitted_evidence_builds_typed_market_observation():
    result = admit_market_valuation_observation(**admitted())
    assert result.status is AdmissionStatus.ADMITTED
    assert result.observation is not None
    assert result.observation.price == Decimal("291.11")
    assert result.observation.economic_variable == "ebitda"
    assert result.observation.net_debt == Decimal("-351500000000")


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        (
            {"known": datetime(2026, 10, 5, 1, tzinfo=timezone.utc)},
            "known_at is after cutoff",
        ),
        (
            {"temporal": TemporalProvenance.RETROSPECTIVE_RECOMPUTED},
            "temporal_provenance is not admissible",
        ),
        (
            {"temporal": TemporalProvenance.UNKNOWN},
            "temporal_provenance is not admissible",
        ),
        (
            {"exact_bytes": False},
            "exact_bytes must be true",
        ),
    ],
)
def test_material_pit_or_exact_byte_failure_blocks(kwargs, expected):
    args = admitted()
    args["price_evidence"] = evidence("p1", "market_price", "291.11", **kwargs)
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert result.observation is None
    assert any(expected in blocker for blocker in result.blockers)


def test_observation_date_mismatch_blocks():
    args = admitted()
    args["economic_evidence"] = evidence(
        "f1", "ebitda", "100000000000", observed=date(2026, 9, 29)
    )
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert "price/economic observation dates must match" in result.blockers


def test_duplicate_evidence_id_blocks():
    args = admitted()
    args["net_debt_evidence"] = evidence("p1", "net_debt", "-351500000000")
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert "evidence_ids must be unique" in result.blockers


def test_bad_sha_blocks_before_market_observation_is_created():
    args = admitted()
    args["price_evidence"] = evidence("p1", "market_price", "291.11")
    args["price_evidence"] = VerifiedMarketEvidence(
        **{
            **args["price_evidence"].__dict__,
            "content_sha256": "B" * 64,
        }
    )
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert result.observation is None


def test_naive_known_at_is_not_admissible():
    args = admitted()
    args["price_evidence"] = evidence(
        "p1",
        "market_price",
        "291.11",
        known=datetime(2026, 9, 30, 2),
    )
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert result.observation is None


def test_non_positive_market_observation_blocks():
    args = admitted()
    args["price_evidence"] = evidence("p1", "market_price", "0")
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert "market price must be > 0" in result.blockers


def test_non_positive_economic_value_blocks():
    args = admitted()
    args["economic_evidence"] = evidence("f1", "ebitda", "0")
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert "economic variable value must be > 0" in result.blockers


def test_net_debt_variable_must_be_explicit():
    args = admitted()
    args["net_debt_evidence"] = evidence("n1", "cash", "351500000000")
    result = admit_market_valuation_observation(**args)
    assert result.status is AdmissionStatus.BLOCKED
    assert "net_debt_evidence.variable must be net_debt" in result.blockers
