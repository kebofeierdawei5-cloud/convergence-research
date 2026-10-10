"""P0 fail-closed regression tests replacing Batch-0 characterization probes.

These tests assert that bypasses return NON_CANONICAL/BLOCKED and cannot write
formal artifacts. The positive path uses synthetic fixtures only to verify the
run authorization mechanics; it is not evidence of real-company admission or
economic reasoning validity.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from iios_mvp.cli import parser
from iios_mvp.engine import run_case, sha256_obj
from iios_mvp.machine_publication import write_machine_publication
from iios_mvp.store import create_or_load_series, write_decision_revision, write_snapshot
from iios_mvp.investor_review_report_v02 import write_investor_review_report_v02
from iios_mvp.canonical_run_authority_v01 import CanonicalRunAuthorizationError, run_state_path
from iios_mvp.canonical_research_orchestrator import Stage
from tests.decision_admission_fixture import (
    build_fixture_admission_receipt,
    prepare_authorized_test_run,
)


def _legacy_unadmitted_case() -> dict:
    """Synthetic only: intentionally no raw-byte or B2 Evidence/PIT admission."""
    return {
        "case_id": "INCIDENT-PROBE-CN-A-605016-20261009",
        "market": "CN-A",
        "symbol": "605016.SH",
        "company": "百龙创园（synthetic bypass probe only）",
        "as_of_date": "2026-10-09",
        "cutoff_date": "2026-10-09",
        "thesis": {"status": "HEALTHY", "summary": "SYNTHETIC_TEST_ONLY"},
        "trust": {"status": "PASS", "notes": "SYNTHETIC_TEST_ONLY"},
        "evidence": [{
            "source": "UNVERIFIED_TEST_SOURCE",
            "known_at": "2026-08-20",
            "claim": "SYNTHETIC_UNVERIFIED_CLAIM",
        }],
        "reality": {"periods": [{
            "period": "2026Q2", "value": 1, "known_at": "2026-08-20",
            "source": "UNVERIFIED_TEST_SOURCE",
        }]},
        "forecast": {
            "origin": "2026-10-09", "method": "SYNTHETIC_TEST_ONLY",
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
            "currency": "CNY", "current_price": 20.28,
            "shares_outstanding": 420000000, "required_return_pct": 15,
            "bear_multiple": 15, "base_multiple": 18, "bull_multiple": 22,
            "market_implied_multiple": 18,
        },
        "risk": {"max_loss_pct": 30, "thesis_breaks": ["SYNTHETIC_TEST_ONLY"]},
        "portfolio": {
            "position_pct": 0, "can_add": True,
            "buy_add_package": {
                "entry_zone": "SYNTHETIC_TEST_ONLY",
                "initial_position_pct": 1, "target_position_pct": 5,
                "max_position_pct": 10,
            },
        },
        "monitoring": [{"metric": "SYNTHETIC_TEST_ONLY", "condition": "SYNTHETIC_TEST_ONLY"}],
    }


def _v03_snapshot() -> dict:
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
        "risk_portfolio_contract": {"status": "UNKNOWN"},
        "monitoring": [],
    }
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case_id, "market": "CN-A", "symbol": "605016.SH",
            "company": company, "as_of_date": "2026-10-09", "cutoff_date": "2026-10-09",
        },
        "decision": decision,
    }
    return {**core, "snapshot_hash": sha256_obj(core)}


def test_p0_ce_01_direct_cli_entry_returns_noncanonical_and_writes_nothing(tmp_path, capsys):
    case_path = tmp_path / "synthetic_case.json"
    output_root = tmp_path / "runs"
    case_path.write_text(json.dumps(_legacy_unadmitted_case(), ensure_ascii=False), encoding="utf-8")
    args = parser().parse_args(["run", str(case_path), "--out", str(output_root)])
    code = args.func(args)
    output = json.loads(capsys.readouterr().out)
    assert code == 2
    assert output["status"] == "NON_CANONICAL"
    assert output["canonical_decision_created"] is False
    assert output["decision_revision_created"] is False
    assert not output_root.exists() or not list(output_root.glob("*.decision.json"))


def test_p0_ce_01b_official_canonical_entry_never_falls_back_when_runtime_missing(tmp_path, capsys):
    bundle = tmp_path / "request.json"
    bundle.write_text(json.dumps({"raw_request": "使用新版本IIOS分析百龙创园605016，截止2026-10-09"}), encoding="utf-8")
    args = parser().parse_args(["canonical-run", str(bundle), "--out", str(tmp_path / "runs")])
    code = args.func(args)
    output = json.loads(capsys.readouterr().out)
    assert code == 2
    assert output["status"] == "BLOCKED"
    assert output["canonical_decision_created"] is False
    assert output["reason"] == "CANONICAL_RUNTIME_NOT_REGISTERED"
    assert not (tmp_path / "runs").exists()


def test_p0_ce_01c_explicit_runtime_factory_is_trusted_host_input(monkeypatch, tmp_path):
    import sys
    import types

    import iios_mvp.cli as cli
    from iios_mvp.canonical_natural_language_entry_v01 import (
        RequestIntent,
        RequestInterpreterRegistration,
        RequestInterpreterRegistry,
    )
    from iios_mvp.canonical_runtime_registry_v01 import CanonicalRuntimeBindings
    from iios_mvp.semantic_producer_admission_v01 import (
        ProducerRegistration,
        ProducerRegistry,
    )

    class TestInterpreter:
        interpreter_id = "test-interpreter"
        interpreter_type = "LLM_REQUEST_INTERPRETER"
        interpreter_version = "test-v1"
        policy_version = "test-policy-v1"

        def interpret(self, raw_request):
            return RequestIntent("CN-A", "605016.SH", "2026-10-09", 0)

    class TestSemanticProducer:
        producer_id = "test-semantic-producer"
        producer_type = "LLM_SEMANTIC_PRODUCER"
        producer_version = "test-v1"
        policy_version = "test-policy-v1"

        def produce(self, request):
            return {"status": "TEST_ONLY"}

    interpreter = TestInterpreter()
    producer = TestSemanticProducer()
    request_registry = RequestInterpreterRegistry((
        RequestInterpreterRegistration(
            interpreter.interpreter_id, interpreter.interpreter_type,
            interpreter.interpreter_version, interpreter.policy_version,
        ),
    ))
    producer_registry = ProducerRegistry((
        ProducerRegistration(
            producer.producer_id, producer.producer_type,
            producer.producer_version, producer.policy_version,
        ),
    ))

    module_name = "iios_mvp_test_runtime_factory"
    module = types.ModuleType(module_name)
    calls = {}
    expected = CanonicalRuntimeBindings(
        request_interpreter=interpreter,
        request_registry=request_registry,
        semantic_producer=producer,
        producer_registry=producer_registry,
        current_price_resolver=types.SimpleNamespace(resolve_current_price=lambda *args, **kwargs: {}),
        independent_forecast_resolver=types.SimpleNamespace(resolve_independent_forecast=lambda *args, **kwargs: {}),
        upstream_authority_resolver=types.SimpleNamespace(resolve=lambda *args, **kwargs: {}),
        valuation_output_resolver=types.SimpleNamespace(resolve_valuation_output=lambda *args, **kwargs: {}),
    )

    def build_runtime(*, bundle, output_root):
        calls["bundle"] = bundle
        calls["output_root"] = output_root
        return expected

    module.build_runtime = build_runtime
    monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setattr(cli, "get_canonical_runtime", lambda: None)

    bundle = {"raw_request": "test request", "runtime_factory": "THIS_MUST_NOT_BE_READ_FROM_REQUEST"}
    runtime = cli._resolve_canonical_runtime(
        factory_spec=f"{module_name}:build_runtime",
        bundle=bundle,
        output_root=str(tmp_path / "runs"),
    )
    assert runtime is expected
    assert calls == {"bundle": bundle, "output_root": str(tmp_path / "runs")}

    with pytest.raises(ValueError, match="trusted module:callable"):
        cli._resolve_canonical_runtime(
            factory_spec="arbitrary code supplied by request bundle",
            bundle=bundle,
            output_root=str(tmp_path / "runs"),
        )

    from dataclasses import replace

    module.build_invalid_runtime = lambda **kwargs: replace(
        expected, current_price_resolver=object()
    )
    with pytest.raises(ValueError, match="current_price_resolver must implement callable resolve_current_price"):
        cli._resolve_canonical_runtime(
            factory_spec=f"{module_name}:build_invalid_runtime",
            bundle=bundle,
            output_root=str(tmp_path / "runs"),
        )


def test_p0_ce_01d_invalid_runtime_factory_blocks_without_artifacts(tmp_path, capsys, monkeypatch):
    import iios_mvp.cli as cli

    monkeypatch.setattr(cli, "get_canonical_runtime", lambda: None)
    bundle = tmp_path / "request.json"
    output_root = tmp_path / "runs"
    bundle.write_text(
        json.dumps({"raw_request": "使用新版本IIOS分析百龙创园605016，截止2026-10-09"}),
        encoding="utf-8",
    )
    args = parser().parse_args([
        "canonical-run", str(bundle), "--out", str(output_root),
        "--runtime-factory", "arbitrary code supplied by request bundle",
    ])
    code = args.func(args)
    output = json.loads(capsys.readouterr().out)
    assert code == 2
    assert output["status"] == "BLOCKED"
    assert output["canonical_decision_created"] is False
    assert output["reason"] == "CANONICAL_RUNTIME_FACTORY_INVALID"
    assert output["error_type"] == "ValueError"
    assert not output_root.exists()


def test_p0_ce_01e_incomplete_pre_registered_runtime_is_blocked_before_artifacts(
    tmp_path, capsys, monkeypatch
):
    import iios_mvp.cli as cli
    from iios_mvp.canonical_runtime_registry_v01 import CanonicalRuntimeBindings

    incomplete = CanonicalRuntimeBindings(
        request_interpreter=object(),
        request_registry=object(),
        semantic_producer=object(),
        producer_registry=object(),
        current_price_resolver=object(),
        independent_forecast_resolver=object(),
        upstream_authority_resolver=object(),
        valuation_output_resolver=None,
    )
    monkeypatch.setattr(cli, "get_canonical_runtime", lambda: incomplete)

    bundle = tmp_path / "request.json"
    output_root = tmp_path / "runs"
    bundle.write_text(
        json.dumps({"raw_request": "使用新版本IIOS分析百龙创园605016，截止2026-10-09"}),
        encoding="utf-8",
    )
    args = parser().parse_args([
        "canonical-run", str(bundle), "--out", str(output_root),
    ])
    code = args.func(args)
    output = json.loads(capsys.readouterr().out)

    assert code == 2
    assert output["status"] == "BLOCKED"
    assert output["canonical_decision_created"] is False
    assert output["reason"] == "CANONICAL_RUNTIME_FACTORY_INVALID"
    assert not output_root.exists()


def test_p0_ce_01f_runtime_registry_rejects_incomplete_bindings(monkeypatch):
    import iios_mvp.canonical_runtime_registry_v01 as registry

    monkeypatch.setattr(registry, "_RUNTIME", None)
    incomplete = registry.CanonicalRuntimeBindings(
        request_interpreter=object(),
        request_registry=object(),
        semantic_producer=object(),
        producer_registry=object(),
        current_price_resolver=object(),
        independent_forecast_resolver=object(),
        upstream_authority_resolver=object(),
        valuation_output_resolver=None,
    )

    with pytest.raises(ValueError, match="runtime has missing bindings"):
        registry.register_canonical_runtime(incomplete)
    assert registry.get_canonical_runtime() is None


def test_p0_ce_02_unadmitted_evidence_cannot_become_canonical_decision():
    snapshot, _digest = run_case(_legacy_unadmitted_case())
    assert snapshot["execution_classification"]["status"] == "NON_CANONICAL"
    assert snapshot["execution_classification"]["classification_hash"]
    assert snapshot["snapshot_schema"] == "IIOS-MVP-SNAPSHOT-0.1.1"


def test_p0_ce_03_missing_semantic_artifact_cannot_be_promoted():
    case = _legacy_unadmitted_case()
    assert "semantic_artifact" not in case and "semantic_admission" not in case
    snapshot, _digest = run_case(case)
    assert snapshot["execution_classification"]["status"] == "NON_CANONICAL"


def test_p0_ce_04_direct_engine_call_is_diagnostic_only():
    snapshot, digest = run_case(_legacy_unadmitted_case())
    assert len(digest) == 64
    assert snapshot["snapshot_hash"] == digest
    assert snapshot["execution_classification"]["status"] == "NON_CANONICAL"
    assert "run_envelope" not in snapshot
    assert "run_receipt" not in snapshot


def test_p0_ce_05_decision_revision_write_without_persisted_run_is_blocked(tmp_path):
    snapshot = _v03_snapshot()
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(
        tmp_path, "CN-A", "605016.SH", snapshot["input"]["company"],
        "2026-10-09T23:59:00+08:00",
    )
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"])
    with pytest.raises(CanonicalRunAuthorizationError, match="Run Envelope/Receipt is absent"):
        write_decision_revision(
            tmp_path, series["decision_series_id"], 1, snapshot,
            "CALLER_SUPPLIED_NOT_AN_ORCHESTRATOR_RUN",
            decision_admission=admission,
        )
    assert not (tmp_path / f"{series['decision_series_id']}-r001.decision.json").exists()


def test_p0_ce_05b_publication_and_report_without_canonical_revision_are_blocked(tmp_path):
    with pytest.raises(ValueError, match="decision revision not found"):
        write_machine_publication(
            tmp_path, decision_id="CN-A-605016.SH-r001",
            published_at="2026-10-09T23:59:00+08:00",
        )
    fake_publication_path = tmp_path / "untrusted-publication.json"
    fake_publication_path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        write_investor_review_report_v02(
            tmp_path, publication_path=fake_publication_path,
            generated_at="2026-10-09T23:59:30+08:00",
        )
    assert not list(tmp_path.glob("*.investor-review-v02.json"))


def test_p0_ce_06_positive_synthetic_run_binds_revision_publication_report_and_receipt(tmp_path):
    snapshot = _v03_snapshot()
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(
        tmp_path, "CN-A", "605016.SH", snapshot["input"]["company"],
        "2026-10-09T23:59:00+08:00",
    )
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"])
    run_id = "synthetic-authorized-605016-run"
    prepare_authorized_test_run(
        root=str(tmp_path), run_id=run_id,
        snapshot=snapshot, decision_admission=admission,
    )
    revision_path = write_decision_revision(
        tmp_path, series["decision_series_id"], 1, snapshot, run_id,
        decision_admission=admission,
    )
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    assert revision["run_authority_ref"]["run_id"] == run_id
    assert revision["run_authority_ref"]["stage"] == Stage.DECISION_ADMITTED.value

    publication_path = write_machine_publication(
        tmp_path, decision_id=revision["decision_id"],
        published_at="2026-10-09T23:59:10+08:00",
    )
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    assert publication["canonical_run_ref"]["stage"] == Stage.HUMAN_APPROVAL_PENDING.value
    assert publication["decision_ref"]["revision_hash"] == revision["revision_hash"]

    report_path, machine_path, markdown_path, qa_path = write_investor_review_report_v02(
        tmp_path, publication_path=publication_path,
        generated_at="2026-10-09T23:59:30+08:00",
    )
    assert all(x.is_file() for x in (report_path, machine_path, markdown_path, qa_path))
    run_receipt_path = tmp_path / f"{run_id}.run-receipt.json"
    assert run_receipt_path.is_file()
    run_receipt = json.loads(run_receipt_path.read_text(encoding="utf-8"))
    assert run_receipt["run_id"] == run_id
    assert run_receipt["run_status"] == "COMPLETE"
    assert len(run_receipt["receipt_hash"]) == 64



def test_p0_ce_07_formal_writers_block_when_upstream_admission_bytes_are_missing(tmp_path):
    """Existing, hash-shaped stage receipts cannot substitute for missing upstream bytes."""

    def seed(root: Path, run_id: str):
        snapshot = _v03_snapshot()
        write_snapshot(root, snapshot)
        series = create_or_load_series(
            root, "CN-A", "605016.SH", snapshot["input"]["company"],
            "2026-10-09T23:59:00+08:00",
        )
        admission = build_fixture_admission_receipt(
            snapshot=snapshot, canonical_decision=snapshot["decision"]
        )
        prepare_authorized_test_run(
            root=str(root), run_id=run_id,
            snapshot=snapshot, decision_admission=admission,
        )
        return snapshot, series, admission

    # Decision Revision: deleting the exact admitted semantic bytes blocks
    # before a formal decision file/index or the next stage can be written.
    decision_root = tmp_path / "decision-gate"
    decision_root.mkdir()
    snapshot, series, admission = seed(decision_root, "synthetic-missing-semantic-run")
    semantic_files = list((decision_root / "canonical-artifacts").glob("*.semantic-artifact.json"))
    assert len(semantic_files) == 1
    semantic_files[0].unlink()
    state_before = run_state_path(decision_root, "synthetic-missing-semantic-run").read_bytes()
    with pytest.raises(CanonicalRunAuthorizationError, match="BLOCKED: admitted semantic-artifact artifact is absent"):
        write_decision_revision(
            decision_root, series["decision_series_id"], 1, snapshot,
            "synthetic-missing-semantic-run", decision_admission=admission,
        )
    assert not list(decision_root.glob("*.decision.json"))
    assert run_state_path(decision_root, "synthetic-missing-semantic-run").read_bytes() == state_before
    assert not list(decision_root.glob("*.publication.json"))
    assert not list(decision_root.glob("*.investor-review-v02.json"))

    # Publication: a valid revision does not keep publication authority after an
    # upstream valuation payload disappears.
    publication_root = tmp_path / "publication-gate"
    publication_root.mkdir()
    snapshot, series, admission = seed(publication_root, "synthetic-missing-valuation-run")
    revision_path = write_decision_revision(
        publication_root, series["decision_series_id"], 1, snapshot,
        "synthetic-missing-valuation-run", decision_admission=admission,
    )
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    valuation_files = list((publication_root / "canonical-artifacts").glob("*.valuation-output.json"))
    assert len(valuation_files) == 1
    valuation_files[0].unlink()
    from iios_mvp.canonical_run_authority_v01 import run_state_path as _run_state_path
    state_before = _run_state_path(publication_root, "synthetic-missing-valuation-run").read_bytes()
    with pytest.raises(CanonicalRunAuthorizationError, match="BLOCKED: admitted valuation-output artifact is absent"):
        write_machine_publication(
            publication_root, decision_id=revision["decision_id"],
            published_at="2026-10-09T23:59:10+08:00",
        )
    assert not list(publication_root.glob("*.publication.json"))
    assert _run_state_path(publication_root, "synthetic-missing-valuation-run").read_bytes() == state_before

    # Report: a prior publication cannot authorize a report if forecast admission
    # bytes have disappeared; no report/QA/markdown artifact or completion receipt
    # may be emitted on that blocked path.
    report_root = tmp_path / "report-gate"
    report_root.mkdir()
    snapshot, series, admission = seed(report_root, "synthetic-missing-forecast-run")
    revision_path = write_decision_revision(
        report_root, series["decision_series_id"], 1, snapshot,
        "synthetic-missing-forecast-run", decision_admission=admission,
    )
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    publication_path = write_machine_publication(
        report_root, decision_id=revision["decision_id"],
        published_at="2026-10-09T23:59:10+08:00",
    )
    forecast_files = list((report_root / "canonical-artifacts").glob("*.forecast-admission.json"))
    assert len(forecast_files) == 1
    forecast_files[0].unlink()
    state_before = _run_state_path(report_root, "synthetic-missing-forecast-run").read_bytes()
    with pytest.raises(CanonicalRunAuthorizationError, match="BLOCKED: admitted forecast-admission artifact is absent"):
        write_investor_review_report_v02(
            report_root, publication_path=publication_path,
            generated_at="2026-10-09T23:59:30+08:00",
        )
    assert not list(report_root.glob("*.investor-review-v02.json"))
    assert not list(report_root.glob("*.investor-review-v02.md"))
    assert not (report_root / "synthetic-missing-forecast-run.run-receipt.json").exists()
    assert _run_state_path(report_root, "synthetic-missing-forecast-run").read_bytes() == state_before
