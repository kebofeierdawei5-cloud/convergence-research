import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.human_report import (
    QA_VERSION,
    REPORT_VERSION,
    build_human_report,
    qa_human_report,
    validate_human_report,
    validate_report_qa,
    write_human_report,
)
from iios_mvp.machine_publication import build_machine_publication
from iios_mvp.store import (
    create_or_load_series,
    write_decision_revision,
    write_snapshot,
)
from iios_mvp.engine import sha256_obj


def make_snapshot(action="REVIEW_REQUIRED"):
    case_id = "C2-001"
    cutoff = "2026-10-06"
    decision = {
        "engine_version": "0.3.0",
        "case_id": case_id,
        "symbol": "300750",
        "company": "CATL",
        "cutoff_date": cutoff,
        "action": action,
        "decision_status": "REVIEW_REQUIRED",
        "investability_status": "REVIEW_REQUIRED",
        "primary_reason": "TEST_REASON",
        "human_approval_required": True,
        "auto_execution": False,
        "gates": {
            "trust": "PASS",
            "evidence_pit": True,
            "forecast_ready": True,
            "valuation_ready": True,
            "new_buy_add_allowed": False,
        },
        "return_metrics": {
            "entry_return_cushion": "0.15",
            "expected_total_return": "0.20",
            "expected_annualized_return": "0.15",
            "fundamental_target_pass": True,
            "required_return_pass": True,
            "required_return": "0.10",
        },
        "risk": {"max_loss_pct": "0.25"},
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


def persist_revision(tmp_path, action="REVIEW_REQUIRED"):
    series = create_or_load_series(
        tmp_path, "CN-A", "300750", "CATL", "2026-10-06T00:00:00+00:00"
    )
    snapshot = make_snapshot(action)
    write_snapshot(tmp_path, snapshot)
    decision_id = "CN-A-300750-r001"
    write_decision_revision(tmp_path, series["decision_series_id"], 1, snapshot, "run-c2-001")
    decision_path = tmp_path / f"{decision_id}.decision.json"
    return snapshot, decision_id, decision_path


def make_publication(tmp_path, action="REVIEW_REQUIRED"):
    snapshot, decision_id, _ = persist_revision(tmp_path, action)
    from iios_mvp.machine_publication import write_machine_publication
    publication_path = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T01:00:00+00:00",
    )
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    return publication, publication_path


def test_report_is_readable_bound_and_schema_valid(tmp_path):
    publication, _ = make_publication(tmp_path)
    report = build_human_report(
        publication=publication,
        generated_at="2026-10-06T02:00:00+00:00",
    )
    validate_human_report(report)
    qa = qa_human_report(publication=publication, report=report)
    validate_report_qa(qa)

    report_schema = json.loads(
        Path("schemas/human_report_v0.1.schema.json").read_text(encoding="utf-8")
    )
    qa_schema = json.loads(
        Path("schemas/report_qa_v0.1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(report_schema).validate(report)
    Draft202012Validator(qa_schema).validate(qa)

    assert report["report_version"] == REPORT_VERSION
    assert qa["qa_version"] == QA_VERSION
    assert qa["qa_status"] == "PASS"
    assert report["publication_hash"] == publication["publication_hash"]
    assert "## Executive Decision" in report["markdown"]
    assert "- Action: REVIEW_REQUIRED" in report["markdown"]
    assert "does not independently recalculate company economics" in report["markdown"]


def test_report_generation_is_deterministic_for_same_publication_and_timestamp(tmp_path):
    publication, _ = make_publication(tmp_path)
    a = build_human_report(
        publication=publication, generated_at="2026-10-06T02:00:00+00:00"
    )
    b = build_human_report(
        publication=publication, generated_at="2026-10-06T02:00:00+00:00"
    )
    assert a == b


def test_report_qa_fails_closed_on_decision_drift(tmp_path):
    publication, _ = make_publication(tmp_path)
    report = build_human_report(
        publication=publication, generated_at="2026-10-06T02:00:00+00:00"
    )
    tampered = dict(report)
    tampered["markdown"] = tampered["markdown"].replace(
        "Action: REVIEW_REQUIRED", "Action: BUY"
    )
    with pytest.raises(ValueError, match="human_report hash mismatch"):
        validate_human_report(tampered)

    qa = qa_human_report(publication=publication, report=report)
    tampered_qa_input = dict(report)
    tampered_qa_input["markdown"] = tampered_qa_input["markdown"].replace(
        "Action: REVIEW_REQUIRED", "Action: BUY"
    )
    tampered_qa = qa_human_report(publication=publication, report=tampered_qa_input)
    assert tampered_qa["qa_status"] == "FAIL"
    assert "report_integrity" in " ".join(tampered_qa["issues"])


def test_report_qa_fails_closed_on_publication_binding_mismatch(tmp_path):
    publication, _ = make_publication(tmp_path)
    report = build_human_report(
        publication=publication, generated_at="2026-10-06T02:00:00+00:00"
    )
    second, _ = make_publication(tmp_path / "second")
    qa = qa_human_report(publication=second, report=report)
    assert qa["qa_status"] == "FAIL"
    assert qa["checks"]["publication_binding"] == "FAIL"


def test_write_report_creates_immutable_json_markdown_and_qa(tmp_path):
    publication, publication_path = make_publication(tmp_path)
    report_path, qa_path = write_human_report(
        tmp_path,
        publication_path=publication_path,
        generated_at="2026-10-06T02:00:00+00:00",
    )
    markdown_path = tmp_path / report_path.name.replace(
        ".report.json", ".report.md"
    )
    assert report_path.exists()
    assert markdown_path.exists()
    assert qa_path.exists()

    original_json = report_path.read_bytes()
    original_md = markdown_path.read_bytes()
    original_qa = qa_path.read_bytes()

    report_path2, qa_path2 = write_human_report(
        tmp_path,
        publication_path=publication_path,
        generated_at="2026-10-06T02:00:00+00:00",
    )
    assert report_path2 == report_path
    assert qa_path2 == qa_path
    assert report_path.read_bytes() == original_json
    assert markdown_path.read_bytes() == original_md
    assert qa_path.read_bytes() == original_qa


def test_report_generation_does_not_mutate_publication(tmp_path):
    publication, publication_path = make_publication(tmp_path)
    before = publication_path.read_bytes()
    build_human_report(
        publication=publication, generated_at="2026-10-06T02:00:00+00:00"
    )
    assert publication_path.read_bytes() == before
