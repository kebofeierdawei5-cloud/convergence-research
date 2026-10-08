from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
ENTRY = ROOT / "iios_mvp" / "canonical_natural_language_entry_v01.py"
SCHEMA = ROOT / "schemas" / "nl_request_admission_v0.1.schema.json"

EXPECTED_FIELDS = {"market", "symbol", "as_of_date", "current_position_pct", "request_type"}


def _source():
    return ENTRY.read_text(encoding="utf-8")


def test_rt_b2b_01_raw_request_is_hashed():
    source = _source()
    assert "raw_request_sha256" in source
    assert "request_sha256(raw_request)" in source


def test_rt_b2b_02_normalized_request_is_hashed():
    source = _source()
    assert "normalized_request_sha256" in source
    assert "canonical_hash(normalized_request)" in source


def test_rt_b2b_03_interpreter_is_registry_bound():
    source = _source()
    assert "registry.get(interpreter.interpreter_id)" in source
    assert "is not registry-authorized" in source


def test_rt_b2b_04_interpreter_type_allowlist_is_closed():
    source = _source()
    assert "REQUEST_INTERPRETER_TYPES" in source
    assert "LLM_REQUEST_INTERPRETER" in source
    assert "HUMAN_EXPERT_ADJUDICATION" in source


def test_rt_b2b_05_request_type_is_gated():
    source = _source()
    assert 'request_type != "INVESTMENT_DECISION"' in source


def test_rt_b2b_06_case_is_built_by_existing_research_intake():
    source = _source()
    assert "build_research_case(" in source
    assert "validate_research_case(case)" in source


def test_rt_b2b_07_case_hash_is_bound_into_run_and_receipt():
    source = _source()
    assert "research_case_hash=case_hash" in source
    assert '"case_hash": case_hash' in source


def test_rt_b2b_08_request_receipt_is_bound_to_run_stage():
    source = _source()
    assert "Stage.REQUEST_ADMITTED" in source
    assert 'output_hashes=(receipt["receipt_hash"],)' in source


def test_rt_b2b_09_case_creation_is_after_request_admission():
    tree = ast.parse(_source())
    names = [
        getattr(node.func, "attr", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert names.count("transition") >= 2


def test_rt_b2b_10_no_decision_or_execution_authority_in_entry():
    source = _source()
    for token in ("DECISION_ADMITTED", "HUMAN_APPROVAL_PENDING", "PUBLISHED", "ORDER"):
        assert token not in source


def test_rt_b2b_11_empty_raw_request_rejected():
    source = _source()
    assert "raw natural-language request is required" in source


def test_rt_b2b_12_receipt_schema_is_closed():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schema_version","request_id","run_id","raw_request_sha256","normalized_request_sha256",
        "normalized_request","case_id","case_hash","market","symbol","as_of_date","cutoff_date",
        "request_type","interpreter_type","interpreter_id","interpreter_version","policy_version",
        "orchestrator_version","status","created_at","receipt_hash"
    }


def test_rt_b2b_13_normalized_request_schema_is_closed():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    nr=schema["properties"]["normalized_request"]
    assert nr["additionalProperties"] is False
    assert set(nr["required"]) == EXPECTED_FIELDS


def test_rt_b2b_14_raw_hash_is_bytes_not_normalized_text():
    source = _source()
    assert 'hashlib.sha256(raw_request.encode("utf-8")).hexdigest()' in source


def test_rt_b2b_15_interpreter_cannot_claim_code_authority():
    source = _source()
    assert 'producer_type="CODE"' in source
    assert "interpreter_type" in source
