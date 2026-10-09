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


def test_probe_p0_ce_05_direct_publication_and_report_path_does_not_require_run_receipt(tmp_path, capsys):
    """Reproduce lower-level CLI run -> publish -> report without a Run Receipt."""
    from iios_mvp.cli import parser

    case_path = tmp_path / "synthetic_case.json"
    output_root = tmp_path / "runs"
    case_path.write_text(
        json.dumps(_legacy_unadmitted_case(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Invoke the same CLI command handlers as the product command path.
    run_args = parser().parse_args(["run", str(case_path), "--out", str(output_root)])
    run_args.func(run_args)
    run_output = json.loads(capsys.readouterr().out)
    decision_id = run_output["decision_id"]
    assert (output_root / f"{decision_id}.decision.json").is_file()

    publish_args = parser().parse_args([
        "publish",
        decision_id,
        "--published-at",
        "2026-10-09T23:59:00+08:00",
        "--out",
        str(output_root),
    ])
    publish_args.func(publish_args)
    publish_output = json.loads(capsys.readouterr().out)
    publication_path = Path(publish_output["publication"])
    assert publication_path.is_file()
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    assert publication["human_approval"]["approval_status"] == "PENDING"
    assert "run_receipt_hash" not in publication
    assert "orchestrator_run_id" not in publication

    report_args = parser().parse_args([
        "investor-report-v02",
        str(publication_path),
        "--generated-at",
        "2026-10-09T23:59:30+08:00",
        "--out",
        str(output_root),
    ])
    report_args.func(report_args)
    report_output = json.loads(capsys.readouterr().out)
    assert report_output["status"] == "INVESTOR_REVIEW_REPORT_V02_PUBLISHED"
    assert Path(report_output["markdown"]).is_file()
    # This reproduces report artifact creation. Its own QA/readiness is a
    # separate status and must not be confused with canonical-run admission.
