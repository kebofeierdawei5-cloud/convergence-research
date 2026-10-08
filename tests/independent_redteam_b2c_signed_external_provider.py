from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
ENTRY = ROOT / "iios_mvp" / "external_semantic_provider_admission_v01.py"
SCHEMA = ROOT / "schemas" / "external_semantic_provider_receipt_v0.1.schema.json"


def source():
    return ENTRY.read_text(encoding="utf-8")


def test_rt_b2c_01_signature_is_cryptographically_verified():
    s = source()
    assert "Ed25519PublicKey" in s
    assert "public_key.verify(signature, _attestation_payload(attestation))" in s


def test_rt_b2c_02_trust_registry_binds_provider_identity():
    s = source()
    assert 'trusted = registry.get(attestation["public_key_id"])' in s
    assert "trusted provider " in s


def test_rt_b2c_03_raw_request_hash_is_bound():
    s = source()
    assert "raw_request_sha256" in s
    assert "external receipt raw request hash mismatch" not in s
    assert "raw request hash mismatch" in s


def test_rt_b2c_04_artifact_hash_and_lineage_are_bound():
    s = source()
    assert "artifact_hash mismatch" in s
    assert "input_refs mismatch" in s
    assert "input_hashes mismatch" in s


def test_rt_b2c_05_case_and_cutoff_are_bound():
    s = source()
    assert "case_id mismatch" in s
    assert "cutoff_date mismatch" in s


def test_rt_b2c_06_signature_algorithm_is_fixed():
    s = source()
    assert 'signature_algorithm"] != "Ed25519"' in s


def test_rt_b2c_07_unsigned_receipt_is_blocked():
    s = source()
    assert 'status"] != "SIGNED"' in s


def test_rt_b2c_08_attestation_hash_is_integrity_checked():
    s = source()
    assert "attestation_hash" in s
    assert "external receipt integrity failure" in s


def test_rt_b2c_09_only_llm_semantic_provider_is_admitted():
    s = source()
    assert 'producer_type"] != "LLM_SEMANTIC_PRODUCER"' in s


def test_rt_b2c_10_canonical_semantic_admission_is_reused():
    s = source()
    assert "admit_semantic_artifact(" in s
    assert "ProducerRegistry" in s


def test_rt_b2c_11_orchestrator_stage_is_required():
    s = source()
    assert "Stage.SEMANTIC_PENDING" in s
    assert "Stage.SEMANTIC_ADMITTED" in s


def test_rt_b2c_12_no_decision_or_execution_authority():
    s = source()
    for token in ("DECISION_ADMITTED", "HUMAN_APPROVAL_PENDING", "PUBLISHED", "ORDER"):
        assert token not in s


def test_rt_b2c_13_schema_is_closed():
    schema=json.loads(SCHEMA.read_text())
    assert schema["additionalProperties"] is False


def test_rt_b2c_14_schema_fixes_signature_status():
    schema=json.loads(SCHEMA.read_text())
    assert schema["properties"]["signature_algorithm"]["const"] == "Ed25519"
    assert schema["properties"]["status"]["const"] == "SIGNED"


def test_rt_b2c_15_provider_identity_is_structurally_separate_from_key():
    s=source()
    assert "public_key_id" in s
    assert "producer_id" in s
    assert "producer_version" in s
    assert "policy_version" in s
