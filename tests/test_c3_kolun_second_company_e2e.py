import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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


def test_c3_economic_calculation_is_inspectable_but_lifecycle_is_fail_closed():
    result = run()
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert result["decision"]["decision_status"] == "REVIEW_REQUIRED"
    assert result["decision"]["primary_reason"] == "QUALITY_GATE_UNRESOLVED"
    assert result["decision"]["new_capital_allowed"] is False
    assert result["return_metrics"]["fundamental_target_pass"] is True
    assert result["return_metrics"]["required_return_pass"] is True
    assert result["return_metrics"]["risk_pass"] is True
    assert result["lifecycle"]["status"] == "BLOCKED_NOT_ADMITTED"
    assert result["lifecycle"]["blocking_gate"] == "B2_EVIDENCE_PIT_ADMISSION_REQUIRED"
    assert result["lifecycle"]["formal_decision_revision_created"] is False
    assert result["lifecycle"]["trigger_state"] == "NOT_RUN"
    assert result["lifecycle"]["monitoring_evaluation_status"] == "NOT_RUN"
    assert result["lifecycle"]["validation_status"] == "NOT_RUN"
    assert result["lifecycle"]["decision_replay_status"] == "NOT_RUN"


def test_c3_publication_and_report_are_blocked_without_admitted_b2_manifest():
    result = run()
    assert result["publication"]["status"] == "BLOCKED_NOT_ADMITTED"
    assert result["publication"]["qa_status"] == "BLOCKED_NOT_ADMITTED"
    assert result["publication"]["report_deterministic_replay"] is False
    assert result["publication"]["publication_hash"] is None
    assert result["publication"]["report_hash"] is None
    assert result["publication"]["qa_hash"] is None
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
    from tools.c3_kolun_second_company_e2e import build_case

    built_case = build_case(
        fixture,
        {
            "price_observation_id": "placeholder",
            "admission_record_hash": "0" * 64,
        },
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(built_case),
        key=lambda error: list(error.path),
    )
    assert not errors, [error.message for error in errors]
