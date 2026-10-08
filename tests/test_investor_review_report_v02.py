import json
from pathlib import Path

from jsonschema import Draft202012Validator

from iios_mvp.engine import sha256_obj
from iios_mvp.investor_review_report_v02 import (
    INVESTOR_QA_VERSION,
    INVESTOR_REPORT_VERSION,
    build_investor_review_report_v02,
    build_machine_surface,
    qa_investor_review_v02,
    validate_investor_review_qa_v02,
    validate_investor_review_report_v02,
    write_investor_review_report_v02,
    HUMAN_AUDITABILITY_CONTRACT_VERSION,
)
from iios_mvp.machine_publication import write_machine_publication
from iios_mvp.store import create_or_load_series, write_decision_revision, write_snapshot
from tests.decision_admission_fixture import build_fixture_admission_receipt


def _snapshot():
    cutoff = "2026-10-08"
    case_id = "V02-001"
    decision = {
        "engine_version": "0.3.0",
        "case_id": case_id,
        "symbol": "300750",
        "company": "CATL",
        "cutoff_date": cutoff,
        "action": "REVIEW_REQUIRED",
        "decision_status": "REVIEW_REQUIRED",
        "investability_status": "REVIEW_REQUIRED",
        "primary_reason": "TRUST_REVALIDATION",
        "human_approval_required": True,
        "auto_execution": False,
        "current_price": "291.11",
        "gates": {
            "trust": "REVALIDATION", "quality": "CONDITIONAL", "reality": "PASS",
            "forecast": "PASS", "valuation": "PASS",
            "new_capital_allowed": False, "positioning_sizing_permission": "NO_SIZING_PERMISSION",
        },
        "trust": {"status": "REVALIDATION", "revalidation_required": True, "evidence_ids": ["E001"]},
        "evidence_chain": [
            {"evidence_id": "E001", "claim_type": "OBSERVED_FACT", "source": "annual_report", "period": "2025", "known_at": cutoff, "purpose": "financial history"},
            {"evidence_id": "E002", "claim_type": "OBSERVED_FACT", "source": "exchange", "period": "2026Q2", "known_at": cutoff, "purpose": "quarterly reality"},
        ],
        "quality": {"status": "CONDITIONAL", "business_model": "platform", "competitive_advantage": "scale"},
        "reality": {"status": "PASS", "revenue": "507.1", "operating_cash_flow": "71.4"},
        "thesis": {"status": "ADMITTED", "summary": "scale economics", "falsifiers": ["margin deterioration"]},
        "value_driver_ranking": {"status": "PASS", "drivers": ["volume", "margin", "capital efficiency"]},
        "forecast": {"method": "NORMALIZED_EARNINGS_DRIVER_SCENARIO", "horizon_years": "3",
                     "scenarios": {
                         "bear": {"normalized_eps_cny": "9", "valuation_multiple": "18", "probability": "0.25", "value_per_share": "162"},
                         "base": {"normalized_eps_cny": "11", "valuation_multiple": "22", "probability": "0.50", "value_per_share": "242"},
                         "bull": {"normalized_eps_cny": "13.5", "valuation_multiple": "25", "probability": "0.25", "value_per_share": "337.5"}}},
        "valuation": {"status": "PASS", "primary_model": "FORWARD_PE", "rationale": "normalised EPS",
                      "scenario_values_per_share": {"bear": "162", "base": "242", "bull": "337.5"}},
        "p4f_market_implied_expectation": {"status": "NOT_IDENTIFIABLE", "identifiability": "FAIL", "stability": "UNKNOWN", "decision_grade": "NO"},
        "expectation_gap": {"status": "NOT_IDENTIFIABLE", "reason": "MIE unavailable"},
        "risk": {"status": "PASS", "max_loss_pct": "0.25", "key_risks": ["capex", "margin"]},
        "positioning": {"status": "UNKNOWN", "crowding": "unknown"},
        "return_metrics": {"expected_annualized_return": "0.142", "required_return": "0.10", "margin_of_safety": "0.15", "target_entry_price": "245"},
        "risk_portfolio_contract": {"portfolio": {"position_pct": "0", "buy_add_package": {"entry_zone": ["235", "245"], "initial_position_pct": "5", "target_position_pct": "10", "max_position_pct": "10"}}},
        "monitoring": [{"metric": "margin", "condition": "quarterly check"}],
    }
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0", "engine_version": "0.3.0",
        "input": {"case_id": case_id, "market": "CN-A", "symbol": "300750", "company": "CATL", "as_of_date": cutoff, "cutoff_date": cutoff},
        "decision": decision,
    }
    core["snapshot_hash"] = sha256_obj({"snapshot_schema": core["snapshot_schema"], "engine_version": core["engine_version"], "input": core["input"], "decision": core["decision"]})
    return core


def _publication(tmp_path):
    snapshot = _snapshot()
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-08T00:00:00+00:00")
    decision_id = "CN-A-300750-r001"
    write_decision_revision(tmp_path, series["decision_series_id"], 1, snapshot, "run-v02-001",
                            decision_admission=build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"]))
    path = write_machine_publication(tmp_path, decision_id=decision_id, published_at="2026-10-08T01:00:00+00:00")
    return json.loads(path.read_text(encoding="utf-8")), path


def test_v02_dual_surface_and_schema(tmp_path):
    publication, _ = _publication(tmp_path)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    validate_investor_review_report_v02(report)
    qa = qa_investor_review_v02(publication=publication, report=report)
    validate_investor_review_qa_v02(qa)
    Draft202012Validator(json.loads(Path("schemas/investor_review_report_v0.2.schema.json").read_text())).validate(report)
    Draft202012Validator(json.loads(Path("schemas/investor_review_qa_v0.2.schema.json").read_text())).validate(qa)
    audit_schema = json.loads(Path("schemas/human_auditability_v0.2.schema.json").read_text())
    Draft202012Validator(audit_schema).validate(report["machine_report"]["semantic_surface"]["human_auditability"])
    assert report["report_version"] == INVESTOR_REPORT_VERSION
    assert report["machine_report"]["semantic_surface"]["human_review_readiness"] == "READY"
    assert qa["qa_version"] == INVESTOR_QA_VERSION
    assert qa["qa_status"] == "PASS"
    assert qa["checks"]["human_auditability_contract"] == "PASS"
    assert "## Quality / 经济质量" in report["markdown"]
    assert "## Market Implied Expectation / 市场隐含预期" in report["markdown"]
    assert "NOT_IDENTIFIABLE" in report["markdown"]



def test_v02_p0_required_return_pass_without_value_is_incomplete(tmp_path):
    publication, _ = _publication(tmp_path)
    payload = publication["decision_payload"]
    payload["return_metrics"]["required_return"] = None
    payload["return_metrics"]["required_return_pass"] = True
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["required_return"]["status"] == "INCOMPLETE"
    assert audit["required_return"]["numeric_value"] is None
    assert "Required Return" in report["markdown"]

def test_v02_p0_expected_return_requires_scenario_probabilities(tmp_path):
    publication, _ = _publication(tmp_path)
    scenarios = publication["decision_payload"]["forecast"]["scenarios"]
    for item in scenarios.values():
        item.pop("probability", None)
        item.pop("prob", None)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["scenario_probability"]["status"] == "MISSING"
    assert audit["expected_return"]["status"] == "INCOMPLETE"

def test_v02_p0_threshold_is_not_actionable_entry(tmp_path):
    publication, _ = _publication(tmp_path)
    decision = publication["ai_decision"]
    decision["target_entry_price"] = None
    publication["decision_payload"]["return_metrics"]["target_entry_price"] = "26.60"
    publication["decision_payload"]["target_entry_price_semantics"] = "RETURN_RISK_THRESHOLD_ONLY"
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["entry_price"]["status"] == "THRESHOLD_ONLY"
    assert audit["entry_price"]["actionable_target_entry_price"] is None
    assert audit["entry_price"]["threshold_price"] == "26.60"
    assert "THRESHOLD_ONLY" in report["markdown"]

def test_v02_p0_portfolio_can_add_is_overridden_by_decision(tmp_path):
    publication, _ = _publication(tmp_path)
    payload = publication["decision_payload"]
    payload["gates"]["new_capital_allowed"] = False
    payload["gates"]["positioning_sizing_permission"] = "NO_SIZING_PERMISSION"
    package = publication["ai_decision"]["risk_portfolio_contract"]["portfolio"]
    package["can_add"] = True
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["portfolio_permission"]["status"] == "OVERRIDDEN_BY_DECISION"
    assert audit["portfolio_permission"]["override"] is True
    assert "OVERRIDDEN_BY_DECISION" in report["markdown"]

def test_v02_p0_mie_absence_never_implies_not_identifiable(tmp_path):
    publication, _ = _publication(tmp_path)
    payload = publication["decision_payload"]
    payload.pop("p4f_market_implied_expectation", None)
    payload.pop("expectation_gap", None)
    payload.pop("expectation_gap_evaluation", None)
    payload["gates"]["expectation_gap_status"] = "UNKNOWN"
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["contract_version"] == HUMAN_AUDITABILITY_CONTRACT_VERSION
    assert audit["mie_expectation_gap"]["mie"]["status"] == "NOT_PROVIDED"
    assert audit["mie_expectation_gap"]["mie"]["identifiability"] is None
    assert audit["mie_expectation_gap"]["expectation_gap"]["status"] == "UNKNOWN"
    assert audit["mie_expectation_gap"]["inference_rule"] == "absence_never_implies_not_identifiable"
    assert "NOT_IDENTIFIABLE" not in report["markdown"]

def test_v02_p0_explicit_mie_not_identifiable_is_preserved(tmp_path):
    publication, _ = _publication(tmp_path)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["mie_expectation_gap"]["mie"]["status"] == "NOT_IDENTIFIABLE"
    assert audit["mie_expectation_gap"]["mie"]["identifiability"] == "FAIL"
    assert audit["mie_expectation_gap"]["expectation_gap"]["status"] == "NOT_IDENTIFIABLE"


def test_v02_human_auditability_contract_is_emitted(tmp_path):
    publication, _ = _publication(tmp_path)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["contract_version"] == HUMAN_AUDITABILITY_CONTRACT_VERSION
    assert set(audit) == {
        "contract_version", "required_return", "expected_return",
        "scenario_probability", "entry_price", "portfolio_permission",
        "mie_expectation_gap", "overall_status",
    }


def test_v02_real_xinhecheng_p0_shape_regression(tmp_path):
    publication, _ = _publication(tmp_path)
    payload = publication["decision_payload"]
    decision = publication["ai_decision"]

    # Real XHC PILOT-04 published values:
    payload["gates"]["new_capital_allowed"] = False
    payload["gates"]["positioning_sizing_permission"] = "NO_SIZING_PERMISSION"
    payload["gates"]["expectation_gap_status"] = "UNKNOWN"
    payload["return_metrics"]["required_return"] = None
    payload["return_metrics"]["required_return_pass"] = True
    payload["return_metrics"]["expected_annualized_return"] = "0.201734104046242774566473988"
    payload["return_metrics"]["target_entry_price"] = "26.60"
    payload["target_entry_price_semantics"] = "RETURN_RISK_THRESHOLD_ONLY;OPTIONAL_MIE_REFINEMENT_WHEN_AVAILABLE"
    decision["target_entry_price"] = None
    decision["risk_portfolio_contract"]["portfolio"]["can_add"] = True
    for scenario in payload["forecast"]["scenarios"].values():
        scenario.pop("probability", None)
        scenario.pop("prob", None)
    payload.pop("p4f_market_implied_expectation", None)
    payload.pop("expectation_gap", None)
    payload.pop("expectation_gap_evaluation", None)

    report = build_investor_review_report_v02(
        publication=publication, generated_at="2026-10-08T02:00:00+00:00"
    )
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["required_return"]["status"] == "INCOMPLETE"
    assert audit["expected_return"]["status"] == "INCOMPLETE"
    assert audit["scenario_probability"]["status"] == "MISSING"
    assert audit["entry_price"]["status"] == "THRESHOLD_ONLY"
    assert audit["entry_price"]["threshold_price"] == "26.60"
    assert audit["portfolio_permission"]["status"] == "OVERRIDDEN_BY_DECISION"
    assert audit["mie_expectation_gap"]["mie"]["status"] == "NOT_PROVIDED"
    assert audit["mie_expectation_gap"]["expectation_gap"]["status"] == "UNKNOWN"
    assert audit["mie_expectation_gap"]["inference_rule"] == "absence_never_implies_not_identifiable"
    assert audit["overall_status"] == "INCOMPLETE"

def test_v02_p0_required_return_pass_without_value_is_not_auditable(tmp_path):
    publication, _ = _publication(tmp_path)
    returns = publication["decision_payload"]["return_metrics"]
    returns["required_return"] = None
    returns["required_return_pass"] = True
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["required_return"]["status"] == "INCOMPLETE"
    assert audit["required_return"]["numeric_value"] is None
    assert audit["overall_status"] == "INCOMPLETE"

def test_v02_p0_expected_return_missing_scenario_probabilities_is_incomplete(tmp_path):
    publication, _ = _publication(tmp_path)
    for scenario in publication["decision_payload"]["forecast"]["scenarios"].values():
        scenario.pop("probability", None)
        scenario.pop("prob", None)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["scenario_probability"]["status"] == "MISSING"
    assert audit["expected_return"]["status"] == "INCOMPLETE"

def test_v02_p0_threshold_price_never_becomes_actionable_entry(tmp_path):
    publication, _ = _publication(tmp_path)
    publication["ai_decision"]["target_entry_price"] = None
    publication["decision_payload"]["return_metrics"]["target_entry_price"] = "26.60"
    publication["decision_payload"]["target_entry_price_semantics"] = "RETURN_RISK_THRESHOLD_ONLY"
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["entry_price"]["status"] == "THRESHOLD_ONLY"
    assert audit["entry_price"]["actionable_target_entry_price"] is None
    assert audit["entry_price"]["threshold_price"] == "26.60"

def test_v02_p0_package_can_add_is_overridden_by_decision(tmp_path):
    publication, _ = _publication(tmp_path)
    gates = publication["decision_payload"]["gates"]
    gates["new_capital_allowed"] = False
    gates["positioning_sizing_permission"] = "NO_SIZING_PERMISSION"
    publication["ai_decision"]["risk_portfolio_contract"]["portfolio"]["can_add"] = True
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    assert audit["portfolio_permission"]["status"] == "OVERRIDDEN_BY_DECISION"
    assert audit["portfolio_permission"]["override"] is True
    assert audit["overall_status"] == "INCOMPLETE"

def test_v02_p0_mie_absence_preserves_unknown_vs_not_identifiable(tmp_path):
    publication, _ = _publication(tmp_path)
    payload = publication["decision_payload"]
    payload.pop("p4f_market_implied_expectation", None)
    payload.pop("expectation_gap", None)
    payload.pop("expectation_gap_evaluation", None)
    payload["gates"]["expectation_gap_status"] = "UNKNOWN"
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    mg = audit["mie_expectation_gap"]
    assert mg["mie"]["status"] == "NOT_PROVIDED"
    assert mg["mie"]["identifiability"] is None
    assert mg["expectation_gap"]["status"] == "UNKNOWN"
    assert mg["expectation_gap"]["source_presence"] == "MISSING"
    assert "MIE：**NOT_PROVIDED**" in report["markdown"]

def test_v02_p0_explicit_not_identifiable_is_preserved(tmp_path):
    publication, _ = _publication(tmp_path)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    mg = report["machine_report"]["semantic_surface"]["human_auditability"]["mie_expectation_gap"]
    assert mg["mie"]["status"] == "NOT_IDENTIFIABLE"
    assert mg["mie"]["identifiability"] == "FAIL"

def test_v02_missing_modules_are_explicit_and_not_ready(tmp_path):
    publication, _ = _publication(tmp_path)
    for key in ("quality", "reality", "p4f_market_implied_expectation", "expectation_gap", "positioning"):
        publication["decision_payload"].pop(key, None)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    surface = report["machine_report"]["semantic_surface"]
    assert surface["human_review_readiness"] == "HUMAN_REVIEW_NOT_READY"
    assert "NOT_PROVIDED" in report["markdown"]
    assert set(surface["missing_core_modules"]) >= {"quality", "reality", "mie", "expectation_gap", "positioning"}


def test_v02_preserves_explicit_mie_identifiability_status(tmp_path):
    publication, _ = _publication(tmp_path)
    surface = build_machine_surface(publication)
    assert surface["semantic_matrix"]["mie"]["status"] == "NOT_IDENTIFIABLE"
    assert surface["semantic_matrix"]["expectation_gap"]["status"] == "NOT_IDENTIFIABLE"


def test_v02_machine_surface_tampering_fails_closed(tmp_path):
    publication, _ = _publication(tmp_path)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    tampered = dict(report)
    tampered_machine = dict(tampered["machine_report"])
    tampered_surface = dict(tampered_machine["semantic_surface"])
    tampered_surface["human_review_readiness"] = "READY_FOR_ANYTHING"
    tampered_machine["semantic_surface"] = tampered_surface
    tampered["machine_report"] = tampered_machine
    qa = qa_investor_review_v02(publication=publication, report=tampered)
    assert qa["qa_status"] == "FAIL"
    assert qa["checks"]["machine_surface_integrity"] == "FAIL"


def test_v02_tampering_and_replay(tmp_path):
    publication, _ = _publication(tmp_path)
    report = build_investor_review_report_v02(publication=publication, generated_at="2026-10-08T02:00:00+00:00")
    tampered = dict(report)
    tampered["markdown"] = tampered["markdown"].replace("当前动作：REVIEW_REQUIRED", "当前动作：BUY")
    qa = qa_investor_review_v02(publication=publication, report=tampered)
    assert qa["qa_status"] == "FAIL"
    assert qa["checks"]["human_surface_integrity"] == "FAIL"


def test_v02_immutable_dual_artifacts(tmp_path):
    publication, pub_path = _publication(tmp_path)
    first = write_investor_review_report_v02(tmp_path, publication_path=pub_path, generated_at="2026-10-08T02:00:00+00:00")
    before = [p.read_bytes() for p in first]
    second = write_investor_review_report_v02(tmp_path, publication_path=pub_path, generated_at="2026-10-08T02:00:00+00:00")
    assert first == second
    assert [p.read_bytes() for p in first] == before
