from datetime import date, datetime, timezone
import json

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.evidence_root_admission import (
    FileSystemEvidenceRootRegistry,
    P4F_MIE_SNAPSHOT_ROOT_TYPE,
)
from iios_mvp.p4f_mie_snapshot import P4FProvenanceRecord, build_p4f_snapshot
from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment, CandidateCoverageState,
    EvidenceSufficiencyAssessment, EvidenceSufficiencyState,
    MIEEconomicRequirement, MIEObservationBasis, MIEQualification,
    MIERepresentation, MarketImpliedExpectation,
)
from iios_mvp.market_model_domain import IdentifiabilityState, MarketModelFamily, StabilityState
from iios_mvp.multi_model_market_implied_expectation_set import (
    MIEModelEvaluation, build_multi_model_market_implied_expectation_set,
)

CUTOFF = date(2026, 10, 4)
CREATED = datetime(2026, 10, 4, 17, 10, tzinfo=timezone.utc)


def make_snapshot(case_id="P1-1-CASE"):
    requirement = MIEEconomicRequirement(
        economic_variable="forward_eps",
        unit="CNY/share",
        basis="2026A_to_2028E",
        period="2028E",
        horizon="24M",
        accounting_basis="reported",
        role="IMPLIED_PRIMARY",
        value="10",
        evidence_ids=("req-pe-1",),
    )
    coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState.SUFFICIENT,
        scope_basis="fixture-candidate-set",
        candidate_model_ids=("pe-1",),
        evidence_ids=("cov-pe-1",),
        rationale="The fixture has one admitted market-model candidate.",
    )
    sufficiency = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState.SUFFICIENT,
        rationale="Fixture MIE evidence is complete.",
        evidence_ids=("suff-pe-1",),
    )
    mie = MarketImpliedExpectation(
        expectation_id="mie-pe-1",
        model_id="pe-1",
        market_model=MarketModelFamily.FORWARD_PE,
        identifiability=IdentifiabilityState.IDENTIFIABLE,
        stability=StabilityState.STABLE,
        candidate_coverage=coverage,
        representation=MIERepresentation.IMPLIED_POINT,
        economic_requirements=(requirement,),
        observation_basis=MIEObservationBasis("price-1", CUTOFF, CUTOFF, "CNY", "UNADJUSTED"),
        assumption_set=(),
        evidence_sufficiency=sufficiency,
        evidence_ids=("req-pe-1", "cov-pe-1", "suff-pe-1"),
        qualification=MIEQualification.DECISION_GRADE,
        qualification_rationale="Fixture MIE is decision-grade.",
    )
    mie_set = build_multi_model_market_implied_expectation_set(
        set_id="p1-1-set",
        candidate_coverage=coverage,
        evidence_sufficiency=sufficiency,
        model_evaluations=(MIEModelEvaluation.from_expectation(mie),),
        qualification_rationale="Fixture set resolves uniquely.",
        evidence_ids=("req-pe-1", "cov-pe-1", "suff-pe-1"),
    )
    provenance = []
    for evidence_id in ("cov-pe-1", "price-1", "req-pe-1", "suff-pe-1"):
        provenance.append(
            P4FProvenanceRecord(
                evidence_id=evidence_id,
                variable="market_price" if evidence_id == "price-1" else "fixture_variable",
                unit="CNY" if evidence_id == "price-1" else "CNY/share",
                basis="fixture",
                observation_date=CUTOFF,
                known_at=datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc),
                source="fixture-source",
                source_location=f"fixture://{evidence_id}",
                content_sha256="a" * 64,
                captured_at=CREATED,
            )
        )
    return build_p4f_snapshot(
        case_id=case_id,
        cutoff_date=CUTOFF,
        created_at=CREATED,
        mie_set=mie_set,
        provenance_records=provenance,
    )


def test_admit_and_resolve_round_trip(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    snapshot = make_snapshot()
    ref = registry.admit_p4f_snapshot(snapshot, admitted_at=CREATED)
    assert ref.root_type == P4F_MIE_SNAPSHOT_ROOT_TYPE
    assert ref.root_id == snapshot["snapshot_hash"]
    resolved = registry.resolve_p4f_snapshot(
        ref.to_dict(), case_id=snapshot["case_id"], cutoff_date=CUTOFF
    )
    assert resolved == snapshot


def test_unknown_root_is_fail_closed(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    ref = {
        "root_type": P4F_MIE_SNAPSHOT_ROOT_TYPE,
        "root_id": "1" * 64,
        "content_sha256": "2" * 64,
    }
    with pytest.raises(ValueError, match="unknown or not admitted"):
        registry.resolve_p4f_snapshot(ref, case_id="P1-1-CASE", cutoff_date=CUTOFF)


def test_valid_looking_but_never_admitted_snapshot_is_rejected(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    snapshot = make_snapshot()
    with pytest.raises(ValueError, match="unknown or not admitted"):
        registry.resolve_p4f_snapshot(
            {
                "root_type": P4F_MIE_SNAPSHOT_ROOT_TYPE,
                "root_id": snapshot["snapshot_hash"],
                "content_sha256": "a" * 64,
            },
            case_id=snapshot["case_id"],
            cutoff_date=CUTOFF,
        )


def test_wrong_content_hash_reference_is_rejected(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    ref = registry.admit_p4f_snapshot(make_snapshot(), admitted_at=CREATED)
    forged = {**ref.to_dict(), "content_sha256": "f" * 64}
    with pytest.raises(ValueError, match="does not match admitted root"):
        registry.resolve_p4f_snapshot(
            forged, case_id="P1-1-CASE", cutoff_date=CUTOFF
        )


def test_same_root_id_different_bytes_is_rejected(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    snapshot = make_snapshot()
    ref = registry.admit_p4f_snapshot(snapshot, admitted_at=CREATED)
    artifact = registry.artifacts_dir / f"{snapshot['snapshot_hash']}.mie.json"
    artifact.write_text(
        json.dumps({**snapshot, "case_id": "forged-case"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="content hash mismatch"):
        registry.resolve_p4f_snapshot(
            ref.to_dict(), case_id=snapshot["case_id"], cutoff_date=CUTOFF
        )


def test_tampered_admission_record_is_fail_closed(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    snapshot = make_snapshot()
    ref = registry.admit_p4f_snapshot(snapshot, admitted_at=CREATED)
    admission = registry.admissions_dir / f"{snapshot['snapshot_hash']}.admission.json"
    value = json.loads(admission.read_text(encoding="utf-8"))
    value["case_id"] = "forged-case"
    admission.write_text(json.dumps(value) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="admission record hash mismatch"):
        registry.resolve_p4f_snapshot(
            ref.to_dict(), case_id=snapshot["case_id"], cutoff_date=CUTOFF
        )


def test_cross_case_snapshot_reuse_is_rejected(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    snapshot = make_snapshot(case_id="P1-1-CASE-A")
    ref = registry.admit_p4f_snapshot(snapshot, admitted_at=CREATED)
    with pytest.raises(ValueError, match="case_id mismatch"):
        registry.resolve_p4f_snapshot(
            ref.to_dict(), case_id="P1-1-CASE-B", cutoff_date=CUTOFF
        )


def test_partial_admission_is_fail_closed(tmp_path):
    registry = FileSystemEvidenceRootRegistry(tmp_path)
    snapshot = make_snapshot()
    ref = registry.admit_p4f_snapshot(snapshot, admitted_at=CREATED)
    admission = registry.admissions_dir / f"{snapshot['snapshot_hash']}.admission.json"
    admission.unlink()
    with pytest.raises(ValueError, match="unknown or not admitted"):
        registry.resolve_p4f_snapshot(
            ref.to_dict(), case_id=snapshot["case_id"], cutoff_date=CUTOFF
        )


def test_reference_schema_accepts_only_the_root_pointer_shape():
    from pathlib import Path

    schema = json.loads(
        Path("schemas/evidence_root_reference_v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    ref = {
        "root_type": P4F_MIE_SNAPSHOT_ROOT_TYPE,
        "root_id": "a" * 64,
        "content_sha256": "b" * 64,
    }
    Draft202012Validator(schema).validate(ref)
    with pytest.raises(Exception):
        Draft202012Validator(schema).validate(
            {**ref, "snapshot": {"forged": True}}
        )
