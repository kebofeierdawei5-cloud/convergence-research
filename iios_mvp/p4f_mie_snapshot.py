from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .market_implied_expectation import MIEQualification
from .multi_model_market_implied_expectation_set import (
    MIEModelEvaluationState,
    MIESetResolutionState,
    MultiModelMarketImpliedExpectationSet,
)

P4F_SNAPSHOT_SCHEMA = "IIOS-MIE-SNAPSHOT-0.3"
P4F_VERSION = "P4-F-0.3"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _sha256_obj(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()

def _parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date") from exc

def _parse_datetime(value: Any, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO datetime") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result

@dataclass(frozen=True)
class P4FProvenanceRecord:
    evidence_id: str
    variable: str
    unit: str
    basis: str
    observation_date: date
    known_at: datetime
    source: str
    source_location: str
    content_sha256: str
    captured_at: datetime
    value: Decimal | None = None

    def validate(self, cutoff_date: date) -> None:
        if not self.evidence_id or not self.variable or not self.unit or not self.basis:
            raise ValueError("P4-F provenance identity and semantic metadata are required")
        if not self.source or not self.source_location:
            raise ValueError("P4-F provenance source and source_location are required")
        if not _SHA256_RE.fullmatch(self.content_sha256):
            raise ValueError("P4-F provenance content_sha256 must be 64 lowercase hex characters")
        if self.observation_date > cutoff_date:
            raise ValueError("P4-F PIT violation: observation_date is after cutoff")
        if self.known_at.date() > cutoff_date:
            raise ValueError("P4-F PIT violation: known_at is after cutoff")
        if self.captured_at.tzinfo is None or self.known_at.tzinfo is None:
            raise ValueError("P4-F provenance timestamps must be timezone-aware")
        if self.value is not None and not self.value.is_finite():
            raise ValueError("P4-F provenance value must be finite")

    def to_dict(self) -> dict[str, Any]:
        result = {
            "evidence_id": self.evidence_id, "variable": self.variable, "unit": self.unit,
            "basis": self.basis, "observation_date": self.observation_date.isoformat(),
            "known_at": self.known_at.isoformat(), "source": self.source,
            "source_location": self.source_location, "content_sha256": self.content_sha256,
            "captured_at": self.captured_at.isoformat(),
        }
        if self.value is not None:
            result["value"] = str(self.value)
        return result

def _model_evaluation_from_dict(item: Mapping[str, Any]) -> tuple[str, str]:
    model_id = item.get("model_id")
    state = item.get("state")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("P4-F model evaluation model_id is required")
    if state not in {x.value for x in MIEModelEvaluationState}:
        raise ValueError("P4-F model evaluation state is invalid")
    expectation = item.get("expectation")
    if state == MIEModelEvaluationState.MATERIALIZED.value:
        if not isinstance(expectation, dict):
            raise ValueError("P4-F MATERIALIZED evaluation requires expectation")
        if expectation.get("model_id") != model_id:
            raise ValueError("P4-F model evaluation model_id/expectation mismatch")
    elif expectation is not None:
        raise ValueError("P4-F non-materialized evaluation cannot carry expectation")
    return model_id, state

def _expected_set_semantics(mie_set: Mapping[str, Any]) -> tuple[str, str]:
    coverage = mie_set.get("candidate_coverage") or {}
    sufficiency = mie_set.get("evidence_sufficiency") or {}
    evaluations = mie_set.get("model_evaluations") or []
    candidate_ids = coverage.get("candidate_model_ids") or []
    if not isinstance(candidate_ids, list) or not candidate_ids or len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("P4-F candidate coverage is invalid")
    eval_pairs = [_model_evaluation_from_dict(x) for x in evaluations]
    eval_ids = [x[0] for x in eval_pairs]
    if len(eval_ids) != len(set(eval_ids)) or set(eval_ids) != set(candidate_ids):
        raise ValueError("P4-F model evaluations do not exactly cover candidate models")
    if coverage.get("status") != "SUFFICIENT" or sufficiency.get("status") != "SUFFICIENT":
        return MIESetResolutionState.INSUFFICIENT_EVIDENCE.value, MIEQualification.BLOCKED.value
    states = [x[1] for x in eval_pairs]
    if MIEModelEvaluationState.OUTSIDE_HISTORICAL_SUPPORT.value in states:
        return MIESetResolutionState.NO_DECISION_GRADE_MODEL.value, MIEQualification.BLOCKED.value
    if MIEModelEvaluationState.BLOCKED.value in states:
        return MIESetResolutionState.INSUFFICIENT_EVIDENCE.value, MIEQualification.BLOCKED.value
    materialized = states.count(MIEModelEvaluationState.MATERIALIZED.value)
    if materialized == 0:
        return MIESetResolutionState.NO_FEASIBLE_MODEL.value, MIEQualification.BLOCKED.value
    if materialized > 1:
        return MIESetResolutionState.AMBIGUOUS.value, MIEQualification.CONDITIONAL_ONLY.value
    expectation = next(x.get("expectation") for x in evaluations if x.get("state") == MIEModelEvaluationState.MATERIALIZED.value)
    q = (expectation or {}).get("qualification")
    if q not in {x.value for x in MIEQualification}:
        raise ValueError("P4-F materialized expectation qualification is invalid")
    return MIESetResolutionState.UNIQUE_MODEL.value, q

def _validate_mie_observation_and_evidence(mie_set: Mapping[str, Any], provenance: Mapping[str, P4FProvenanceRecord], cutoff_date: date) -> None:
    referenced_ids = set(mie_set.get("evidence_ids") or [])
    for item in (mie_set.get("candidate_coverage") or {}).get("evidence_ids") or []:
        referenced_ids.add(item)
    for item in (mie_set.get("evidence_sufficiency") or {}).get("evidence_ids") or []:
        referenced_ids.add(item)
    materialized = []
    for evaluation in mie_set.get("model_evaluations") or []:
        for item in evaluation.get("evidence_ids") or []:
            referenced_ids.add(item)
        expectation = evaluation.get("expectation")
        if expectation is not None:
            materialized.append(expectation)
            for item in expectation.get("evidence_ids") or []:
                referenced_ids.add(item)
            for req in expectation.get("economic_requirements") or []:
                referenced_ids.update(req.get("evidence_ids") or [])
            for assumption in expectation.get("assumption_set") or []:
                referenced_ids.update(assumption.get("evidence_ids") or [])
            obs = expectation.get("observation_basis") or {}
            if _parse_date(obs.get("cutoff_date"), "observation_basis.cutoff_date") != cutoff_date:
                raise ValueError("P4-F MIE cutoff_date does not equal snapshot cutoff_date")
            if _parse_date(obs.get("observation_date"), "observation_basis.observation_date") > cutoff_date:
                raise ValueError("P4-F MIE observation_date is after snapshot cutoff")
            price_id = obs.get("price_observation_id")
            if not price_id:
                raise ValueError("P4-F price_observation_id is required")
            referenced_ids.add(price_id)
            price = provenance.get(price_id)
            if price is None:
                raise ValueError("P4-F price observation provenance is missing")
            price.validate(cutoff_date)
            if price.variable != "market_price":
                raise ValueError("P4-F price observation provenance must use variable=market_price")
            if price.observation_date != _parse_date(obs.get("observation_date"), "observation_basis.observation_date"):
                raise ValueError("P4-F price observation date mismatch")
            if price.unit != obs.get("currency"):
                raise ValueError("P4-F price observation currency/unit mismatch")
    missing = referenced_ids - set(provenance)
    if missing:
        raise ValueError(f"P4-F provenance missing evidence IDs: {sorted(missing)}")
    for record in provenance.values():
        record.validate(cutoff_date)

    bases = []
    for expectation in materialized:
        obs = expectation.get("observation_basis") or {}
        bases.append((obs.get("price_observation_id"), obs.get("observation_date"), obs.get("cutoff_date"), obs.get("currency"), obs.get("adjustment_semantics")))
    if len(set(bases)) > 1:
        raise ValueError("P4-F materialized expectations do not share one observation basis")

def build_p4f_snapshot(*, case_id: str, cutoff_date: date, created_at: datetime, mie_set: MultiModelMarketImpliedExpectationSet, provenance_records: Sequence[P4FProvenanceRecord]) -> dict[str, Any]:
    if not case_id:
        raise ValueError("P4-F case_id is required")
    if created_at.tzinfo is None:
        raise ValueError("P4-F created_at must be timezone-aware")
    mie_set.validate()
    provenance = {item.evidence_id: item for item in provenance_records}
    if len(provenance) != len(tuple(provenance_records)):
        raise ValueError("P4-F provenance evidence_ids must be unique")
    payload_set = mie_set.to_dict()
    _validate_mie_observation_and_evidence(payload_set, provenance, cutoff_date)
    canonical_provenance = [provenance[k].to_dict() for k in sorted(provenance)]
    mie_set_hash = _sha256_obj(payload_set)
    provenance_hash = _sha256_obj(canonical_provenance)
    core = {
        "snapshot_schema": P4F_SNAPSHOT_SCHEMA, "p4f_version": P4F_VERSION,
        "case_id": case_id, "cutoff_date": cutoff_date.isoformat(),
        "created_at": created_at.isoformat(), "mie_set": payload_set,
        "provenance_manifest": canonical_provenance,
        "mie_set_hash": mie_set_hash, "provenance_hash": provenance_hash,
    }
    snapshot_hash = _sha256_obj(core)
    return {**core, "snapshot_hash": snapshot_hash}

def write_p4f_snapshot(root: str | Path, snapshot: Mapping[str, Any]) -> Path:
    value = dict(snapshot)
    validate_p4f_snapshot(value)
    path = Path(root) / f"{value['snapshot_hash']}.mie.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if _canonical_json(existing) != _canonical_json(value):
            raise ValueError("P4-F snapshot overwrite or hash collision")
        return path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path

def validate_p4f_snapshot(snapshot: Mapping[str, Any]) -> None:
    required = {"snapshot_schema", "p4f_version", "case_id", "cutoff_date", "created_at", "mie_set", "provenance_manifest", "mie_set_hash", "provenance_hash", "snapshot_hash"}
    if not required.issubset(snapshot):
        raise ValueError("P4-F snapshot is missing required fields")
    if snapshot["snapshot_schema"] != P4F_SNAPSHOT_SCHEMA or snapshot["p4f_version"] != P4F_VERSION:
        raise ValueError("P4-F snapshot schema/version mismatch")
    cutoff = _parse_date(snapshot["cutoff_date"], "cutoff_date")
    _parse_datetime(snapshot["created_at"], "created_at")
    if _sha256_obj(snapshot["mie_set"]) != snapshot["mie_set_hash"]:
        raise ValueError("P4-F MIE set hash mismatch")
    manifest = snapshot["provenance_manifest"]
    if not isinstance(manifest, list) or len({x.get("evidence_id") for x in manifest}) != len(manifest):
        raise ValueError("P4-F provenance manifest is invalid")
    provenance = {}
    for item in manifest:
        record = P4FProvenanceRecord(
            evidence_id=item.get("evidence_id", ""), variable=item.get("variable", ""), unit=item.get("unit", ""), basis=item.get("basis", ""),
            observation_date=_parse_date(item.get("observation_date"), "provenance.observation_date"),
            known_at=_parse_datetime(item.get("known_at"), "provenance.known_at"), source=item.get("source", ""), source_location=item.get("source_location", ""),
            content_sha256=item.get("content_sha256", ""), captured_at=_parse_datetime(item.get("captured_at"), "provenance.captured_at"),
            value=(None if item.get("value") is None else Decimal(str(item.get("value")))),
        )
        record.validate(cutoff)
        provenance[record.evidence_id] = record
    if _sha256_obj([provenance[k].to_dict() for k in sorted(provenance)]) != snapshot["provenance_hash"]:
        raise ValueError("P4-F provenance hash mismatch")
    _validate_mie_observation_and_evidence(snapshot["mie_set"], provenance, cutoff)
    expected_resolution, expected_qualification = _expected_set_semantics(snapshot["mie_set"])
    if snapshot["mie_set"].get("resolution_state") != expected_resolution:
        raise ValueError("P4-F replay semantic mismatch: resolution_state")
    if snapshot["mie_set"].get("qualification") != expected_qualification:
        raise ValueError("P4-F replay semantic mismatch: qualification")
    core = {k: snapshot[k] for k in ("snapshot_schema", "p4f_version", "case_id", "cutoff_date", "created_at", "mie_set", "provenance_manifest", "mie_set_hash", "provenance_hash")}
    if _sha256_obj(core) != snapshot["snapshot_hash"]:
        raise ValueError("P4-F snapshot integrity check failed")

def read_p4f_snapshot(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("P4-F snapshot must be a JSON object")
    validate_p4f_snapshot(value)
    return value

def replay_p4f_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    try:
        validate_p4f_snapshot(snapshot)
    except ValueError as exc:
        return {"replay_status": "FAIL", "integrity_status": "FAIL", "pit_status": "FAIL", "provenance_status": "FAIL", "semantic_status": "FAIL", "reason": str(exc)}
    return {"replay_status": "PASS", "integrity_status": "PASS", "pit_status": "PASS", "provenance_status": "PASS", "semantic_status": "PASS", "snapshot_hash": snapshot["snapshot_hash"]}

