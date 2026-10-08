from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping
import hashlib
import json

from iios_mvp.canonical_research_orchestrator import SEMANTIC_PRODUCER_TYPES, canonical_hash, is_sha256

SEMANTIC_ADMISSION_VERSION = "IIOS-SEMANTIC-PRODUCER-ADMISSION-0.1"
SEMANTIC_PRODUCER_RECEIPT_SCHEMA_VERSION = "IIOS-SEMANTIC-PRODUCER-RECEIPT-0.1"

SEMANTIC_ARTIFACT_TYPES = {
    "REALITY_INTERPRETATION",
    "TRUST_ASSESSMENT",
    "QUALITY_ASSESSMENT",
    "THESIS_ASSESSMENT",
    "VALUE_DRIVER_ASSESSMENT",
    "INDEPENDENT_FORECAST_REASONING",
    "VALUATION_PROPOSAL",
    "MIE_INTERPRETATION",
    "RISK_ASSESSMENT",
    "POSITIONING_ASSESSMENT",
}


class SemanticAdmissionError(ValueError):
    """Raised when semantic output is not canonically admissible."""


@dataclass(frozen=True)
class ProducerRegistration:
    producer_id: str
    producer_type: str
    producer_version: str
    policy_version: str
    active: bool = True


class ProducerRegistry:
    """Deterministic allow-list for semantic producer identity/version/policy."""

    def __init__(self, registrations: tuple[ProducerRegistration, ...] = ()) -> None:
        self._items: dict[str, ProducerRegistration] = {}
        for registration in registrations:
            self.register(registration)

    def register(self, registration: ProducerRegistration) -> None:
        if not registration.producer_id.strip():
            raise ValueError("producer_id is required")
        if registration.producer_type not in SEMANTIC_PRODUCER_TYPES:
            raise ValueError("producer_type is not an authorized semantic producer type")
        if not registration.producer_version.strip():
            raise ValueError("producer_version is required")
        if not registration.policy_version.strip():
            raise ValueError("policy_version is required")
        if registration.producer_id in self._items:
            raise ValueError("producer_id already registered")
        self._items[registration.producer_id] = registration

    def get(self, producer_id: str) -> ProducerRegistration:
        try:
            registration = self._items[producer_id]
        except KeyError as exc:
            raise SemanticAdmissionError("producer is not registered") from exc
        if not registration.active:
            raise SemanticAdmissionError("producer registration is inactive")
        return registration


@dataclass(frozen=True)
class SemanticAdmissionContext:
    case_id: str
    market: str
    symbol: str
    company: str
    cutoff_date: str
    artifact_type: str
    input_refs: tuple[str, ...]
    input_hashes: tuple[str, ...]
    producer_id: str
    producer_version: str
    producer_type: str
    policy_version: str


@dataclass(frozen=True)
class SemanticAdmissionResult:
    status: str
    artifact_hash: str
    producer_receipt_hash: str
    admission_hash: str


def normalize_datetime(value: str | None) -> str:
    parsed = datetime.now(timezone.utc) if value is None else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('created_at must include an explicit timezone')
    return parsed.astimezone(timezone.utc).isoformat()


def _ensure_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def _hash_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _without_hash(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def build_semantic_artifact(
    *,
    artifact_id: str,
    artifact_type: str,
    context: SemanticAdmissionContext,
    output: Mapping[str, Any],
    facts: tuple[Mapping[str, Any], ...] = (),
    inferences: tuple[Mapping[str, Any], ...] = (),
    assumptions: tuple[Mapping[str, Any], ...] = (),
    uncertainties: tuple[Mapping[str, Any], ...] = (),
    decision_relevance: str,
    created_at: str,
) -> dict[str, Any]:
    if not artifact_id.strip():
        raise ValueError("artifact_id is required")
    if artifact_type not in SEMANTIC_ARTIFACT_TYPES:
        raise ValueError("unsupported semantic artifact type")
    if artifact_type != context.artifact_type:
        raise ValueError("artifact_type does not match admission context")
    if context.producer_type not in SEMANTIC_PRODUCER_TYPES:
        raise ValueError("unauthorized semantic producer type")
    if not isinstance(output, Mapping):
        raise ValueError("output must be a mapping")
    _ensure_date(context.cutoff_date)
    created = normalize_datetime(created_at)
    core: dict[str, Any] = {
        'artifact_id': artifact_id,
        'artifact_type': artifact_type,
        'schema_version': 'IIOS-LLM-SEMANTIC-ARTIFACT-0.1',
        'case_id': context.case_id,
        'market': context.market,
        'symbol': context.symbol,
        'company': context.company,
        'cutoff_date': context.cutoff_date,
        'producer_type': context.producer_type,
        'producer_id': context.producer_id,
        'producer_version': context.producer_version,
        'policy_version': context.policy_version,
        'input_refs': list(context.input_refs),
        'input_hashes': list(context.input_hashes),
        'output': dict(output),
        'facts': [dict(item) for item in facts],
        'inferences': [dict(item) for item in inferences],
        'assumptions': [dict(item) for item in assumptions],
        'uncertainties': [dict(item) for item in uncertainties],
        'decision_relevance': decision_relevance,
        'created_at': created,
    }
    return {**core, 'artifact_hash': canonical_hash(core)}


def build_producer_receipt(*, receipt_id: str, artifact: Mapping[str, Any], stage_id: str, created_at: str) -> dict[str, Any]:
    required = (
        'artifact_id', 'artifact_type', 'case_id', 'market', 'symbol', 'company',
        'cutoff_date', 'producer_type', 'producer_id', 'producer_version', 'policy_version',
        'input_refs', 'input_hashes', 'output', 'artifact_hash',
    )
    missing = [field for field in required if field not in artifact]
    if missing:
        raise ValueError(f"artifact missing fields: {', '.join(missing)}")
    artifact_hash = artifact['artifact_hash']
    if not is_sha256(artifact_hash):
        raise ValueError('artifact_hash must be lowercase SHA-256')
    if canonical_hash(_without_hash(artifact, 'artifact_hash')) != artifact_hash:
        raise ValueError('artifact_hash does not match artifact bytes')
    core = {
        'schema_version': SEMANTIC_PRODUCER_RECEIPT_SCHEMA_VERSION,
        'receipt_id': receipt_id,
        'artifact_id': artifact['artifact_id'],
        'artifact_type': artifact['artifact_type'],
        'stage_id': stage_id,
        'case_id': artifact['case_id'],
        'market': artifact['market'],
        'symbol': artifact['symbol'],
        'company': artifact['company'],
        'cutoff_date': artifact['cutoff_date'],
        'producer_type': artifact['producer_type'],
        'producer_id': artifact['producer_id'],
        'producer_version': artifact['producer_version'],
        'policy_version': artifact['policy_version'],
        'input_refs': list(artifact['input_refs']),
        'input_hashes': list(artifact['input_hashes']),
        'artifact_hash': artifact_hash,
        'output_hash': _hash_json(artifact['output']),
        'status': 'PRODUCED',
        'created_at': normalize_datetime(created_at),
    }
    return {**core, 'receipt_hash': canonical_hash(core)}


def admit_semantic_artifact(artifact: Mapping[str, Any], producer_receipt: Mapping[str, Any], *, context: SemanticAdmissionContext, registry: ProducerRegistry) -> SemanticAdmissionResult:
    required_artifact_fields = (
        'artifact_id', 'artifact_type', 'schema_version', 'case_id', 'market', 'symbol',
        'company', 'cutoff_date', 'producer_type', 'producer_id', 'producer_version',
        'policy_version', 'input_refs', 'input_hashes', 'output', 'facts', 'inferences',
        'assumptions', 'uncertainties', 'decision_relevance', 'created_at', 'artifact_hash',
    )
    missing = [field for field in required_artifact_fields if field not in artifact]
    if missing:
        raise SemanticAdmissionError(f"artifact missing required fields: {', '.join(missing)}")
    if artifact['schema_version'] != 'IIOS-LLM-SEMANTIC-ARTIFACT-0.1':
        raise SemanticAdmissionError('unsupported semantic artifact schema')
    if artifact['artifact_type'] != context.artifact_type:
        raise SemanticAdmissionError('artifact_type mismatch')
    for field in ('case_id', 'market', 'symbol', 'company', 'cutoff_date', 'producer_type', 'producer_id', 'producer_version', 'policy_version'):
        if artifact[field] != getattr(context, field):
            raise SemanticAdmissionError(f'{field} mismatch')
    if tuple(artifact['input_refs']) != context.input_refs:
        raise SemanticAdmissionError('input_refs lineage mismatch')
    if tuple(artifact['input_hashes']) != context.input_hashes:
        raise SemanticAdmissionError('input_hashes lineage mismatch')
    if len(artifact['input_refs']) == 0 or len(artifact['input_refs']) != len(artifact['input_hashes']):
        raise SemanticAdmissionError('input lineage must be non-empty and aligned')
    if any(not is_sha256(value) for value in artifact['input_hashes']):
        raise SemanticAdmissionError('input hashes must be lowercase SHA-256')

    registration = registry.get(artifact['producer_id'])
    if registration.producer_type != artifact['producer_type']:
        raise SemanticAdmissionError('registered producer_type mismatch')
    if registration.producer_version != artifact['producer_version']:
        raise SemanticAdmissionError('registered producer_version mismatch')
    if registration.policy_version != artifact['policy_version']:
        raise SemanticAdmissionError('registered policy_version mismatch')

    artifact_hash = artifact['artifact_hash']
    if not is_sha256(artifact_hash):
        raise SemanticAdmissionError('artifact_hash must be lowercase SHA-256')
    if canonical_hash(_without_hash(artifact, 'artifact_hash')) != artifact_hash:
        raise SemanticAdmissionError('artifact_hash integrity failure')

    required_receipt_fields = (
        'schema_version', 'receipt_id', 'artifact_id', 'artifact_type', 'stage_id',
        'case_id', 'market', 'symbol', 'company', 'cutoff_date', 'producer_type',
        'producer_id', 'producer_version', 'policy_version', 'input_refs', 'input_hashes',
        'artifact_hash', 'output_hash', 'status', 'created_at', 'receipt_hash',
    )
    missing_receipt = [field for field in required_receipt_fields if field not in producer_receipt]
    if missing_receipt:
        raise SemanticAdmissionError(f"producer receipt missing required fields: {', '.join(missing_receipt)}")
    if producer_receipt['schema_version'] != SEMANTIC_PRODUCER_RECEIPT_SCHEMA_VERSION:
        raise SemanticAdmissionError('unsupported producer receipt schema')
    if not is_sha256(producer_receipt['receipt_hash']):
        raise SemanticAdmissionError('receipt_hash must be lowercase SHA-256')
    if canonical_hash(_without_hash(producer_receipt, 'receipt_hash')) != producer_receipt['receipt_hash']:
        raise SemanticAdmissionError('producer receipt integrity failure')
    for field in ('artifact_id', 'artifact_type', 'case_id', 'market', 'symbol', 'company', 'cutoff_date', 'producer_type', 'producer_id', 'producer_version', 'policy_version', 'input_refs', 'input_hashes', 'artifact_hash'):
        if producer_receipt[field] != artifact[field]:
            raise SemanticAdmissionError(f'producer receipt mismatch: {field}')
    if producer_receipt['status'] != 'PRODUCED':
        raise SemanticAdmissionError('producer receipt status is not PRODUCED')
    if producer_receipt['stage_id'] != artifact['artifact_type']:
        raise SemanticAdmissionError('producer receipt stage_id must bind artifact_type')
    if producer_receipt['output_hash'] != _hash_json(artifact['output']):
        raise SemanticAdmissionError('producer receipt output_hash mismatch')

    admission_core = {
        'admission_version': SEMANTIC_ADMISSION_VERSION,
        'status': 'ADMITTED',
        'artifact_hash': artifact_hash,
        'producer_receipt_hash': producer_receipt['receipt_hash'],
        'producer_id': registration.producer_id,
        'producer_version': registration.producer_version,
        'policy_version': registration.policy_version,
        'case_id': context.case_id,
        'artifact_type': context.artifact_type,
    }
    return SemanticAdmissionResult(
        status='ADMITTED',
        artifact_hash=artifact_hash,
        producer_receipt_hash=producer_receipt['receipt_hash'],
        admission_hash=canonical_hash(admission_core),
    )


__all__ = [
    'SEMANTIC_ADMISSION_VERSION',
    'SEMANTIC_PRODUCER_RECEIPT_SCHEMA_VERSION',
    'SemanticAdmissionError',
    'ProducerRegistration',
    'ProducerRegistry',
    'SemanticAdmissionContext',
    'SemanticAdmissionResult',
    'build_semantic_artifact',
    'build_producer_receipt',
    'admit_semantic_artifact',
]
