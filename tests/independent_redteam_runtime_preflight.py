from __future__ import annotations

import json
from pathlib import Path

import pytest

from iios_mvp.canonical_host_v01 import HostRequestError, load_trusted_bundle
from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestIntent, RequestInterpreterRegistration, RequestInterpreterRegistry,
)
from iios_mvp.canonical_runtime_registry_v01 import CanonicalRuntimeBindings
from iios_mvp.canonical_runtime_preflight_v01 import perform_callback_preflight
from iios_mvp.semantic_producer_admission_v01 import ProducerRegistration, ProducerRegistry


CASE = {
    "case_id": "RC-CN-A-605016-20261009", "market": "CN-A", "symbol": "605016",
    "company": "百龙创园", "cutoff_date": "2026-10-09", "as_of_date": "2026-10-09",
    "request": {"market": "CN-A", "symbol": "605016", "as_of_date": "2026-10-09", "current_position_pct": 0},
}
VALID_PROJECTION = {
    "status": "UNKNOWN",
    "statement": "Insufficient admitted evidence; do not infer an investment action.",
    "mechanism": "The callback is only a provider connectivity diagnostic.",
    "key_driver_ids": ["UNRESOLVED"],
    "falsifiers": ["An admitted fact contradicts the proposed explanation."],
    "monitoring_triggers": ["Reassess only after B2/PIT admission."],
}


class HostileInterpreter:
    interpreter_id = "rt-interpreter"
    interpreter_type = "LLM_REQUEST_INTERPRETER"
    interpreter_version = "rt-v1"
    policy_version = "rt-policy-v1"

    def __init__(self, intent=None, failure=None):
        self.intent = intent or RequestIntent("CN-A", "605016", "2026-10-09", "0")
        self.failure = failure
        self.calls = 0

    def interpret(self, raw_request):
        self.calls += 1
        if self.failure:
            raise self.failure
        return self.intent


class HostileProducer:
    producer_id = "rt-semantic"
    producer_type = "LLM_SEMANTIC_PRODUCER"
    producer_version = "rt-v1"
    policy_version = "rt-policy-v1"

    def __init__(self, result=None):
        self.result = result or {"core_projection": dict(VALID_PROJECTION)}
        self.calls = 0

    def produce(self, request):
        self.calls += 1
        return self.result


class ResolverNeverUsed:
    def resolve_current_price(self, *a, **kw):
        raise AssertionError("preflight must not resolve Current Price")
    def resolve_independent_forecast(self, *a, **kw):
        raise AssertionError("preflight must not resolve Forecast")
    def resolve(self, *a, **kw):
        raise AssertionError("preflight must not resolve upstream admissions")
    def resolve_valuation_output(self, *a, **kw):
        raise AssertionError("preflight must not resolve Valuation")


def runtime(*, intent=None, producer=None, failure=None):
    interpreter = HostileInterpreter(intent, failure=failure)
    producer = producer or HostileProducer()
    bindings = CanonicalRuntimeBindings(
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
        current_price_resolver=ResolverNeverUsed(),
        independent_forecast_resolver=ResolverNeverUsed(),
        upstream_authority_resolver=ResolverNeverUsed(),
        valuation_output_resolver=ResolverNeverUsed(),
    )
    return bindings, interpreter, producer


def input_bundle(tmp_path: Path, *, manifest_text: str | None = None):
    data = tmp_path / "data"
    raw = data / "raw"
    raw.mkdir(parents=True)
    manifest = data / "manifest.json"
    if manifest_text is None:
        manifest_text = json.dumps({
            "case_id": CASE["case_id"], "market": CASE["market"], "symbol": CASE["symbol"],
            "company": CASE["company"], "cutoff_date": CASE["cutoff_date"], "status": "NOT_ADMITTED",
            "evidence": [{"evidence_id": "E-UNADMITTED", "content_sha256": "a" * 64}],
        })
    manifest.write_text(manifest_text, encoding="utf-8")
    return {
        "raw_request": "Analyze 百龙创园 605016 as of 2026-10-09.",
        "company": CASE["company"], "investment_case": CASE,
        "evidence_manifest_path": str(manifest), "evidence_root": str(raw),
        "artifact_type": "THESIS_ASSESSMENT",
        "semantic_prompt": "Prompt marker: DO-NOT-LEAK-SEMANTIC-PROMPT",
        "decision_relevance": "No decision authority.",
    }, manifest


def test_redteam_bundle_path_traversal_is_rejected_before_filesystem_escape(tmp_path):
    root = tmp_path / "bundles"
    data = tmp_path / "data"
    root.mkdir()
    data.mkdir()
    outside = tmp_path / "secret.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(HostRequestError, match="INVALID_BUNDLE_ID"):
        load_trusted_bundle(bundle_id="../secret", bundle_root=root, data_root=data)


def test_redteam_duplicate_manifest_keys_block_before_any_callback(tmp_path):
    duplicate = (
        '{"case_id":"RC-CN-A-605016-20261009",'
        '"case_id":"RC-HK-00700-20261009",'
        '"market":"CN-A","symbol":"605016","company":"百龙创园",'
        '"cutoff_date":"2026-10-09","evidence":[{"evidence_id":"E1","content_sha256":"' + "a" * 64 + '"}]}'
    )
    bundle, _ = input_bundle(tmp_path, manifest_text=duplicate)
    bindings, interpreter, producer = runtime()
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(HostRequestError, match="DUPLICATE_JSON_KEY"):
        perform_callback_preflight(
            bundle=bundle, runtime=bindings, output_root=out,
            provider_id="rt", provider_version="rt-v1", model="rt-model",
            runtime_factory="trusted:factory", run_id="rt-1", request_id="rt-1-request",
        )
    assert interpreter.calls == 0
    assert producer.calls == 0


def test_redteam_semantic_authority_field_blocks_and_never_becomes_decision(tmp_path):
    bundle, _ = input_bundle(tmp_path)
    poisoned = {"core_projection": {**VALID_PROJECTION, "action": "BUY", "human_approval_required": False}}
    bindings, interpreter, producer = runtime(producer=HostileProducer(poisoned))
    out = tmp_path / "out"
    out.mkdir()
    report = perform_callback_preflight(
        bundle=bundle, runtime=bindings, output_root=out,
        provider_id="rt", provider_version="rt-v1", model="rt-model",
        runtime_factory="trusted:factory", run_id="rt-2", request_id="rt-2-request",
    )
    assert report["status"] == "PREFLIGHT_ONLY_BLOCKED"
    assert report["reason"] == "PREFLIGHT_SEMANTIC_PROJECTION_SCHEMA_INVALID"
    assert report["decision_created"] is False
    assert report["publication_created"] is False
    assert report["run_receipt_created"] is False
    assert report["human_approval_required"] is True
    assert report["auto_execution"] is False
    assert producer.calls == 1


def test_redteam_model_failure_has_no_fixture_fallback_and_error_is_redacted(tmp_path):
    bundle, _ = input_bundle(tmp_path)
    bindings, interpreter, producer = runtime(failure=RuntimeError("private endpoint token=TOP_SECRET"))
    out = tmp_path / "out"
    out.mkdir()
    report = perform_callback_preflight(
        bundle=bundle, runtime=bindings, output_root=out,
        provider_id="rt", provider_version="rt-v1", model="rt-model",
        runtime_factory="trusted:factory", run_id="rt-3", request_id="rt-3-request",
    )
    assert report["status"] == "PREFLIGHT_ONLY_BLOCKED"
    assert report["failure_stage"] == "REQUEST_CALLBACK"
    assert report["reason"] == "RuntimeError"
    assert "TOP_SECRET" not in json.dumps(report)
    assert producer.calls == 0
    assert report["decision_created"] is False


def test_redteam_preflight_report_does_not_echo_prompt_or_semantic_model_output(tmp_path):
    bundle, _ = input_bundle(tmp_path)
    marker = "MODEL-PRIVATE-OUTPUT-MUST-NOT-BE-COPIED"
    safe_projection = {**VALID_PROJECTION, "statement": marker}
    bindings, _, _ = runtime(producer=HostileProducer({"core_projection": safe_projection}))
    out = tmp_path / "out"
    out.mkdir()
    report = perform_callback_preflight(
        bundle=bundle, runtime=bindings, output_root=out,
        provider_id="rt", provider_version="rt-v1", model="rt-model",
        runtime_factory="trusted:factory", run_id="rt-4", request_id="rt-4-request",
    )
    report_json = json.dumps(report, ensure_ascii=False)
    assert report["status"] == "PREFLIGHT_ONLY_COMPLETE"
    assert marker not in report_json
    assert "DO-NOT-LEAK-SEMANTIC-PROMPT" not in report_json
    assert report["evidence_pit_admission_checked"] is False
    assert report["semantic_admission_checked"] is False
