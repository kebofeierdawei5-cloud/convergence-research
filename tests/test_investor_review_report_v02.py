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
    assert report["report_version"] == INVESTOR_REPORT_VERSION
    assert report["machine_report"]["semantic_surface"]["human_review_readiness"] == "READY"
    assert qa["qa_version"] == INVESTOR_QA_VERSION
    assert qa["qa_status"] == "PASS"
    assert "## Quality / 经济质量" in report["markdown"]
    assert "## Market Implied Expectation / 市场隐含预期" in report["markdown"]
    assert "NOT_IDENTIFIABLE" in report["markdown"]


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
