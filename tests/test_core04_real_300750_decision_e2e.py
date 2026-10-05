import json

from tools.core04_real_300750_decision_e2e import run


def test_core04_real_300750_production_decision_e2e():
    result = run()

    assert result["case_id"] == "RC-CN-A-300750-20261004"
    assert result["current_price"] == "291.11"

    ret = result["return_metrics"]
    assert ret["fundamental_target_pass"] is False
    assert ret["required_return_pass"] is True
    assert ret["risk_pass"] is True
    assert ret["expected_annualized_return"].startswith("0.142001125678525")

    strict = result["strict_real_case"]
    assert strict["action"] == "REVIEW_REQUIRED"
    assert strict["capital_admitted"] is False

    diagnostic = result["gate_normalized_diagnostic"]
    assert diagnostic["action"] == "WATCH"
    assert diagnostic["capital_admitted"] is False
    assert diagnostic["mie_policy"] == "OPTIONAL_EXPLANATORY"


def test_core04_real_300750_output_is_json_serializable():
    result = run()
    json.dumps(result, ensure_ascii=False, sort_keys=True)
