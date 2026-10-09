"""Batch-0 characterization probes.

A PASS from this module means the previously reported bypass can still be
reproduced on the examined baseline. It is NOT product compliance PASS.
Replace these characterization assertions with fail-closed assertions in
Batch 1/2 after the enforcement path exists.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "iios_mvp" / "cli.py"
ENGINE_PATH = ROOT / "iios_mvp" / "engine.py"


def _legacy_unadmitted_case() -> dict:
    """Intentionally synthetic diagnostic input; never an investment case."""
    return {
        "case_id": "INCIDENT-PROBE-CN-A-605016-20261009",
        "market": "CN-A",
        "symbol": "605016.SH",
        "company": "百龙创园（synthetic bypass probe only）",
        "as_of_date": "2026-10-09",
        "cutoff_date": "2026-10-09",
        "thesis": {
            "status": "HEALTHY",
            "summary": "SYNTHETIC_TEST_ONLY_NOT_AN_INVESTMENT_THESIS",
        },
        "trust": {"status": "PASS", "notes": "SYNTHETIC_TEST_ONLY"},
        # Deliberately no raw-byte artifact, SHA-256, B2 admission receipt,
        # source-origin verification, or admitted provenance class.
        "evidence": [
            {
                "source": "UNVERIFIED_TEST_SOURCE",
                "known_at": "2026-08-20",
                "claim": "SYNTHETIC_UNVERIFIED_CLAIM",
            }
        ],
        "reality": {
            "periods": [
                {
                    "period": "2026Q2",
                    "value": 1,
                    "known_at": "2026-08-20",
                    "source": "UNVERIFIED_TEST_SOURCE",
                }
            ]
        },
        # Values are chosen only to make the legacy calculation executable.
        "forecast": {
            "origin": "2026-10-09",
            "method": "SYNTHETIC_TEST_ONLY",
            "prepared_using_current_price": False,
            "assumptions": ["SYNTHETIC_TEST_ONLY"],
            "bear": {"net_profit": 650000000},
            "base": {"net_profit": 750000000},
            "bull": {"net_profit": 950000000},
        },
        "valuation": {
            "model": "forward_pe",
            "model_selection": {
                "selection_method": "HUMAN",
                "economic_profile": "mature_cash_earning_business",
                "primary_model": "forward_pe",
                "rationale": "SYNTHETIC_TEST_ONLY",
            },
            "currency": "CNY",
            "current_price": 20.28,
            "shares_outstanding": 420000000,
            "required_return_pct": 15,
            "bear_multiple": 15,
            "base_multiple": 18,
            "bull_multiple": 22,
            "market_implied_multiple": 18,
        },
        "risk": {"max_loss_pct": 30, "thesis_breaks": ["SYNTHETIC_TEST_ONLY"]},
        "portfolio": {
            "position_pct": 0,
            "can_add": True,
            "buy_add_package": {
                "entry_zone": "SYNTHETIC_TEST_ONLY",
                "initial_position_pct": 1,
                "target_position_pct": 5,
                "max_position_pct": 10,
            },
        },
        "monitoring": [{"metric": "SYNTHETIC_TEST_ONLY", "condition": "SYNTHETIC_TEST_ONLY"}],
    }


def _function_ast(path: Path, name: str) -> ast.FunctionDef:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function not found: {path}:{name}")


def _called_names(node: ast.AST) -> set[str]:
    result: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = child.func
            if isinstance(fn, ast.Name):
                result.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                result.add(fn.attr)
    return result


def test_probe_p0_ce_01_cli_decision_entry_has_no_run_envelope_authorization():
    """Reproduce request-to-decision path that bypasses the orchestrator."""
    cli_source = CLI_PATH.read_text(encoding="utf-8")
    assert "canonical_research_orchestrator" not in cli_source
    cmd_run = _function_ast(CLI_PATH, "cmd_run")
    calls = _called_names(cmd_run)
    assert "run_case" in calls, "baseline bypass no longer reproduced; replace probe with an enforcement assertion"
    assert "authorize" not in calls
    assert "build_run_receipt" not in calls


def test_probe_p0_ce_02_unadmitted_evidence_can_pass_legacy_validation():
    """A source label + date + claim is not raw-byte/B2 PIT admission."""
    from iios_mvp.engine import run_case

    case = _legacy_unadmitted_case()
    snapshot, _ = run_case(case)
    assert snapshot["decision"]["validation"]["status"] == "PASS"
    assert snapshot["input"]["evidence"][0]["source"] == "UNVERIFIED_TEST_SOURCE"
    assert not any(
        key in snapshot["input"]["evidence"][0]
        for key in ("artifact_id", "content_sha256", "provenance_class", "admission_status")
    )
    assert snapshot["snapshot_schema"] == "IIOS-MVP-SNAPSHOT-0.1.1"


def test_probe_p0_ce_03_missing_semantic_artifact_does_not_stop_lower_level_engine():
    """Legacy decision construction does not require an admitted semantic artifact."""
    from iios_mvp.engine import run_case

    case = _legacy_unadmitted_case()
    assert "semantic_artifact" not in case
    assert "semantic_admission" not in case
    snapshot, _ = run_case(case)
    assert isinstance(snapshot["decision"].get("decision"), dict)
    assert snapshot["decision"]["decision"].get("action")


def test_probe_p0_ce_04_direct_lower_level_engine_invocation_emits_decision_without_envelope():
    """Direct run_case remains callable and can emit a decision snapshot."""
    from iios_mvp.engine import run_case

    case = _legacy_unadmitted_case()
    snapshot, digest = run_case(case)
    assert len(digest) == 64
    assert snapshot["snapshot_hash"] == digest
    assert "run_envelope" not in snapshot
    assert "run_receipt" not in snapshot
    assert snapshot["decision"]["decision"].get("action")


def test_probe_p0_ce_05_direct_revision_publication_and_report_without_run_envelope(tmp_path):
    """A caller-supplied run_id plus Decision Admission can publish without Run Receipt."""
    from iios_mvp.engine import sha256_obj
    from iios_mvp.investor_review_report_v02 import write_investor_review_report_v02
    from iios_mvp.machine_publication import write_machine_publication
    from iios_mvp.store import (
        create_or_load_series,
        write_decision_revision,
        write_snapshot,
    )
    from tests.decision_admission_fixture import build_fixture_admission_receipt

    case_id = "INCIDENT-PROBE-CN-A-605016-20261009"
    company = "百龙创园（synthetic bypass probe only）"
    # A deliberately minimal snapshot: no Research Case admission, Evidence/PIT
    # admission, semantic artifact, or Run Envelope/receipt.
    decision = {
        "engine_version": "0.3.0",
        "case_id": case_id,
        "symbol": "605016.SH",
        "company": company,
        "cutoff_date": "2026-10-09",
        "action": "REVIEW_REQUIRED",
        "decision_status": "REVIEW_REQUIRED",
        "investability_status": "REVIEW_REQUIRED",
        "primary_reason": "SYNTHETIC_INCIDENT_PROBE_ONLY",
        "human_approval_required": True,
        "auto_execution": False,
        "gates": {"trust": "UNKNOWN", "new_capital_allowed": False},
        "return_metrics": {"expected_annualized_return": None},
        "monitoring": [],
    }
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case_id,
            "market": "CN-A",
            "symbol": "605016.SH",
            "company": company,
            "as_of_date": "2026-10-09",
            "cutoff_date": "2026-10-09",
        },
        "decision": decision,
    }
    snapshot = {
        **core,
        "snapshot_hash": sha256_obj(core),
    }

    series = create_or_load_series(
        tmp_path, "CN-A", "605016.SH", company, "2026-10-09T23:59:00+08:00"
    )
    write_snapshot(tmp_path, snapshot)
    decision_admission = build_fixture_admission_receipt(
        snapshot=snapshot, canonical_decision=decision
    )
    decision_id = f"{series['decision_series_id']}-r001"
    # The run_id below is an arbitrary caller string, not a Run Envelope ID.
    write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        run_id="CALLER_SUPPLIED_NOT_AN_ORCHESTRATOR_RUN",
        decision_admission=decision_admission,
    )
    publication_path = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-09T23:59:10+08:00",
    )
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    assert publication_path.is_file()
    assert publication["decision_ref"]["run_id"] == "CALLER_SUPPLIED_NOT_AN_ORCHESTRATOR_RUN"
    assert "run_receipt_hash" not in publication
    assert "orchestrator_run_id" not in publication

    report_path, machine_path, markdown_path, qa_path = write_investor_review_report_v02(
        tmp_path,
        publication_path=publication_path,
        generated_at="2026-10-09T23:59:30+08:00",
    )
    assert report_path.is_file()
    assert machine_path.is_file()
    assert markdown_path.is_file()
    assert qa_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    # Creation of artifacts is reproduced. Report QA/readiness is separate and
    # cannot compensate for the missing canonical run authorization.
    assert report.get("publication_hash") == publication["publication_hash"]


def test_probe_p0_ce_05b_legacy_cli_publish_is_blocked_for_a_different_guard(tmp_path, capsys):
    """Record existing Decision Admission protection without overclaiming run enforcement."""
    from iios_mvp.cli import parser

    case_path = tmp_path / "synthetic_legacy_case.json"
    output_root = tmp_path / "runs"
    case_path.write_text(
        json.dumps(_legacy_unadmitted_case(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    run_args = parser().parse_args(["run", str(case_path), "--out", str(output_root)])
    run_args.func(run_args)
    run_output = json.loads(capsys.readouterr().out)
    decision_id = run_output["decision_id"]

    publish_args = parser().parse_args([
        "publish",
        decision_id,
        "--published-at",
        "2026-10-09T23:59:00+08:00",
        "--out",
        str(output_root),
    ])
    with pytest.raises(ValueError, match="canonical v0.3 Decision Revision requires decision_admission"):
        publish_args.func(publish_args)
