import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

from tools.c3_kolun_second_company_e2e import run, CASE_PATH, PRICE_CAPTURE_PATH


def test_c3_kolun_is_a_real_second_company_case():
    result = run()
    assert result["case_id"] == "RC-CN-A-002422-20261004"
    assert result["company"] == "四川科伦药业股份有限公司"
    assert result["symbol"] == "002422"
    assert result["economic_structure"] == "PHARMA_MANUFACTURING_AND_CONTROLLED_BIOTECH"
    assert result["valuation_primary_model"] == "SOTP"
    assert result["forecast_assumption_version"] == "C3-KOLUN-FORECAST-ASSUMPTIONS-0.1"
    assert result["current_price"] == "40.85"


def test_c3_decision_and_lifecycle_are_canonical_paths():
    result = run()
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert result["decision"]["decision_status"] == "REVIEW_REQUIRED"
    assert result["decision"]["primary_reason"] == "QUALITY_GATE_UNRESOLVED"
    assert result["decision"]["new_capital_allowed"] is False
    assert result["return_metrics"]["fundamental_target_pass"] is True
    assert result["return_metrics"]["required_return_pass"] is True
    assert result["return_metrics"]["risk_pass"] is True
    assert result["lifecycle"]["trigger_state"] == "MATCHED"
    assert result["lifecycle"]["monitoring_evaluation_status"] == "MATCHED"
    assert result["lifecycle"]["validation_status"] == "PASS"
    assert result["lifecycle"]["decision_replay_status"] == "PASS"


def test_c3_publication_and_report_are_deterministic_projections():
    result = run()
    assert result["publication"]["qa_status"] == "PASS"
    assert result["publication"]["report_deterministic_replay"] is True
    assert len(result["publication"]["publication_hash"]) == 64
    assert len(result["publication"]["report_hash"]) == 64
    assert len(result["publication"]["qa_hash"]) == 64
    assert result["authority_boundary"]["human_approval_required"] is True
    assert result["authority_boundary"]["auto_execution"] is False
    assert result["authority_boundary"]["report_policy_effect"] == "REPORT_ONLY_PROJECTION"
    assert result["authority_boundary"]["validation_policy_effect"] == "NO_DIRECT_DECISION_PRECEDENCE_CHANGE"


def test_c3_fixture_evidence_hashes_and_case_schema_are_bound():
    fixture = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    for row in fixture["evidence"]:
        if "capture" in row:
            assert hashlib.sha256(row["capture"].encode("utf-8")).hexdigest() == row["capture_sha256"]

    assert hashlib.sha256(PRICE_CAPTURE_PATH.read_bytes()).hexdigest() == fixture["evidence"][-1]["capture_sha256"]
    schema = json.loads(Path("schemas/investment_core_case_v0.3.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors({
        **__import__("tools.c3_kolun_second_company_e2e", fromlist=["build_case"]).build_case(
            fixture,
            {
                "price_observation_id": "placeholder",
                "admission_record_hash": "0" * 64,
            },
        )
    }), key=lambda error: list(error.path))
    assert not errors, [error.message for error in errors]
