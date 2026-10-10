from __future__ import annotations

import base64
from datetime import date
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from iios_mvp.canonical_runtime_registry_v01 import validate_canonical_runtime_bindings
from iios_mvp.canonical_investment_admission_v01 import build_canonical_investment_admission
from iios_mvp.canonical_runtime_factory_v01 import (
    FileSystemCanonicalInvestmentAdmissionResolver,
    FileSystemCanonicalValuationOutputResolver,
    LiveJsonRequestInterpreter,
    LiveJsonSemanticProducer,
    RuntimeFactoryError,
    RuntimeCaseContext,
    build_canonical_runtime,
)


def _keypair():
    private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    private_bytes = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (
        base64.b64encode(private_bytes).decode("ascii"),
        base64.b64encode(public_bytes).decode("ascii"),
    )


def _env(tmp_path, monkeypatch, **overrides):
    private_b64, public_b64 = _keypair()
    root = tmp_path / "admissions"
    root.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    base = {
        "IIOS_LLM_PROVIDER_BASE_URL": "https://127.0.0.1:9443/v1/responses",
        "IIOS_LLM_PROVIDER_MODEL": "local-json-model",
        "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64": private_b64,
        "IIOS_LLM_PROVIDER_ID": "trusted-self-hosted-runtime",
        "IIOS_LLM_PROVIDER_VERSION": "local-v1",
        "IIOS_LLM_PROVIDER_PROTOCOL": "OPENAI_RESPONSES",
        "IIOS_LLM_PROVIDER_AUTH_MODE": "NONE",
        "IIOS_LLM_PROVIDER_DEPLOYMENT_MODE": "SELF_HOSTED",
        "IIOS_CANONICAL_ADMISSION_ROOT": str(root),
        "IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64": public_b64,
    }
    base.update(overrides)
    for key, value in base.items():
        monkeypatch.setenv(key, value)
    return base, root, out


def _bundle():
    return {
        "raw_request": "请对百龙创园进行投资决策，截止2026-10-09",
        "request_id": "host-request-test",
        "run_id": "host-test-run",
        "company": "百龙创园",
        "investment_case": {
            "case_id": "RC-CN-A-605016-20261009",
            "market": "CN-A",
            "symbol": "605016",
            "company": "百龙创园",
            "as_of_date": "2026-10-09",
            "cutoff_date": "2026-10-09",
        },
        "evidence_manifest_path": "/trusted/manifest.json",
        "evidence_root": "/trusted/raw",
        "artifact_type": "THESIS_ASSESSMENT",
        "semantic_prompt": "Use only admitted evidence and describe thesis mechanism, drivers and falsifiers.",
        "decision_relevance": "Thesis proposal only; never set the investment action.",
    }


def test_trusted_factory_builds_all_eight_validated_bindings_without_paid_api_key(tmp_path, monkeypatch):
    env, _, out = _env(tmp_path, monkeypatch)
    env.pop("IIOS_LLM_PROVIDER_API_KEY", None)
    runtime = build_canonical_runtime(bundle=_bundle(), output_root=out, env=env)
    assert validate_canonical_runtime_bindings(runtime) is runtime
    assert runtime.request_interpreter.interpreter_id == "iios-live-json-request-interpreter"
    assert runtime.semantic_producer.producer_id == "iios-live-json-semantic-producer"
    assert runtime.current_price_resolver.__class__.__name__ == "FileSystemCanonicalCurrentPriceRegistry"
    assert runtime.independent_forecast_resolver.__class__.__name__ == "FileSystemCanonicalIndependentForecastRegistry"
    assert runtime.upstream_authority_resolver.__class__.__name__ == "FileSystemCanonicalInvestmentAdmissionResolver"
    assert runtime.valuation_output_resolver.__class__.__name__ == "FileSystemCanonicalValuationOutputResolver"
    assert not list((out / "live-provider-evidence").glob("*.json"))


def test_trusted_factory_blocks_unbound_case_identity(tmp_path, monkeypatch):
    env, _, out = _env(tmp_path, monkeypatch)
    bundle = _bundle()
    bundle["company"] = "wrong-company"
    with pytest.raises(RuntimeFactoryError, match="COMPANY_CASE_MISMATCH"):
        build_canonical_runtime(bundle=bundle, output_root=out, env=env)


def test_trusted_factory_rejects_unverified_http_endpoint_even_if_self_hosted(tmp_path, monkeypatch):
    env, _, out = _env(tmp_path, monkeypatch, IIOS_LLM_PROVIDER_BASE_URL="http://127.0.0.1:11434/v1/responses")
    with pytest.raises(RuntimeFactoryError, match="REQUIRES_HTTPS"):
        build_canonical_runtime(bundle=_bundle(), output_root=out, env=env)


def test_filesystem_admission_resolver_blocks_missing_or_wrong_case_record(tmp_path):
    root = tmp_path / "admissions"
    root.mkdir()
    resolver = FileSystemCanonicalInvestmentAdmissionResolver(root)
    reference = {
        "admission_id": "missing-record",
        "admission_record_hash": "a" * 64,
        "contract_version": "IIOS-CANONICAL-INVESTMENT-ADMISSION-0.1",
        "domain": "REALITY",
        "case_id": "RC-CN-A-605016-20261009",
        "market": "CN-A",
        "symbol": "605016",
        "company": "百龙创园",
        "cutoff_date": "2026-10-09",
    }
    with pytest.raises(RuntimeFactoryError, match="ADMISSION_NOT_FOUND"):
        resolver.resolve(
            reference,
            expected_domain="REALITY",
            case_id="RC-CN-A-605016-20261009",
            market="CN-A",
            symbol="605016",
            company="百龙创园",
            cutoff_date=date(2026, 10, 9),
        )


def test_valuation_resolver_requires_admitted_valuation_and_materialized_output(tmp_path):
    root = tmp_path / "admissions"
    root.mkdir()
    resolver = FileSystemCanonicalInvestmentAdmissionResolver(root)
    valuation = FileSystemCanonicalValuationOutputResolver(root, admission_resolver=resolver)
    reference = {
        "admission_id": "not-admitted",
        "admission_record_hash": "a" * 64,
        "contract_version": "IIOS-CANONICAL-INVESTMENT-ADMISSION-0.1",
        "domain": "VALUATION",
        "case_id": "RC-CN-A-605016-20261009",
        "market": "CN-A",
        "symbol": "605016",
        "company": "百龙创园",
        "cutoff_date": "2026-10-09",
    }
    with pytest.raises(RuntimeFactoryError, match="INVESTMENT_ADMISSION_NOT_FOUND"):
        valuation.resolve_valuation_output(
            reference,
            case_id="RC-CN-A-605016-20261009",
            market="CN-A",
            symbol="605016",
            company="百龙创园",
            cutoff_date=date(2026, 10, 9),
        )


class _FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_live_request_interpreter_blocks_model_instrument_drift():
    client = _FakeClient({
        "market": "CN-A", "symbol": "300750", "as_of_date": "2026-10-09",
        "current_position_pct": "0", "request_type": "INVESTMENT_DECISION",
    })
    context = RuntimeCaseContext(
        case_id="RC-CN-A-605016-20261009", market="CN-A", symbol="605016",
        company="百龙创园", cutoff_date="2026-10-09", run_id="run-1", request_id="req-1",
    )
    interpreter = LiveJsonRequestInterpreter(client=client, context=context)
    with pytest.raises(RuntimeFactoryError, match="REQUEST_INTENT_DOES_NOT_MATCH"):
        interpreter.interpret("Analyze CATL")


def test_live_semantic_producer_rejects_authority_or_extra_fields():
    client = _FakeClient({
        "core_projection": {
            "status": "INTACT", "statement": "Statement",
            "mechanism": "Mechanism", "key_driver_ids": ["D1"],
            "falsifiers": ["F1"], "monitoring_triggers": ["T1"],
            "action": "BUY",
        }
    })
    from iios_mvp.llm_semantic_workbench_v01 import SemanticRequest
    producer = LiveJsonSemanticProducer(client=client)
    request = SemanticRequest(
        request_id="req-1", run_id="run-1", case_id="RC-CN-A-605016-20261009",
        market="CN-A", symbol="605016", company="百龙创园",
        cutoff_date="2026-10-09", artifact_type="THESIS_ASSESSMENT",
        input_refs=("manifest-ref",), input_hashes=("a" * 64,),
        prompt="Use only admitted facts", created_at="2026-10-10T00:00:00+00:00",
    )
    with pytest.raises(RuntimeFactoryError, match="CORE_PROJECTION_KEYS_INVALID"):
        producer.produce(request)


def test_build_canonical_runtime_requires_all_trusted_configuration(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(Exception):
        build_canonical_runtime(bundle=_bundle(), output_root=out, env={})
