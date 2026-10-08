from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
from iios_mvp.semantic_producer_admission_v01 import (
    ProducerRegistry,
    SemanticAdmissionContext,
    SemanticAdmissionResult,
    admit_semantic_artifact,
    build_producer_receipt,
    build_semantic_artifact,
)

LLM_SEMANTIC_WORKBENCH_VERSION = "IIOS-LLM-SEMANTIC-WORKBENCH-0.1"

@dataclass(frozen=True)
class SemanticRequest:
    request_id: str
    run_id: str
    case_id: str
    market: str
    symbol: str
    company: str
    cutoff_date: str
    artifact_type: str
    input_refs: tuple[str, ...]
    input_hashes: tuple[str, ...]
    prompt: str
    created_at: str

class SemanticProducer(Protocol):
    producer_id: str
    producer_type: str
    producer_version: str
    policy_version: str

    def produce(self, request: SemanticRequest) -> Mapping[str, Any]: ...

@dataclass(frozen=True)
class WorkbenchResult:
    artifact: Mapping[str, Any]
    producer_receipt: Mapping[str, Any]
    admission: SemanticAdmissionResult

class LLMSemanticWorkbench:
    """B2 semantic boundary; producer output is untrusted until deterministic admission."""

    def __init__(self, *, orchestrator: CanonicalResearchOrchestrator, registry: ProducerRegistry) -> None:
        self._orchestrator = orchestrator
        self._registry = registry

    def run(self, *, producer: SemanticProducer, request: SemanticRequest, decision_relevance: str, facts: tuple[Mapping[str, Any], ...] = (), inferences: tuple[Mapping[str, Any], ...] = (), assumptions: tuple[Mapping[str, Any], ...] = (), uncertainties: tuple[Mapping[str, Any], ...] = ()) -> WorkbenchResult:
        self._orchestrator.authorize(request.run_id, Stage.SEMANTIC_PENDING)
        registration = self._registry.get(producer.producer_id)
        if producer.producer_type != 'LLM_SEMANTIC_PRODUCER':
            raise ValueError('LLM semantic workbench requires an LLM semantic producer')
        for field in ('producer_type', 'producer_version', 'policy_version'):
            if getattr(registration, field) != getattr(producer, field):
                raise ValueError(f'{field} is not registry-authorized')
        run = self._orchestrator.get(request.run_id)
        for field in ('case_id', 'market', 'symbol', 'cutoff_date'):
            if getattr(run, field) != getattr(request, field):
                raise ValueError(f'request {field} does not match canonical run')
        evidence_receipts = [receipt for receipt in run.stage_receipts if receipt.stage_id == Stage.EVIDENCE_ADMITTED.value]
        if not evidence_receipts:
            raise ValueError("semantic inputs require an admitted evidence receipt")
        admitted_pairs = {
            pair for pair in zip(
                evidence_receipts[-1].output_refs,
                evidence_receipts[-1].output_hashes,
                strict=True,
            )
        }
        requested_pairs = set(zip(request.input_refs, request.input_hashes, strict=True))
        if not requested_pairs or not requested_pairs.issubset(admitted_pairs):
            raise ValueError("semantic input lineage is not fully admitted")
        context = SemanticAdmissionContext(
            case_id=request.case_id,
            market=request.market,
            symbol=request.symbol,
            company=request.company,
            cutoff_date=request.cutoff_date,
            artifact_type=request.artifact_type,
            input_refs=request.input_refs,
            input_hashes=request.input_hashes,
            producer_id=producer.producer_id,
            producer_version=producer.producer_version,
            producer_type=producer.producer_type,
            policy_version=producer.policy_version,
        )
        output = producer.produce(request)
        if not isinstance(output, Mapping):
            raise ValueError('semantic producer must return a mapping')
        artifact = build_semantic_artifact(
            artifact_id=f'{request.run_id}:{request.request_id}',
            artifact_type=request.artifact_type,
            context=context,
            output=output,
            facts=facts,
            inferences=inferences,
            assumptions=assumptions,
            uncertainties=uncertainties,
            decision_relevance=decision_relevance,
            created_at=request.created_at,
        )
        producer_receipt = build_producer_receipt(
            receipt_id=f"{artifact['artifact_id']}:receipt",
            artifact=artifact,
            stage_id=request.artifact_type,
            created_at=request.created_at,
        )
        admission = admit_semantic_artifact(
            artifact, producer_receipt, context=context, registry=self._registry
        )
        self._orchestrator.transition(
            request.run_id,
            Stage.SEMANTIC_ADMITTED,
            artifact_ref=artifact['artifact_id'],
            input_refs=request.input_refs,
            input_hashes=request.input_hashes,
            output_hashes=(artifact['artifact_hash'],),
            producer_type=producer.producer_type,
            producer_version=producer.producer_version,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return WorkbenchResult(artifact=artifact, producer_receipt=producer_receipt, admission=admission)

__all__ = ['LLM_SEMANTIC_WORKBENCH_VERSION', 'SemanticRequest', 'SemanticProducer', 'WorkbenchResult', 'LLMSemanticWorkbench']
