import json
from pathlib import Path

from jsonschema import Draft202012Validator

from iios_mvp.canonical_research_orchestrator import canonical_hash


def _schema(name: str) -> dict:
    path = Path(__file__).parents[1] / "schemas" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_receipt_schema_accepts_canonical_complete_receipt():
    core = {
        "schema_version": "IIOS-RUN-RECEIPT-0.1",
        "run_id": "r-schema",
        "case_id": "c-schema",
        "market": "CN-A",
        "symbol": "002001.SZ",
        "cutoff_date": "2026-10-07",
        "as_of_date": "2026-10-07",
        "orchestrator_version": "IIOS-CANONICAL-RESEARCH-ORCHESTRATOR-0.1",
        "research_case_hash": "a" * 64,
        "evidence_manifest_hash": "b" * 64,
        "semantic_artifact_hashes": ["c" * 64],
        "forecast_admission_hash": "d" * 64,
        "valuation_admission_hash": "e" * 64,
        "return_hash": "f" * 64,
        "risk_portfolio_hash": "0" * 64,
        "decision_admission_hash": "1" * 64,
        "decision_revision": 1,
        "publication_hash": "2" * 64,
        "report_hash": "3" * 64,
        "run_status": "COMPLETE",
    }
    record = {**core, "receipt_hash": canonical_hash(core)}
    Draft202012Validator(_schema("iios_run_receipt_v0.1.schema.json")).validate(record)


def test_semantic_artifact_schema_rejects_external_json():
    artifact = {
        "artifact_id": "a1",
        "artifact_type": "QUALITY_ASSESSMENT",
        "schema_version": "IIOS-LLM-SEMANTIC-ARTIFACT-0.1",
        "case_id": "c1",
        "market": "CN-A",
        "symbol": "002001.SZ",
        "company": "Test",
        "cutoff_date": "2026-10-07",
        "producer_type": "EXTERNAL_JSON",
        "producer_id": "external",
        "producer_version": "1",
        "policy_version": "p0",
        "input_refs": ["e1"],
        "input_hashes": ["a" * 64],
        "output": {},
        "facts": [],
        "inferences": [],
        "assumptions": [],
        "uncertainties": [],
        "decision_relevance": "test",
        "created_at": "2026-10-07T00:00:00+00:00",
        "artifact_hash": "b" * 64,
    }
    errors = list(Draft202012Validator(_schema("llm_semantic_artifact_v0.1.schema.json")).iter_errors(artifact))
    assert any("is not one of" in error.message for error in errors)
