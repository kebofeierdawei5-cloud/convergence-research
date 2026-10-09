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


def test_p0_ce_01_v03_cli_requires_authorization_before_any_persistent_write():
    """The canonical CLI must validate the orchestrator receipt before writing."""
    cli_source = CLI_PATH.read_text(encoding="utf-8")
    assert "canonical_run_authorization" in cli_source
    cmd_run = _function_ast(CLI_PATH, "cmd_run")
    names = [
        child.func.id if isinstance(child.func, ast.Name) else child.func.attr
        for child in ast.walk(cmd_run)
        if isinstance(child, ast.Call)
    ]
    assert "verify_snapshot_write_authorization" in names
    assert "write_snapshot" in names
    assert "write_decision_revision" in names
    # Python AST walk order is not execution order; inspect source positions.
    body = ast.get_source_segment(cli_source, cmd_run)
    assert body.index("verify_snapshot_write_authorization(") < body.index("write_snapshot(")
    assert body.index("verify_snapshot_write_authorization(") < body.index("write_decision_revision(")
    assert 'CANONICAL_RUN_AUTHORIZATION_BLOCKED' in body


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


def test_p0_ce_05_direct_revision_write_fails_without_persisted_run_authorization(tmp_path):
    """A valid-looking Decision Admission is not a canonical orchestrator receipt."""
    from iios_mvp.engine import sha256_obj
    from iios_mvp.store import create_or_load_series, write_decision_revision, write_snapshot
    from tests.decision_admission_fixture import build_fixture_admission_receipt

    case_id = "INCIDENT-PROBE-CN-A-605016-20261009"
    company = "百龙创园（synthetic bypass probe only）"
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
    snapshot = {**core, "snapshot_hash": sha256_obj(core)}
    series = create_or_load_series(
        tmp_path, "CN-A", "605016.SH", company, "2026-10-09T23:59:00+08:00"
    )
    write_snapshot(tmp_path, snapshot)
    decision_admission = build_fixture_admission_receipt(
        snapshot=snapshot, canonical_decision=decision
    )

    with pytest.raises(ValueError, match="CANONICAL_RUN_AUTHORIZATION_BLOCKED"):
        write_decision_revision(
            tmp_path,
            series["decision_series_id"],
            1,
            snapshot,
            run_id="CALLER_SUPPLIED_NOT_AN_ORCHESTRATOR_RUN",
            decision_admission=decision_admission,
        )
    assert not (tmp_path / f'{series["decision_series_id"]}-r001.decision.json').exists()
    assert not list(tmp_path.glob("*.publication.json"))
    assert not list(tmp_path.glob("*.investor-review-v02.json"))


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


def test_p0_positive_canonical_run_authorization_allows_exact_revision(tmp_path):
    """The new gate must admit a fully bound orchestrator receipt, not block everything."""
    from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
    from iios_mvp.canonical_run_authorization import canonical_hash, write_run_authorization
    from iios_mvp.engine import sha256_obj
    from iios_mvp.store import create_or_load_series, write_decision_revision, write_snapshot
    from tests.decision_admission_fixture import build_fixture_admission_receipt

    case_id = "P0-POSITIVE-CN-A-605016-20261009"
    company = "百龙创园（synthetic authorization test only）"
    input_data = {
        "case_id": case_id,
        "market": "CN-A",
        "symbol": "605016.SH",
        "company": company,
        "as_of_date": "2026-10-09",
        "cutoff_date": "2026-10-09",
    }
    decision = {
        "engine_version": "0.3.0",
        "case_id": case_id,
        "symbol": "605016.SH",
        "company": company,
        "cutoff_date": "2026-10-09",
        "action": "REVIEW_REQUIRED",
        "decision_status": "REVIEW_REQUIRED",
        "investability_status": "REVIEW_REQUIRED",
        "primary_reason": "SYNTHETIC_AUTHORIZATION_TEST_ONLY",
        "human_approval_required": True,
        "auto_execution": False,
        "gates": {"trust": "UNKNOWN", "new_capital_allowed": False},
        "return_metrics": {"expected_annualized_return": None},
        "monitoring": [],
    }
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": input_data,
        "decision": decision,
    }
    snapshot = {**core, "snapshot_hash": sha256_obj(core)}
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=decision)

    run_id = "P0-POSITIVE-AUTH-TEST-RUN"
    orchestrator = CanonicalResearchOrchestrator()
    orchestrator.start(
        run_id=run_id,
        case_id=case_id,
        market="CN-A",
        symbol="605016.SH",
        cutoff_date="2026-10-09",
        as_of_date="2026-10-09",
        research_case_hash=canonical_hash(input_data),
        created_at="2026-10-09T15:00:00+00:00",
    )
    stages = [
        (Stage.REQUEST_ADMITTED, "CODE"),
        (Stage.CASE_CREATED, "CODE"),
        (Stage.EVIDENCE_PENDING, "CODE"),
        (Stage.EVIDENCE_ADMITTED, "B2_EVIDENCE_PIT_VALIDATOR"),
        (Stage.SEMANTIC_PENDING, "CODE"),
        (Stage.SEMANTIC_ADMITTED, "LLM_SEMANTIC_PRODUCER"),
        (Stage.FORECAST_PENDING, "CODE"),
        (Stage.FORECAST_ADMITTED, "INDEPENDENT_FORECAST_ADMISSION"),
        (Stage.VALUATION_PENDING, "CODE"),
        (Stage.VALUATION_ADMITTED, "VALUATION_ADMISSION"),
        (Stage.DECISION_PENDING, "CODE"),
        (Stage.DECISION_ADMITTED, "DECISION_ADMISSION_VALIDATOR"),
    ]
    previous_hash = None
    for index, (stage, producer) in enumerate(stages, start=1):
        if stage == Stage.CASE_CREATED:
            output_hash = canonical_hash(input_data)
        elif stage == Stage.DECISION_ADMITTED:
            output_hash = canonical_hash(admission)
        else:
            output_hash = canonical_hash({"test_stage": stage.value, "ordinal": index})
        input_hashes = () if previous_hash is None else (previous_hash,)
        orchestrator.transition(
            run_id,
            stage,
            input_refs=() if previous_hash is None else (f"stage-output:{index-1}",),
            input_hashes=input_hashes,
            output_refs=(f"stage-output:{index}",),
            output_hashes=(output_hash,),
            producer_type=producer,
            producer_version=f"test-producer-{index}",
            status="PASS",
            created_at="2026-10-09T15:00:00+00:00",
        )
        previous_hash = output_hash

    write_run_authorization(
        tmp_path,
        envelope=orchestrator.get(run_id),
        snapshot=snapshot,
        decision_admission=admission,
        issued_at="2026-10-09T15:01:00+00:00",
    )
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(
        tmp_path, "CN-A", "605016.SH", company, "2026-10-09T15:02:00+00:00"
    )
    decision_path = write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        run_id=run_id,
        decision_admission=admission,
    )
    assert decision_path.is_file()
