from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import iios_mvp.canonical_runtime_preflight_v01 as preflight
from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestIntent, RequestInterpreterRegistration, RequestInterpreterRegistry,
)
from iios_mvp.canonical_runtime_registry_v01 import CanonicalRuntimeBindings
from iios_mvp.semantic_producer_admission_v01 import ProducerRegistration, ProducerRegistry

CASE = {
    "case_id": "RC-CN-A-605016-20261009",
    "market": "CN-A", "symbol": "605016", "company": "百龙创园",
    "cutoff_date": "2026-10-09", "as_of_date": "2026-10-09",
    "request": {
        "market": "CN-A", "symbol": "605016", "as_of_date": "2026-10-09",
        "current_position_pct": 0,
    },
}


class FakeInterpreter:
    interpreter_id = "preflight-interpreter"
    interpreter_type = "LLM_REQUEST_INTERPRETER"
    interpreter_version = "preflight-v1"
    policy_version = "preflight-policy-v1"

    def __init__(self, intent=None):
        self.intent = intent or RequestIntent("CN-A", "605016", "2026-10-09", "0")
        self.calls = 0

    def interpret(self, raw_request):
        self.calls += 1
        return self.intent


class FakeProducer:
    producer_id = "preflight-semantic"
    producer_type = "LLM_SEMANTIC_PRODUCER"
    producer_version = "preflight-v1"
    policy_version = "preflight-policy-v1"

    def __init__(self):
        self.calls = 0

    def produce(self, request):
        self.calls += 1
        self.last_request = request
        return {"core_projection": {
            "status": "UNKNOWN",
            "statement": "Preflight only; no admitted investment thesis.",
            "mechanism": "A provider callback smoke output.",
            "key_driver_ids": ["UNKNOWN"],
            "falsifiers": ["An admitted observation contradicts the statement."],
            "monitoring_triggers": ["Reassess after evidence admission."],
        }}


class ResolverStubs:
    def resolve_current_price(self, *args, **kwargs):
        raise AssertionError("preflight must not resolve Current Price")

    def resolve_independent_forecast(self, *args, **kwargs):
        raise AssertionError("preflight must not resolve Forecast")

    def resolve(self, *args, **kwargs):
        raise AssertionError("preflight must not resolve upstream admission")

    def resolve_valuation_output(self, *args, **kwargs):
        raise AssertionError("preflight must not resolve Valuation")


def fake_runtime(intent=None):
    interpreter, producer = FakeInterpreter(intent), FakeProducer()
    runtime = CanonicalRuntimeBindings(
        request_interpreter=interpreter,
        request_registry=RequestInterpreterRegistry((RequestInterpreterRegistration(
            interpreter.interpreter_id, interpreter.interpreter_type,
            interpreter.interpreter_version, interpreter.policy_version,
        ),)),
        semantic_producer=producer,
        producer_registry=ProducerRegistry((ProducerRegistration(
            producer.producer_id, producer.producer_type,
            producer.producer_version, producer.policy_version,
        ),)),
        current_price_resolver=ResolverStubs(),
        independent_forecast_resolver=ResolverStubs(),
        upstream_authority_resolver=ResolverStubs(),
        valuation_output_resolver=ResolverStubs(),
    )
    return runtime


def staged_bundle(tmp_path: Path):
    data_root = tmp_path / "data"
    evidence_root = data_root / "raw"
    evidence_root.mkdir(parents=True)
    manifest_path = data_root / "manifest.json"
    # Intentionally NOT admitted. The preflight should test provider callbacks,
    # but must not change this status or report admission.
    manifest_path.write_text(json.dumps({
        "case_id": CASE["case_id"], "market": CASE["market"], "symbol": CASE["symbol"],
        "company": CASE["company"], "cutoff_date": CASE["cutoff_date"],
        "status": "BLOCKED_NOT_ADMITTED",
        "evidence": [{"evidence_id": "E-PREFLIGHT-ONLY", "content_sha256": "a" * 64,
                      "status": "NOT_ADMITTED"}],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bundle = {
        "raw_request": "使用 IIOS 分析百龙创园 605016，截止 2026-10-09",
        "company": CASE["company"], "investment_case": CASE,
        "evidence_manifest_path": str(manifest_path), "evidence_root": str(evidence_root),
        "artifact_type": "THESIS_ASSESSMENT",
        "semantic_prompt": "Preflight only. Do not treat the following manifest row as admitted.",
        "decision_relevance": "No investment authority.",
    }
    return bundle, manifest_path


def test_callback_preflight_calls_both_callbacks_but_never_admits_or_decides(tmp_path):
    bundle, manifest_path = staged_bundle(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    runtime = fake_runtime()
    report = preflight.perform_callback_preflight(
        bundle=bundle, runtime=runtime, output_root=out,
        provider_id="local-provider", provider_version="local-v1", model="small-local-model",
        runtime_factory="iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime",
        run_id="preflight-run-1", request_id="preflight-request-1",
        created_at="2026-10-10T00:00:00+00:00",
    )
    assert report["status"] == "PREFLIGHT_ONLY_COMPLETE"
    assert report["request_callback_status"] == "PASS"
    assert report["semantic_callback_status"] == "PASS"
    assert report["manifest_row_count"] == 1
    assert report["evidence_pit_admission_checked"] is False
    assert report["semantic_admission_checked"] is False
    assert report["decision_created"] is False
    assert report["publication_created"] is False
    assert report["run_receipt_created"] is False
    assert report["human_approval_required"] is True
    assert report["auto_execution"] is False
    assert runtime.request_interpreter.calls == 1
    assert runtime.semantic_producer.calls == 1
    assert runtime.semantic_producer.last_request.input_refs == ("E-PREFLIGHT-ONLY",)
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "BLOCKED_NOT_ADMITTED"
    assert not list(out.glob("*.decision.json"))
    assert not list(out.glob("*.run-receipt.json"))


def test_model_intent_for_wrong_instrument_blocks_before_semantic_call(tmp_path):
    bundle, _ = staged_bundle(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    runtime = fake_runtime(RequestIntent("CN-A", "300750", "2026-10-09", "0"))
    report = preflight.perform_callback_preflight(
        bundle=bundle, runtime=runtime, output_root=out,
        provider_id="local-provider", provider_version="v1", model="model",
        runtime_factory="trusted:factory", run_id="preflight-run-2", request_id="preflight-request-2",
        created_at="2026-10-10T00:00:00+00:00",
    )
    assert report["status"] == "PREFLIGHT_ONLY_BLOCKED"
    assert report["failure_stage"] == "REQUEST_CALLBACK"
    assert report["reason"] == "PREFLIGHT_REQUEST_INTENT_CASE_MISMATCH"
    assert runtime.semantic_producer.calls == 0
    assert report["decision_created"] is False


def test_manifest_identity_mismatch_blocks_without_calling_provider(tmp_path):
    bundle, manifest_path = staged_bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["symbol"] = "300750"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    runtime = fake_runtime()
    with pytest.raises(preflight.HostRequestError, match="PREFLIGHT_MANIFEST_CASE_IDENTITY_MISMATCH"):
        preflight.perform_callback_preflight(
            bundle=bundle, runtime=runtime, output_root=out,
            provider_id="local-provider", provider_version="v1", model="model",
            runtime_factory="trusted:factory", run_id="preflight-run-3", request_id="preflight-request-3",
        )
    assert runtime.request_interpreter.calls == 0
    assert runtime.semantic_producer.calls == 0


def test_preflight_report_hash_is_recomputed_and_file_is_immutable(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    report = {
        "schema_version": preflight.VERSION, "status": "PREFLIGHT_ONLY_COMPLETE",
        "run_id": "preflight-hash-test", "evidence_pit_admission_checked": False,
        "semantic_admission_checked": False, "decision_created": False,
        "publication_created": False, "run_receipt_created": False,
        "human_approval_required": True, "auto_execution": False,
    }
    path, saved = preflight._save(out, report)
    core = {key: value for key, value in saved.items() if key != "report_sha256"}
    assert path.is_file()
    assert saved["report_sha256"] == hashlib.sha256(preflight._canonical(core)).hexdigest()
    with pytest.raises(preflight.HostRequestError, match="PREFLIGHT_REPORT_IMMUTABLE_COLLISION"):
        preflight._save(out, report)


def test_environment_entry_uses_trusted_loader_and_persists_report(tmp_path, monkeypatch):
    bundle, _ = staged_bundle(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (tmp_path / "bundles").mkdir()
    config = {
        "bundle_root": tmp_path / "bundles", "data_root": tmp_path / "data",
        "output_root": out, "factory_spec": "iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime",
    }
    monkeypatch.setattr(preflight, "load_host_config", lambda: config)
    monkeypatch.setattr(preflight, "load_trusted_bundle", lambda **_: dict(bundle))
    monkeypatch.setattr(preflight, "_resolve_canonical_runtime", lambda **_: fake_runtime())
    monkeypatch.setenv("IIOS_LLM_PROVIDER_ID", "local-provider")
    monkeypatch.setenv("IIOS_LLM_PROVIDER_VERSION", "local-v1")
    monkeypatch.setenv("IIOS_LLM_PROVIDER_MODEL", "model")
    status, result = preflight.run_from_environment("case-605016")
    assert status == 0
    assert result["status"] == "PREFLIGHT_ONLY_COMPLETE"
    report_path = Path(result["report_path"])
    assert report_path.is_file()
    stored = json.loads(report_path.read_text(encoding="utf-8"))
    assert stored["report_sha256"] == result["report_sha256"]
    assert stored["evidence_pit_admission_checked"] is False
    assert stored["decision_created"] is False
