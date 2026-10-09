from __future__ import annotations

"""Application composition root for the canonical natural-language entry.

The registry is intentionally empty by default. A deployment must explicitly
register an approved request interpreter, semantic producer and the canonical
price/forecast/authority/valuation resolvers. The CLI returns BLOCKED when no
runtime has been registered; it never falls back to ad-hoc analysis.
"""

from dataclasses import dataclass
from typing import Any

from .canonical_natural_language_entry_v01 import RequestInterpreter, RequestInterpreterRegistry
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


_RUNTIME: CanonicalRuntimeBindings | None = None


def register_canonical_runtime(runtime: CanonicalRuntimeBindings) -> None:
    global _RUNTIME
    if _RUNTIME is not None and _RUNTIME != runtime:
        raise RuntimeError("canonical IIOS runtime is already registered; restart the host to replace it")
    _RUNTIME = runtime


def get_canonical_runtime() -> CanonicalRuntimeBindings | None:
    return _RUNTIME


def reset_canonical_runtime_for_tests() -> None:
    """Test-only process cleanup; production entry points must not call this."""
    global _RUNTIME
    _RUNTIME = None


__all__ = [
    "CanonicalRuntimeBindings",
    "register_canonical_runtime",
    "get_canonical_runtime",
    "reset_canonical_runtime_for_tests",
]
