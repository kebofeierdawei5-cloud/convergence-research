from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
ADMISSION = ROOT / "iios_mvp" / "semantic_producer_admission_v01.py"
WORKBENCH = ROOT / "iios_mvp" / "llm_semantic_workbench_v01.py"
SCHEMA = ROOT / "schemas" / "semantic_producer_receipt_v0.1.schema.json"

ALLOWED_TYPES = {
    "LLM_SEMANTIC_PRODUCER",
    "HUMAN_EXPERT_ADJUDICATION",
}
ARTIFACT_TYPES = {
    "REALITY_INTERPRETATION",
    "TRUST_ASSESSMENT",
    "QUALITY_ASSESSMENT",
    "THESIS_ASSESSMENT",
    "VALUE_DRIVER_ASSESSMENT",
    "INDEPENDENT_FORECAST_REASONING",
    "VALUATION_PROPOSAL",
    "MIE_INTERPRETATION",
    "RISK_ASSESSMENT",
    "POSITIONING_ASSESSMENT",
}


def sha256_json(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_rt_b2_01_producer_allowlist_is_closed():
    source = ADMISSION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        node.targets[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and node.targets
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "SEMANTIC_ARTIFACT_TYPES"
    }
    assert names == {"SEMANTIC_ARTIFACT_TYPES"}
    for token in ("LLM_SEMANTIC_PRODUCER", "HUMAN_EXPERT_ADJUDICATION"):
        assert token in source


def test_rt_b2_02_external_json_not_authorized():
    source = ADMISSION.read_text(encoding="utf-8")
    assert "producer_type not in SEMANTIC_PRODUCER_TYPES" in source
    assert "registration = registry.get" in source


def test_rt_b2_03_registry_binds_version_and_policy():
    source = ADMISSION.read_text(encoding="utf-8")
    for token in (
        "producer_type mismatch",
        "producer_version mismatch",
        "policy_version mismatch",
        "producer receipt integrity failure",
    ):
        assert token in source


def test_rt_b2_04_artifact_hash_covers_full_artifact_without_hash_field():
    source = ADMISSION.read_text(encoding="utf-8")
    assert "_without_hash(artifact, 'artifact_hash')" in source
    assert "artifact_hash integrity failure" in source


def test_rt_b2_05_receipt_hash_is_separate_from_artifact_hash():
    source = ADMISSION.read_text(encoding="utf-8")
    assert "SEMANTIC_PRODUCER_RECEIPT_SCHEMA_VERSION" in source
    assert "receipt_hash" in source
    assert "output_hash" in source


def test_rt_b2_06_output_hash_binds_actual_output():
    source = ADMISSION.read_text(encoding="utf-8")
    assert "_hash_json(artifact['output'])" in source
    assert "producer receipt output_hash mismatch" in source


def test_rt_b2_07_exact_identity_and_cutoff_binding():
    source = ADMISSION.read_text(encoding="utf-8")
    for field in ("case_id", "market", "symbol", "company", "cutoff_date"):
        assert field in source
        assert f"{field} mismatch" in source


def test_rt_b2_08_exact_input_lineage_binding():
    source = ADMISSION.read_text(encoding="utf-8")
    assert "input_refs lineage mismatch" in source
    assert "input_hashes lineage mismatch" in source
    assert "semantic input lineage is not fully admitted" in WORKBENCH.read_text(encoding="utf-8")


def test_rt_b2_09_workbench_requires_semantic_pending():
    source = WORKBENCH.read_text(encoding="utf-8")
    assert "Stage.SEMANTIC_PENDING" in source
    assert ".authorize(request.run_id, Stage.SEMANTIC_PENDING)" in source


def test_rt_b2_10_workbench_binds_request_to_run():
    source = WORKBENCH.read_text(encoding="utf-8")
    assert "request case_id does not match canonical run" in source
    assert "request market does not match canonical run" in source
    assert "request symbol does not match canonical run" in source
    assert "request cutoff_date does not match canonical run" in source


def test_rt_b2_11_workbench_requires_admitted_evidence_receipt():
    source = WORKBENCH.read_text(encoding="utf-8")
    assert "Stage.EVIDENCE_ADMITTED.value" in source
    assert "semantic inputs require an admitted evidence receipt" in source


def test_rt_b2_12_workbench_only_advances_semantic_stage():
    source = WORKBENCH.read_text(encoding="utf-8")
    assert "Stage.SEMANTIC_ADMITTED" in source
    assert "Stage.DECISION_ADMITTED" not in source
    assert "Stage.HUMAN_APPROVAL_PENDING" not in source


def test_rt_b2_13_schema_closes_unknown_receipt_fields():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["properties"]["producer_type"]["enum"] == sorted(ALLOWED_TYPES) or set(
        schema["properties"]["producer_type"]["enum"]
    ) == ALLOWED_TYPES
    assert set(schema["properties"]["artifact_type"]["enum"]) == ARTIFACT_TYPES


def test_rt_b2_14_hash_fixture_is_deterministic():
    core = {
        "case_id": "c",
        "producer_id": "p",
        "producer_version": "v",
        "policy_version": "policy",
        "input_refs": ["E001"],
        "input_hashes": ["a" * 64],
        "output": {"status": "PASS"},
    }
    assert sha256_json(core) == sha256_json(dict(reversed(list(core.items()))))


def test_rt_b2_15_evidence_hash_does_not_equal_semantic_authority():
    source = ADMISSION.read_text(encoding="utf-8")
    assert "producer is not registered" in source
    assert "registered producer_type mismatch" in source
    assert "registered producer_version mismatch" in source
    assert "registered policy_version mismatch" in source
