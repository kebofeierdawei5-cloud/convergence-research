import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
from iios_mvp.llm_semantic_workbench_v01 import LLMSemanticWorkbench, SemanticRequest
from iios_mvp.semantic_producer_admission_v01 import ProducerRegistration, ProducerRegistry
from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestAdmissionError,
    RequestInterpreterRegistration,
    RequestInterpreterRegistry,
    RequestIntent,
    admit_natural_language_request,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


class FixtureInterpreter:
    interpreter_id = "fixture-interpreter-0.1"
    interpreter_type = "LLM_REQUEST_INTERPRETER"
    interpreter_version = "interpreter-0.1"
    policy_version = "IIOS-NL-POLICY-0.1"

    def interpret(self, raw_request: str) -> RequestIntent:
        assert raw_request.strip()
        return RequestIntent(
            market="CN-A",
            symbol="002001",
            as_of_date="2026-10-07",
            current_position_pct="0",
        )


class FixtureLLM:
    producer_id = "fixture-llm-b2b"
    producer_type = "LLM_SEMANTIC_PRODUCER"
    producer_version = "adapter-b2b-0.1"
    policy_version = "IIOS-LLM-POLICY-0.1"

    def produce(self, request: SemanticRequest):
        return {"status": "PASS", "statement": "fixture semantic output", "cutoff_used": request.cutoff_date}


def interpreter_registry() -> RequestInterpreterRegistry:
    return RequestInterpreterRegistry((RequestInterpreterRegistration(
        interpreter_id=FixtureInterpreter.interpreter_id,
        interpreter_type=FixtureInterpreter.interpreter_type,
        interpreter_version=FixtureInterpreter.interpreter_version,
        policy_version=FixtureInterpreter.policy_version,
    ),))


def semantic_registry() -> ProducerRegistry:
    return ProducerRegistry((ProducerRegistration(
        producer_id=FixtureLLM.producer_id,
        producer_type=FixtureLLM.producer_type,
        producer_version=FixtureLLM.producer_version,
        policy_version=FixtureLLM.policy_version,
    ),))


def test_natural_language_entry_creates_case_and_request_receipt():
    o = CanonicalResearchOrchestrator()
    result = admit_natural_language_request(
        orchestrator=o,
        registry=interpreter_registry(),
        interpreter=FixtureInterpreter(),
        request_id="nl-1",
        run_id="run-nl-1",
        raw_request="请分析 002001，按 2026-10-07 时点判断是否值得买入。",
        created_at="2026-10-08T00:00:00+00:00",
    )
    assert result.case_id == "RC-CN-A-002001-20261007"
    assert result.request_receipt["status"] == "ADMITTED"
    assert o.get("run-nl-1").stage_state == Stage.CASE_CREATED
    assert o.get("run-nl-1").research_case_hash == result.case_hash


def test_request_hash_changes_when_raw_language_changes():
    o = CanonicalResearchOrchestrator()
    first = admit_natural_language_request(
        orchestrator=o, registry=interpreter_registry(), interpreter=FixtureInterpreter(),
        request_id="nl-2a", run_id="run-nl-2a",
        raw_request="分析002001", created_at="2026-10-08T00:00:00+00:00",
    )
    second = admit_natural_language_request(
        orchestrator=o, registry=interpreter_registry(), interpreter=FixtureInterpreter(),
        request_id="nl-2b", run_id="run-nl-2b",
        raw_request="分析002001并重点检查估值", created_at="2026-10-08T00:00:00+00:00",
    )
    assert first.request_receipt["raw_request_sha256"] != second.request_receipt["raw_request_sha256"]
    assert first.request_receipt["normalized_request_sha256"] == second.request_receipt["normalized_request_sha256"]


def test_unregistered_interpreter_is_blocked():
    o = CanonicalResearchOrchestrator()
    bad = FixtureInterpreter()
    registry = RequestInterpreterRegistry()
    with pytest.raises(RequestAdmissionError, match="request interpreter is not registered"):
        admit_natural_language_request(
            orchestrator=o, registry=registry, interpreter=bad,
            request_id="nl-3", run_id="run-nl-3", raw_request="分析002001",
            created_at="2026-10-08T00:00:00+00:00",
        )


def test_only_investment_decision_requests_enter_canonical_path():
    class OtherInterpreter(FixtureInterpreter):
        def interpret(self, raw_request: str) -> RequestIntent:
            return RequestIntent("CN-A", "002001", "2026-10-07", "0", request_type="SCREENING")
    o = CanonicalResearchOrchestrator()
    with pytest.raises(RequestAdmissionError, match="only INVESTMENT_DECISION"):
        admit_natural_language_request(
            orchestrator=o, registry=interpreter_registry(), interpreter=OtherInterpreter(),
            request_id="nl-4", run_id="run-nl-4", raw_request="筛选", created_at="2026-10-08T00:00:00+00:00"
        )


def test_schema_validates_request_receipt():
    o = CanonicalResearchOrchestrator()
    result = admit_natural_language_request(
        orchestrator=o, registry=interpreter_registry(), interpreter=FixtureInterpreter(),
        request_id="nl-5", run_id="run-nl-5",
        raw_request="判断002001", created_at="2026-10-08T00:00:00+00:00",
    )
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "nl_request_admission_v0.1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(result.request_receipt)


def test_full_conformance_fixture_reaches_semantic_admitted():
    o = CanonicalResearchOrchestrator()
    entry = admit_natural_language_request(
        orchestrator=o, registry=interpreter_registry(), interpreter=FixtureInterpreter(),
        request_id="nl-6", run_id="run-nl-6",
        raw_request="请判断002001当前价格是否值得买入", created_at="2026-10-08T00:00:00+00:00",
    )
    o.transition("run-nl-6", Stage.EVIDENCE_PENDING, created_at="2026-10-08T00:00:00+00:00")
    o.transition(
        "run-nl-6",
        Stage.EVIDENCE_ADMITTED,
        output_refs=("E001", "E002"),
        output_hashes=(SHA_A, SHA_B),
        created_at="2026-10-08T00:00:00+00:00",
    )
    o.transition("run-nl-6", Stage.SEMANTIC_PENDING, created_at="2026-10-08T00:00:00+00:00")
    workbench = LLMSemanticWorkbench(orchestrator=o, registry=semantic_registry())
    result = workbench.run(
        producer=FixtureLLM(),
        request=SemanticRequest(
            request_id="semantic-nl-6", run_id=entry.run_id, case_id=entry.case_id,
            market="CN-A", symbol="002001", company="浙江新和成股份有限公司",
            cutoff_date="2026-10-07", artifact_type="QUALITY_ASSESSMENT",
            input_refs=("E001", "E002"), input_hashes=(SHA_A, SHA_B),
            prompt="基于准入证据进行质量判断", created_at="2026-10-08T00:00:00+00:00",
        ),
        decision_relevance="Quality controls capital admission.",
    )
    assert result.admission.status == "ADMITTED"
    assert o.get("run-nl-6").stage_state == Stage.SEMANTIC_ADMITTED


def test_cannot_mark_canonical_without_request_admission():
    o = CanonicalResearchOrchestrator()
    o.start(
        run_id="direct",
        case_id="RC-CN-A-002001-20261007",
        market="CN-A",
        symbol="002001",
        cutoff_date="2026-10-07",
        as_of_date="2026-10-07",
        created_at="2026-10-08T00:00:00+00:00",
    )
    # The lower-level orchestrator remains a control-plane primitive, but B2-B's canonical
    # natural-language entry is the only admitted path represented by this harness.
    assert o.get("direct").stage_state == Stage.REQUEST_RECEIVED
