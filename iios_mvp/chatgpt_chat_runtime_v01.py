from __future__ import annotations

"""Canonical runtime composition using operator-mediated ChatGPT Free web output.

No API endpoint/key, browser automation, cookie access or hidden session access is
used. A missing response writes an immutable handoff prompt and fails closed.
"""

import os
from pathlib import Path
from typing import Any, Mapping

from .canonical_current_price import FileSystemCanonicalCurrentPriceRegistry
from .canonical_independent_forecast import FileSystemCanonicalIndependentForecastRegistry
from .canonical_runtime_factory_v01 import (
    FileSystemCanonicalInvestmentAdmissionResolver,
    FileSystemCanonicalValuationOutputResolver,
    LiveJsonRequestInterpreter,
    LiveJsonSemanticProducer,
    RuntimeFactoryError,
    _case_context,
)
from .canonical_runtime_registry_v01 import CanonicalRuntimeBindings, validate_canonical_runtime_bindings
from .canonical_natural_language_entry_v01 import RequestInterpreterRegistration, RequestInterpreterRegistry
from .semantic_producer_admission_v01 import ProducerRegistration, ProducerRegistry
from .chatgpt_chat_handoff_v01 import ChatGPTChatJsonClient, DEFAULT_MODEL_LABEL

CHATGPT_CHAT_RUNTIME_VERSION = "IIOS-CHATGPT-FREE-WEB-RUNTIME-0.1"
REQUEST_INTERPRETER_ID = "iios-chatgpt-web-request-interpreter"
REQUEST_INTERPRETER_VERSION = "0.1.0"
REQUEST_INTERPRETER_POLICY = "IIOS-CHATGPT-WEB-OPERATOR-POLICY-0.1"
SEMANTIC_PRODUCER_ID = "iios-chatgpt-web-semantic-producer"
SEMANTIC_PRODUCER_VERSION = "0.1.0"
SEMANTIC_PRODUCER_POLICY = "IIOS-CHATGPT-WEB-OPERATOR-POLICY-0.1"


class ChatGPTChatRequestInterpreter(LiveJsonRequestInterpreter):
    interpreter_id = REQUEST_INTERPRETER_ID
    interpreter_version = REQUEST_INTERPRETER_VERSION
    policy_version = REQUEST_INTERPRETER_POLICY


class ChatGPTChatSemanticProducer(LiveJsonSemanticProducer):
    producer_id = SEMANTIC_PRODUCER_ID
    producer_version = SEMANTIC_PRODUCER_VERSION
    policy_version = SEMANTIC_PRODUCER_POLICY


def build_chatgpt_chat_runtime(
    *,
    bundle: Mapping[str, Any],
    output_root: str | Path,
    env: Mapping[str, str] | None = None,
) -> CanonicalRuntimeBindings:
    """Build all eight runtime bindings without any provider endpoint or API key."""
    values = os.environ if env is None else env
    context = _case_context(bundle)
    handoff_root = str(values.get("IIOS_CHATGPT_HANDOFF_ROOT", ".iios-chatgpt-handoff")).strip()
    if not handoff_root:
        raise RuntimeFactoryError("IIOS_CHATGPT_HANDOFF_ROOT_REQUIRED")
    model_label = str(values.get("IIOS_CHATGPT_MODEL_LABEL", DEFAULT_MODEL_LABEL)).strip() or DEFAULT_MODEL_LABEL
    admission_root_raw = str(values.get("IIOS_CANONICAL_ADMISSION_ROOT", "")).strip()
    if not admission_root_raw:
        raise RuntimeFactoryError("IIOS_CANONICAL_ADMISSION_ROOT_REQUIRED")
    admission_root = Path(admission_root_raw).expanduser().resolve(strict=True)
    if not admission_root.is_dir():
        raise RuntimeFactoryError("CANONICAL_ADMISSION_ROOT_MUST_BE_DIRECTORY")
    output_path = Path(output_root).expanduser().resolve(strict=True)

    client = ChatGPTChatJsonClient(root=handoff_root, model_label=model_label)
    request_interpreter = ChatGPTChatRequestInterpreter(client=client, context=context)
    request_registry = RequestInterpreterRegistry((
        RequestInterpreterRegistration(
            interpreter_id=request_interpreter.interpreter_id,
            interpreter_type=request_interpreter.interpreter_type,
            interpreter_version=request_interpreter.interpreter_version,
            policy_version=request_interpreter.policy_version,
            active=True,
        ),
    ))
    semantic_producer = ChatGPTChatSemanticProducer(client=client)
    producer_registry = ProducerRegistry((
        ProducerRegistration(
            producer_id=semantic_producer.producer_id,
            producer_type=semantic_producer.producer_type,
            producer_version=semantic_producer.producer_version,
            policy_version=semantic_producer.policy_version,
            active=True,
        ),
    ))
    upstream_resolver = FileSystemCanonicalInvestmentAdmissionResolver(admission_root)
    runtime = CanonicalRuntimeBindings(
        request_interpreter=request_interpreter,
        request_registry=request_registry,
        semantic_producer=semantic_producer,
        producer_registry=producer_registry,
        current_price_resolver=FileSystemCanonicalCurrentPriceRegistry(admission_root),
        independent_forecast_resolver=FileSystemCanonicalIndependentForecastRegistry(admission_root),
        upstream_authority_resolver=upstream_resolver,
        valuation_output_resolver=FileSystemCanonicalValuationOutputResolver(
            admission_root, admission_resolver=upstream_resolver
        ),
    )
    return validate_canonical_runtime_bindings(runtime)


__all__ = [
    "CHATGPT_CHAT_RUNTIME_VERSION",
    "ChatGPTChatRequestInterpreter",
    "ChatGPTChatSemanticProducer",
    "build_chatgpt_chat_runtime",
]
