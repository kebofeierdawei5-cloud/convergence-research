import json
from argparse import Namespace
from pathlib import Path

from jsonschema import Draft202012Validator

from iios_mvp.investor_review_report import (
    INVESTOR_QA_VERSION,
    INVESTOR_REPORT_VERSION,
    build_investor_review_report,
    qa_investor_review_report,
    validate_investor_review_qa,
    validate_investor_review_report,
    write_investor_review_report,
)
from iios_mvp.engine import sha256_obj
from iios_mvp.store import create_or_load_series, write_decision_revision, write_snapshot
from tests.decision_admission_fixture import build_fixture_admission_receipt, prepare_authorized_test_run


def make_snapshot():
    case_id = "C2-001"
    cutoff = "2026-10-06"
    decision = {
        "engine_version": "0.3.0",
        "case_id": case_id,
        "symbol": "300750",
        "company": "CATL",
        "cutoff_date": cutoff,
        "action": "REVIEW_REQUIRED",
        "decision_status": "REVIEW_REQUIRED",
        "investability_status": "REVIEW_REQUIRED",
        "primary_reason": "TEST_REASON",
        "human_approval_required": True,
        "auto_execution": False,
        "gates": {
            "trust": "REVALIDATION",
            "reality": "PASS",
            "forecast": "PASS",
            "valuation": "PASS",
            "new_capital_allowed": False,
            "positioning_sizing_permission": "NO_SIZING_PERMISSION",
        },
        "evidence_chain": [{"evidence_id": "E001"}],
        "forecast": {
            "method": "NORMALIZED_EARNINGS_DRIVER_SCENARIO",
            "horizon_years": "1",
            "style_weighting": {"cyclical": "0.70", "growth": "0.30"},
            "scenarios": {
                "base": {"normalized_eps_cny": "2.80", "valuation_multiple": "11.5"},
                "bear": {"normalized_eps_cny": "2.10"},
                "bull": {"normalized_eps_cny": "3.50"},
            },
        },
        "valuation": {
            "primary_model": "FORWARD_PE",
            "scenario_values_per_share": {"base": "32.20", "bear": "19.95", "bull": "45.50"},
        },
        "return_metrics": {
            "entry_return_cushion": "0.15",
            "expected_total_return": "0.20",
            "expected_annualized_return": "0.15",
            "fundamental_target_pass": True,
            "required_return_pass": True,
            "required_return": None,
            "target_entry_price": "26.60",
            "margin_of_safety": "0.1941",
        },
        "risk": {"max_loss_pct": "25"},
        "risk_portfolio_contract": {
            "portfolio": {
                "position_pct": "0",
                "can_add": True,
                "buy_add_package": {
                    "entry_zone": ["24.00", "25.95"],
                    "initial_position_pct": "5",
                    "target_position_pct": "10",
                    "max_position_pct": "10",
                }
            }
        },
        "thesis": {"falsifiers": ["TEST_FALSIFIER"]},
        "monitoring": [{"metric": "quality", "condition": "recheck quarterly"}],
    }
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case_id,
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "as_of_date": cutoff,
            "cutoff_date": cutoff,
        },
        "decision": decision,
    }
    core["snapshot_hash"] = sha256_obj({
        "snapshot_schema": core["snapshot_schema"],
        "engine_version": core["engine_version"],
        "input": core["input"],
        "decision": core["decision"],
    })
    return core


def make_publication(tmp_path):
    snapshot = make_snapshot()
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(
        tmp_path, "CN-A", "300750", "CATL", "2026-10-06T00:00:00+00:00"
    )
    decision_id = "CN-A-300750-r001"
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"])
    prepare_authorized_test_run(root=str(tmp_path), run_id="run-c2-001", snapshot=snapshot, decision_admission=admission)
    write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        "run-c2-001",
        decision_admission=admission,
    )
    from iios_mvp.machine_publication import write_machine_publication
    publication_path = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T01:00:00+00:00",
    )
    return json.loads(publication_path.read_text(encoding="utf-8")), publication_path


def test_investor_report_is_chinese_detailed_and_schema_valid(tmp_path):
    publication, _ = make_publication(tmp_path)
    report = build_investor_review_report(
        publication=publication,
        generated_at="2026-10-06T02:00:00+00:00",
    )
    validate_investor_review_report(report)
    qa = qa_investor_review_report(publication=publication, report=report)
    validate_investor_review_qa(qa)
    schema = json.loads(
        Path("schemas/investor_review_report_v0.1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(report)
    assert report["report_version"] == INVESTOR_REPORT_VERSION
    assert report["language"] == "zh-CN"
    assert qa["qa_version"] == INVESTOR_QA_VERSION
    assert qa["qa_status"] == "PASS"
    assert "## 一页结论" in report["markdown"]
    assert "## 人工判断边界" in report["markdown"]
    assert "不能被理解为“到价即可买入”" in report["markdown"]
    assert "当前动作：REVIEW_REQUIRED" in report["markdown"]


def test_investor_report_replay_is_deterministic(tmp_path):
    publication, _ = make_publication(tmp_path)
    a = build_investor_review_report(publication=publication, generated_at="2026-10-06T02:00:00+00:00")
    b = build_investor_review_report(publication=publication, generated_at="2026-10-06T02:00:00+00:00")
    assert a == b


def test_investor_report_fails_closed_on_binding_drift(tmp_path):
    publication, _ = make_publication(tmp_path)
    report = build_investor_review_report(publication=publication, generated_at="2026-10-06T02:00:00+00:00")
    other, _ = make_publication(tmp_path / "other")
    qa = qa_investor_review_report(publication=other, report=report)
    assert qa["qa_status"] == "FAIL"
    assert qa["checks"]["publication_binding"] == "FAIL"


def test_write_investor_report_is_immutable(tmp_path):
    publication, pub_path = make_publication(tmp_path)
    rp, qp = write_investor_review_report(tmp_path, publication_path=pub_path, generated_at="2026-10-06T02:00:00+00:00")
    md = tmp_path / rp.name.replace(".investor-review.json", ".investor-review.md")
    original = (rp.read_bytes(), md.read_bytes(), qp.read_bytes())
    rp2, qp2 = write_investor_review_report(tmp_path, publication_path=pub_path, generated_at="2026-10-06T02:00:00+00:00")
    assert rp2 == rp and qp2 == qp
    assert (rp.read_bytes(), md.read_bytes(), qp.read_bytes()) == original


def test_cli_investor_report(tmp_path, capsys):
    publication, pub_path = make_publication(tmp_path)
    args = Namespace(out=str(tmp_path), publication=str(pub_path), generated_at="2026-10-06T02:00:00+00:00")
    from iios_mvp import cli
    assert cli.cmd_investor_report(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "INVESTOR_REVIEW_REPORT_PUBLISHED"
    assert result["qa_status"] == "PASS"
    assert Path(result["markdown"]).exists()
