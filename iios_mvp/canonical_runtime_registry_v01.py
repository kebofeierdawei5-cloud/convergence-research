from __future__ import annotations

"""Application composition root for the canonical natural-language entry.

The registry is intentionally empty by default. A deployment must explicitly
register an approved request interpreter, semantic producer and the canonical
price/forecast/authority/valuation resolvers. The CLI returns BLOCKED when no
runtime has been registered; it never falls back to ad-hoc analysis.
"""

from dataclasses import dataclass
from typing import Any

from .canonical_natural_language_entry_v01 import (
    RequestInterpreter,
    RequestInterpreterRegistry,
)
from .llm_semantic_workbench_v01 import SemanticProducer
from .semantic_producer_admission_v01 import ProducerRegistry


@dataclass(frozen=True)
class CanonicalRuntimeBindings:
    request_interpreter: RequestInterpreter
    request_registry: RequestInterpreterRegistry
    semantic_producer: SemanticProducer
    producer_registry: ProducerRegistry
    current_price_resolver: Any
    independent_forecast_resolver: Any
    upstream_authority_resolver: Any
    valuation_output_resolver: Any


RUNTIME_REQUIRED_BINDINGS = (
    "request_interpreter",
    "request_registry",
    "semantic_producer",
    "producer_registry",
    "current_price_resolver",
    "independent_forecast_resolver",
    "upstream_authority_resolver",
    "valuation_output_resolver",
)


def validate_canonical_runtime_bindings(runtime: Any) -> CanonicalRuntimeBindings:
    """Validate every runtime entry path before a canonical run can start.

    The registered-host and factory paths deliberately share this validation.
    Non-null placeholders are not sufficient for the request/semantic
    boundaries: both registries must be typed allow-lists, the producers must
    expose the callable contract used by B2-E, and their identity/version/policy
    must be active and registered.
    """
    if not isinstance(runtime, CanonicalRuntimeBindings):
        raise ValueError("runtime must be CanonicalRuntimeBindings")

    missing = [
        name for name in RUNTIME_REQUIRED_BINDINGS
        if getattr(runtime, name, None) is None
    ]
    if missing:
        raise ValueError("runtime has missing bindings: " + ", ".join(missing))

    interpreter = runtime.request_interpreter
    interpreter_fields = (
        "interpreter_id", "interpreter_type", "interpreter_version", "policy_version"
    )
    if not callable(getattr(interpreter, "interpret", None)):
        raise ValueError("request interpreter must implement callable interpret(raw_request)")
    if any(not isinstance(getattr(interpreter, field, None), str)
           or not getattr(interpreter, field).strip()
           for field in interpreter_fields):
        raise ValueError("request interpreter identity/version/policy fields are required")
    if not isinstance(runtime.request_registry, RequestInterpreterRegistry):
        raise ValueError("request_registry must be RequestInterpreterRegistry")
    try:
        interpreter_registration = runtime.request_registry.get(interpreter.interpreter_id)
    except Exception as exc:
        raise ValueError("request interpreter is not active in its registry") from exc
    for field in ("interpreter_type", "interpreter_version", "policy_version"):
        if getattr(interpreter_registration, field) != getattr(interpreter, field):
            raise ValueError("request interpreter identity/version/policy does not match its registry")

    producer = runtime.semantic_producer
    producer_fields = ("producer_id", "producer_type", "producer_version", "policy_version")
    if not callable(getattr(producer, "produce", None)):
        raise ValueError("semantic producer must implement callable produce(request)")
    if getattr(producer, "producer_type", None) != "LLM_SEMANTIC_PRODUCER":
        raise ValueError("canonical natural-language entry requires an LLM semantic producer")
    if any(not isinstance(getattr(producer, field, None), str)
           or not getattr(producer, field).strip()
           for field in producer_fields):
        raise ValueError("semantic producer identity/version/policy fields are required")
    if not isinstance(runtime.producer_registry, ProducerRegistry):
        raise ValueError("producer_registry must be ProducerRegistry")
    try:
        producer_registration = runtime.producer_registry.get(producer.producer_id)
    except Exception as exc:
        raise ValueError("semantic producer is not active in its registry") from exc
    for field in ("producer_type", "producer_version", "policy_version"):
        if getattr(producer_registration, field) != getattr(producer, field):
            raise ValueError("semantic producer identity/version/policy does not match its registry")

    resolver_methods = {
        "current_price_resolver": "resolve_current_price",
        "independent_forecast_resolver": "resolve_independent_forecast",
        "upstream_authority_resolver": "resolve",
        "valuation_output_resolver": "resolve_valuation_output",
    }
    for binding_name, method_name in resolver_methods.items():
        resolver = getattr(runtime, binding_name)
        if not callable(getattr(resolver, method_name, None)):
            raise ValueError(
                f"{binding_name} must implement callable {method_name}(...)"
            )

    return runtime


_RUNTIME: CanonicalRuntimeBindings | None = None


def register_canonical_runtime(runtime: CanonicalRuntimeBindings) -> None:
    global _RUNTIME
    validated = validate_canonical_runtime_bindings(runtime)
    if _RUNTIME is not None and _RUNTIME != validated:
        raise RuntimeError("canonical IIOS runtime is already registered; restart the host to replace it")
    _RUNTIME = validated


def get_canonical_runtime() -> CanonicalRuntimeBindings | None:
    if _RUNTIME is None:
        return None
    # Validate again at the trust boundary so corrupted process state or a
    # future alternate registration path cannot bypass the admission contract.
    return validate_canonical_runtime_bindings(_RUNTIME)


def reset_canonical_runtime_for_tests() -> None:
    """Test-only process cleanup; production entry points must not call this."""
    global _RUNTIME
    _RUNTIME = None


__all__ = [
    "CanonicalRuntimeBindings",
    "RUNTIME_REQUIRED_BINDINGS",
    "validate_canonical_runtime_bindings",
    "register_canonical_runtime",
    "get_canonical_runtime",
    "reset_canonical_runtime_for_tests",
]
