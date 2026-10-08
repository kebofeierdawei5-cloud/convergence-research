from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestAdmissionResult,
    RequestInterpreter,
    RequestInterpreterRegistry,
    admit_natural_language_request,
)
from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
from iios_mvp.decision_admission import admit_canonical_decision
from iios_mvp.decision_lifecycle_production import build_decision_revision, validate_decision_revision
from iios_mvp.decision_upstream_admission_v03 import DECISION_UPSTREAM_ADMISSION_V02
from iios_mvp.investment_core_contract_v03 import decide_v03
from iios_mvp.llm_semantic_workbench_v01 import (
    LLMSemanticWorkbench,
    SemanticProducer,
    SemanticRequest,
    WorkbenchResult,
)
from iios_mvp.semantic_producer_admission_v01 import ProducerRegistry

B2E_CONTRACT_VERSION = "IIOS-B2-E-NL-SEMANTIC-DECISION-E2E-0.1"
B2E_STATUS_ADMITTED = "ADMITTED"
FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS = frozenset(
    {
        "action",
        "decision_status",
        "new_capital_allowed",
        "human_approval_required",
        "auto_execution",
        "capital_effect",
        "decision_admission",
        "decision_precedence_rule_id",
        "decision_pre_admission_action",
    }
)


class B2EE2EError(ValueError):
    """Raised when the B2-E natural-language-to-decision boundary is invalid."""


@dataclass(frozen=True)
class B2EConformanceResult:
    request_admission: RequestAdmissionResult
    semantic: WorkbenchResult
    decision_admission: Mapping[str, Any]
    decision_revision: Mapping[str, Any]
    binding_receipt: Mapping[str, Any]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _assert_no_authority_fields(value: Mapping[str, Any]) -> None:
    output = value.get("output")
    if not isinstance(output, Mapping):
        raise B2EE2EError("semantic artifact output must be an object")
    present = sorted(FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS.intersection(output.keys()))
    if present:
        raise B2EE2EError(
            "semantic producer attempted decision authority fields: " + ", ".join(present)
        )


def _build_snapshot(
    *,
    case: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": dict(case),
        "decision": dict(decision),
    }
    return {**core, "snapshot_hash": sha256(core)}


def _transition_pre_decision(
    orchestrator: CanonicalResearchOrchestrator,
    *,
    run_id: str,
    case: Mapping[str, Any],
    created_at: str,
) -> None:
    forecast = case.get("forecast")
    valuation = case.get("valuation")
    if not isinstance(forecast, Mapping) or not isinstance(valuation, Mapping):
        raise B2EE2EError("canonical case forecast and valuation are required for B2-E")

    orchestrator.transition(
        run_id,
        Stage.FORECAST_PENDING,
        created_at=created_at,
    )
    forecast_hash = sha256(forecast)
    orchestrator.transition(
        run_id,
        Stage.FORECAST_ADMITTED,
        output_refs=("forecast",),
        output_hashes=(forecast_hash,),
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.VALUATION_PENDING,
        created_at=created_at,
    )
    valuation_hash = sha256(valuation)
    orchestrator.transition(
        run_id,
        Stage.VALUATION_ADMITTED,
        output_refs=("valuation",),
        output_hashes=(valuation_hash,),
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.DECISION_PENDING,
        created_at=created_at,
    )


def run_b2e_conformance(
    *,
    raw_request: str,
    request_id: str,
    run_id: str,
    created_at: str,
    request_interpreter: RequestInterpreter,
    request_registry: RequestInterpreterRegistry,
    semantic_producer: SemanticProducer,
    producer_registry: ProducerRegistry,
    company: str,
    evidence_refs: tuple[str, ...],
    evidence_hashes: tuple[str, ...],
    artifact_type: str,
    semantic_prompt: str,
    semantic_facts: tuple[Mapping[str, Any], ...] = (),
    semantic_inferences: tuple[Mapping[str, Any], ...] = (),
    semantic_assumptions: tuple[Mapping[str, Any], ...] = (),
    semantic_uncertainties: tuple[Mapping[str, Any], ...] = (),
    decision_relevance: str,
    case: Mapping[str, Any],
    current_price_resolver: Any,
    independent_forecast_resolver: Any,
    upstream_authority_resolver: Any,
    valuation_output_resolver: Any,
) -> B2EConformanceResult:
    orchestrator = CanonicalResearchOrchestrator()
    admitted = admit_natural_language_request(
        orchestrator=orchestrator,
        registry=request_registry,
        interpreter=request_interpreter,
        request_id=request_id,
        run_id=run_id,
        raw_request=raw_request,
        created_at=created_at,
    )

    if sha256(admitted.research_case) != admitted.case_hash:
        raise B2EE2EError("research case hash binding failed")
    if admitted.case_hash != sha256(case):
        raise B2EE2EError("canonical case supplied to B2-E does not match admitted Research Case")

    orchestrator.transition(
        run_id,
        Stage.EVIDENCE_PENDING,
        created_at=created_at,
    )
    if len(evidence_refs) == 0 or len(evidence_refs) != len(evidence_hashes):
        raise B2EE2EError("evidence lineage must contain matching non-empty references and hashes")
    orchestrator.transition(
        run_id,
        Stage.EVIDENCE_ADMITTED,
        output_refs=evidence_refs,
        output_hashes=evidence_hashes,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.SEMANTIC_PENDING,
        created_at=created_at,
    )

    semantic_request = SemanticRequest(
        request_id=request_id,
        run_id=run_id,
        case_id=admitted.case_id,
        market=admitted.research_case["request"]["market"],
        symbol=admitted.research_case["request"]["symbol"],
        company=company,
        cutoff_date=admitted.research_case["temporal_scope"]["cutoff_date"],
        artifact_type=artifact_type,
        input_refs=evidence_refs,
        input_hashes=evidence_hashes,
        prompt=semantic_prompt,
        created_at=created_at,
    )
    semantic = LLMSemanticWorkbench(
        orchestrator=orchestrator,
        registry=producer_registry,
    ).run(
        producer=semantic_producer,
        request=semantic_request,
        decision_relevance=decision_relevance,
        facts=semantic_facts,
        inferences=semantic_inferences,
        assumptions=semantic_assumptions,
        uncertainties=semantic_uncertainties,
    )
    _assert_no_authority_fields(semantic.artifact)

    _transition_pre_decision(
        orchestrator,
        run_id=run_id,
        case=case,
        created_at=created_at,
    )

    canonical_decision = decide_v03(
        dict(case),
        current_price_resolver=current_price_resolver,
        independent_forecast_resolver=independent_forecast_resolver,
        upstream_authority_resolver=upstream_authority_resolver,
        valuation_output_resolver=valuation_output_resolver,
    )
    snapshot = _build_snapshot(case=case, decision=canonical_decision)
    decision_admission = admit_canonical_decision(
        case=case,
        snapshot=snapshot,
        current_price_resolver=current_price_resolver,
        independent_forecast_resolver=independent_forecast_resolver,
        upstream_authority_resolver=upstream_authority_resolver,
        valuation_output_resolver=valuation_output_resolver,
    )

    orchestrator.transition(
        run_id,
        Stage.DECISION_ADMITTED,
        output_refs=(decision_admission["admission_record_hash"],),
        output_hashes=(decision_admission["admission_record_hash"],),
        input_refs=(semantic.artifact["artifact_id"],),
        input_hashes=(semantic.artifact["artifact_hash"],),
        created_at=created_at,
    )

    revision = build_decision_revision(
        decision_series_id=f"{admitted.case_id}:{admitted.research_case['request']['market']}:{admitted.research_case['request']['symbol']}",
        revision=1,
        snapshot=snapshot,
        run_id=run_id,
        decision_admission=decision_admission,
    )
    validate_decision_revision(
        revision,
        case_id=admitted.case_id,
        cutoff_date=admitted.research_case["temporal_scope"]["cutoff_date"],
    )

    core = {
        "schema_version": B2E_CONTRACT_VERSION,
        "status": B2E_STATUS_ADMITTED,
        "run_id": run_id,
        "request_id": request_id,
        "case_id": admitted.case_id,
        "market": admitted.research_case["request"]["market"],
        "symbol": admitted.research_case["request"]["symbol"],
        "cutoff_date": admitted.research_case["temporal_scope"]["cutoff_date"],
        "raw_request_sha256": admitted.request_receipt["raw_request_sha256"],
        "request_receipt_hash": admitted.request_receipt["receipt_hash"],
        "case_hash": admitted.case_hash,
        "semantic_artifact_hash": semantic.artifact["artifact_hash"],
        "semantic_admission_hash": semantic.admission.admission_hash,
        "decision_admission_hash": decision_admission["admission_record_hash"],
        "decision_revision_hash": revision["revision_hash"],
        "action": decision_admission["canonical_action"],
        "human_approval_required": True,
        "auto_execution": False,
        "authority_boundary": {
            "semantic_producer_can_decide": False,
            "canonical_decision_kernel_is_authoritative": True,
            "human_approval_is_required": True,
            "automatic_execution_is_forbidden": True,
        },
        "created_at": created_at,
    }
    receipt = {**core, "binding_receipt_hash": sha256(core)}

    return B2EConformanceResult(
        request_admission=admitted,
        semantic=semantic,
        decision_admission=decision_admission,
        decision_revision=revision,
        binding_receipt=receipt,
    )


__all__ = [
    "B2E_CONTRACT_VERSION",
    "B2EE2EError",
    "B2EConformanceResult",
    "FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS",
    "run_b2e_conformance",
    "sha256",
]
