import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
from iios_mvp.llm_semantic_workbench_v01 import LLMSemanticWorkbench, SemanticRequest
from iios_mvp.semantic_producer_admission_v01 import (
    ProducerRegistration,
    ProducerRegistry,
    SemanticAdmissionContext,
    SemanticAdmissionError,
    admit_semantic_artifact,
    build_producer_receipt,
    build_semantic_artifact,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


class FixtureLLM:
    producer_id = "fixture-llm-0.1"
    producer_type = "LLM_SEMANTIC_PRODUCER"
    producer_version = "adapter-0.1"
    policy_version = "IIOS-LLM-POLICY-0.1"

    def produce(self, request: SemanticRequest):
        return {"status": "PASS", "statement": "fixture semantic output", "cutoff_used": request.cutoff_date}


def registry() -> ProducerRegistry:
    return ProducerRegistry((ProducerRegistration(
        producer_id=FixtureLLM.producer_id,
        producer_type=FixtureLLM.producer_type,
        producer_version=FixtureLLM.producer_version,
        policy_version=FixtureLLM.policy_version,
    ),))


def context() -> SemanticAdmissionContext:
    return SemanticAdmissionContext(
        case_id="RC-CN-A-002001-20261008",
        market="CN-A",
        symbol="002001.SZ",
        company="浙江新和成股份有限公司",
        cutoff_date="2026-10-08",
        artifact_type="QUALITY_ASSESSMENT",
        input_refs=("E001", "E002"),
        input_hashes=(SHA_A, SHA_B),
        producer_id=FixtureLLM.producer_id,
        producer_version=FixtureLLM.producer_version,
        producer_type=FixtureLLM.producer_type,
        policy_version=FixtureLLM.policy_version,
    )


def make_artifact():
    return build_semantic_artifact(
        artifact_id="a1",
        artifact_type="QUALITY_ASSESSMENT",
        context=context(),
        output={"status": "CONDITIONAL"},
        facts=({"evidence_id": "E001"},),
        inferences=({"text": "inference"},),
        assumptions=({"text": "assumption"},),
        uncertainties=({"text": "uncertainty"},),
        decision_relevance="Quality controls new-capital admission.",
        created_at="2026-10-08T00:00:00+00:00",
    )


def test_schema_and_receipt_are_valid():
    artifact = make_artifact()
    receipt = build_producer_receipt(receipt_id="r1", artifact=artifact, stage_id="QUALITY_ASSESSMENT", created_at="2026-10-08T00:00:00+00:00")
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "semantic_producer_receipt_v0.1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(receipt)
    admission = admit_semantic_artifact(artifact, receipt, context=context(), registry=registry())
    assert admission.status == "ADMITTED"
    assert len(admission.admission_hash) == 64


def test_unregistered_producer_is_blocked():
    artifact = make_artifact()
    receipt = build_producer_receipt(receipt_id="r2", artifact=artifact, stage_id="QUALITY_ASSESSMENT", created_at="2026-10-08T00:00:00+00:00")
    bad_context = SemanticAdmissionContext(**{**context().__dict__, "producer_id": "unregistered"})
    with pytest.raises(SemanticAdmissionError, match="producer is not registered"):
        admit_semantic_artifact(artifact, receipt, context=bad_context, registry=registry())


def test_artifact_hash_tampering_is_blocked():
    artifact = make_artifact()
    tampered = dict(artifact)
    tampered["output"] = {"status": "PASS"}
    receipt = build_producer_receipt(receipt_id="r3", artifact=artifact, stage_id="QUALITY_ASSESSMENT", created_at="2026-10-08T00:00:00+00:00")
    with pytest.raises(SemanticAdmissionError, match="artifact_hash integrity failure"):
        admit_semantic_artifact(tampered, receipt, context=context(), registry=registry())


def test_receipt_tampering_is_blocked():
    artifact = make_artifact()
    receipt = build_producer_receipt(receipt_id="r4", artifact=artifact, stage_id="QUALITY_ASSESSMENT", created_at="2026-10-08T00:00:00+00:00")
    tampered = dict(receipt)
    tampered["producer_version"] = "forged-version"
    with pytest.raises(SemanticAdmissionError, match="producer receipt integrity failure"):
        admit_semantic_artifact(artifact, tampered, context=context(), registry=registry())


def test_input_lineage_must_match_exactly():
    artifact = make_artifact()
    receipt = build_producer_receipt(receipt_id="r5", artifact=artifact, stage_id="QUALITY_ASSESSMENT", created_at="2026-10-08T00:00:00+00:00")
    bad_context = SemanticAdmissionContext(**{**context().__dict__, "input_hashes": (SHA_B, SHA_A)})
    with pytest.raises(SemanticAdmissionError, match="input_hashes lineage mismatch"):
        admit_semantic_artifact(artifact, receipt, context=bad_context, registry=registry())


def test_output_hash_mismatch_is_blocked():
    artifact = make_artifact()
    receipt = build_producer_receipt(receipt_id="r6", artifact=artifact, stage_id="QUALITY_ASSESSMENT", created_at="2026-10-08T00:00:00+00:00")
    tampered = dict(receipt)
    tampered["output_hash"] = SHA_B
    tampered["receipt_hash"] = "c" * 64
    with pytest.raises(SemanticAdmissionError, match="producer receipt integrity failure"):
        admit_semantic_artifact(artifact, tampered, context=context(), registry=registry())


def test_orchestrator_stage_cannot_be_bypassed():
    orchestrator = CanonicalResearchOrchestrator()
    orchestrator.start(run_id="b2-bypass", case_id="c-b2", market="CN-A", symbol="002001.SZ", cutoff_date="2026-10-08", as_of_date="2026-10-08", created_at="2026-10-08T00:00:00+00:00")
    with pytest.raises(ValueError, match="stage authorization failed"):
        LLMSemanticWorkbench(orchestrator=orchestrator, registry=registry()).run(
            producer=FixtureLLM(),
            request=SemanticRequest(
                request_id="req", run_id="b2-bypass", case_id="c-b2", market="CN-A", symbol="002001.SZ",
                company="浙江新和成股份有限公司", cutoff_date="2026-10-08", artifact_type="QUALITY_ASSESSMENT",
                input_refs=("E001",), input_hashes=(SHA_A,), prompt="Assess quality",
                created_at="2026-10-08T00:00:00+00:00"),
            decision_relevance="test",
        )


def test_workbench_rejects_unadmitted_semantic_input():
    orchestrator = CanonicalResearchOrchestrator()
    orchestrator.start(
        run_id="b2-lineage",
        case_id="RC-CN-A-002001-20261008",
        market="CN-A",
        symbol="002001.SZ",
        cutoff_date="2026-10-08",
        as_of_date="2026-10-08",
        created_at="2026-10-08T00:00:00+00:00",
    )
    orchestrator.transition("b2-lineage", Stage.REQUEST_ADMITTED)
    orchestrator.transition("b2-lineage", Stage.CASE_CREATED)
    orchestrator.transition("b2-lineage", Stage.EVIDENCE_PENDING)
    orchestrator.transition(
        "b2-lineage",
        Stage.EVIDENCE_ADMITTED,
        output_refs=("E001",),
        output_hashes=(SHA_A,),
    )
    orchestrator.transition("b2-lineage", Stage.SEMANTIC_PENDING)
    with pytest.raises(ValueError, match="semantic input lineage is not fully admitted"):
        LLMSemanticWorkbench(orchestrator=orchestrator, registry=registry()).run(
            producer=FixtureLLM(),
            request=SemanticRequest(
                request_id="req-lineage",
                run_id="b2-lineage",
                case_id="RC-CN-A-002001-20261008",
                market="CN-A",
                symbol="002001.SZ",
                company="浙江新和成股份有限公司",
                cutoff_date="2026-10-08",
                artifact_type="QUALITY_ASSESSMENT",
                input_refs=("E001", "E002"),
                input_hashes=(SHA_A, SHA_B),
                prompt="Assess Quality from admitted evidence only.",
                created_at="2026-10-08T00:00:00+00:00",
            ),
            decision_relevance="Quality controls capital admission.",
        )


def test_workbench_admits_authorized_fixture_and_advances_orchestrator():
    orchestrator = CanonicalResearchOrchestrator()
    orchestrator.start(run_id="b2-run", case_id="RC-CN-A-002001-20261008", market="CN-A", symbol="002001.SZ", cutoff_date="2026-10-08", as_of_date="2026-10-08", created_at="2026-10-08T00:00:00+00:00")
    orchestrator.transition("b2-run", Stage.REQUEST_ADMITTED)
    orchestrator.transition("b2-run", Stage.CASE_CREATED)
    orchestrator.transition("b2-run", Stage.EVIDENCE_PENDING)
    orchestrator.transition("b2-run", Stage.EVIDENCE_ADMITTED, output_refs=("E001", "E002"), output_hashes=(SHA_A, SHA_B))
    orchestrator.transition("b2-run", Stage.SEMANTIC_PENDING)
    result = LLMSemanticWorkbench(orchestrator=orchestrator, registry=registry()).run(
        producer=FixtureLLM(),
        request=SemanticRequest(
            request_id="req-1", run_id="b2-run", case_id="RC-CN-A-002001-20261008", market="CN-A",
            symbol="002001.SZ", company="浙江新和成股份有限公司", cutoff_date="2026-10-08",
            artifact_type="QUALITY_ASSESSMENT", input_refs=("E001", "E002"), input_hashes=(SHA_A, SHA_B),
            prompt="Assess Quality from admitted evidence only.", created_at="2026-10-08T00:00:00+00:00"),
        decision_relevance="Quality controls capital admission.",
    )
    assert result.admission.status == "ADMITTED"
    assert result.artifact["producer_type"] == "LLM_SEMANTIC_PRODUCER"
    assert result.producer_receipt["artifact_hash"] == result.artifact["artifact_hash"]
    assert orchestrator.get("b2-run").stage_state == Stage.SEMANTIC_ADMITTED


def test_human_expert_registration_remains_distinct():
    human_registry = ProducerRegistry((ProducerRegistration(
        producer_id="human-adjudicator-1",
        producer_type="HUMAN_EXPERT_ADJUDICATION",
        producer_version="1.0",
        policy_version="IIOS-HUMAN-ADJUDICATION-0.1",
    ),))
    assert human_registry.get("human-adjudicator-1").producer_type == "HUMAN_EXPERT_ADJUDICATION"


def test_context_identity_mismatch_blocks_admission():
    artifact = make_artifact()
    receipt = build_producer_receipt(receipt_id="r7", artifact=artifact, stage_id="QUALITY_ASSESSMENT", created_at="2026-10-08T00:00:00+00:00")
    bad_context = SemanticAdmissionContext(**{**context().__dict__, "symbol": "300750.SZ"})
    with pytest.raises(SemanticAdmissionError, match="symbol mismatch"):
        admit_semantic_artifact(artifact, receipt, context=bad_context, registry=registry())
