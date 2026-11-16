from __future__ import annotations

from datetime import date
import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iios_mvp.canonical_independent_forecast import InMemoryCanonicalIndependentForecastRegistry
from iios_mvp.canonical_forecast_evidence_binding_v01 import (
    FileSystemCanonicalSignedEvidenceAdmissionResolver,
    build_canonical_signed_evidence_admission_reference,
)
from iios_mvp.canonical_signed_evidence_admission_v01 import (
    RIGHTS_SCHEMA,
    SIGNED_ADMISSION_SCHEMA,
    SIGNER_REGISTRY_SCHEMA,
    add_signature,
    build_admission_payload,
)
from iios_mvp.canonical_evidence_admission_v01 import REQUIRED_FIELD_GROUPS
from iios_mvp.canonical_investment_admission_v01 import (
    InMemoryCanonicalInvestmentAdmissionRegistry,
    build_canonical_investment_admission,
)
from iios_mvp.forecast_valuation_return_lineage_v01 import (
    FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
    InMemoryCanonicalValuationOutputResolver,
    build_canonical_valuation_output,
    validate_forecast_valuation_return_lineage,
)
from iios_mvp.investment_core_contract_v03 import validate_case_v03


CASE_ID = "B04-CASE-001"
MARKET = "CN-A"
SYMBOL = "300750"
COMPANY = "CATL"
CUTOFF = date(2026, 10, 4)
SIGNED_AT = "2026-10-05T12:00:00+00:00"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _evidence_admission_bundle(
    tmp_path: Path,
    *,
    case_id: str = CASE_ID,
    market: str = MARKET,
    symbol: str = SYMBOL,
    company: str = COMPANY,
    cutoff_date: date = CUTOFF,
    manifest_cutoff_value: str | None = None,
    known_at_value: str = "2026-10-03T12:00:00+00:00",
):
    """Build a synthetic but fully signed Evidence/PIT bundle; no real source data."""
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    raw_bytes = b"B04 signed Evidence/PIT fixture; synthetic bytes only.\\n"
    (raw_root / "source.bin").write_bytes(raw_bytes)
    raw_hash = _sha(raw_bytes)

    evidence_ids = ["b04-forecast-evidence", "b04-valuation-evidence"]
    evidence_ids.extend(f"B04-CORE-E-{idx:02d}" for idx in range(1, len(REQUIRED_FIELD_GROUPS) + 1))
    evidence_rows = []
    raw_artifacts = []
    for idx, evidence_id in enumerate(evidence_ids, start=1):
        field_group = REQUIRED_FIELD_GROUPS[(idx - 1) % len(REQUIRED_FIELD_GROUPS)]
        evidence_rows.append({
            "evidence_id": evidence_id,
            "subject_id": case_id,
            "field_id": f"{field_group}.b04_fixture_fact_{idx}",
            "claim_type": "B04_SYNTHETIC_FIXTURE",
            "known_at": known_at_value,
            "retrieved_at": "2026-10-05T12:00:00+00:00",
            "published_at": "2026-10-03T10:00:00+00:00",
            "source_ref": "https://example.invalid/b04-fixture",
            "artifact_id": f"B04-ARTIFACT-{idx:02d}",
            "content_sha256": raw_hash,
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
        })
        raw_artifacts.append({
            "evidence_id": evidence_id,
            "relative_path": "source.bin",
            "expected_sha256": raw_hash,
            "expected_size_bytes": len(raw_bytes),
        })

    manifest_body = {
        "schema_version": "IIOS-COMPANY-EVIDENCE-MANIFEST-0.1",
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "company": company,
        "cutoff_date": manifest_cutoff_value or cutoff_date.isoformat(),
        "required_field_groups": list(REQUIRED_FIELD_GROUPS),
        "evidence": evidence_rows,
        "raw_artifacts": raw_artifacts,
    }
    manifest = {
        **manifest_body,
        "audit": {"manifest_sha256": _sha(_canonical(manifest_body))},
        "status": "PASS",
        "validation_errors": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    permission_path = tmp_path / "permission-instrument.bin"
    permission_bytes = b"Synthetic written permission instrument; fixture only.\\n"
    permission_path.write_bytes(permission_bytes)
    rights_path = tmp_path / "rights.json"
    rights = {
        "schema_version": RIGHTS_SCHEMA,
        "case_id": case_id,
        "source_class": "EXCHANGE_MARKET_DATA",
        "status": "ALLOWED",
        "basis_kind": "EXPLICIT_WRITTEN_PERMISSION",
        "permission_instrument_id": "B04-TEST-PERMISSION",
        "permission_evidence_sha256": _sha(permission_bytes),
        "allowed_uses": ["PRIVATE_STORAGE", "LOCAL_COMPUTATION", "INTERNAL_DISPLAY"],
        "required_signer_roles": ["EVIDENCE_ADMISSION_SIGNER"],
        "expires_at": "2027-01-01T00:00:00+00:00",
    }
    rights_path.write_text(
        json.dumps(rights, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    private_raw = bytes(range(32))
    private_key = Ed25519PrivateKey.from_private_bytes(private_raw)
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    private_path = tmp_path / "admission.key"
    private_path.write_text(base64.b64encode(private_raw).decode("ascii") + "\n", encoding="ascii")
    private_path.chmod(0o600)
    registry_path = tmp_path / "signer-registry.json"
    registry_path.write_text(json.dumps({
        "schema_version": SIGNER_REGISTRY_SCHEMA,
        "registry_status": "ACTIVE",
        "signers": [{
            "signer_key_id": "b04-test-owner",
            "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
            "roles": ["EVIDENCE_ADMISSION_SIGNER"],
            "status": "ACTIVE",
            "case_scopes": [case_id],
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_until": None,
            "revoked_at": None,
        }],
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    payload = build_admission_payload(
        manifest_path=manifest_path,
        raw_root=raw_root,
        rights_record_path=rights_path,
        permission_evidence_path=permission_path,
        decision="ADMIT",
        signed_at=SIGNED_AT,
    )
    envelope = add_signature(
        {"schema_version": SIGNED_ADMISSION_SCHEMA, "payload": payload, "signatures": []},
        signer_registry_path=registry_path,
        signer_key_id="b04-test-owner",
        private_key_path=private_path,
        signed_at=SIGNED_AT,
    )
    envelope_path = tmp_path / "signed-admission.json"
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    reference = build_canonical_signed_evidence_admission_reference(
        envelope_path=envelope_path,
        manifest_path=manifest_path,
        rights_record_path=rights_path,
        permission_evidence_path=permission_path,
    )
    resolver = FileSystemCanonicalSignedEvidenceAdmissionResolver(
        envelope_path=envelope_path,
        manifest_path=manifest_path,
        raw_root=raw_root,
        rights_record_path=rights_path,
        permission_evidence_path=permission_path,
        signer_registry_path=registry_path,
    )
    return reference, resolver, envelope_path, evidence_ids


def _forecast(
    forecast_id: str = "forecast-b04-001",
    registry=None,
    evidence_ids=None,
    *,
    forecast_origin: str = "2026-10-03T10:00:00+08:00",
    known_at: str = "2026-10-03T18:00:00+08:00",
):
    if registry is None:
        registry = InMemoryCanonicalIndependentForecastRegistry()
    ref = registry.admit_independent_forecast({
        "case_id": CASE_ID,
        "market": MARKET,
        "symbol": SYMBOL,
        "cutoff_date": CUTOFF.isoformat(),
        "forecast_id": forecast_id,
        "forecast_version": "B04-FORECAST-0.1",
        "model_version": "B04-MODEL-0.1",
        "variable_id": "forward_eps",
        "value": "20",
        "unit": "CNY/share",
        "basis": "2026A_to_2029E",
        "horizon_years": "3",
        "forecast_origin": forecast_origin,
        "known_at": known_at,
        "prepared_without_current_price": True,
        "evidence_ids": evidence_ids or ["b04-forecast-evidence"],
    })
    return registry, ref.to_dict()


def _valuation(forecast_ref):
    output = build_canonical_valuation_output({
        "valuation_id": "valuation-b04-001",
        "valuation_version": "B04-VALUATION-0.1",
        "case_id": CASE_ID,
        "market": MARKET,
        "symbol": SYMBOL,
        "company": COMPANY,
        "cutoff_date": CUTOFF.isoformat(),
        "forecast_ref": forecast_ref,
        "horizon_years": "3",
        "reference_value_per_share": "430",
        "scenarios": {
            "bear": {"probability": "0.25", "value_per_share": "280", "cash_distributions_per_share": "0"},
            "base": {"probability": "0.50", "value_per_share": "430", "cash_distributions_per_share": "10"},
            "bull": {"probability": "0.25", "value_per_share": "650", "cash_distributions_per_share": "15"},
        },
        "evidence_ids": ["b04-valuation-evidence"],
    })
    admission_registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    admission = build_canonical_investment_admission(
        admission_id="valuation-admission-b04-001",
        domain="VALUATION",
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        company=COMPANY,
        cutoff_date=CUTOFF.isoformat(),
        domain_status="PASS",
        source_record_id=output["valuation_id"],
        source_record_hash="a" * 64,
        output_hash=output["output_hash"],
        producer_version="B04-VALUATION-PRODUCER-0.1",
        evidence_ids=["b04-valuation-evidence"],
        admitted_at="2026-10-04T16:00:00+00:00",
    )
    ref = admission_registry.admit(admission).to_dict()
    resolver = InMemoryCanonicalValuationOutputResolver(admission_registry)
    resolver.register_output(
        valuation_reference=ref,
        valuation_output=output,
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        company=COMPANY,
        cutoff_date=CUTOFF,
    )
    return resolver, ref, output


def _return_gate(forecast_ref, valuation_ref, evidence_ref):
    return {
        "lineage_version": FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
        "canonical_forecast_ref": forecast_ref,
        "canonical_valuation_ref": valuation_ref,
        "canonical_evidence_admission_ref": evidence_ref,
        "entry_price": "291.11",
        "entry_value_reference": "430",
        "horizon_years": "3",
        "horizon_override": True,
        "horizon_override_basis": ["MAJOR_INDUSTRY_LEADER"],
        "horizon_selection_rationale": "B04 test horizon",
        "buy_entry_return_cushion_threshold": "0.15",
        "fundamental_target_annualized_return": "0.15",
        "required_return_annualized": "0.10",
        "scenarios": {
            "bear": {"probability": "0.25", "terminal_value_per_share": "280", "cash_distributions_per_share": "0", "probability_rationale": "canonical valuation"},
            "base": {"probability": "0.50", "terminal_value_per_share": "430", "cash_distributions_per_share": "10", "probability_rationale": "canonical valuation"},
            "bull": {"probability": "0.25", "terminal_value_per_share": "650", "cash_distributions_per_share": "15", "probability_rationale": "canonical valuation"},
        },
    }


def _validate_lineage(forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver):
    return validate_forecast_valuation_return_lineage(
        return_gate=_return_gate(forecast_ref, valuation_ref, evidence_ref),
        canonical_forecast_ref=forecast_ref,
        canonical_valuation_ref=valuation_ref,
        canonical_evidence_admission_ref=evidence_ref,
        independent_forecast_resolver=forecast_registry,
        evidence_admission_resolver=evidence_resolver,
        valuation_output_resolver=valuation_resolver,
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        company=COMPANY,
        cutoff_date=CUTOFF,
    )


def test_b04_lineage_accepts_forecast_valuation_and_signed_evidence_pit(tmp_path):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _evidence_ids = _evidence_admission_bundle(tmp_path)
    result = _validate_lineage(
        forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
    )
    assert result["status"] == "PASS"
    assert result["binding"] == "FORECAST_REF_EQUALITY_EVIDENCE_ID_SUBSET_CANONICAL_VALUATION_SCENARIO_EQUALITY_AND_SIGNED_EVIDENCE_PIT"
    assert result["evidence_pit_admission_status"] == "FORMALLY_ADMITTED"
    assert result["evidence_ids_verified"] == ["b04-forecast-evidence", "b04-valuation-evidence"]
    assert result["evidence_pit_admission"]["core_pit_validation"] == "PASS"


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (("probability", "base", "0.75"), "is not canonical"),
        (("terminal_value_per_share", "base", "999"), "is not canonical"),
        (("cash_distributions_per_share", "bull", "999"), "is not canonical"),
    ],
)
def test_b04_return_gate_cannot_substitute_economic_inputs(mutation, expected, tmp_path):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(tmp_path)
    gate = _return_gate(forecast_ref, valuation_ref, evidence_ref)
    field, scenario, value = mutation
    gate["scenarios"][scenario][field] = value
    with pytest.raises(ValueError, match=expected):
        validate_forecast_valuation_return_lineage(
            return_gate=gate,
            canonical_forecast_ref=forecast_ref,
            canonical_valuation_ref=valuation_ref,
            canonical_evidence_admission_ref=evidence_ref,
            independent_forecast_resolver=forecast_registry,
            evidence_admission_resolver=evidence_resolver,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID,
            market=MARKET,
            symbol=SYMBOL,
            company=COMPANY,
            cutoff_date=CUTOFF,
        )


def test_b04_return_gate_reference_value_and_horizon_are_bound(tmp_path):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(tmp_path)
    gate = _return_gate(forecast_ref, valuation_ref, evidence_ref)

    gate["entry_value_reference"] = "500"
    with pytest.raises(ValueError, match="reference value"):
        validate_forecast_valuation_return_lineage(
            return_gate=gate,
            canonical_forecast_ref=forecast_ref,
            canonical_valuation_ref=valuation_ref,
            canonical_evidence_admission_ref=evidence_ref,
            independent_forecast_resolver=forecast_registry,
            evidence_admission_resolver=evidence_resolver,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID, market=MARKET, symbol=SYMBOL, company=COMPANY, cutoff_date=CUTOFF,
        )

    gate = _return_gate(forecast_ref, valuation_ref, evidence_ref)
    gate["horizon_years"] = "2"
    with pytest.raises(ValueError, match="horizon"):
        validate_forecast_valuation_return_lineage(
            return_gate=gate,
            canonical_forecast_ref=forecast_ref,
            canonical_valuation_ref=valuation_ref,
            canonical_evidence_admission_ref=evidence_ref,
            independent_forecast_resolver=forecast_registry,
            evidence_admission_resolver=evidence_resolver,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID, market=MARKET, symbol=SYMBOL, company=COMPANY, cutoff_date=CUTOFF,
        )


def test_b04_forecast_to_valuation_binding_is_strict(tmp_path):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    _, unrelated_ref = _forecast("forecast-b04-002", registry=forecast_registry)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(tmp_path)
    with pytest.raises(ValueError, match="valuation.forecast_ref"):
        validate_forecast_valuation_return_lineage(
            return_gate=_return_gate(unrelated_ref, valuation_ref, evidence_ref),
            canonical_forecast_ref=unrelated_ref,
            canonical_valuation_ref=valuation_ref,
            canonical_evidence_admission_ref=evidence_ref,
            independent_forecast_resolver=forecast_registry,
            evidence_admission_resolver=evidence_resolver,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID, market=MARKET, symbol=SYMBOL, company=COMPANY, cutoff_date=CUTOFF,
        )


def test_b04_signed_manifest_end_of_day_timestamp_matches_local_cutoff_date(tmp_path):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(
        tmp_path,
        manifest_cutoff_value="2026-10-04T23:59:59+08:00",
        known_at_value="2026-10-04T10:00:00+08:00",
    )
    result = _validate_lineage(
        forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
    )
    assert result["status"] == "PASS"
    assert result["evidence_pit_admission_status"] == "FORMALLY_ADMITTED"


def test_b04_signed_manifest_next_local_day_does_not_match_cutoff(tmp_path):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(
        tmp_path,
        manifest_cutoff_value="2026-10-05T00:00:00+08:00",
    )
    with pytest.raises(ValueError, match="cutoff_date does not match forecast lineage"):
        _validate_lineage(
            forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
        )


def test_b04_lineage_blocks_forecast_evidence_id_absent_from_signed_manifest(tmp_path):
    forecast_registry, invalid_ref = _forecast(
        "forecast-with-unsupported-evidence",
        evidence_ids=["not-in-signed-manifest"],
    )
    valuation_resolver, valuation_ref, _ = _valuation(invalid_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(tmp_path)
    with pytest.raises(ValueError, match="absent from signed manifest"):
        _validate_lineage(
            forecast_registry, invalid_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
        )


def test_b04_lineage_rejects_tampered_signed_evidence_envelope(tmp_path):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, envelope_path, _ids = _evidence_admission_bundle(tmp_path)
    envelope_path.write_text(envelope_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="envelope bytes differ from reference"):
        _validate_lineage(
            forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
        )



def test_b80_exact_signed_cutoff_accepts_equal_instant_and_normalizes_timezone_offsets(tmp_path):
    forecast_registry, forecast_ref = _forecast(
        forecast_origin="2026-10-04T11:30:00+08:00",
        known_at="2026-10-04T04:00:00Z",
    )
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(
        tmp_path,
        manifest_cutoff_value="2026-10-04T12:00:00+08:00",
        known_at_value="2026-10-04T12:00:00+08:00",
    )

    result = _validate_lineage(
        forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
    )

    assert result["status"] == "PASS"
    assert result["evidence_pit_cutoff_instant"] == "2026-10-04T12:00:00+08:00"
    assert result["forecast_pit_temporal_status"] == "PASS_EXACT_SIGNED_CUTOFF"
    assert result["forecast_known_at"] == "2026-10-04T04:00:00+00:00"


@pytest.mark.parametrize(
    "forecast_origin, known_at, field",
    [
        (
            "2026-10-04T12:00:01+08:00",
            "2026-10-04T11:00:00+08:00",
            "forecast_origin",
        ),
        (
            "2026-10-04T11:00:00+08:00",
            "2026-10-04T12:00:01+08:00",
            "known_at",
        ),
    ],
)
def test_b80_forecast_timestamp_after_intraday_signed_cutoff_is_rejected(
    tmp_path, forecast_origin, known_at, field
):
    forecast_registry, forecast_ref = _forecast(
        forecast_origin=forecast_origin,
        known_at=known_at,
    )
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(
        tmp_path,
        manifest_cutoff_value="2026-10-04T12:00:00+08:00",
        known_at_value="2026-10-04T11:00:00+08:00",
    )

    with pytest.raises(
        ValueError,
        match=f"canonical independent forecast {field} is after signed Evidence/PIT cutoff",
    ):
        _validate_lineage(
            forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
        )


def test_b80_date_only_signed_cutoff_uses_shanghai_midnight_for_forecast_timestamps(tmp_path):
    forecast_registry, forecast_ref = _forecast(
        forecast_origin="2026-10-04T00:00:01+08:00",
        known_at="2026-10-03T23:30:00+08:00",
    )
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    evidence_ref, evidence_resolver, _envelope, _ids = _evidence_admission_bundle(
        tmp_path,
        manifest_cutoff_value="2026-10-04",
    )

    with pytest.raises(
        ValueError,
        match="canonical independent forecast forecast_origin is after signed Evidence/PIT cutoff",
    ):
        _validate_lineage(
            forecast_registry, forecast_ref, valuation_resolver, valuation_ref, evidence_ref, evidence_resolver
        )
