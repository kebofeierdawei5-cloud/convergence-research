from __future__ import annotations

"""Durable, fail-closed authorization for canonical IIOS run stages.

This module binds write operations to the existing CanonicalResearchOrchestrator
stage chain. It does not decide economics. Its records are integrity-checked,
case/cutoff-bound and replayed from append-only stage receipts.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from .canonical_research_orchestrator import (
    ORCHESTRATOR_VERSION,
    CanonicalResearchOrchestrator,
    RunEnvelope,
    RunStatus,
    Stage,
    StageReceipt,
    canonical_hash,
    is_sha256,
)

RUN_STATE_SCHEMA_VERSION = "IIOS-CANONICAL-RUN-STATE-0.1"
RUN_STAGE_AUTH_SCHEMA_VERSION = "IIOS-RUN-STAGE-AUTH-0.1"
RUN_RECEIPT_V02_SCHEMA_VERSION = "IIOS-RUN-RECEIPT-0.2"
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


class CanonicalRunAuthorizationError(ValueError):
    """Canonical run evidence is absent, invalid, stale, or not authorized."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        raise CanonicalRunAuthorizationError("run_id is invalid")
    return run_id


def run_state_path(root: str | Path, run_id: str) -> Path:
    safe = _safe_run_id(run_id)
    return Path(root) / "canonical-runs" / f"{safe}.run.json"


def run_receipt_path(root: str | Path, run_id: str) -> Path:
    safe = _safe_run_id(run_id)
    return Path(root) / f"{safe}.run-receipt.json"


def _stage_receipt_mapping(receipt: StageReceipt) -> dict[str, Any]:
    return receipt.as_mapping()


def _envelope_mapping(envelope: RunEnvelope) -> dict[str, Any]:
    return {
        "run_id": envelope.run_id,
        "case_id": envelope.case_id,
        "market": envelope.market,
        "symbol": envelope.symbol,
        "cutoff_date": envelope.cutoff_date,
        "as_of_date": envelope.as_of_date,
        "request_type": envelope.request_type,
        "orchestrator_version": envelope.orchestrator_version,
        "research_case_hash": envelope.research_case_hash,
        "stage_state": envelope.stage_state.value,
        "run_status": envelope.run_status.value,
        "artifact_refs": list(envelope.artifact_refs),
        "stage_receipts": [_stage_receipt_mapping(x) for x in envelope.stage_receipts],
        "non_canonical_reason": envelope.non_canonical_reason,
        "created_at": envelope.created_at,
    }


def _make_record(envelope: RunEnvelope, metadata: Mapping[str, Any]) -> dict[str, Any]:
    envelope_payload = _envelope_mapping(envelope)
    receipt_hashes = [
        canonical_hash(item) for item in envelope_payload["stage_receipts"]
    ]
    core = {
        "schema_version": RUN_STATE_SCHEMA_VERSION,
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "envelope": envelope_payload,
        "request_metadata": dict(metadata),
        "stage_receipt_hashes": receipt_hashes,
        "stage_chain_hash": canonical_hash({"stage_receipt_hashes": receipt_hashes}),
    }
    return {**core, "state_hash": canonical_hash(core)}


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    os.replace(temporary, path)


def _same_prefix(previous: Mapping[str, Any], current: Mapping[str, Any]) -> None:
    old_env = previous["envelope"]
    new_env = current["envelope"]
    old_receipts = old_env["stage_receipts"]
    new_receipts = new_env["stage_receipts"]
    if len(new_receipts) < len(old_receipts):
        raise CanonicalRunAuthorizationError("stage receipt history cannot shrink")
    if new_receipts[:len(old_receipts)] != old_receipts:
        raise CanonicalRunAuthorizationError("stage receipt history is append-only")
    old_meta = previous["request_metadata"]
    new_meta = current["request_metadata"]
    for field in ("request_id", "raw_request_sha256", "request_receipt_hash",
                  "normalized_request_sha256"):
        if old_meta.get(field) not in (None, "") and new_meta.get(field) != old_meta[field]:
            raise CanonicalRunAuthorizationError("request metadata cannot be rewritten")


def _replay_record(record: Mapping[str, Any]) -> CanonicalResearchOrchestrator:
    env = record["envelope"]
    orchestrator = CanonicalResearchOrchestrator()
    orchestrator.start(
        run_id=env["run_id"],
        case_id=env["case_id"],
        market=env["market"],
        symbol=env["symbol"],
        cutoff_date=env["cutoff_date"],
        as_of_date=env["as_of_date"],
        request_type=env["request_type"],
        research_case_hash=env["research_case_hash"],
        created_at=env["created_at"],
    )
    for raw in env["stage_receipts"]:
        orchestrator.transition(
            env["run_id"],
            Stage(raw["stage_id"]),
            input_refs=tuple(raw["input_refs"]),
            input_hashes=tuple(raw["input_hashes"]),
            output_refs=tuple(raw["output_refs"]),
            output_hashes=tuple(raw["output_hashes"]),
            producer_type=raw["producer_type"],
            producer_version=raw["producer_version"],
            status=raw["status"],
            created_at=raw["created_at"],
        )
    replayed = _envelope_mapping(orchestrator.get(env["run_id"]))
    expected = dict(env)
    # Terminal/non-canonical state changes do not create an ordinary stage receipt.
    if expected["run_status"] in {RunStatus.BLOCKED.value, RunStatus.NON_CANONICAL.value, RunStatus.FAILED.value}:
        replayed["stage_state"] = expected["stage_state"]
        replayed["run_status"] = expected["run_status"]
        replayed["non_canonical_reason"] = expected["non_canonical_reason"]
    if replayed != expected:
        raise CanonicalRunAuthorizationError("persisted envelope does not replay from its receipts")
    return orchestrator


def validate_run_state_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise CanonicalRunAuthorizationError("canonical run state must be an object")
    required = {
        "schema_version", "orchestrator_version", "envelope",
        "request_metadata", "stage_receipt_hashes", "stage_chain_hash", "state_hash",
    }
    if set(record) != required or record["schema_version"] != RUN_STATE_SCHEMA_VERSION:
        raise CanonicalRunAuthorizationError("canonical run state schema/version mismatch")
    core = {k: record[k] for k in required if k != "state_hash"}
    if record["state_hash"] != canonical_hash(core):
        raise CanonicalRunAuthorizationError("canonical run state hash mismatch")
    env = record["envelope"]
    env_required = {
        "run_id", "case_id", "market", "symbol", "cutoff_date", "as_of_date",
        "request_type", "orchestrator_version", "research_case_hash", "stage_state",
        "run_status", "artifact_refs", "stage_receipts", "non_canonical_reason",
        "created_at",
    }
    if not isinstance(env, Mapping) or set(env) != env_required:
        raise CanonicalRunAuthorizationError("run envelope fields are invalid")
    _safe_run_id(env["run_id"])
    if env["market"] not in {"CN-A", "HK"}:
        raise CanonicalRunAuthorizationError("run market is invalid")
    if not isinstance(env["case_id"], str) or not env["case_id"].strip():
        raise CanonicalRunAuthorizationError("run case_id is required")
    if not is_sha256(env["research_case_hash"]):
        raise CanonicalRunAuthorizationError("run research_case_hash is required")
    hashes = [canonical_hash(x) for x in env["stage_receipts"]]
    if record["stage_receipt_hashes"] != hashes:
        raise CanonicalRunAuthorizationError("stage receipt hash list mismatch")
    if record["stage_chain_hash"] != canonical_hash({"stage_receipt_hashes": hashes}):
        raise CanonicalRunAuthorizationError("stage receipt chain hash mismatch")
    metadata = record["request_metadata"]
    if not isinstance(metadata, Mapping):
        raise CanonicalRunAuthorizationError("request metadata must be an object")
    for field in ("raw_request_sha256", "request_receipt_hash", "normalized_request_sha256"):
        value = metadata.get(field)
        if value is not None and not is_sha256(value):
            raise CanonicalRunAuthorizationError(f"request metadata {field} is invalid")
    # Replay proves monotonic stage order and immutable receipt lineage.
    orchestrator = _replay_record(record)
    replayed = orchestrator.get(env["run_id"])
    if replayed.stage_state.value != env["stage_state"] or replayed.run_status.value != env["run_status"]:
        raise CanonicalRunAuthorizationError("run stage/status does not match replay")
    if env["run_status"] == RunStatus.COMPLETE.value and env["stage_state"] != Stage.COMPLETE.value:
        raise CanonicalRunAuthorizationError("complete run must end at COMPLETE")
    # Any formal write requires the request, case, evidence, semantics, forecast,
    # valuation and decision receipts; a bare state file is never sufficient.
    if env["run_status"] == RunStatus.IN_PROGRESS.value:
        stages = [x["stage_id"] for x in env["stage_receipts"]]
        if Stage.REQUEST_ADMITTED.value in stages:
            req = next(x for x in env["stage_receipts"] if x["stage_id"] == Stage.REQUEST_ADMITTED.value)
            if not is_sha256(metadata.get("raw_request_sha256")) or not is_sha256(metadata.get("request_receipt_hash")):
                raise CanonicalRunAuthorizationError("request raw hash and admission receipt are required")
            if metadata["request_receipt_hash"] not in req["output_hashes"]:
                raise CanonicalRunAuthorizationError("request admission receipt is not bound to stage chain")
        if Stage.CASE_CREATED.value in stages:
            case = next(x for x in env["stage_receipts"] if x["stage_id"] == Stage.CASE_CREATED.value)
            if env["research_case_hash"] not in case["output_hashes"]:
                raise CanonicalRunAuthorizationError("Research Case hash is not bound to stage chain")
    return dict(record)


class PersistedCanonicalResearchOrchestrator(CanonicalResearchOrchestrator):
    """Orchestrator adapter that persists every transition and enforces append-only history."""

    def __init__(self, root: str | Path) -> None:
        super().__init__()
        self.root = Path(root)
        self._request_metadata: dict[str, dict[str, Any]] = {}

    def bind_request(self, *, run_id: str, raw_request: str,
                     request_receipt: Mapping[str, Any]) -> None:
        if not isinstance(raw_request, str) or not raw_request.strip():
            raise CanonicalRunAuthorizationError("raw natural-language request is required")
        raw_hash = _sha_bytes(raw_request.encode("utf-8"))
        if request_receipt.get("raw_request_sha256") != raw_hash:
            raise CanonicalRunAuthorizationError("raw request hash does not match admission receipt")
        if request_receipt.get("run_id") != run_id:
            raise CanonicalRunAuthorizationError("request receipt run_id mismatch")
        supplied_hash = request_receipt.get("receipt_hash")
        receipt_core = {k: v for k, v in request_receipt.items() if k != "receipt_hash"}
        if not is_sha256(supplied_hash) or canonical_hash(receipt_core) != supplied_hash:
            raise CanonicalRunAuthorizationError("request admission receipt hash mismatch")
        self._request_metadata[run_id] = {
            "request_id": request_receipt.get("request_id"),
            "raw_request_sha256": raw_hash,
            "request_receipt_hash": supplied_hash,
            "normalized_request_sha256": request_receipt.get("normalized_request_sha256"),
        }

    def start(self, **kwargs: Any) -> RunEnvelope:
        run_id = str(kwargs.get("run_id", ""))
        metadata = self._request_metadata.get(run_id)
        if metadata is None:
            raise CanonicalRunAuthorizationError("canonical run cannot start without bound raw request/admission")
        envelope = super().start(**kwargs)
        self._persist(run_id)
        return envelope

    def transition(self, run_id: str, next_stage: Stage, **kwargs: Any) -> RunEnvelope:
        envelope = super().transition(run_id, next_stage, **kwargs)
        self._persist(run_id)
        return envelope

    def block(self, run_id: str, reason: str) -> RunEnvelope:
        envelope = super().block(run_id, reason)
        self._persist(run_id)
        return envelope

    def classify_direct_execution_as_non_canonical(self, *, run_id: str, reason: str) -> RunEnvelope:
        envelope = super().classify_direct_execution_as_non_canonical(run_id=run_id, reason=reason)
        self._persist(run_id)
        return envelope

    def _persist(self, run_id: str) -> dict[str, Any]:
        envelope = self.get(run_id)
        record = _make_record(envelope, self._request_metadata[run_id])
        path = run_state_path(self.root, run_id)
        if path.exists():
            previous = validate_run_state_record(json.loads(path.read_text(encoding="utf-8")))
            _same_prefix(previous, record)
        _atomic_write_json(path, record)
        return record


def _load_record(root: str | Path, run_id: str) -> dict[str, Any]:
    path = run_state_path(root, run_id)
    if not path.exists():
        raise CanonicalRunAuthorizationError("canonical Run Envelope/Receipt is absent")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalRunAuthorizationError("canonical run state cannot be read") from exc
    return validate_run_state_record(value)


def _receipt_for_stage(record: Mapping[str, Any], stage: Stage) -> tuple[int, Mapping[str, Any]]:
    matches = [
        (i, item) for i, item in enumerate(record["envelope"]["stage_receipts"])
        if item["stage_id"] == stage.value
    ]
    if not matches:
        raise CanonicalRunAuthorizationError(f"required stage receipt is absent: {stage.value}")
    return matches[-1]


def _record_hash_at_prefix(record: Mapping[str, Any], end_index: int) -> str:
    env = record["envelope"]
    subset = dict(env)
    subset["stage_receipts"] = list(env["stage_receipts"][:end_index + 1])
    refs: list[str] = []
    for receipt in subset["stage_receipts"]:
        for ref in receipt["output_refs"]:
            if ref not in refs:
                refs.append(ref)
    subset["artifact_refs"] = refs
    subset["stage_state"] = subset["stage_receipts"][-1]["stage_id"]
    subset["run_status"] = (
        RunStatus.COMPLETE.value if subset["stage_state"] == Stage.COMPLETE.value
        else RunStatus.IN_PROGRESS.value
    )
    core = {
        "schema_version": RUN_STATE_SCHEMA_VERSION,
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "envelope": subset,
        "request_metadata": dict(record["request_metadata"]),
        "stage_receipt_hashes": [
            canonical_hash(x) for x in subset["stage_receipts"]
        ],
        "stage_chain_hash": canonical_hash({
            "stage_receipt_hashes": [canonical_hash(x) for x in subset["stage_receipts"]]
        }),
    }
    return canonical_hash(core)


def make_stage_authority_ref(
    root: str | Path,
    run_id: str,
    required_stage: Stage,
    *,
    required_hashes: tuple[str, ...] = (),
    required_refs: tuple[str, ...] = (),
    allow_later_stage: bool = False,
) -> dict[str, Any]:
    record = _load_record(root, run_id)
    env = record["envelope"]
    current = Stage(env["stage_state"])
    if env["run_status"] != RunStatus.IN_PROGRESS.value and not (allow_later_stage and env["stage_state"] == Stage.COMPLETE.value):
        raise CanonicalRunAuthorizationError("terminal/non-canonical runs cannot authorize new writes")
    if allow_later_stage:
        stage_order = [s.value for s in Stage]
        if stage_order.index(current.value) < stage_order.index(required_stage.value):
            raise CanonicalRunAuthorizationError("required authorization stage has not been reached")
    elif current != required_stage:
        raise CanonicalRunAuthorizationError(
            f"run stage authorization failed: current={current.value}, required={required_stage.value}"
        )
    idx, receipt = _receipt_for_stage(record, required_stage)
    missing_hashes = sorted(set(required_hashes) - set(receipt["output_hashes"]))
    missing_refs = sorted(set(required_refs) - set(receipt["output_refs"]))
    if missing_hashes:
        raise CanonicalRunAuthorizationError(
            f"{required_stage.value} does not authorize required output hashes: {missing_hashes}"
        )
    if missing_refs:
        raise CanonicalRunAuthorizationError(
            f"{required_stage.value} does not authorize required output refs: {missing_refs}"
        )
    receipt_hash = canonical_hash(receipt)
    core = {
        "schema_version": RUN_STAGE_AUTH_SCHEMA_VERSION,
        "run_id": run_id,
        "case_id": env["case_id"],
        "market": env["market"],
        "symbol": env["symbol"],
        "cutoff_date": env["cutoff_date"],
        "stage": required_stage.value,
        "stage_receipt_hash": receipt_hash,
        "state_hash_at_stage": _record_hash_at_prefix(record, idx),
        "authorized_refs": list(receipt["output_refs"]),
        "authorized_hashes": list(receipt["output_hashes"]),
    }
    return {**core, "authorization_hash": canonical_hash(core)}


def validate_stage_authority_ref(
    root: str | Path,
    authority_ref: Any,
    *,
    required_stage: Stage,
    required_hashes: tuple[str, ...] = (),
    current_stage: Stage | None = None,
) -> dict[str, Any]:
    if not isinstance(authority_ref, Mapping):
        raise CanonicalRunAuthorizationError("canonical run stage authority is required")
    required_fields = {
        "schema_version", "run_id", "case_id", "market", "symbol", "cutoff_date",
        "stage", "stage_receipt_hash", "state_hash_at_stage", "authorized_refs",
        "authorized_hashes", "authorization_hash",
    }
    if set(authority_ref) != required_fields:
        raise CanonicalRunAuthorizationError("run stage authority fields are invalid")
    if authority_ref["schema_version"] != RUN_STAGE_AUTH_SCHEMA_VERSION or authority_ref["stage"] != required_stage.value:
        raise CanonicalRunAuthorizationError("run stage authority version/stage mismatch")
    core = {k: authority_ref[k] for k in required_fields if k != "authorization_hash"}
    if authority_ref["authorization_hash"] != canonical_hash(core):
        raise CanonicalRunAuthorizationError("run stage authorization hash mismatch")
    record = _load_record(root, str(authority_ref["run_id"]))
    env = record["envelope"]
    if any(authority_ref[field] != env[env_field] for field, env_field in (
        ("case_id", "case_id"), ("market", "market"), ("symbol", "symbol"),
        ("cutoff_date", "cutoff_date"),
    )):
        raise CanonicalRunAuthorizationError("run stage authority identity/cutoff mismatch")
    if current_stage is not None and env["stage_state"] != current_stage.value:
        raise CanonicalRunAuthorizationError(
            f"current run stage must be {current_stage.value}, got {env['stage_state']}"
        )
    idx, receipt = _receipt_for_stage(record, required_stage)
    if canonical_hash(receipt) != authority_ref["stage_receipt_hash"]:
        raise CanonicalRunAuthorizationError("run stage receipt binding mismatch")
    if _record_hash_at_prefix(record, idx) != authority_ref["state_hash_at_stage"]:
        raise CanonicalRunAuthorizationError("historical run state binding mismatch")
    if authority_ref["authorized_refs"] != receipt["output_refs"] or authority_ref["authorized_hashes"] != receipt["output_hashes"]:
        raise CanonicalRunAuthorizationError("run stage output binding mismatch")
    missing = sorted(set(required_hashes) - set(receipt["output_hashes"]))
    if missing:
        raise CanonicalRunAuthorizationError(f"run stage lacks required hashes: {missing}")
    return dict(record)


def authorize_decision_revision_write(
    root: str | Path,
    *,
    run_id: str,
    snapshot: Mapping[str, Any],
    decision_admission: Mapping[str, Any],
) -> dict[str, Any]:
    if snapshot.get("snapshot_schema") != "IIOS-MVP-SNAPSHOT-0.3.0":
        raise CanonicalRunAuthorizationError("canonical run authorization requires Investment Core v0.3 snapshot")
    hashes = (
        str(snapshot.get("snapshot_hash", "")),
        str(decision_admission.get("admission_record_hash", "")),
    )
    if any(not is_sha256(x) for x in hashes):
        raise CanonicalRunAuthorizationError("snapshot/Decision Admission hashes are required")
    return make_stage_authority_ref(
        root, run_id, Stage.DECISION_ADMITTED,
        required_hashes=hashes,
    )


def authorize_publication_write(
    root: str | Path,
    *,
    revision: Mapping[str, Any],
) -> dict[str, Any]:
    ref = revision.get("run_authority_ref")
    validate_stage_authority_ref(
        root, ref, required_stage=Stage.DECISION_ADMITTED,
        required_hashes=(str(revision.get("snapshot_hash", "")),),
    )
    run_id = str(revision["run_id"])
    record = _load_record(root, run_id)
    env = record["envelope"]
    if env["stage_state"] == Stage.HUMAN_APPROVAL_PENDING.value:
        return make_stage_authority_ref(
            root, run_id, Stage.HUMAN_APPROVAL_PENDING,
            required_hashes=(str(revision["revision_hash"]),),
            required_refs=(str(revision["decision_id"]),),
        )
    if env["stage_state"] in {Stage.PUBLISHED.value, Stage.REPORTED.value, Stage.COMPLETE.value}:
        # Idempotent replay: the existing publication stage must cite this revision.
        _, stage_receipt = _receipt_for_stage(record, Stage.HUMAN_APPROVAL_PENDING)
        if str(revision["revision_hash"]) not in stage_receipt["output_hashes"] or str(revision["decision_id"]) not in stage_receipt["output_refs"]:
            raise CanonicalRunAuthorizationError("published run does not bind this Decision Revision")
        return make_stage_authority_ref(
            root, run_id, Stage.HUMAN_APPROVAL_PENDING,
            required_hashes=(str(revision["revision_hash"]),),
            required_refs=(str(revision["decision_id"]),),
            allow_later_stage=True,
        )
    raise CanonicalRunAuthorizationError("publication requires HUMAN_APPROVAL_PENDING run state")


def authorize_report_write(
    root: str | Path,
    *,
    publication: Mapping[str, Any],
) -> dict[str, Any]:
    run_ref = publication.get("canonical_run_ref")
    validate_stage_authority_ref(
        root, run_ref, required_stage=Stage.HUMAN_APPROVAL_PENDING,
        required_hashes=(str(publication.get("decision_ref", {}).get("revision_hash", "")),),
        current_stage=None,
    )
    run_id = str(run_ref["run_id"])
    record = _load_record(root, run_id)
    env = record["envelope"]
    if env["stage_state"] not in {
        Stage.PUBLISHED.value, Stage.REPORTED.value, Stage.COMPLETE.value
    }:
        raise CanonicalRunAuthorizationError("report requires an admitted Machine Publication stage")
    _, pub_stage = _receipt_for_stage(record, Stage.PUBLISHED)
    pub_hash = str(publication.get("publication_hash", ""))
    if not is_sha256(pub_hash) or pub_hash not in pub_stage["output_hashes"]:
        raise CanonicalRunAuthorizationError("Machine Publication hash is not bound to the run")
    return make_stage_authority_ref(
        root, run_id, Stage.PUBLISHED,
        required_hashes=(pub_hash,),
        required_refs=(str(publication.get("publication_id", "")),),
        allow_later_stage=True,
    )


def advance_persisted_run(
    root: str | Path,
    run_id: str,
    next_stage: Stage,
    *,
    input_refs: tuple[str, ...] = (),
    input_hashes: tuple[str, ...] = (),
    output_refs: tuple[str, ...] = (),
    output_hashes: tuple[str, ...] = (),
    producer_type: str = "CODE",
    producer_version: str = ORCHESTRATOR_VERSION,
    status: str = "PASS",
    created_at: str | None = None,
) -> dict[str, Any]:
    record = _load_record(root, run_id)
    env = record["envelope"]
    orchestrator = _replay_record(record)
    result = orchestrator.transition(
        run_id, next_stage,
        input_refs=input_refs, input_hashes=input_hashes,
        output_refs=output_refs, output_hashes=output_hashes,
        producer_type=producer_type, producer_version=producer_version,
        status=status, created_at=created_at,
    )
    return _persist_replayed(root, result, record["request_metadata"], previous=record)


def _persist_replayed(
    root: str | Path,
    envelope: RunEnvelope,
    metadata: Mapping[str, Any],
    *,
    previous: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = _make_record(envelope, metadata)
    path = run_state_path(root, envelope.run_id)
    if previous is not None:
        _same_prefix(previous, record)
    elif path.exists():
        _same_prefix(_load_record(root, envelope.run_id), record)
    _atomic_write_json(path, record)
    return record


def write_complete_run_receipt(
    root: str | Path,
    run_id: str,
    *,
    report_hash: str,
) -> dict[str, Any]:
    record = _load_record(root, run_id)
    env = record["envelope"]
    if env["stage_state"] != Stage.COMPLETE.value or env["run_status"] != RunStatus.COMPLETE.value:
        raise CanonicalRunAuthorizationError("complete run receipt requires COMPLETE state")
    by_stage = {x["stage_id"]: x for x in env["stage_receipts"]}
    required_stages = (
        Stage.REQUEST_ADMITTED, Stage.CASE_CREATED, Stage.EVIDENCE_ADMITTED,
        Stage.SEMANTIC_ADMITTED, Stage.FORECAST_ADMITTED, Stage.VALUATION_ADMITTED,
        Stage.DECISION_ADMITTED, Stage.HUMAN_APPROVAL_PENDING, Stage.PUBLISHED,
        Stage.REPORTED, Stage.COMPLETE,
    )
    missing = [s.value for s in required_stages if s.value not in by_stage]
    if missing:
        raise CanonicalRunAuthorizationError("completed run has missing stages: " + ", ".join(missing))
    meta = record["request_metadata"]
    evidence = by_stage[Stage.EVIDENCE_ADMITTED.value]
    semantic = by_stage[Stage.SEMANTIC_ADMITTED.value]
    forecast = by_stage[Stage.FORECAST_ADMITTED.value]
    valuation = by_stage[Stage.VALUATION_ADMITTED.value]
    decision = by_stage[Stage.DECISION_ADMITTED.value]
    published = by_stage[Stage.PUBLISHED.value]
    reported = by_stage[Stage.REPORTED.value]
    if not is_sha256(report_hash) or report_hash not in reported["output_hashes"]:
        raise CanonicalRunAuthorizationError("final report hash is not bound to REPORTED stage")
    ref_hashes = dict(zip(decision["output_refs"], decision["output_hashes"]))
    # Decision stage explicitly names these values; all must be backed by the
    # admitted, canonical Decision snapshot rather than a renderer calculation.
    return_hash = ref_hashes.get("return_metrics")
    risk_portfolio_hash = ref_hashes.get("risk_portfolio")
    admission_hash = ref_hashes.get("decision_admission")
    if not all(is_sha256(x) for x in (return_hash, risk_portfolio_hash, admission_hash)):
        raise CanonicalRunAuthorizationError("Decision stage lacks return/risk/admission hashes")
    revision_refs = [x for x in by_stage[Stage.HUMAN_APPROVAL_PENDING.value]["output_refs"] if re.search(r"-r([0-9]+)$", x)]
    if len(revision_refs) != 1:
        raise CanonicalRunAuthorizationError("HUMAN_APPROVAL_PENDING must identify one Decision Revision")
    revision_match = re.search(r"-r([0-9]+)$", revision_refs[0])
    assert revision_match is not None
    receipt_core = {
        "schema_version": RUN_RECEIPT_V02_SCHEMA_VERSION,
        "run_id": run_id,
        "case_id": env["case_id"],
        "market": env["market"],
        "symbol": env["symbol"],
        "cutoff_date": env["cutoff_date"],
        "as_of_date": env["as_of_date"],
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "research_case_hash": env["research_case_hash"],
        "raw_request_sha256": meta["raw_request_sha256"],
        "request_receipt_hash": meta["request_receipt_hash"],
        "normalized_request_sha256": meta["normalized_request_sha256"],
        "stage_receipt_hashes": list(record["stage_receipt_hashes"]),
        "stage_chain_hash": record["stage_chain_hash"],
        "evidence_manifest_hash": canonical_hash({
            "refs": evidence["output_refs"], "hashes": evidence["output_hashes"]
        }),
        "semantic_artifact_hashes": list(semantic["output_hashes"]),
        "forecast_admission_hash": forecast["output_hashes"][0],
        "valuation_admission_hash": valuation["output_hashes"][0],
        "return_hash": return_hash,
        "risk_portfolio_hash": risk_portfolio_hash,
        "decision_admission_hash": admission_hash,
        "decision_revision": int(revision_match.group(1)),
        "publication_hash": published["output_hashes"][0],
        "report_hash": report_hash,
        "run_status": RunStatus.COMPLETE.value,
    }
    receipt = {**receipt_core, "receipt_hash": canonical_hash(receipt_core)}
    path = run_receipt_path(root, run_id)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != receipt:
            raise CanonicalRunAuthorizationError("complete Run Receipt is immutable")
    else:
        _atomic_write_json(path, receipt)
    return receipt


__all__ = [
    "RUN_STATE_SCHEMA_VERSION", "RUN_STAGE_AUTH_SCHEMA_VERSION",
    "RUN_RECEIPT_V02_SCHEMA_VERSION", "CanonicalRunAuthorizationError",
    "PersistedCanonicalResearchOrchestrator", "run_state_path", "run_receipt_path",
    "validate_run_state_record", "make_stage_authority_ref", "validate_stage_authority_ref",
    "authorize_decision_revision_write", "authorize_publication_write",
    "authorize_report_write", "advance_persisted_run", "write_complete_run_receipt",
]
