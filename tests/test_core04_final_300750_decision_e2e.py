import json

from tools.core04_final_300750_decision_e2e import run


def test_core04_final_300750_decision_chain():
    result = run()
    assert result["case_id"] == "RC-CN-A-300750-20261004"
    assert result["default_horizon_years"] == "1"
    assert result["selected_horizon_years"] == "3"
    assert result["horizon_override"] is True
    assert result["quality_gate_status"] == "CONDITIONAL"
    assert result["thesis_admission_status"] == "ADMITTED"

    ret = result["return_metrics"]
    assert ret["fundamental_target_pass"] is False
    assert ret["required_return_pass"] is True
    assert ret["risk_pass"] is True

    strict = result["strict_decision"]
    assert strict["action"] == "REVIEW_REQUIRED"
    assert strict["capital_admitted"] is False

    isolated = result["quality_isolated_decision"]
    assert isolated["action"] == "REVIEW_REQUIRED"
    assert isolated["primary_reason"] == "QUALITY_GATE_UNRESOLVED"
    assert isolated["capital_admitted"] is False


def test_core04_final_300750_result_is_serializable():
    json.dumps(run(), ensure_ascii=False, sort_keys=True)
