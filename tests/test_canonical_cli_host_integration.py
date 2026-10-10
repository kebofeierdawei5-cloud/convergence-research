"""Host-level canonical CLI integration; fixture outputs are control-plane only.

This test intentionally exercises the supported command-line host entry
(`iios_mvp.cli.main`) rather than calling run_b2e_conformance directly.
All model/evidence fixtures remain explicitly synthetic and are not production
semantic conformance or real-company evidence admission.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from iios_mvp.canonical_run_authority_v01 import run_state_path
from iios_mvp.canonical_runtime_registry_v01 import CanonicalRuntimeBindings
from iios_mvp.cli import main
from tests.test_b2e_nl_semantic_decision_e2e import (
    CREATED,
    RAW,
    FixtureInterpreter,
    FixtureSemanticProducer,
    _admitted_synthetic_manifest,
    _case_and_resolvers,
    _registries,
)


def test_cli_host_routes_natural_language_request_through_canonical_run(
    tmp_path, monkeypatch, capsys
):
    """A fresh request through the supported host persists run and stage receipts."""
    case, current_price, forecast, upstream, valuation = _case_and_resolvers()
    evidence_root, manifest, manifest_path = _admitted_synthetic_manifest(tmp_path, case)
    # Materialize standards-compliant JSON for the real CLI file loader. The
    # helper's returned mapping is fixture evidence; the CLI receives only the
    # serialized manifest path, exactly as a host deployment would.
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    request_id = "host-b1-request-20261010"
    run_id = "host-b1-run-20261010"
    output_root = tmp_path / "canonical-runs"

    request_registry, producer_registry = _registries()
    interpreter = FixtureInterpreter()
    producer = FixtureSemanticProducer()
    runtime = CanonicalRuntimeBindings(
        request_interpreter=interpreter,
        request_registry=request_registry,
        semantic_producer=producer,
        producer_registry=producer_registry,
        current_price_resolver=current_price,
        independent_forecast_resolver=forecast,
        upstream_authority_resolver=upstream,
        valuation_output_resolver=valuation,
    )

    factory_module_name = "iios_test_host_b1_runtime_factory"
    factory_module = types.ModuleType(factory_module_name)

    def build_runtime(*, bundle, output_root):
        # The host request cannot choose this factory; it is injected by trusted
        # CLI configuration. The factory still receives the request for normal
        # case composition but returns only this explicitly test-only runtime.
        assert bundle["run_id"] == run_id
        assert str(output_root) == output_root_arg
        return runtime

    output_root_arg = str(output_root)
    factory_module.build_runtime = build_runtime
    monkeypatch.setitem(sys.modules, factory_module_name, factory_module)

    bundle = {
        "raw_request": RAW,
        "request_id": request_id,
        "run_id": run_id,
        "created_at": CREATED,
        "company": "宁德时代",
        "investment_case": case,
        "evidence_manifest_path": str(manifest_path),
        "evidence_root": str(evidence_root),
        "artifact_type": "THESIS_ASSESSMENT",
        "semantic_prompt": (
            "SYNTHETIC_TEST_ONLY: assess the thesis from admitted fixture inputs; "
            "never issue an action or execution instruction."
        ),
        "decision_relevance": "SYNTHETIC_TEST_ONLY control-plane integration test.",
        "semantic_facts": [
            {
                "evidence_id": row["evidence_id"],
                "statement": "SYNTHETIC_TEST_ONLY_NOT_A_REAL_COMPANY_FACT",
            }
            for row in manifest["evidence"]
        ],
        "semantic_inferences": [],
        "semantic_assumptions": [{"text": "SYNTHETIC_TEST_ONLY"}],
        "semantic_uncertainties": [{"text": "SYNTHETIC_TEST_ONLY"}],
    }
    bundle_path = tmp_path / "canonical-request-bundle.json"
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "iios-mvp",
            "canonical-run",
            str(bundle_path),
            "--out",
            str(output_root),
            "--runtime-factory",
            f"{factory_module_name}:build_runtime",
        ],
    )

    exit_code = main()
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["run_id"] == run_id
    assert output["case_id"] == case["case_id"]
    assert output["human_approval_required"] is True
    assert output["auto_execution"] is False
    assert output["publication_required"] is True
    assert output["human_report_required"] is True

    state_path = run_state_path(output_root, run_id)
    assert state_path.is_file(), "host entry must persist the canonical Run Envelope"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    envelope = state["envelope"]
    assert envelope["run_id"] == run_id
    assert envelope["case_id"] == case["case_id"]
    assert envelope["symbol"] == "300750"
    assert envelope["cutoff_date"] == case["cutoff_date"]
    assert envelope["run_status"] == "IN_PROGRESS"

    stage_ids = [item["stage_id"] for item in envelope["stage_receipts"]]
    expected_subsequence = [
        "REQUEST_ADMITTED",
        "CASE_CREATED",
        "EVIDENCE_ADMITTED",
        "SEMANTIC_ADMITTED",
        "FORECAST_ADMITTED",
        "VALUATION_ADMITTED",
        "DECISION_ADMITTED",
        "HUMAN_APPROVAL_PENDING",
    ]
    cursor = 0
    for stage_id in stage_ids:
        if cursor < len(expected_subsequence) and stage_id == expected_subsequence[cursor]:
            cursor += 1
    assert cursor == len(expected_subsequence), (
        "canonical host run must persist the required ordered stage receipts; "
        f"actual={stage_ids}"
    )

    # This host integration stops at an AI proposal; publication/report and the
    # complete Run Receipt are intentionally separate commands/gates.
    assert not list(output_root.glob("*.run-receipt.json"))
    assert not list(output_root.glob("*.investor-review-v02.json"))
    assert manifest["status"] == "PASS"
    assert all(row["license_status"] == "TEST_ONLY" for row in manifest["evidence"])
