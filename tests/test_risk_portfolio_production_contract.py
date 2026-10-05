from json import load
from decimal import Decimal
import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.risk_portfolio_production_contract import (
    RISK_PORTFOLIO_CONTRACT_VERSION,
    build_risk_portfolio_contract,
    validate_risk_portfolio_contract,
)

CASE_ID = "V03-RP-001"
CUTOFF = "2026-10-04"

def risk(**overrides):
    x = {"status":"PASS","max_loss_pct":"25","thesis_breaks":["driver deterioration"],"evidence_ids":["risk-evidence-1"]}
    x.update(overrides)
    return x

def portfolio(**overrides):
    x = {"position_pct":"0","constraint_status":"PASS","can_add":True,"buy_add_package":{
        "entry_zone":["95","100"],"initial_position_pct":"5","target_position_pct":"10","max_position_pct":"10",
        "thesis_break_triggers":["driver deterioration"],"monitoring_triggers":["quarterly results"]}}
    x.update(overrides)
    return x

def test_deterministic_and_versioned():
    a = build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=portfolio())
    b = build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=portfolio())
    assert a == b
    assert a["contract_version"] == RISK_PORTFOLIO_CONTRACT_VERSION
    validate_risk_portfolio_contract(a, case_id=CASE_ID, cutoff_date=CUTOFF)

def test_missing_can_add_fails_closed():
    p = portfolio(); del p["can_add"]
    with pytest.raises(ValueError, match="can_add is required"):
        build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=p)

def test_missing_risk_budget_fails_closed():
    x = risk(); del x["max_loss_pct"]
    with pytest.raises(ValueError, match="max_loss_pct"):
        build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=x, portfolio=portfolio())

def test_position_and_package_order_fail_closed():
    with pytest.raises(ValueError, match="position_pct"):
        build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=portfolio(position_pct="101"))
    p = portfolio()
    p["buy_add_package"]["initial_position_pct"] = "12"
    with pytest.raises(ValueError, match="initial <= target"):
        build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=p)

def test_absent_package_is_not_ready():
    x = build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=portfolio(buy_add_package=None))
    assert x["portfolio"]["package_status"] == "ABSENT"
    assert x["readiness"]["package_ready"] is False

def test_tampering_is_detected():
    x = build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=portfolio())
    x["risk"]["max_loss_pct"] = "20"
    with pytest.raises(ValueError, match="audit hash mismatch"):
        validate_risk_portfolio_contract(x, case_id=CASE_ID, cutoff_date=CUTOFF)

def test_schema_accepts_record():
    x = build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(), portfolio=portfolio())
    schema = load("schemas/risk_portfolio_production_v0.1.schema.json")
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(x)) == []

def test_unknown_is_valid_state_but_not_ready():
    x = build_risk_portfolio_contract(case_id=CASE_ID, cutoff_date=CUTOFF, risk=risk(status="UNKNOWN"), portfolio=portfolio(constraint_status="UNKNOWN"))
    assert x["readiness"]["risk_ready"] is False
    assert x["readiness"]["portfolio_constraint_ready"] is False
