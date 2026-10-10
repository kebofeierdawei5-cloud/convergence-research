from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import iios_mvp.self_hosted_semantic_runtime_v01 as semantic_runtime
import iios_mvp.self_hosted_runtime_factory_v01 as runtime_factory
from iios_mvp.canonical_investment_admission_v01 import (
    CanonicalInvestmentAdmissionRecord,
    build_canonical_investment_admission,
)
from iios_mvp.forecast_valuation_return_lineage_v01 import build_canonical_valuation_output
from iios_mvp.llm_semantic_workbench_v01 import SemanticRequest
from iios_mvp.thesis_admission_v03 import THESIS_STATUSES


def env_config(endpoint="http://127.0.0.1:11434/v1/responses"):
    return {
        "IIOS_SELF_HOSTED_RESPONSES_ENDPOINT": endpoint,
        "IIOS_SELF_HOSTED_MODEL": "qwen3:8b",
        "IIOS_SELF_HOSTED_PROVIDER_ID": "ollama-local",
        "IIOS_SELF_HOSTED_PROVIDER_VERSION": "ollama-v0.13.3",
    }


def expected_case():
    return {
        "case_id": "RC-CN-A-605016-20261009",
        "market": "CN-A",
        "symbol": "605016",
        "company": "百龙创园",
        "cutoff_date": "2026-10-09",
        "as_of_date": "2026-10-09",
        "request": {
            "market": "CN-A",
            "symbol": "605016",
            "as_of_date": "2026-10-09",
            "current_position_pct": 0,
        },
    }


class FakeResponsesClient:
    def __init__(self, result):
        self.result = result
        self.prompts = []

    def generate_json(self, prompt):
        self.prompts.append(prompt)
        return self.result


def _write_admission(root: Path, record: CanonicalInvestmentAdmissionRecord):
    root.mkdir(parents=True, exist_ok=True)
    path_hash = hashlib.sha256(record.admission_record_hash.encode("utf-8")).hexdigest()
    path = root / f"{path_hash}.admission.json"
    path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_local_runtime_requires_no_api_key_and_accepts_loopback_endpoint():
    config = semantic_runtime.load_self_hosted_responses_config(env_config())
    assert config.endpoint == "http://127.0.0.1:11434/v1/responses"
    assert config.model == "qwen3:8b"
    assert config.timeout_seconds == 120


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com/v1/responses",
        "http://192.168.1.10:11434/v1/responses",
        "https://api.example.com/v1/responses",
        "http://127.0.0.1:11434/v1/chat/completions",
        "http://user:password@127.0.0.1:11434/v1/responses",
        "http://127.0.0.1:11434/v1/responses?api_key=secret",
    ],
)
def test_local_runtime_rejects_non_loopback_or_wrong_endpoint(endpoint):
    with pytest.raises(semantic_runtime.SelfHostedRuntimeError):
        semantic_runtime.load_self_hosted_responses_config(env_config(endpoint))


def test_responses_client_uses_no_auth_and_extracts_json(monkeypatch):
    body = json.dumps({"output_text": json.dumps({"ok": True})}).encode("utf-8")
    response = SimpleNamespace(response_bytes=body, http_status=200, content_type="application/json")
    captured = {}

    def fake_invoke(*, config, payload):
        captured["config"] = config
        captured["payload"] = payload
        return response

    monkeypatch.setattr(semantic_runtime, "invoke_live_provider", fake_invoke)
    client = semantic_runtime.SelfHostedResponsesClient(
        semantic_runtime.load_self_hosted_responses_config(env_config())
    )
    assert client.generate_json("return JSON") == {"ok": True}
    assert captured["config"].auth_mode == "NONE"
    assert captured["config"].api_key == ""
    assert captured["payload"]["store"] is False
    assert "Authorization" not in captured


def test_responses_client_extracts_nested_output_text(monkeypatch):
    body = json.dumps({
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "{\"status\":\"ok\"}"}]}
        ]
    }).encode("utf-8")
    monkeypatch.setattr(
        semantic_runtime, "invoke_live_provider",
        lambda **_: SimpleNamespace(response_bytes=body, http_status=200, content_type="application/json"),
    )
    client = semantic_runtime.SelfHostedResponsesClient(
        semantic_runtime.load_self_hosted_responses_config(env_config())
    )
    assert client.generate_json("return JSON") == {"status": "ok"}


def test_responses_client_rejects_duplicate_json_keys(monkeypatch):
    body = json.dumps({"output_text": '{"status":"ok","status":"fake"}'}).encode("utf-8")
    monkeypatch.setattr(
        semantic_runtime, "invoke_live_provider",
        lambda **_: SimpleNamespace(response_bytes=body, http_status=200, content_type="application/json"),
    )
    client = semantic_runtime.SelfHostedResponsesClient(
        semantic_runtime.load_self_hosted_responses_config(env_config())
    )
    with pytest.raises(semantic_runtime.SelfHostedRuntimeError, match="DUPLICATE_JSON_KEY"):
        client.generate_json("return JSON")


def test_request_interpreter_uses_staged_values_only_for_missing_fields():
    parsed = {
        "market": None,
        "symbol": "605016",
        "as_of_date": None,
        "current_position_pct": None,
        "request_type": "INVESTMENT_DECISION",
    }
    client = FakeResponsesClient(parsed)
    interpreter = semantic_runtime.SelfHostedRequestInterpreter(
        client=client, expected_case=expected_case(), interpreter_id="local:request"
    )
    intent = interpreter.interpret("使用 IIOS 分析百龙创园 605016，截止 2026-10-09")
    assert intent.market == "CN-A"
    assert intent.symbol == "605016"
    assert intent.as_of_date == "2026-10-09"
    assert intent.current_position_pct == "0"
    assert "RAW REQUEST" in client.prompts[0]


@pytest.mark.parametrize(
    "field,value",
    [
        ("symbol", "300750"),
        ("market", "HK"),
        ("as_of_date", "2026-10-08"),
        ("current_position_pct", 16),
    ],
)
def test_request_interpreter_blocks_conflict_with_staged_case(field, value):
    parsed = {
        "market": "CN-A",
        "symbol": "605016",
        "as_of_date": "2026-10-09",
        "current_position_pct": 0,
        "request_type": "INVESTMENT_DECISION",
    }
    parsed[field] = value
    interpreter = semantic_runtime.SelfHostedRequestInterpreter(
        client=FakeResponsesClient(parsed), expected_case=expected_case(), interpreter_id="local:request"
    )
    with pytest.raises(semantic_runtime.SelfHostedRuntimeError, match="REQUEST_INTENT_TRUSTED_CASE_MISMATCH"):
        interpreter.interpret("different request")


def valid_projection():
    return {
        "status": "UNKNOWN",
        "statement": "Evidence is insufficient to admit a positive thesis.",
        "mechanism": "The required source-admitted causal chain is not yet available.",
        "key_driver_ids": ["DRIVER_UNRESOLVED"],
        "falsifiers": ["A source-admitted observation contradicts the proposed mechanism."],
        "monitoring_triggers": ["Reassess only after required Evidence/PIT admission."],
    }


def semantic_request():
    return SemanticRequest(
        request_id="req-1",
        run_id="run-1",
        case_id="case-1",
        market="CN-A",
        symbol="605016",
        company="百龙创园",
        cutoff_date="2026-10-09",
        artifact_type="THESIS_ASSESSMENT",
        input_refs=("evidence-1",),
        input_hashes=("a" * 64,),
        prompt="Use source-located excerpts only; unresolved facts remain UNKNOWN.",
        created_at="2026-10-10T00:00:00+00:00",
    )


def test_semantic_producer_accepts_only_exact_thesis_projection():
    output = {"core_projection": valid_projection()}
    producer = semantic_runtime.SelfHostedThesisSemanticProducer(
        client=FakeResponsesClient(output),
        producer_id="local:thesis",
        producer_version="ollama-v0.13.3:qwen3:8b",
    )
    assert producer.produce(semantic_request()) == output
    assert "Do not output trade action" in producer.client.prompts[0]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"action": "BUY"}),
        lambda value: value["core_projection"].update({"confidence": 0.99}),
        lambda value: value["core_projection"].update({"key_driver_ids": []}),
        lambda value: value["core_projection"].update({"status": "BUY"}),
    ],
)
def test_semantic_producer_rejects_invalid_or_authority_output(mutate):
    output = {"core_projection": valid_projection()}
    mutate(output)
    producer = semantic_runtime.SelfHostedThesisSemanticProducer(
        client=FakeResponsesClient(output),
        producer_id="local:thesis",
        producer_version="ollama-v0.13.3:qwen3:8b",
    )
    with pytest.raises(semantic_runtime.SelfHostedRuntimeError):
        producer.produce(semantic_request())


def test_filesystem_admission_resolver_checks_hash_identity_and_domain(tmp_path):
    record = build_canonical_investment_admission(
        admission_id="admission-reality-1",
        domain="REALITY",
        case_id="case-1",
        market="CN-A",
        symbol="605016",
        company="百龙创园",
        cutoff_date="2026-10-09",
        domain_status="PASS",
        source_record_id="reality-1",
        source_record_hash="a" * 64,
        output_hash="b" * 64,
        producer_version="reality-producer-v1",
        evidence_ids=["evidence-1"],
        admitted_at="2026-10-10T00:00:00+00:00",
    )
    root = tmp_path / "admissions"
    _write_admission(root, record)
    resolver = runtime_factory.FileSystemCanonicalInvestmentAdmissionResolver(root)
    resolved = resolver.resolve(
        record.reference().to_dict(),
        expected_domain="REALITY",
        case_id="case-1",
        market="CN-A",
        symbol="605016",
        company="百龙创园",
        cutoff_date=date(2026, 10, 9),
    )
    assert resolved.admission_record_hash == record.admission_record_hash
    with pytest.raises(ValueError, match="DOMAIN_MISMATCH"):
        resolver.resolve(
            record.reference().to_dict(),
            expected_domain="QUALITY",
            case_id="case-1",
            market="CN-A",
            symbol="605016",
            company="百龙创园",
            cutoff_date=date(2026, 10, 9),
        )


def test_filesystem_valuation_resolver_binds_output_to_admission(tmp_path):
    forecast_ref = {"forecast_id": "forecast-1", "admission_record_hash": "c" * 64}
    output = build_canonical_valuation_output({
        "valuation_id": "valuation-1",
        "valuation_version": "valuation-v1",
        "case_id": "case-1",
        "market": "CN-A",
        "symbol": "605016",
        "company": "百龙创园",
        "cutoff_date": "2026-10-09",
        "forecast_ref": forecast_ref,
        "horizon_years": "1",
        "reference_value_per_share": "25",
        "scenarios": {
            "bear": {"probability": "0.25", "value_per_share": "18", "cash_distributions_per_share": "0"},
            "base": {"probability": "0.50", "value_per_share": "25", "cash_distributions_per_share": "0"},
            "bull": {"probability": "0.25", "value_per_share": "34", "cash_distributions_per_share": "0"},
        },
        "evidence_ids": ["evidence-valuation-1"],
    })
    admission = build_canonical_investment_admission(
        admission_id="valuation-admission-1",
        domain="VALUATION",
        case_id="case-1",
        market="CN-A",
        symbol="605016",
        company="百龙创园",
        cutoff_date="2026-10-09",
        domain_status="PASS",
        source_record_id="valuation-source-1",
        source_record_hash="d" * 64,
        output_hash=output["output_hash"],
        producer_version="valuation-producer-v1",
        evidence_ids=["evidence-valuation-1"],
        admitted_at="2026-10-10T00:00:00+00:00",
    )
    admission_root = tmp_path / "admissions"
    _write_admission(admission_root, admission)
    valuation_root = tmp_path / "valuations"
    valuation_root.mkdir()
    filename_hash = hashlib.sha256(admission.admission_record_hash.encode("utf-8")).hexdigest()
    (valuation_root / f"{filename_hash}.valuation.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    admission_resolver = runtime_factory.FileSystemCanonicalInvestmentAdmissionResolver(admission_root)
    resolver = runtime_factory.FileSystemCanonicalValuationOutputResolver(
        records_root=valuation_root, admission_resolver=admission_resolver
    )
    resolved = resolver.resolve_valuation_output(
        admission.reference().to_dict(),
        case_id="case-1",
        market="CN-A",
        symbol="605016",
        company="百龙创园",
        cutoff_date=date(2026, 10, 9),
    )
    assert resolved["output_hash"] == output["output_hash"]
    with pytest.raises(ValueError, match="CASE_BINDING_MISMATCH"):
        resolver.resolve_valuation_output(
            admission.reference().to_dict(),
            case_id="case-other",
            market="CN-A",
            symbol="605016",
            company="百龙创园",
            cutoff_date=date(2026, 10, 9),
        )


def test_runtime_factory_blocks_when_required_admitted_stores_are_missing(tmp_path, monkeypatch):
    runtime_root = tmp_path / "runtime-data"
    runtime_root.mkdir()
    monkeypatch.setenv("IIOS_HOST_RUNTIME_DATA_ROOT", str(runtime_root))
    with pytest.raises(runtime_factory.SelfHostedRuntimeFactoryError, match="CURRENT_PRICE_ROOT_MISSING"):
        runtime_factory.create_canonical_runtime(
            bundle={"company": "百龙创园", "investment_case": expected_case()},
            output_root=str(tmp_path / "out"),
        )


def test_runtime_factory_blocks_when_local_model_config_is_missing(tmp_path, monkeypatch):
    runtime_root = tmp_path / "runtime-data"
    (runtime_root / "current_price" / "current_price_admissions").mkdir(parents=True)
    (runtime_root / "independent_forecast" / "independent_forecast_admissions").mkdir(parents=True)
    (runtime_root / "investment_admissions").mkdir(parents=True)
    (runtime_root / "valuation_outputs").mkdir(parents=True)
    (runtime_root / "current_price" / "current_price_admissions" / "placeholder.price.json").write_text("{}", encoding="utf-8")
    (runtime_root / "independent_forecast" / "independent_forecast_admissions" / "placeholder.forecast.json").write_text("{}", encoding="utf-8")
    (runtime_root / "investment_admissions" / "placeholder.admission.json").write_text("{}", encoding="utf-8")
    (runtime_root / "valuation_outputs" / "placeholder.valuation.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("IIOS_HOST_RUNTIME_DATA_ROOT", str(runtime_root))
    for key in (
        "IIOS_SELF_HOSTED_RESPONSES_ENDPOINT", "IIOS_SELF_HOSTED_MODEL",
        "IIOS_SELF_HOSTED_PROVIDER_ID", "IIOS_SELF_HOSTED_PROVIDER_VERSION",
    ):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(runtime_factory.SelfHostedRuntimeFactoryError, match="SELF_HOSTED_MODEL_CONFIG_MISSING"):
        runtime_factory.create_canonical_runtime(
            bundle={"company": "百龙创园", "investment_case": expected_case()},
            output_root=str(tmp_path / "out"),
        )
