from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .execution_receipt_production import (
    build_execution_receipt,
    execution_receipt_path,
    replay_execution_receipt,
    validate_execution_receipt,
)
from .decision_lifecycle_production import (
    build_decision_revision,
    build_human_approval,
    project_current_approval,
    validate_current_projection,
    validate_decision_revision,
    validate_human_approval,
)
from .engine import canonical_json, replay, sha256_obj
from .trigger_production import (
    build_trigger_contract,
    build_trigger_event,
    validate_trigger_contract,
    validate_trigger_event,
)
from .monitoring_state import (
    apply_trigger_event,
    build_monitoring_state,
    validate_monitoring_state,
)

from .validation_replay import (
    build_monitoring_evaluation_record,
    build_monitoring_initialization_record,
    build_validation_record,
    validate_monitoring_evaluation_record,
    validate_monitoring_initialization_record,
    validate_validation_record,
)


def store_root(root: str | Path = "runs") -> Path:
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def snapshot_path(root: str | Path, snapshot_hash: str) -> Path:
    return store_root(root) / f"{snapshot_hash}.json"


def write_snapshot(root: str | Path, snapshot: dict[str, Any]) -> Path:
    path = snapshot_path(root, snapshot["snapshot_hash"])
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if canonical_json(existing) != canonical_json(snapshot):
            raise ValueError("snapshot hash collision or attempted overwrite")
        return path
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def read_snapshot(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or "snapshot_hash" not in value:
        raise ValueError("invalid IIOS snapshot")
    expected = sha256_obj({
        "snapshot_schema": value["snapshot_schema"],
        "engine_version": value["engine_version"],
        "input": value["input"],
        "decision": value["decision"],
    })
    if expected != value["snapshot_hash"]:
        raise ValueError("snapshot integrity check failed")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return value


def _atomic_create(path: Path, payload: dict[str, Any]) -> Path:
    if path.exists():
        existing = _load_json(path)
        if canonical_json(existing) != canonical_json(payload):
            raise ValueError(f"immutable object already exists with different content: {path.name}")
        return path
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    tmp.replace(path)
    return path


def _atomic_replace(path: Path, payload: dict[str, Any]) -> Path:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    tmp.replace(path)
    return path


def decision_series_id(market: str, symbol: str) -> str:
    return f"{market.upper()}-{symbol.upper()}"


def load_series(root: str | Path, series_id: str) -> dict[str, Any]:
    return _load_json(store_root(root) / f"{series_id}.series.json")


def create_or_load_series(
    root: str | Path,
    market: str,
    symbol: str,
    company: str,
    created_at: str,
) -> dict[str, Any]:
    sid = decision_series_id(market, symbol)
    payload = {
        "decision_series_id": sid,
        "company_id": sid,
        "market": market.upper(),
        "symbol": symbol.upper(),
        "company_name": company,
        "created_at": created_at,
        "schema_version": "IIOS-SERIES-1.0",
    }
    series = _load_json(
        _atomic_create(store_root(root) / f"{sid}.series.json", payload)
    )
    index_path = store_root(root) / f"{sid}.index.json"
    if not index_path.exists():
        _atomic_create(index_path, {"next_revision": 1})
    return series


def _index_path(root: str | Path, series_id: str) -> Path:
    return store_root(root) / f"{series_id}.index.json"


def next_revision(root: str | Path, series_id: str) -> int:
    index = _load_json(_index_path(root, series_id))
    value = index.get("next_revision", 1)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("revision index next_revision must be a positive integer")
    return value


def _decision_path(root: str | Path, decision_id: str) -> Path:
    return store_root(root) / f"{decision_id}.decision.json"


def _approval_path(root: str | Path, decision_id: str) -> Path:
    return store_root(root) / f"{decision_id}.approval.json"


def _current_path(root: str | Path, series_id: str) -> Path:
    return store_root(root) / f"{series_id}.current.json"


def _load_revision(root: str | Path, decision_id: str) -> dict[str, Any]:
    record = _load_json(_decision_path(root, decision_id))
    if not record:
        raise ValueError("decision revision not found")
    return record


def write_decision_revision(
    root: str | Path,
    series_id: str,
    revision: int,
    snapshot: dict[str, Any],
    run_id: str,
    trigger_event_id: str | None = None,
    decision_admission: dict[str, Any] | None = None,
) -> Path:
    from .canonical_run_authority_v01 import (
        CanonicalRunAuthorizationError,
        authorize_decision_revision_write,
        advance_persisted_run,
        run_state_path,
        validate_run_state_record,
        validate_stage_authority_ref,
    )
    from .canonical_research_orchestrator import Stage

    if snapshot.get("snapshot_schema") != "IIOS-MVP-SNAPSHOT-0.3.0":
        raise CanonicalRunAuthorizationError(
            "NON_CANONICAL: only v0.3 snapshots may be persisted as formal Decision Revisions"
        )
    if decision_admission is None:
        raise CanonicalRunAuthorizationError(
            "BLOCKED: canonical v0.3 Decision Revision requires a Decision Admission receipt"
        )
    if run_id != decision_admission.get("run_id", run_id):
        raise CanonicalRunAuthorizationError("Decision Admission run binding mismatch")

    expected_revision = next_revision(root, series_id)
    series = load_series(root, series_id)
    if not series:
        raise ValueError("decision series not found")
    input_data = snapshot.get("input")
    if not isinstance(input_data, dict):
        raise ValueError("snapshot input is required for series identity binding")
    identity_pairs = (
        ("market", "market"),
        ("symbol", "symbol"),
        ("company", "company_name"),
    )
    for field, series_field in identity_pairs:
        snapshot_value = str(input_data.get(field, "")).strip()
        series_value = str(series.get(series_field, "")).strip()
        if field != "company":
            snapshot_value = snapshot_value.upper()
            series_value = series_value.upper()
        if not snapshot_value or snapshot_value != series_value:
            raise ValueError(f"decision series identity mismatch: {field}")

    canonical_decision_id = f"{series_id}-r{revision:03d}"
    path = _decision_path(root, canonical_decision_id)
    if path.exists():
        existing = _load_revision(root, canonical_decision_id)
        validate_decision_revision(
            existing,
            case_id=str(input_data.get("case_id")),
            cutoff_date=str(input_data.get("cutoff_date")),
        )
        if (
            existing.get("snapshot_hash") != snapshot.get("snapshot_hash")
            or existing.get("run_id") != run_id
            or existing.get("decision_admission") != decision_admission
        ):
            raise CanonicalRunAuthorizationError(
                "immutable Decision Revision does not match this request/run/admission"
            )
        validate_stage_authority_ref(
            root,
            existing.get("run_authority_ref"),
            required_stage=Stage.DECISION_ADMITTED,
            required_hashes=(
                str(snapshot.get("snapshot_hash")),
                str(decision_admission.get("admission_record_hash")),
            ),
        )
        state_path = run_state_path(root, run_id)
        state = validate_run_state_record(json.loads(state_path.read_text(encoding="utf-8")))
        if state["envelope"]["stage_state"] == Stage.DECISION_ADMITTED.value:
            advance_persisted_run(
                root, run_id, Stage.HUMAN_APPROVAL_PENDING,
                input_refs=("snapshot", "decision_admission"),
                input_hashes=(
                    str(snapshot["snapshot_hash"]),
                    str(decision_admission["admission_record_hash"]),
                ),
                output_refs=(existing["decision_id"], f"revision:{revision}"),
                output_hashes=(existing["revision_hash"],),
            )
        return path

    if revision != expected_revision:
        raise ValueError(
            f"revision {revision} is not the next canonical revision; expected {expected_revision}"
        )
    run_authority_ref = authorize_decision_revision_write(
        root,
        run_id=run_id,
        snapshot=snapshot,
        decision_admission=decision_admission,
    )
    payload = build_decision_revision(
        decision_series_id=series_id,
        revision=revision,
        snapshot=snapshot,
        run_id=run_id,
        trigger_event_id=trigger_event_id,
        decision_admission=decision_admission,
        run_authority_ref=run_authority_ref,
    )
    _atomic_create(path, payload)
    _atomic_replace(_index_path(root, series_id), {"next_revision": revision + 1})

    # Writing a revision advances the persisted run into the only stage that
    # permits publication. A caller-provided string run_id alone is insufficient.
    advance_persisted_run(
        root, run_id, Stage.HUMAN_APPROVAL_PENDING,
        input_refs=("snapshot", "decision_admission"),
        input_hashes=(
            str(snapshot["snapshot_hash"]),
            str(decision_admission["admission_record_hash"]),
        ),
        output_refs=(payload["decision_id"], f"revision:{revision}"),
        output_hashes=(payload["revision_hash"],),
    )
    return path

def write_human_approval(
    root: str | Path,
    snapshot: dict[str, Any],
    approved: bool,
    note: str,
    decision_id: str | None = None,
    actor_identity: str | None = None,
    authorization_method: str = "HUMAN_AUTHENTICATED",
) -> Path:
    if not decision_id:
        raise ValueError("decision_id is required")
    revision = _load_revision(root, decision_id)
    if revision["snapshot_hash"] != snapshot.get("snapshot_hash"):
        raise ValueError("decision revision and snapshot are not bound to the same snapshot")
    if not actor_identity:
        raise ValueError("actor_identity is required for human approval")
    approval = build_human_approval(
        decision_revision=revision,
        approved=approved,
        note=note,
        actor_identity=actor_identity,
        authorization_method=authorization_method,
    )
    return _atomic_create(_approval_path(root, decision_id), approval)


def approve_revision(
    root: str | Path,
    decision_id: str,
    snapshot: dict[str, Any],
    approved: bool,
    note: str,
    actor_identity: str | None = None,
    authorization_method: str = "HUMAN_AUTHENTICATED",
) -> dict[str, Any]:
    revision = _load_revision(root, decision_id)
    if revision["snapshot_hash"] != snapshot.get("snapshot_hash"):
        raise ValueError("decision revision and snapshot are not bound to the same snapshot")
    if not actor_identity:
        raise ValueError("actor_identity is required for human approval")
    approval_path = write_human_approval(
        root,
        snapshot,
        approved,
        note,
        decision_id,
        actor_identity=actor_identity,
        authorization_method=authorization_method,
    )
    approval = _load_json(approval_path)
    validate_human_approval(approval, decision_revision=revision)

    current_path = _current_path(root, revision["decision_series_id"])
    current = _load_json(current_path) if current_path.exists() else None
    projected = project_current_approval(
        previous=current,
        decision_revision=revision,
        approval=approval,
    )

    if projected.get("projection_status") == "CURRENT":
        _atomic_replace(current_path, projected)
        return {
            "decision_id": decision_id,
            "status": "HUMAN_APPROVED",
            "current": True,
            "approval": str(approval_path),
            "current_projection": str(current_path),
        }

    return {
        "decision_id": decision_id,
        "status": "HUMAN_REJECTED" if not approved else "HUMAN_APPROVED",
        "current": bool(
            current and current.get("current_decision_id") == decision_id
        ),
        "approval": str(approval_path),
        "current_projection": str(current_path) if current_path.exists() else None,
    }


def replay_decision_lifecycle(
    root: str | Path,
    decision_id: str,
) -> dict[str, Any]:
    revision = _load_revision(root, decision_id)
    validate_decision_revision(
        revision,
        case_id=revision["case_id"],
        cutoff_date=revision["cutoff_date"],
    )

    snapshot = read_snapshot(
        snapshot_path(root, revision["snapshot_hash"])
    )
    expected_revision = build_decision_revision(
        decision_series_id=revision["decision_series_id"],
        revision=revision["revision"],
        snapshot=snapshot,
        run_id=revision["run_id"],
        trigger_event_id=revision["trigger_event_id"],
        decision_admission=revision["decision_admission"],
        run_authority_ref=revision.get("run_authority_ref"),
    )
    if canonical_json(expected_revision) != canonical_json(revision):
        raise ValueError("decision revision replay mismatch")

    series_prefix = revision["decision_series_id"] + "-r"
    revision_files = sorted(
        store_root(root).glob(f"{series_prefix}*.decision.json"),
        key=lambda p: int(
            p.name.removesuffix(".decision.json").rsplit("-r", 1)[1]
        ),
    )
    if not revision_files:
        raise ValueError("decision revision history is empty")
    records = []
    for path in revision_files:
        record = _load_json(path)
        if record["case_id"] != revision["case_id"]:
            raise ValueError("decision revision history contains a different case_id")
        validate_decision_revision(
            record,
            case_id=record["case_id"],
            cutoff_date=record["cutoff_date"],
        )
        historical_snapshot = read_snapshot(
            snapshot_path(root, record["snapshot_hash"])
        )
        expected_historical_revision = build_decision_revision(
            decision_series_id=record["decision_series_id"],
            revision=record["revision"],
            snapshot=historical_snapshot,
            run_id=record["run_id"],
            trigger_event_id=record["trigger_event_id"],
            decision_admission=record["decision_admission"],
            run_authority_ref=record.get("run_authority_ref"),
        )
        if canonical_json(expected_historical_revision) != canonical_json(record):
            raise ValueError(
                f"decision revision replay mismatch: {record['decision_id']}"
            )
        records.append(record)

    numbers = [record["revision"] for record in records]
    if numbers != list(range(1, max(numbers) + 1)):
        raise ValueError("decision revision history is not contiguous")

    current: dict[str, Any] | None = None
    approval_status = "PENDING"
    for record in records:
        approval_path = _approval_path(root, record["decision_id"])
        if not approval_path.exists():
            continue
        approval = _load_json(approval_path)
        validate_human_approval(approval, decision_revision=record)
        if record["decision_id"] == decision_id:
            approval_status = approval["approval_status"]
        projected = project_current_approval(
            previous=current,
            decision_revision=record,
            approval=approval,
        )
        if projected.get("projection_status") == "CURRENT":
            current = projected

    current_exists = _current_path(root, revision["decision_series_id"]).exists()
    persisted_current = (
        _load_json(_current_path(root, revision["decision_series_id"]))
        if current_exists
        else None
    )
    if persisted_current is not None:
        validate_current_projection(persisted_current)
        if current is None or canonical_json(persisted_current) != canonical_json(current):
            raise ValueError("current projection replay mismatch")
    elif current is not None:
        raise ValueError("current projection is missing from persistent store")

    return {
        "replay_status": "PASS",
        "decision_id": decision_id,
        "decision_revision": revision["revision"],
        "approval_status": approval_status,
        "current_decision_id": current["current_decision_id"] if current else None,
        "current_revision": current["current_revision"] if current else None,
        "snapshot_hash": revision["snapshot_hash"],
    }


def _trigger_contract_path(root: str | Path, trigger_id: str) -> Path:
    return store_root(root) / f"{trigger_id}.trigger.json"


def _trigger_event_path(root: str | Path, trigger_event_id: str) -> Path:
    return store_root(root) / f"{trigger_event_id}.event.json"


def _validate_trigger_revision_binding(
    root: str | Path,
    *,
    decision_id: str,
    decision_series_id: str,
    revision: int,
    decision_revision_hash: str,
    case_id: str,
    decision_cutoff_date: str,
) -> None:
    revision_record = _load_revision(root, decision_id)
    validate_decision_revision(
        revision_record,
        case_id=revision_record["case_id"],
        cutoff_date=revision_record["cutoff_date"],
    )
    expected = {
        "decision_id": revision_record["decision_id"],
        "decision_series_id": revision_record["decision_series_id"],
        "revision": revision_record["revision"],
        "decision_revision_hash": revision_record["revision_hash"],
        "case_id": revision_record["case_id"],
        "decision_cutoff_date": revision_record["cutoff_date"],
    }
    actual = {
        "decision_id": decision_id,
        "decision_series_id": decision_series_id,
        "revision": revision,
        "decision_revision_hash": decision_revision_hash,
        "case_id": case_id,
        "decision_cutoff_date": decision_cutoff_date,
    }
    if actual != expected:
        raise ValueError("trigger contract is not bound to the persisted decision revision")


def _load_trigger_contract(root: str | Path, trigger_id: str) -> dict[str, Any]:
    record = _load_json(_trigger_contract_path(root, trigger_id))
    if not record:
        raise ValueError("trigger contract not found")
    validate_trigger_contract(record)
    _validate_trigger_revision_binding(
        root,
        decision_id=record["decision_id"],
        decision_series_id=record["decision_series_id"],
        revision=record["revision"],
        decision_revision_hash=record["decision_revision_hash"],
        case_id=record["case_id"],
        decision_cutoff_date=record["decision_cutoff_date"],
    )
    return record


def write_trigger_contract(root: str | Path, decision_id: str, contract: dict[str, Any]) -> Path:
    payload = dict(contract)
    payload["decision_id"] = decision_id
    payload.pop("contract_version", None)
    payload.pop("trigger_hash", None)
    fields = {
        "trigger_id",
        "decision_id",
        "decision_series_id",
        "revision",
        "decision_revision_hash",
        "case_id",
        "decision_cutoff_date",
        "role",
        "metric_id",
        "operator",
        "target",
        "unit",
        "evidence_ids",
        "enabled",
    }
    if set(payload) != fields:
        raise ValueError("trigger contract input fields are invalid")
    canonical = build_trigger_contract(**payload)
    _validate_trigger_revision_binding(
        root,
        decision_id=canonical["decision_id"],
        decision_series_id=canonical["decision_series_id"],
        revision=canonical["revision"],
        decision_revision_hash=canonical["decision_revision_hash"],
        case_id=canonical["case_id"],
        decision_cutoff_date=canonical["decision_cutoff_date"],
    )
    path = _trigger_contract_path(root, canonical["trigger_id"])
    return _atomic_create(path, canonical)


def write_trigger_event(root: str | Path, event: dict[str, Any]) -> Path:
    payload = dict(event)
    trigger_id = payload.get("trigger_id")
    if not isinstance(trigger_id, str) or not trigger_id.strip():
        raise ValueError("trigger_id is required for trigger event")
    contract = _load_trigger_contract(root, trigger_id)
    payload.pop("trigger_id", None)
    fields = {
        "trigger_event_id",
        "evaluation_cutoff_at",
        "observed_at",
        "known_at",
        "source_id",
        "evidence_id",
        "value",
        "previous_value",
    }
    if set(payload) != fields:
        raise ValueError("trigger event input fields are invalid")
    canonical = build_trigger_event(trigger_contract=contract, **payload)
    path = _trigger_event_path(root, canonical["trigger_event_id"])
    existing = _load_json(path) if path.exists() else None
    if existing is not None:
        validate_trigger_event(existing, trigger_contract=contract)
    return _atomic_create(path, canonical)


def _monitoring_state_path(root: str | Path, trigger_id: str) -> Path:
    return store_root(root) / f"{trigger_id}.monitor.json"


def _monitoring_initialization_path(root: str | Path, trigger_id: str) -> Path:
    return store_root(root) / f"{trigger_id}.monitor.initial.json"


def _monitoring_evaluation_path(root: str | Path, trigger_event_id: str) -> Path:
    return store_root(root) / f"{trigger_event_id}.evaluation.json"


def _validation_path(root: str | Path, validation_id: str) -> Path:
    return store_root(root) / f"{validation_id}.validation.json"


def initialize_monitoring_state(
    root: str | Path,
    trigger_id: str,
    monitor_id: str,
    lifecycle_status: str = "ACTIVE",
    next_due_at: str | None = None,
    evaluation_reference_at: str | None = None,
) -> Path:
    contract = _load_trigger_contract(root, trigger_id)
    state = build_monitoring_state(
        monitor_id=monitor_id,
        trigger_contract=contract,
        lifecycle_status=lifecycle_status,
        next_due_at=next_due_at,
        evaluation_reference_at=evaluation_reference_at,
    )
    initialization = build_monitoring_initialization_record(
        trigger_contract=contract,
        initial_state=state,
    )
    _atomic_create(_monitoring_initialization_path(root, trigger_id), initialization)
    return _atomic_create(_monitoring_state_path(root, trigger_id), state)


def _load_monitoring_initialization(
    root: str | Path,
    trigger_id: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    record = _load_json(_monitoring_initialization_path(root, trigger_id))
    if not record:
        raise ValueError("monitoring initialization record not found")
    validate_monitoring_initialization_record(record, trigger_contract=contract)
    return record


def _load_monitoring_events(
    root: str | Path,
    trigger_id: str,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in store_root(root).glob("*.event.json"):
        record = _load_json(path)
        if record.get("trigger_id") == trigger_id:
            events.append(record)
    events.sort(key=lambda record: (record["known_at"], record["trigger_event_id"]))
    return events


def _load_monitoring_evaluation(
    root: str | Path,
    trigger_event_id: str,
) -> dict[str, Any]:
    record = _load_json(_monitoring_evaluation_path(root, trigger_event_id))
    if not record:
        raise ValueError(
            f"monitoring evaluation record not found for event: {trigger_event_id}"
        )
    return record


def apply_monitoring_event(
    root: str | Path,
    trigger_event_id: str,
    next_due_at: str | None = None,
) -> Path:
    event_path = _trigger_event_path(root, trigger_event_id)
    event = _load_json(event_path)
    if not event:
        raise ValueError("trigger event not found")
    trigger_id = event.get("trigger_id")
    if not isinstance(trigger_id, str) or not trigger_id.strip():
        raise ValueError("trigger event trigger_id is required")
    contract = _load_trigger_contract(root, trigger_id)
    state_path = _monitoring_state_path(root, trigger_id)
    previous = _load_json(state_path)
    if not previous:
        raise ValueError("monitoring state not initialized")
    validate_monitoring_state(previous, trigger_contract=contract)
    validate_trigger_event(event, trigger_contract=contract)
    if event["trigger_event_id"] == previous.get("last_event_id"):
        existing_evaluation = _load_json(
            _monitoring_evaluation_path(root, event["trigger_event_id"])
        )
        if not existing_evaluation:
            raise ValueError("idempotent monitoring event is missing its immutable evaluation record")
        return state_path
    updated = apply_trigger_event(
        previous_state=previous,
        trigger_contract=contract,
        trigger_event=event,
        next_due_at=next_due_at,
    )
    evaluation = build_monitoring_evaluation_record(
        trigger_contract=contract,
        trigger_event=event,
        previous_state=previous,
        resulting_state=updated,
    )
    _atomic_create(_monitoring_evaluation_path(root, trigger_event_id), evaluation)
    return _atomic_replace(state_path, updated)


def replay_monitoring_state(root: str | Path, trigger_id: str) -> dict[str, Any]:
    contract = _load_trigger_contract(root, trigger_id)
    state_path = _monitoring_state_path(root, trigger_id)
    persisted = _load_json(state_path)
    if not persisted:
        raise ValueError("monitoring state not initialized")
    validate_monitoring_state(persisted, trigger_contract=contract)
    initialization = _load_monitoring_initialization(root, trigger_id, contract)
    replayed = dict(initialization["initial_state"])
    events = _load_monitoring_events(root, trigger_id)
    seen: set[str] = set()
    for event in events:
        event_id = event["trigger_event_id"]
        if event_id in seen:
            raise ValueError(f"duplicate trigger_event_id in monitoring history: {event_id}")
        seen.add(event_id)
        validate_trigger_event(event, trigger_contract=contract)
        evaluation = _load_monitoring_evaluation(root, event_id)
        validate_monitoring_evaluation_record(
            evaluation,
            trigger_contract=contract,
            trigger_event=event,
            previous_state=replayed,
            resulting_state=apply_trigger_event(
                previous_state=replayed,
                trigger_contract=contract,
                trigger_event=event,
                next_due_at=evaluation.get("resulting_next_due_at"),
            ),
        )
        if evaluation["previous_state_hash"] != replayed["state_hash"]:
            raise ValueError(
                f"monitoring evaluation history previous_state_hash mismatch: {event_id}"
            )
        replayed = apply_trigger_event(
            previous_state=replayed,
            trigger_contract=contract,
            trigger_event=event,
            next_due_at=evaluation["resulting_next_due_at"],
        )
        if evaluation["resulting_state_hash"] != replayed["state_hash"]:
            raise ValueError(
                f"monitoring evaluation history resulting_state_hash mismatch: {event_id}"
            )
    validate_monitoring_state(replayed, trigger_contract=contract)
    if canonical_json(replayed) != canonical_json(persisted):
        raise ValueError("monitoring state replay mismatch")
    return {
        "replay_status": "PASS",
        "trigger_id": trigger_id,
        "monitor_id": persisted["monitor_id"],
        "last_event_id": persisted["last_event_id"],
        "evaluation_status": persisted["evaluation_status"],
        "last_trigger_state": persisted["last_trigger_state"],
        "due_state": persisted["due_state"],
        "state_hash": persisted["state_hash"],
        "event_count": len(events),
        "initial_state_hash": initialization["initial_state_hash"],
        "history_head_hash": (
            _load_monitoring_evaluation(root, events[-1]["trigger_event_id"])["evaluation_hash"]
            if events
            else initialization["initialization_hash"]
        ),
    }


def validate_monitoring_chain(
    root: str | Path,
    trigger_id: str,
    validation_cutoff_at: str,
    validation_id: str | None = None,
) -> dict[str, Any]:
    contract = _load_trigger_contract(root, trigger_id)
    state_path = _monitoring_state_path(root, trigger_id)
    persisted = _load_json(state_path)
    if not persisted:
        raise ValueError("monitoring state not initialized")
    validate_monitoring_state(persisted, trigger_contract=contract)
    initialization = _load_monitoring_initialization(root, trigger_id, contract)
    events = _load_monitoring_events(root, trigger_id)

    checks = {
        "decision_revision_replay": "PASS",
        "trigger_contract_binding": "PASS",
        "trigger_event_pit": "PASS",
        "monitoring_state_integrity": "PASS",
        "transition_history": "PASS",
        "monitoring_replay": "PASS",
    }
    issues: list[str] = []

    try:
        replay_decision_lifecycle(root, contract["decision_id"])
    except Exception as exc:
        checks["decision_revision_replay"] = "FAIL"
        issues.append(f"decision_revision_replay: {exc}")

    try:
        _load_trigger_contract(root, trigger_id)
    except Exception as exc:
        checks["trigger_contract_binding"] = "FAIL"
        issues.append(f"trigger_contract_binding: {exc}")

    from .validation_replay import _timestamp
    normalized_validation_cutoff = _timestamp(validation_cutoff_at, "validation_cutoff_at")
    cutoff_dt = __import__("datetime").datetime.fromisoformat(
        normalized_validation_cutoff.replace("Z", "+00:00")
    )
    for event in events:
        try:
            validate_trigger_event(event, trigger_contract=contract)
            known_dt = __import__("datetime").datetime.fromisoformat(event["known_at"].replace("Z", "+00:00"))
            eval_dt = __import__("datetime").datetime.fromisoformat(event["evaluation_cutoff_at"].replace("Z", "+00:00"))
            if known_dt > cutoff_dt or eval_dt > cutoff_dt:
                raise ValueError("event is newer than validation_cutoff_at")
        except Exception as exc:
            checks["trigger_event_pit"] = "FAIL"
            issues.append(f"trigger_event_pit[{event.get('trigger_event_id')}]: {exc}")

    try:
        validate_monitoring_initialization_record(
            initialization,
            trigger_contract=contract,
        )
        validate_monitoring_state(persisted, trigger_contract=contract)
    except Exception as exc:
        checks["monitoring_state_integrity"] = "FAIL"
        issues.append(f"monitoring_state_integrity: {exc}")

    replayed = dict(initialization["initial_state"])
    history_head_hash = initialization["initialization_hash"]
    try:
        seen: set[str] = set()
        for event in events:
            event_id = event["trigger_event_id"]
            if event_id in seen:
                raise ValueError(f"duplicate trigger_event_id: {event_id}")
            seen.add(event_id)
            validate_trigger_event(event, trigger_contract=contract)
            evaluation = _load_monitoring_evaluation(root, event_id)
            candidate = apply_trigger_event(
                previous_state=replayed,
                trigger_contract=contract,
                trigger_event=event,
                next_due_at=evaluation.get("resulting_next_due_at"),
            )
            validate_monitoring_evaluation_record(
                evaluation,
                trigger_contract=contract,
                trigger_event=event,
                previous_state=replayed,
                resulting_state=candidate,
            )
            if evaluation["previous_state_hash"] != replayed["state_hash"]:
                raise ValueError(f"previous_state_hash mismatch for {event_id}")
            replayed = candidate
            if evaluation["resulting_state_hash"] != replayed["state_hash"]:
                raise ValueError(f"resulting_state_hash mismatch for {event_id}")
            history_head_hash = evaluation["evaluation_hash"]
    except Exception as exc:
        checks["transition_history"] = "FAIL"
        checks["monitoring_replay"] = "FAIL"
        issues.append(f"transition_history: {exc}")

    if checks["monitoring_replay"] == "PASS":
        try:
            validate_monitoring_state(replayed, trigger_contract=contract)
            if canonical_json(replayed) != canonical_json(persisted):
                raise ValueError("replayed state does not equal persisted state")
        except Exception as exc:
            checks["monitoring_replay"] = "FAIL"
            issues.append(f"monitoring_replay: {exc}")

    record = build_validation_record(
        validation_id=(
            validation_id
            if validation_id is not None
            else f"{trigger_id}-validation-{normalized_validation_cutoff.replace(':', '').replace('+', 'p')}"
        ),
        trigger_contract=contract,
        monitor_id=persisted["monitor_id"],
        validation_cutoff_at=_timestamp(validation_cutoff_at, "validation_cutoff_at"),
        checks=checks,
        checked_event_ids=[event["trigger_event_id"] for event in events],
        initial_state_hash=initialization["initial_state_hash"],
        replayed_state_hash=replayed["state_hash"] if checks["monitoring_replay"] == "PASS" else None,
        persisted_state_hash=persisted["state_hash"],
        history_head_hash=history_head_hash,
        issues=issues,
    )
    return record


def write_monitoring_validation(
    root: str | Path,
    trigger_id: str,
    validation_cutoff_at: str,
    validation_id: str | None = None,
) -> Path:
    record = validate_monitoring_chain(
        root,
        trigger_id,
        validation_cutoff_at,
        validation_id=validation_id,
    )
    path = _validation_path(root, record["validation_id"])
    return _atomic_create(path, record)


def replay_monitoring_validation(root: str | Path, validation_id: str) -> dict[str, Any]:
    record = _load_json(_validation_path(root, validation_id))
    if not record:
        raise ValueError("validation record not found")
    validate_validation_record(record)
    fresh = validate_monitoring_chain(
        root,
        record["trigger_id"],
        record["validation_cutoff_at"],
        validation_id=record["validation_id"],
    )
    if fresh["validation_id"] != record["validation_id"] or canonical_json(fresh) != canonical_json(record):
        raise ValueError("validation replay mismatch")
    return {
        "validation_replay_status": "PASS",
        "validation_id": validation_id,
        "validation_status": record["validation_status"],
        "event_count": record["event_count"],
        "validation_hash": record["validation_hash"],
    }



def write_execution_receipt(
    root: str | Path,
    execution_receipt_id: str,
    decision_id: str,
    snapshot: dict[str, Any],
    executed_at: str,
    execution_status: str,
    actor_identity: str,
    executed_quantity: Any = None,
    executed_position_pct: Any = None,
    executed_price: Any = None,
) -> Path:
    revision = _load_revision(root, decision_id)
    if revision["snapshot_hash"] != snapshot.get("snapshot_hash"):
        raise ValueError("execution receipt and snapshot are not bound to the same snapshot")
    approval_path = _approval_path(root, decision_id)
    if not approval_path.exists():
        raise ValueError("human approval is required before execution receipt")
    approval = _load_json(approval_path)
    receipt = build_execution_receipt(
        execution_receipt_id=execution_receipt_id,
        decision_revision=revision,
        human_approval=approval,
        executed_at=executed_at,
        execution_status=execution_status,
        executed_quantity=executed_quantity,
        executed_position_pct=executed_position_pct,
        executed_price=executed_price,
        actor_identity=actor_identity,
    )
    return _atomic_create(
        execution_receipt_path(root, execution_receipt_id),
        receipt,
    )


def read_execution_receipt(path: str | Path) -> dict[str, Any]:
    record = _load_json(Path(path))
    validate_execution_receipt(record)
    return record


def replay_persisted_execution_receipt(
    root: str | Path,
    execution_receipt_id: str,
) -> dict[str, Any]:
    record = read_execution_receipt(execution_receipt_path(root, execution_receipt_id))
    revision = _load_revision(root, record["decision_id"])
    snapshot = read_snapshot(snapshot_path(root, revision["snapshot_hash"]))
    if record["snapshot_hash"] != snapshot["snapshot_hash"]:
        raise ValueError("execution receipt snapshot binding mismatch")
    approval = _load_json(_approval_path(root, record["decision_id"]))
    validate_human_approval(approval, decision_revision=revision)
    return replay_execution_receipt(
        record,
        decision_revision=revision,
        human_approval=approval,
    )
