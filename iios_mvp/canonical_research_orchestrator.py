from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Mapping
import hashlib
import json

ORCHESTRATOR_VERSION = "IIOS-CANONICAL-RESEARCH-ORCHESTRATOR-0.1"
RUN_RECEIPT_SCHEMA_VERSION = "IIOS-RUN-RECEIPT-0.1"
SEMANTIC_PRODUCER_TYPES = {"LLM_SEMANTIC_PRODUCER", "HUMAN_EXPERT_ADJUDICATION"}


class RunStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    NON_CANONICAL = "NON_CANONICAL"
    FAILED = "FAILED"


class Stage(str, Enum):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REQUEST_ADMITTED = "REQUEST_ADMITTED"
    CASE_CREATED = "CASE_CREATED"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    EVIDENCE_ADMITTED = "EVIDENCE_ADMITTED"
    SEMANTIC_PENDING = "SEMANTIC_PENDING"
    SEMANTIC_ADMITTED = "SEMANTIC_ADMITTED"
    FORECAST_PENDING = "FORECAST_PENDING"
    FORECAST_ADMITTED = "FORECAST_ADMITTED"
    VALUATION_PENDING = "VALUATION_PENDING"
    VALUATION_ADMITTED = "VALUATION_ADMITTED"
    DECISION_PENDING = "DECISION_PENDING"
    DECISION_ADMITTED = "DECISION_ADMITTED"
    HUMAN_APPROVAL_PENDING = "HUMAN_APPROVAL_PENDING"
    PUBLISHED = "PUBLISHED"
    REPORTED = "REPORTED"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    NON_CANONICAL = "NON_CANONICAL"
    FAILED = "FAILED"


REQUIRED_PREDECESSOR: dict[Stage, Stage | None] = {
    Stage.REQUEST_RECEIVED: None,
    Stage.REQUEST_ADMITTED: Stage.REQUEST_RECEIVED,
    Stage.CASE_CREATED: Stage.REQUEST_ADMITTED,
    Stage.EVIDENCE_PENDING: Stage.CASE_CREATED,
    Stage.EVIDENCE_ADMITTED: Stage.EVIDENCE_PENDING,
    Stage.SEMANTIC_PENDING: Stage.EVIDENCE_ADMITTED,
    Stage.SEMANTIC_ADMITTED: Stage.SEMANTIC_PENDING,
    Stage.FORECAST_PENDING: Stage.SEMANTIC_ADMITTED,
    Stage.FORECAST_ADMITTED: Stage.FORECAST_PENDING,
    Stage.VALUATION_PENDING: Stage.FORECAST_ADMITTED,
    Stage.VALUATION_ADMITTED: Stage.VALUATION_PENDING,
    Stage.DECISION_PENDING: Stage.VALUATION_ADMITTED,
    Stage.DECISION_ADMITTED: Stage.DECISION_PENDING,
    Stage.HUMAN_APPROVAL_PENDING: Stage.DECISION_ADMITTED,
    Stage.PUBLISHED: Stage.HUMAN_APPROVAL_PENDING,
    Stage.REPORTED: Stage.PUBLISHED,
    Stage.COMPLETE: Stage.REPORTED,
}

ARTIFACT_GATED = {
    Stage.EVIDENCE_ADMITTED,
    Stage.SEMANTIC_ADMITTED,
    Stage.FORECAST_ADMITTED,
    Stage.VALUATION_ADMITTED,
    Stage.DECISION_ADMITTED,
    Stage.PUBLISHED,
    Stage.REPORTED,
}


@dataclass(frozen=True)
class StageReceipt:
    stage_id: str
    stage_version: str
    input_refs: tuple[str, ...]
    input_hashes: tuple[str, ...]
    output_refs: tuple[str, ...]
    output_hashes: tuple[str, ...]
    producer_type: str
    producer_version: str
    status: str
    cutoff_date: str
    created_at: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_version": self.stage_version,
            "input_refs": list(self.input_refs),
            "input_hashes": list(self.input_hashes),
            "output_refs": list(self.output_refs),
            "output_hashes": list(self.output_hashes),
            "producer_type": self.producer_type,
            "producer_version": self.producer_version,
            "status": self.status,
            "cutoff_date": self.cutoff_date,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RunEnvelope:
    run_id: str
    case_id: str
    market: str
    symbol: str
    cutoff_date: str
    as_of_date: str
    request_type: str
    orchestrator_version: str = ORCHESTRATOR_VERSION
    research_case_hash: str | None = None
    stage_state: Stage = Stage.REQUEST_RECEIVED
    run_status: RunStatus = RunStatus.IN_PROGRESS
    artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    stage_receipts: tuple[StageReceipt, ...] = field(default_factory=tuple)
    non_canonical_reason: str | None = None
    created_at: str = ""


class CanonicalResearchOrchestrator:
    """B1 control-plane authority; it does not infer economics or make decisions."""

    def __init__(self) -> None:
        self._runs: dict[str, RunEnvelope] = {}

    def start(
        self, *, run_id: str, case_id: str, market: str, symbol: str,
        cutoff_date: str, as_of_date: str, request_type: str = "INVESTMENT_DECISION",
        research_case_hash: str | None = None, created_at: str | None = None,
    ) -> RunEnvelope:
        if run_id in self._runs:
            raise ValueError("run_id already exists")
        for name, value in (("run_id", run_id), ("case_id", case_id), ("market", market), ("symbol", symbol), ("request_type", request_type)):
            if not str(value).strip():
                raise ValueError(f"{name} is required")
        cutoff = date.fromisoformat(cutoff_date)
        as_of = date.fromisoformat(as_of_date)
        if as_of > cutoff:
            raise ValueError("as_of_date cannot be later than cutoff_date")
        if research_case_hash is not None and not is_sha256(research_case_hash):
            raise ValueError("research_case_hash must be lowercase SHA-256")
        envelope = RunEnvelope(
            run_id=run_id, case_id=case_id, market=str(market).upper(), symbol=str(symbol).upper(),
            cutoff_date=cutoff.isoformat(), as_of_date=as_of.isoformat(), request_type=request_type,
            research_case_hash=research_case_hash, created_at=normalize_datetime(created_at),
        )
        self._runs[run_id] = envelope
        return envelope

    def transition(self, run_id: str, next_stage: Stage, *, artifact_ref: str | None = None,
                   input_refs: tuple[str, ...] = (), input_hashes: tuple[str, ...] = (),
                   output_refs: tuple[str, ...] = (), output_hashes: tuple[str, ...] = (),
                   producer_type: str = "CODE", producer_version: str = ORCHESTRATOR_VERSION,
                   status: str = "PASS", created_at: str | None = None) -> RunEnvelope:
        envelope = self._require(run_id)
        if envelope.run_status != RunStatus.IN_PROGRESS:
            raise ValueError("terminal run cannot transition")
        expected = REQUIRED_PREDECESSOR.get(next_stage)
        if expected is None and next_stage != Stage.REQUEST_RECEIVED:
            raise ValueError(f"unsupported transition target: {next_stage.value}")
        if expected is not None and envelope.stage_state != expected:
            raise ValueError(f"stage bypass forbidden: current={envelope.stage_state.value}, required={expected.value}")
        outputs = tuple(output_refs) + ((artifact_ref,) if artifact_ref else ())
        if next_stage in ARTIFACT_GATED and not outputs:
            raise ValueError(f"{next_stage.value} requires an admitted output artifact reference")
        if next_stage == Stage.SEMANTIC_ADMITTED and producer_type not in SEMANTIC_PRODUCER_TYPES:
            raise ValueError("SEMANTIC_ADMITTED requires an authorized semantic producer type")
        if next_stage in {Stage.PUBLISHED, Stage.REPORTED} and producer_type != "CODE":
            raise ValueError(f"{next_stage.value} must be emitted by CODE")
        if any(not is_sha256(value) for value in tuple(input_hashes) + tuple(output_hashes)):
            raise ValueError("stage input/output hashes must be lowercase SHA-256 values")
        receipt = StageReceipt(
            stage_id=next_stage.value, stage_version=producer_version,
            input_refs=tuple(input_refs), input_hashes=tuple(input_hashes),
            output_refs=outputs, output_hashes=tuple(output_hashes),
            producer_type=producer_type, producer_version=producer_version,
            status=status, cutoff_date=envelope.cutoff_date, created_at=normalize_datetime(created_at),
        )
        refs = envelope.artifact_refs + tuple(x for x in outputs if x not in envelope.artifact_refs)
        updated = RunEnvelope(**{**envelope.__dict__, "stage_state": next_stage,
                                 "run_status": RunStatus.COMPLETE if next_stage == Stage.COMPLETE else RunStatus.IN_PROGRESS,
                                 "artifact_refs": refs, "stage_receipts": envelope.stage_receipts + (receipt,)})
        self._runs[run_id] = updated
        return updated

    def authorize(self, run_id: str, required_stage: Stage) -> RunEnvelope:
        envelope = self._require(run_id)
        if envelope.run_status != RunStatus.IN_PROGRESS:
            raise ValueError("canonical execution authorization requires an active run")
        if envelope.stage_state != required_stage:
            raise ValueError(f"canonical stage authorization failed: current={envelope.stage_state.value}, required={required_stage.value}")
        return envelope

    def block(self, run_id: str, reason: str) -> RunEnvelope:
        envelope = self._require(run_id)
        if envelope.run_status != RunStatus.IN_PROGRESS:
            raise ValueError("terminal run cannot be blocked")
        if not reason.strip():
            raise ValueError("block reason is required")
        updated = RunEnvelope(**{**envelope.__dict__, "stage_state": Stage.BLOCKED,
                                 "run_status": RunStatus.BLOCKED, "non_canonical_reason": reason})
        self._runs[run_id] = updated
        return updated

    def classify_direct_execution_as_non_canonical(self, *, run_id: str, reason: str) -> RunEnvelope:
        envelope = self._require(run_id)
        if not reason.strip():
            raise ValueError("non-canonical reason is required")
        updated = RunEnvelope(**{**envelope.__dict__, "stage_state": Stage.NON_CANONICAL,
                                 "run_status": RunStatus.NON_CANONICAL, "non_canonical_reason": reason})
        self._runs[run_id] = updated
        return updated

    def build_run_receipt(self, run_id: str, *, evidence_manifest_hash: str,
                          semantic_artifact_hashes: tuple[str, ...], forecast_admission_hash: str,
                          valuation_admission_hash: str, return_hash: str, risk_portfolio_hash: str,
                          decision_admission_hash: str, decision_revision: int,
                          publication_hash: str, report_hash: str) -> dict[str, Any]:
        envelope = self._require(run_id)
        if envelope.run_status != RunStatus.COMPLETE:
            raise ValueError("complete IIOS_RUN_RECEIPT requires a COMPLETE run")
        all_hashes = (evidence_manifest_hash, *semantic_artifact_hashes, forecast_admission_hash,
                      valuation_admission_hash, return_hash, risk_portfolio_hash,
                      decision_admission_hash, publication_hash, report_hash)
        if any(not is_sha256(value) for value in all_hashes):
            raise ValueError("all receipt hashes must be lowercase SHA-256 values")
        if decision_revision < 1:
            raise ValueError("decision_revision must be >= 1")
        core = {
            "schema_version": RUN_RECEIPT_SCHEMA_VERSION,
            "run_id": envelope.run_id, "case_id": envelope.case_id,
            "market": envelope.market, "symbol": envelope.symbol,
            "cutoff_date": envelope.cutoff_date, "as_of_date": envelope.as_of_date,
            "orchestrator_version": envelope.orchestrator_version,
            "research_case_hash": envelope.research_case_hash,
            "evidence_manifest_hash": evidence_manifest_hash,
            "semantic_artifact_hashes": list(semantic_artifact_hashes),
            "forecast_admission_hash": forecast_admission_hash,
            "valuation_admission_hash": valuation_admission_hash,
            "return_hash": return_hash, "risk_portfolio_hash": risk_portfolio_hash,
            "decision_admission_hash": decision_admission_hash, "decision_revision": decision_revision,
            "publication_hash": publication_hash, "report_hash": report_hash,
            "run_status": envelope.run_status.value,
        }
        return {**core, "receipt_hash": canonical_hash(core)}

    def get(self, run_id: str) -> RunEnvelope:
        return self._require(run_id)

    def _require(self, run_id: str) -> RunEnvelope:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise ValueError("unknown run_id") from exc


def normalize_datetime(value: str | None) -> str:
    parsed = datetime.now(timezone.utc) if value is None else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("created_at must include an explicit timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def is_sha256(value: str | None) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def canonical_hash(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


__all__ = ["ORCHESTRATOR_VERSION", "RUN_RECEIPT_SCHEMA_VERSION", "SEMANTIC_PRODUCER_TYPES",
           "RunStatus", "Stage", "StageReceipt", "RunEnvelope", "CanonicalResearchOrchestrator", "canonical_hash"]
