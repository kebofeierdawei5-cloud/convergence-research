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

from .canonical_evidence_admission_v01 import validate_company_evidence_manifest
from .canonical_independent_forecast import (
    CanonicalIndependentForecastReference,
    validate_canonical_independent_forecast_admission,
)
from .canonical_investment_admission_v01 import (
    CanonicalInvestmentAdmissionReference,
    validate_canonical_investment_admission_record,
)
from .forecast_valuation_return_lineage_v01 import (
    FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
    validate_canonical_valuation_output,
)
from .semantic_producer_admission_v01 import SEMANTIC_ADMISSION_VERSION
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



def _require_content_addressed_artifact(
    root: str | Path,
    *,
    suffix: str,
    payload: Mapping[str, Any],
) -> Path:
    """Require the exact immutable payload the canonical run claims to have admitted."""
    raw = _canonical_bytes(payload)
    digest = _sha_bytes(raw)
    path = Path(root) / "canonical-artifacts" / f"{digest}.{suffix}.json"
    if not path.is_file():
        raise CanonicalRunAuthorizationError(
            f"BLOCKED: admitted {suffix} artifact is absent"
        )
    try:
        persisted = path.read_bytes()
    except OSError as exc:
        raise CanonicalRunAuthorizationError(
            f"BLOCKED: admitted {suffix} artifact cannot be read"
        ) from exc
    if persisted != raw or _sha_bytes(persisted) != digest:
        raise CanonicalRunAuthorizationError(
            f"BLOCKED: admitted {suffix} artifact bytes/hash mismatch"
        )
    return path


def _validate_canonical_upstream_admissions(
    root: str | Path,
    record: Mapping[str, Any],
    *,
    manifest_evidence_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Re-open and validate persisted semantic, forecast and valuation admission bytes."""
    env = record["envelope"]
    identity = {
        "run_id": str(env["run_id"]),
        "case_id": str(env["case_id"]),
        "market": str(env["market"]).upper(),
        "symbol": str(env["symbol"]).upper(),
        "cutoff_date": str(env["cutoff_date"]),
    }
    semantic_stage = _receipt_for_stage(record, Stage.SEMANTIC_ADMITTED)[1]
    forecast_stage = _receipt_for_stage(record, Stage.FORECAST_ADMITTED)[1]
    valuation_stage = _receipt_for_stage(record, Stage.VALUATION_ADMITTED)[1]
    decision_stage = _receipt_for_stage(record, Stage.DECISION_ADMITTED)[1]
    decision_pending = _receipt_for_stage(record, Stage.DECISION_PENDING)[1]

    if any(
        len(stage["output_refs"]) != len(stage["output_hashes"])
        for stage in (semantic_stage, forecast_stage, valuation_stage, decision_stage, decision_pending)
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: upstream stage refs/hashes are not positionally bound"
        )

    bundle_entries = [
        (ref, digest)
        for ref, digest in zip(decision_stage["output_refs"], decision_stage["output_hashes"], strict=True)
        if str(ref).startswith("canonical-upstream-admissions:")
    ]
    if len(bundle_entries) != 1:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: DECISION_ADMITTED does not bind exactly one persisted upstream-admission bundle"
        )
    bundle_ref, bundle_digest = bundle_entries[0]
    expected_ref = f"canonical-upstream-admissions:{bundle_digest}"
    if bundle_ref != expected_ref or not is_sha256(str(bundle_digest)):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: upstream-admission bundle ref/hash is malformed"
        )

    bundle_path = Path(root) / "canonical-artifacts" / f"{bundle_digest}.canonical-upstream-admissions.json"
    if not bundle_path.is_file():
        raise CanonicalRunAuthorizationError(
            "BLOCKED: persisted canonical upstream-admission bundle is absent"
        )
    try:
        bundle_bytes = bundle_path.read_bytes()
        bundle = json.loads(bundle_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: persisted canonical upstream-admission bundle is unreadable"
        ) from exc
    if _sha_bytes(bundle_bytes) != bundle_digest or _canonical_bytes(bundle) != bundle_bytes:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: upstream-admission bundle bytes are not canonical or content-addressed"
        )
    required_bundle_fields = {
        "schema_version", "run_id", "case_id", "market", "symbol", "company",
        "cutoff_date", "semantic_artifact", "semantic_producer_receipt",
        "semantic_admission", "canonical_forecast_ref", "forecast_record",
        "canonical_valuation_ref", "valuation_admission_record", "valuation_output",
        "validated_lineage", "bundle_hash",
    }
    if not isinstance(bundle, Mapping) or set(bundle) != required_bundle_fields:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: canonical upstream-admission bundle fields are invalid"
        )
    bundle_core = {key: value for key, value in bundle.items() if key != "bundle_hash"}
    if (
        bundle["schema_version"] != "IIOS-CANONICAL-UPSTREAM-ADMISSIONS-0.1"
        or bundle["bundle_hash"] != canonical_hash(bundle_core)
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: canonical upstream-admission bundle schema/hash mismatch"
        )
    for field, expected in identity.items():
        if bundle.get(field) != expected:
            raise CanonicalRunAuthorizationError(
                f"BLOCKED: upstream-admission bundle {field} identity mismatch"
            )
    if not isinstance(bundle.get("company"), str) or not bundle["company"].strip():
        raise CanonicalRunAuthorizationError(
            "BLOCKED: upstream-admission bundle company identity is missing"
        )

    semantic = bundle["semantic_artifact"]
    producer = bundle["semantic_producer_receipt"]
    semantic_admission = bundle["semantic_admission"]
    if not isinstance(semantic, Mapping) or not isinstance(producer, Mapping) or not isinstance(semantic_admission, Mapping):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic artifact/producer/admission payloads must be objects"
        )
    if (
        len(semantic_stage["output_refs"]) != 1
        or len(semantic_stage["output_hashes"]) != 1
        or semantic_stage["output_refs"][0] != semantic.get("artifact_id")
        or semantic_stage["output_hashes"][0] != semantic.get("artifact_hash")
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: SEMANTIC_ADMITTED receipt does not bind the exact semantic artifact"
        )
    semantic_core = {key: value for key, value in semantic.items() if key != "artifact_hash"}
    if (
        semantic.get("schema_version") != "IIOS-LLM-SEMANTIC-ARTIFACT-0.1"
        or not is_sha256(str(semantic.get("artifact_hash", "")))
        or semantic.get("artifact_hash") != canonical_hash(semantic_core)
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic artifact schema/integrity check failed"
        )
    semantic_identity = {
        "case_id": identity["case_id"],
        "market": identity["market"],
        "symbol": identity["symbol"],
        "cutoff_date": identity["cutoff_date"],
    }
    for field, expected in semantic_identity.items():
        if semantic.get(field) != expected:
            raise CanonicalRunAuthorizationError(
                f"BLOCKED: semantic artifact {field} identity mismatch"
            )
    if semantic.get("company") != bundle["company"]:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic artifact company identity mismatch"
        )
    if (
        semantic.get("producer_type") not in {"LLM_SEMANTIC_PRODUCER", "HUMAN_EXPERT_ADJUDICATION"}
        or not str(semantic.get("producer_id", "")).strip()
        or not str(semantic.get("producer_version", "")).strip()
        or not str(semantic.get("policy_version", "")).strip()
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic producer identity/version/policy is not admitted"
        )
    evidence_stage = _receipt_for_stage(record, Stage.EVIDENCE_ADMITTED)[1]
    admitted_input_pairs = list(zip(
        evidence_stage["output_refs"][1:],
        evidence_stage["output_hashes"][1:],
        strict=True,
    ))
    semantic_input_pairs = list(zip(
        semantic.get("input_refs", []),
        semantic.get("input_hashes", []),
        strict=True,
    ))
    if not semantic_input_pairs or semantic_input_pairs != admitted_input_pairs:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic input lineage differs from admitted Evidence/PIT receipt"
        )
    forbidden = {
        "action", "decision_status", "new_capital_allowed", "human_approval_required",
        "auto_execution", "capital_effect", "decision_admission",
        "decision_precedence_rule_id", "decision_pre_admission_action",
    }
    def reject_authority_fields(node: Any) -> bool:
        if isinstance(node, Mapping):
            if forbidden.intersection(node):
                return True
            return any(reject_authority_fields(value) for value in node.values())
        if isinstance(node, (list, tuple)):
            return any(reject_authority_fields(value) for value in node)
        return False
    if reject_authority_fields(semantic.get("output")):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic producer artifact contains Decision-authoritative fields"
        )

    required_producer_fields = {
        "schema_version", "receipt_id", "artifact_id", "artifact_type", "stage_id",
        "case_id", "market", "symbol", "company", "cutoff_date", "producer_type",
        "producer_id", "producer_version", "policy_version", "input_refs", "input_hashes",
        "artifact_hash", "output_hash", "status", "created_at", "receipt_hash",
    }
    if set(producer) != required_producer_fields:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic producer receipt fields are invalid"
        )
    producer_core = {key: value for key, value in producer.items() if key != "receipt_hash"}
    if (
        producer.get("schema_version") != "IIOS-SEMANTIC-PRODUCER-RECEIPT-0.1"
        or producer.get("receipt_hash") != canonical_hash(producer_core)
        or producer.get("status") != "PRODUCED"
        or producer.get("artifact_hash") != semantic.get("artifact_hash")
        or producer.get("artifact_id") != semantic.get("artifact_id")
        or producer.get("stage_id") != semantic.get("artifact_type")
        or producer.get("output_hash") != canonical_hash(semantic.get("output"))
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic producer receipt does not validate against semantic artifact"
        )
    for field in (
        "artifact_id", "artifact_type", "case_id", "market", "symbol", "company",
        "cutoff_date", "producer_type", "producer_id", "producer_version",
        "policy_version", "input_refs", "input_hashes", "artifact_hash",
    ):
        if producer.get(field) != semantic.get(field):
            raise CanonicalRunAuthorizationError(
                f"BLOCKED: semantic producer receipt binding mismatch: {field}"
            )
    if set(semantic_admission) != {"status", "artifact_hash", "producer_receipt_hash", "admission_hash"}:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic admission receipt fields are invalid"
        )
    admission_core = {
        "admission_version": SEMANTIC_ADMISSION_VERSION,
        "status": semantic_admission["status"],
        "artifact_hash": semantic_admission["artifact_hash"],
        "producer_receipt_hash": semantic_admission["producer_receipt_hash"],
        "producer_id": semantic.get("producer_id"),
        "producer_version": semantic.get("producer_version"),
        "policy_version": semantic.get("policy_version"),
        "case_id": semantic.get("case_id"),
        "artifact_type": semantic.get("artifact_type"),
    }
    if (
        semantic_admission["status"] != "ADMITTED"
        or semantic_admission["artifact_hash"] != semantic.get("artifact_hash")
        or semantic_admission["producer_receipt_hash"] != producer.get("receipt_hash")
        or semantic_admission["admission_hash"] != canonical_hash(admission_core)
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: semantic producer admission does not bind the exact artifact and receipt"
        )
    _require_content_addressed_artifact(root, suffix="semantic-artifact", payload=semantic)
    _require_content_addressed_artifact(root, suffix="semantic-producer-receipt", payload=producer)
    _require_content_addressed_artifact(root, suffix="semantic-admission", payload=semantic_admission)

    forecast_ref = bundle["canonical_forecast_ref"]
    forecast_record = bundle["forecast_record"]
    if not isinstance(forecast_ref, Mapping) or not isinstance(forecast_record, Mapping):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: canonical Forecast reference/record must be objects"
        )
    try:
        parsed_forecast_ref = CanonicalIndependentForecastReference.from_mapping(forecast_ref)
        validate_canonical_independent_forecast_admission(forecast_record)
    except (TypeError, ValueError) as exc:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: canonical Forecast admission validation failed"
        ) from exc
    if (
        len(forecast_stage["output_refs"]) != 1
        or len(forecast_stage["output_hashes"]) != 1
        or forecast_stage["output_refs"][0] != parsed_forecast_ref.forecast_id
        or forecast_stage["output_hashes"][0] != parsed_forecast_ref.admission_record_hash
        or forecast_record.get("forecast_id") != parsed_forecast_ref.forecast_id
        or forecast_record.get("admission_record_hash") != parsed_forecast_ref.admission_record_hash
        or forecast_record.get("status") != "ADMITTED"
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: FORECAST_ADMITTED receipt does not bind the exact forecast admission record"
        )
    for field, expected in {
        "case_id": identity["case_id"], "market": identity["market"],
        "symbol": identity["symbol"], "cutoff_date": identity["cutoff_date"],
    }.items():
        if forecast_record.get(field) != expected:
            raise CanonicalRunAuthorizationError(
                f"BLOCKED: forecast admission {field} identity mismatch"
            )
    if manifest_evidence_ids is not None and not set(forecast_record.get("evidence_ids", [])).issubset(manifest_evidence_ids):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: forecast admission references Evidence IDs outside the admitted manifest"
        )
    _require_content_addressed_artifact(root, suffix="forecast-admission", payload=forecast_record)

    valuation_ref = bundle["canonical_valuation_ref"]
    valuation_admission = bundle["valuation_admission_record"]
    valuation_output = bundle["valuation_output"]
    if not isinstance(valuation_ref, Mapping) or not isinstance(valuation_admission, Mapping) or not isinstance(valuation_output, Mapping):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: canonical Valuation reference/admission/output must be objects"
        )
    try:
        parsed_valuation_ref = CanonicalInvestmentAdmissionReference.from_mapping(valuation_ref)
        validate_canonical_investment_admission_record(valuation_admission)
        validate_canonical_valuation_output(valuation_output)
    except (TypeError, ValueError) as exc:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: canonical Valuation admission/output validation failed"
        ) from exc
    expected_valuation_ref = {
        "admission_id": parsed_valuation_ref.admission_id,
        "admission_record_hash": parsed_valuation_ref.admission_record_hash,
        "contract_version": parsed_valuation_ref.contract_version,
        "domain": parsed_valuation_ref.domain,
        "case_id": parsed_valuation_ref.case_id,
        "market": parsed_valuation_ref.market,
        "symbol": parsed_valuation_ref.symbol,
        "company": parsed_valuation_ref.company,
        "cutoff_date": parsed_valuation_ref.cutoff_date,
    }
    if (
        expected_valuation_ref != dict(valuation_ref)
        or parsed_valuation_ref.domain != "VALUATION"
        or valuation_admission.get("status") != "ADMITTED"
        or valuation_admission.get("domain") != "VALUATION"
        or valuation_admission.get("admission_id") != parsed_valuation_ref.admission_id
        or valuation_admission.get("admission_record_hash") != parsed_valuation_ref.admission_record_hash
        or valuation_admission.get("output_hash") != valuation_output.get("output_hash")
        or valuation_output.get("forecast_ref") != dict(forecast_ref)
        or len(valuation_stage["output_refs"]) != 1
        or len(valuation_stage["output_hashes"]) != 1
        or valuation_stage["output_refs"][0] != parsed_valuation_ref.admission_id
        or valuation_stage["output_hashes"][0] != parsed_valuation_ref.admission_record_hash
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: VALUATION_ADMITTED receipt does not bind the exact admitted valuation output"
        )
    for field, expected in {
        "case_id": identity["case_id"], "market": identity["market"],
        "symbol": identity["symbol"], "company": bundle["company"],
        "cutoff_date": identity["cutoff_date"],
    }.items():
        if valuation_admission.get(field) != expected or valuation_output.get(field) != expected:
            raise CanonicalRunAuthorizationError(
                f"BLOCKED: valuation admission/output {field} identity mismatch"
            )
    if manifest_evidence_ids is not None and not set(valuation_admission.get("evidence_ids", [])).issubset(manifest_evidence_ids):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: valuation admission references Evidence IDs outside the admitted manifest"
        )
    _require_content_addressed_artifact(root, suffix="valuation-admission", payload=valuation_admission)
    _require_content_addressed_artifact(root, suffix="valuation-output", payload=valuation_output)

    if (
        decision_pending.get("input_refs") != [parsed_forecast_ref.forecast_id, parsed_valuation_ref.admission_id]
        or decision_pending.get("input_hashes") != [parsed_forecast_ref.admission_record_hash, parsed_valuation_ref.admission_record_hash]
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: DECISION_PENDING does not bind admitted Forecast and Valuation records"
        )
    validated_lineage = bundle["validated_lineage"]
    if (
        not isinstance(validated_lineage, Mapping)
        or validated_lineage.get("status") != "PASS"
        or validated_lineage.get("lineage_version") != FORECAST_VALUATION_RETURN_LINEAGE_VERSION
        or validated_lineage.get("canonical_forecast_ref") != dict(forecast_ref)
        or validated_lineage.get("canonical_valuation_ref") != dict(valuation_ref)
        or validated_lineage.get("forecast_id") != forecast_record.get("forecast_id")
        or validated_lineage.get("valuation_id") != valuation_output.get("valuation_id")
        or validated_lineage.get("binding") != "FORECAST_REF_EQUALITY_AND_CANONICAL_VALUATION_SCENARIO_EQUALITY"
    ):
        raise CanonicalRunAuthorizationError(
            "BLOCKED: persisted Forecast/Valuation return-lineage admission is inconsistent"
        )
    return dict(bundle)


def authorize_decision_revision_write(
    root: str | Path,
    *,
    run_id: str,
    snapshot: Mapping[str, Any],
    decision_admission: Mapping[str, Any],
) -> dict[str, Any]:
    if snapshot.get("snapshot_schema") != "IIOS-MVP-SNAPSHOT-0.3.0":
        raise CanonicalRunAuthorizationError("canonical run authorization requires Investment Core v0.3 snapshot")
    execution_classification = snapshot.get("execution_classification")
    if isinstance(execution_classification, Mapping) and execution_classification.get("status") == "NON_CANONICAL":
        raise CanonicalRunAuthorizationError("NON_CANONICAL: lower-level engine snapshot cannot be promoted to Decision Revision")
    snapshot_input = snapshot.get("input")
    if not isinstance(snapshot_input, Mapping):
        raise CanonicalRunAuthorizationError("snapshot input identity is required")
    admission_identity = {
        "case_id": decision_admission.get("case_id"),
        "market": str(decision_admission.get("market", "")).upper(),
        "symbol": str(decision_admission.get("symbol", "")).upper(),
        "company": decision_admission.get("company"),
        "cutoff_date": decision_admission.get("cutoff_date"),
    }
    snapshot_identity = {
        "case_id": snapshot_input.get("case_id"),
        "market": str(snapshot_input.get("market", "")).upper(),
        "symbol": str(snapshot_input.get("symbol", "")).upper(),
        "company": snapshot_input.get("company"),
        "cutoff_date": snapshot_input.get("cutoff_date"),
    }
    if snapshot_identity != admission_identity:
        raise CanonicalRunAuthorizationError("snapshot/Decision Admission identity mismatch")
    record = _load_record(root, run_id)
    envelope = record["envelope"]

    # The persisted DECISION_ADMITTED stage is not sufficient by itself.
    # Re-open the immutable admitted B2 manifest and hash-check every raw byte
    # before permitting a formal Decision Revision write. This blocks a forged
    # run-state file that merely lists arbitrary evidence IDs and digest strings.
    evidence_stage = _receipt_for_stage(record, Stage.EVIDENCE_ADMITTED)[1]
    if not evidence_stage["output_hashes"] or not evidence_stage["output_refs"]:
        raise CanonicalRunAuthorizationError("BLOCKED: Evidence/PIT stage has no manifest-bound receipt")
    manifest_hash = str(evidence_stage["output_hashes"][0])
    expected_manifest_ref = f"evidence-manifest:{manifest_hash}"
    if evidence_stage["output_refs"][0] != expected_manifest_ref:
        raise CanonicalRunAuthorizationError("BLOCKED: Evidence stage is not bound to a canonical manifest")
    manifest_dir = Path(root) / "canonical-artifacts"
    evidence_root = Path(root) / "canonical-evidence"
    candidates = []
    for path in manifest_dir.glob("*.evidence-manifest.json"):
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        audit = candidate.get("audit") if isinstance(candidate, Mapping) else None
        if isinstance(audit, Mapping) and audit.get("manifest_sha256") == manifest_hash:
            candidates.append(candidate)
    if len(candidates) != 1:
        observed = []
        if manifest_dir.is_dir():
            for path in sorted(manifest_dir.glob("*.evidence-manifest.json")):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    audit = payload.get("audit") if isinstance(payload, Mapping) else None
                    observed.append({
                        "path": path.name,
                        "manifest_sha256": audit.get("manifest_sha256") if isinstance(audit, Mapping) else None,
                    })
                except (OSError, json.JSONDecodeError):
                    observed.append({"path": path.name, "manifest_sha256": "UNREADABLE"})
        raise CanonicalRunAuthorizationError(
            "BLOCKED: exact admitted B2 Evidence Manifest artifact is absent or ambiguous; "
            + json.dumps({
                "expected_manifest_sha256": manifest_hash,
                "canonical_artifacts_dir": str(manifest_dir),
                "candidate_count": len(candidates),
                "observed_manifest_artifacts": observed[:20],
            }, ensure_ascii=False, sort_keys=True)
        )
    manifest = candidates[0]
    evidence_errors = validate_company_evidence_manifest(
        manifest, raw_root=evidence_root, require_raw_verification=True
    )
    if evidence_errors:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: persisted B2 Evidence/PIT admission no longer validates: "
            + "; ".join(sorted(set(evidence_errors)))
        )
    manifest_identity = {
        "case_id": str(manifest.get("case_id", "")),
        "market": str(manifest.get("market", "")).upper(),
        "symbol": str(manifest.get("symbol", "")).upper(),
        "company": str(manifest.get("company", "")),
        "cutoff_date": str(manifest.get("cutoff_date", ""))[:10],
    }
    if manifest_identity != snapshot_identity:
        raise CanonicalRunAuthorizationError("BLOCKED: Evidence Manifest identity/cutoff mismatch")
    manifest_evidence = manifest.get("evidence") or []
    expected_refs = [expected_manifest_ref, *[str(x.get("evidence_id", "")) for x in manifest_evidence]]
    expected_hashes = [manifest_hash, *[str(x.get("content_sha256", "")) for x in manifest_evidence]]
    if evidence_stage["output_refs"] != expected_refs or evidence_stage["output_hashes"] != expected_hashes:
        raise CanonicalRunAuthorizationError("BLOCKED: Evidence stage receipts differ from the admitted Manifest")
    _validate_canonical_upstream_admissions(
        root,
        record,
        manifest_evidence_ids={str(item.get("evidence_id", "")) for item in manifest_evidence},
    )
    if any((
        str(envelope["case_id"]) != str(snapshot_identity["case_id"]),
        str(envelope["market"]).upper() != str(snapshot_identity["market"]),
        str(envelope["symbol"]).upper() != str(snapshot_identity["symbol"]),
        str(envelope["cutoff_date"]) != str(snapshot_identity["cutoff_date"]),
        str(envelope["as_of_date"]) != str(snapshot_input.get("as_of_date") or snapshot_identity["cutoff_date"]),
        str(decision_admission.get("snapshot_hash")) != str(snapshot.get("snapshot_hash")),
    )):
        raise CanonicalRunAuthorizationError("snapshot/Decision Admission does not match canonical Run Envelope")
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
    _validate_canonical_upstream_admissions(root, record)
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
    _validate_canonical_upstream_admissions(root, record)
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


def block_persisted_run(root: str | Path, run_id: str, reason: str) -> dict[str, Any]:
    """Record a terminal BLOCKED result for any failed canonical run stage."""
    record = _load_record(root, run_id)
    env = record["envelope"]
    if env["run_status"] != RunStatus.IN_PROGRESS.value:
        return dict(record)
    orchestrator = _replay_record(record)
    blocked = orchestrator.block(run_id, reason or "CANONICAL_STAGE_FAILED")
    return _persist_replayed(
        root, blocked, record["request_metadata"], previous=record
    )


def validate_complete_run_receipt(
    root: str | Path,
    run_id: str,
) -> dict[str, Any]:
    """Replay the complete receipt against the exact persisted Run Envelope."""
    path = run_receipt_path(root, run_id)
    if not path.is_file():
        raise CanonicalRunAuthorizationError("complete Run Receipt is absent")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalRunAuthorizationError("complete Run Receipt cannot be read") from exc
    fields = {
        "schema_version", "run_id", "case_id", "market", "symbol", "cutoff_date",
        "as_of_date", "orchestrator_version", "research_case_hash", "raw_request_sha256",
        "request_receipt_hash", "normalized_request_sha256", "stage_receipt_hashes",
        "stage_chain_hash", "evidence_manifest_hash", "semantic_artifact_hashes",
        "forecast_admission_hash", "valuation_admission_hash", "return_hash",
        "risk_portfolio_hash", "decision_admission_hash", "decision_revision",
        "publication_hash", "report_hash", "run_status", "receipt_hash",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != fields:
        raise CanonicalRunAuthorizationError("complete Run Receipt fields are invalid")
    if receipt["schema_version"] != RUN_RECEIPT_V02_SCHEMA_VERSION or receipt["run_id"] != run_id:
        raise CanonicalRunAuthorizationError("complete Run Receipt version/run_id mismatch")
    core = {k: receipt[k] for k in fields if k != "receipt_hash"}
    if not is_sha256(receipt["receipt_hash"]) or canonical_hash(core) != receipt["receipt_hash"]:
        raise CanonicalRunAuthorizationError("complete Run Receipt hash mismatch")
    record = _load_record(root, run_id)
    env = record["envelope"]
    if env["run_status"] != RunStatus.COMPLETE.value or env["stage_state"] != Stage.COMPLETE.value:
        raise CanonicalRunAuthorizationError("Run Envelope is not COMPLETE")
    metadata = record["request_metadata"]
    bindings = {
        "run_id": env["run_id"], "case_id": env["case_id"], "market": env["market"],
        "symbol": env["symbol"], "cutoff_date": env["cutoff_date"], "as_of_date": env["as_of_date"],
        "orchestrator_version": env["orchestrator_version"],
        "research_case_hash": env["research_case_hash"],
        "raw_request_sha256": metadata["raw_request_sha256"],
        "request_receipt_hash": metadata["request_receipt_hash"],
        "normalized_request_sha256": metadata["normalized_request_sha256"],
        "stage_receipt_hashes": record["stage_receipt_hashes"],
        "stage_chain_hash": record["stage_chain_hash"],
        "run_status": RunStatus.COMPLETE.value,
    }
    for key, expected in bindings.items():
        if receipt[key] != expected:
            raise CanonicalRunAuthorizationError(f"Run Receipt {key} does not match Run Envelope")
    stages = {x["stage_id"]: x for x in env["stage_receipts"]}
    for stage in (
        Stage.EVIDENCE_ADMITTED, Stage.SEMANTIC_ADMITTED, Stage.FORECAST_ADMITTED,
        Stage.VALUATION_ADMITTED, Stage.DECISION_ADMITTED,
        Stage.HUMAN_APPROVAL_PENDING, Stage.PUBLISHED, Stage.REPORTED, Stage.COMPLETE,
    ):
        if stage.value not in stages:
            raise CanonicalRunAuthorizationError("complete Run Receipt omits required stage " + stage.value)
    evidence = stages[Stage.EVIDENCE_ADMITTED.value]
    semantic = stages[Stage.SEMANTIC_ADMITTED.value]
    forecast = stages[Stage.FORECAST_ADMITTED.value]
    valuation = stages[Stage.VALUATION_ADMITTED.value]
    decision = stages[Stage.DECISION_ADMITTED.value]
    published = stages[Stage.PUBLISHED.value]
    reported = stages[Stage.REPORTED.value]
    if receipt["evidence_manifest_hash"] != evidence["output_hashes"][0]:
        raise CanonicalRunAuthorizationError("Run Receipt Evidence Manifest binding mismatch")
    if receipt["semantic_artifact_hashes"] != semantic["output_hashes"]:
        raise CanonicalRunAuthorizationError("Run Receipt semantic artifact binding mismatch")
    if receipt["forecast_admission_hash"] != forecast["output_hashes"][0]:
        raise CanonicalRunAuthorizationError("Run Receipt Forecast admission binding mismatch")
    if receipt["valuation_admission_hash"] != valuation["output_hashes"][0]:
        raise CanonicalRunAuthorizationError("Run Receipt Valuation admission binding mismatch")
    decision_hashes = dict(zip(decision["output_refs"], decision["output_hashes"]))
    for key, ref in (("return_hash", "return_metrics"), ("risk_portfolio_hash", "risk_portfolio"), ("decision_admission_hash", "decision_admission")):
        if receipt[key] != decision_hashes.get(ref):
            raise CanonicalRunAuthorizationError(f"Run Receipt {key} binding mismatch")
    revision_refs = [
        x for x in stages[Stage.HUMAN_APPROVAL_PENDING.value]["output_refs"]
        if re.search(r"-r([0-9]+)$", x)
    ]
    if len(revision_refs) != 1:
        raise CanonicalRunAuthorizationError("Run Receipt cannot identify one Decision Revision")
    revision_match = re.search(r"-r([0-9]+)$", revision_refs[0])
    assert revision_match is not None
    if receipt["decision_revision"] != int(revision_match.group(1)):
        raise CanonicalRunAuthorizationError("Run Receipt Decision Revision number mismatch")
    if receipt["publication_hash"] != published["output_hashes"][0]:
        raise CanonicalRunAuthorizationError("Run Receipt Publication binding mismatch")
    if not reported["output_hashes"] or receipt["report_hash"] != reported["output_hashes"][0]:
        raise CanonicalRunAuthorizationError("Run Receipt final report binding mismatch")
    return dict(receipt)


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
        "evidence_manifest_hash": evidence["output_hashes"][0],
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
    return validate_complete_run_receipt(root, run_id)


__all__ = [
    "RUN_STATE_SCHEMA_VERSION", "RUN_STAGE_AUTH_SCHEMA_VERSION",
    "RUN_RECEIPT_V02_SCHEMA_VERSION", "CanonicalRunAuthorizationError",
    "PersistedCanonicalResearchOrchestrator", "run_state_path", "run_receipt_path",
    "validate_run_state_record", "make_stage_authority_ref", "validate_stage_authority_ref",
    "authorize_decision_revision_write", "authorize_publication_write",
    "authorize_report_write", "advance_persisted_run", "block_persisted_run", "write_complete_run_receipt", "validate_complete_run_receipt",
]
