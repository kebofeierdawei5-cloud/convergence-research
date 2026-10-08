from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol
import hashlib
import json

from iios_mvp.canonical_research_orchestrator import (
    ORCHESTRATOR_VERSION,
    CanonicalResearchOrchestrator,
)
from iios_mvp.research_intake import build_research_case, validate_research_case

REQUEST_ADMISSION_SCHEMA_VERSION = "IIOS-NL-REQUEST-ADMISSION-0.1"
REQUEST_ADMISSION_VERSION = "IIOS-NL-REQUEST-ADMISSION-0.1"
REQUEST_INTERPRETER_TYPES = {"LLM_REQUEST_INTERPRETER", "HUMAN_EXPERT_ADJUDICATION"}


class RequestAdmissionError(ValueError):
    """Raised when a natural-language request cannot enter the canonical path."""


@dataclass(frozen=True)
class RequestIntent:
    market: str
    symbol: str
    as_of_date: str
    current_position_pct: str | int | float
    request_type: str = "INVESTMENT_DECISION"


class RequestInterpreter(Protocol):
    interpreter_id: str
    interpreter_type: str
    interpreter_version: str
    policy_version: str

    def interpret(self, raw_request: str) -> RequestIntent:
        ...


@dataclass(frozen=True)
class RequestInterpreterRegistration:
    interpreter_id: str
    interpreter_type: str
    interpreter_version: str
    policy_version: str
    active: bool = True


class RequestInterpreterRegistry:
    def __init__(self, registrations: tuple[RequestInterpreterRegistration, ...] = ()) -> None:
        self._items: dict[str, RequestInterpreterRegistration] = {}
        for item in registrations:
            self.register(item)

    def register(self, registration: RequestInterpreterRegistration) -> None:
        if not registration.interpreter_id.strip():
            raise ValueError("interpreter_id is required")
        if registration.interpreter_type not in REQUEST_INTERPRETER_TYPES:
            raise ValueError("interpreter_type is not authorized")
        if not registration.interpreter_version.strip():
            raise ValueError("interpreter_version is required")
        if not registration.policy_version.strip():
            raise ValueError("policy_version is required")
        if registration.interpreter_id in self._items:
            raise ValueError("interpreter_id already registered")
        self._items[registration.interpreter_id] = registration

    def get(self, interpreter_id: str) -> RequestInterpreterRegistration:
        try:
            item = self._items[interpreter_id]
        except KeyError as exc:
            raise RequestAdmissionError("request interpreter is not registered") from exc
        if not item.active:
            raise RequestAdmissionError("request interpreter registration is inactive")
        return item


@dataclass(frozen=True)
class RequestAdmissionResult:
    run_id: str
    case_id: str
    case_hash: str
    request_receipt: Mapping[str, Any]
    research_case: Mapping[str, Any]


def canonical_hash(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def request_sha256(raw_request: str) -> str:
    if not isinstance(raw_request, str) or not raw_request.strip():
        raise RequestAdmissionError("raw natural-language request is required")
    return hashlib.sha256(raw_request.encode("utf-8")).hexdigest()


def admit_natural_language_request(
    *,
    orchestrator: CanonicalResearchOrchestrator,
    registry: RequestInterpreterRegistry,
    interpreter: RequestInterpreter,
    request_id: str,
    run_id: str,
    raw_request: str,
    created_at: str,
) -> RequestAdmissionResult:
    if not request_id.strip() or not run_id.strip():
        raise RequestAdmissionError("request_id and run_id are required")
    registration = registry.get(interpreter.interpreter_id)
    for field in ("interpreter_type", "interpreter_version", "policy_version"):
        if getattr(registration, field) != getattr(interpreter, field):
            raise RequestAdmissionError(f"{field} is not registry-authorized")

    raw_hash = request_sha256(raw_request)
    intent = interpreter.interpret(raw_request)
    if not isinstance(intent, RequestIntent):
        raise RequestAdmissionError("request interpreter must return RequestIntent")
    if intent.request_type != "INVESTMENT_DECISION":
        raise RequestAdmissionError("only INVESTMENT_DECISION requests enter this canonical path")

    case = build_research_case(
        symbol=intent.symbol,
        as_of_date=intent.as_of_date,
        current_position_pct=intent.current_position_pct,
        market=intent.market,
        generated_at=created_at,
    )
    case_errors = validate_research_case(case)
    if case_errors:
        raise RequestAdmissionError("research case admission failed: " + "; ".join(case_errors))
    case_hash = canonical_hash(case)
    normalized_request = {
        "market": case["request"]["market"],
        "symbol": case["request"]["symbol"],
        "as_of_date": case["request"]["as_of_date"],
        "current_position_pct": case["request"]["current_position_pct"],
        "request_type": intent.request_type,
    }
    normalized_hash = canonical_hash(normalized_request)
    receipt_core = {
        "schema_version": REQUEST_ADMISSION_SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "raw_request_sha256": raw_hash,
        "normalized_request_sha256": normalized_hash,
        "normalized_request": normalized_request,
        "case_id": case["case_id"],
        "case_hash": case_hash,
        "market": case["request"]["market"],
        "symbol": case["request"]["symbol"],
        "as_of_date": case["request"]["as_of_date"],
        "cutoff_date": case["temporal_scope"]["cutoff_date"],
        "request_type": intent.request_type,
        "interpreter_type": interpreter.interpreter_type,
        "interpreter_id": interpreter.interpreter_id,
        "interpreter_version": interpreter.interpreter_version,
        "policy_version": interpreter.policy_version,
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "status": "ADMITTED",
        "created_at": created_at,
    }
    receipt = {**receipt_core, "receipt_hash": canonical_hash(receipt_core)}

    envelope = orchestrator.start(
        run_id=run_id,
        case_id=case["case_id"],
        market=case["request"]["market"],
        symbol=case["request"]["symbol"],
        cutoff_date=case["temporal_scope"]["cutoff_date"],
        as_of_date=case["request"]["as_of_date"],
        request_type=intent.request_type,
        research_case_hash=case_hash,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        next_stage=__import__("iios_mvp.canonical_research_orchestrator", fromlist=["Stage"]).Stage.REQUEST_ADMITTED,
        output_refs=(receipt["request_id"],),
        output_hashes=(receipt["receipt_hash"],),
        producer_type=interpreter.interpreter_type,
        producer_version=interpreter.interpreter_version,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        next_stage=__import__("iios_mvp.canonical_research_orchestrator", fromlist=["Stage"]).Stage.CASE_CREATED,
        output_refs=(case["case_id"],),
        output_hashes=(case_hash,),
        producer_type="CODE",
        producer_version=case["generator_version"],
        created_at=created_at,
    )
    return RequestAdmissionResult(
        run_id=envelope.run_id,
        case_id=case["case_id"],
        case_hash=case_hash,
        request_receipt=receipt,
        research_case=case,
    )


__all__ = [
    "REQUEST_ADMISSION_SCHEMA_VERSION",
    "REQUEST_ADMISSION_VERSION",
    "REQUEST_INTERPRETER_TYPES",
    "RequestAdmissionError",
    "RequestIntent",
    "RequestInterpreter",
    "RequestInterpreterRegistration",
    "RequestInterpreterRegistry",
    "RequestAdmissionResult",
    "admit_natural_language_request",
    "canonical_hash",
    "request_sha256",
]
