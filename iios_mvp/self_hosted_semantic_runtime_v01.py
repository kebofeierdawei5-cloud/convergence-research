from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import ipaddress
import json
import os
from typing import Any, Mapping
from urllib.parse import urlsplit

from iios_mvp.canonical_natural_language_entry_v01 import RequestIntent
from iios_mvp.canonical_runtime_registry_v01 import CanonicalRuntimeBindings
from iios_mvp.live_provider_invocation_v01 import (
    build_provider_payload,
    invoke_live_provider,
)
from iios_mvp.live_provider_preflight_v01 import LiveProviderConfig
from iios_mvp.llm_semantic_workbench_v01 import SemanticRequest
from iios_mvp.provider_runtime_v01 import validate_provider_runtime_policy
from iios_mvp.semantic_to_core_projection_v01 import THESIS_PROJECTION_FIELDS
from iios_mvp.thesis_admission_v03 import THESIS_STATUSES

SELF_HOSTED_SEMANTIC_RUNTIME_VERSION = "IIOS-SELF-HOSTED-SEMANTIC-RUNTIME-0.1"
SELF_HOSTED_POLICY_VERSION = "SELF_HOSTED_OPENAI_RESPONSES_JSON_V1"
_MAX_PROMPT_CHARS = 250_000
_MAX_RESPONSE_BYTES = 1_000_000
_REQUIRED_CONFIG = (
    "IIOS_SELF_HOSTED_RESPONSES_ENDPOINT",
    "IIOS_SELF_HOSTED_MODEL",
    "IIOS_SELF_HOSTED_PROVIDER_ID",
    "IIOS_SELF_HOSTED_PROVIDER_VERSION",
)


class SelfHostedRuntimeError(ValueError):
    """Raised when the local model runtime or its output is not admissible."""


def _reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SelfHostedRuntimeError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise SelfHostedRuntimeError("NON_FINITE_JSON_NUMBER")


def _validate_loopback_endpoint(endpoint: str) -> None:
    try:
        parsed = urlsplit(endpoint)
    except ValueError as exc:
        raise SelfHostedRuntimeError("INVALID_SELF_HOSTED_ENDPOINT") from exc
    if parsed.scheme != "http" or not parsed.hostname:
        raise SelfHostedRuntimeError("SELF_HOSTED_ENDPOINT_MUST_USE_LOOPBACK_HTTP")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SelfHostedRuntimeError("SELF_HOSTED_ENDPOINT_MUST_NOT_INCLUDE_CREDENTIALS_OR_QUERY")
    if parsed.path.rstrip("/") != "/v1/responses":
        raise SelfHostedRuntimeError("SELF_HOSTED_ENDPOINT_MUST_END_IN_V1_RESPONSES")
    host = parsed.hostname.lower()
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = host == "localhost"
    if not is_loopback:
        raise SelfHostedRuntimeError("SELF_HOSTED_ENDPOINT_MUST_BE_LOOPBACK_ONLY")
    try:
        validate_provider_runtime_policy(
            base_url=endpoint,
            protocol="OPENAI_RESPONSES",
            auth_mode="NONE",
            deployment_mode="SELF_HOSTED",
        )
    except ValueError as exc:
        raise SelfHostedRuntimeError("SELF_HOSTED_PROVIDER_POLICY_REJECTED") from exc


@dataclass(frozen=True)
class SelfHostedResponsesConfig:
    endpoint: str
    model: str
    provider_id: str
    provider_version: str
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        _validate_loopback_endpoint(self.endpoint)
        for field_name in ("model", "provider_id", "provider_version"):
            if not str(getattr(self, field_name)).strip():
                raise SelfHostedRuntimeError(f"SELF_HOSTED_{field_name.upper()}_REQUIRED")
        if not 1 <= int(self.timeout_seconds) <= 300:
            raise SelfHostedRuntimeError("SELF_HOSTED_TIMEOUT_OUT_OF_RANGE")


def load_self_hosted_responses_config(
    env: Mapping[str, str] | None = None,
) -> SelfHostedResponsesConfig:
    """Load a local model endpoint without any commercial API-key dependency."""
    values = os.environ if env is None else env
    missing = [name for name in _REQUIRED_CONFIG if not str(values.get(name, "")).strip()]
    if missing:
        raise SelfHostedRuntimeError("SELF_HOSTED_MODEL_CONFIG_MISSING:" + ",".join(missing))
    try:
        timeout = int(str(values.get("IIOS_SELF_HOSTED_TIMEOUT_SECONDS", "120")))
    except ValueError as exc:
        raise SelfHostedRuntimeError("SELF_HOSTED_TIMEOUT_MUST_BE_INTEGER") from exc
    return SelfHostedResponsesConfig(
        endpoint=str(values["IIOS_SELF_HOSTED_RESPONSES_ENDPOINT"]).strip(),
        model=str(values["IIOS_SELF_HOSTED_MODEL"]).strip(),
        provider_id=str(values["IIOS_SELF_HOSTED_PROVIDER_ID"]).strip(),
        provider_version=str(values["IIOS_SELF_HOSTED_PROVIDER_VERSION"]).strip(),
        timeout_seconds=timeout,
    )


def _extract_output_text(response: Mapping[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    output = response.get("output")
    if isinstance(output, list):
        fragments: list[str] = []
        for item in output:
            if not isinstance(item, Mapping) or not isinstance(item.get("content"), list):
                continue
            for part in item["content"]:
                if isinstance(part, Mapping) and part.get("type") in {"output_text", "text"}:
                    text_value = part.get("text")
                    if isinstance(text_value, str):
                        fragments.append(text_value)
        if fragments and "".join(fragments).strip():
            return "".join(fragments)
    raise SelfHostedRuntimeError("SELF_HOSTED_RESPONSE_HAS_NO_OUTPUT_TEXT")


@dataclass(frozen=True)
class SelfHostedResponsesClient:
    config: SelfHostedResponsesConfig

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> "SelfHostedResponsesClient":
        return cls(load_self_hosted_responses_config(env))

    def generate_json(self, prompt: str) -> dict[str, Any]:
        if not isinstance(prompt, str) or not prompt.strip():
            raise SelfHostedRuntimeError("SELF_HOSTED_PROMPT_REQUIRED")
        if len(prompt) > _MAX_PROMPT_CHARS:
            raise SelfHostedRuntimeError("SELF_HOSTED_PROMPT_TOO_LARGE")
        provider_config = LiveProviderConfig(
            base_url=self.config.endpoint,
            api_key="",
            model=self.config.model,
            runtime_private_key_b64="",
            provider_id=self.config.provider_id,
            provider_version=self.config.provider_version,
            protocol="OPENAI_RESPONSES",
            timeout_seconds=self.config.timeout_seconds,
            auth_mode="NONE",
            deployment_mode="SELF_HOSTED",
        )
        payload = build_provider_payload(config=provider_config, prompt=prompt)
        response = invoke_live_provider(config=provider_config, payload=payload)
        if not 200 <= int(response.http_status) < 300:
            raise SelfHostedRuntimeError("SELF_HOSTED_HTTP_STATUS_NOT_SUCCESS")
        if "application/json" not in str(response.content_type).lower():
            raise SelfHostedRuntimeError("SELF_HOSTED_RESPONSE_CONTENT_TYPE_NOT_JSON")
        if len(response.response_bytes) > _MAX_RESPONSE_BYTES:
            raise SelfHostedRuntimeError("SELF_HOSTED_RESPONSE_TOO_LARGE")
        try:
            decoded_response = json.loads(
                response.response_bytes.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_json_pairs,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SelfHostedRuntimeError("SELF_HOSTED_RESPONSE_ENVELOPE_INVALID_JSON") from exc
        if not isinstance(decoded_response, Mapping):
            raise SelfHostedRuntimeError("SELF_HOSTED_RESPONSE_ENVELOPE_NOT_OBJECT")
        text_value = _extract_output_text(decoded_response)
        try:
            value = json.loads(
                text_value,
                object_pairs_hook=_reject_duplicate_json_pairs,
                parse_constant=_reject_json_constant,
            )
        except json.JSONDecodeError as exc:
            raise SelfHostedRuntimeError("SELF_HOSTED_MODEL_OUTPUT_NOT_JSON") from exc
        if not isinstance(value, dict):
            raise SelfHostedRuntimeError("SELF_HOSTED_MODEL_OUTPUT_MUST_BE_OBJECT")
        return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise SelfHostedRuntimeError(f"REQUEST_INTENT_{field.upper()}_INVALID")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SelfHostedRuntimeError(f"REQUEST_INTENT_{field.upper()}_INVALID") from exc
    if not result.is_finite():
        raise SelfHostedRuntimeError(f"REQUEST_INTENT_{field.upper()}_INVALID")
    return result


class SelfHostedRequestInterpreter:
    """Local-model request parser; conflicts with the operator-staged case block."""

    interpreter_type = "LLM_REQUEST_INTERPRETER"
    interpreter_version = SELF_HOSTED_SEMANTIC_RUNTIME_VERSION
    policy_version = SELF_HOSTED_POLICY_VERSION

    def __init__(
        self,
        *,
        client: SelfHostedResponsesClient,
        expected_case: Mapping[str, Any],
        interpreter_id: str,
    ):
        self.client = client
        self.interpreter_id = interpreter_id
        seed = expected_case.get("request")
        if not isinstance(seed, Mapping):
            raise SelfHostedRuntimeError("TRUSTED_CASE_REQUEST_SEED_REQUIRED")
        required = ("market", "symbol", "as_of_date", "current_position_pct")
        missing = [name for name in required if seed.get(name) in (None, "")]
        if missing:
            raise SelfHostedRuntimeError("TRUSTED_CASE_REQUEST_SEED_MISSING:" + ",".join(missing))
        self.expected = {
            "market": str(seed["market"]).strip().upper(),
            "symbol": str(seed["symbol"]).strip().upper(),
            "as_of_date": date.fromisoformat(str(seed["as_of_date"])).isoformat(),
            "current_position_pct": _decimal(seed["current_position_pct"], "current_position_pct"),
        }

    def interpret(self, raw_request: str) -> RequestIntent:
        prompt = (
            "You are the IIOS request-intent parser. Extract only request intent from the "
            "raw request. Return exactly one JSON object with keys market, symbol, "
            "as_of_date, current_position_pct, request_type. Use null only when a field "
            "is not explicit; do not guess. request_type must be INVESTMENT_DECISION. "
            "Do not analyze the company or recommend an action. If an explicit value conflicts "
            "with the trusted staged case, preserve the explicit value so the application blocks.\n"
            "RAW REQUEST:\n" + raw_request
        )
        parsed = self.client.generate_json(prompt)
        keys = {"market", "symbol", "as_of_date", "current_position_pct", "request_type"}
        if set(parsed) != keys:
            raise SelfHostedRuntimeError("REQUEST_INTENT_FIELDS_INVALID")
        if parsed["request_type"] != "INVESTMENT_DECISION":
            raise SelfHostedRuntimeError("REQUEST_INTENT_TYPE_NOT_ALLOWED")
        observed = dict(parsed)
        for name in ("market", "symbol", "as_of_date", "current_position_pct"):
            if observed[name] is None or observed[name] == "":
                observed[name] = self.expected[name]
        if not isinstance(observed["market"], str) or not observed["market"].strip():
            raise SelfHostedRuntimeError("REQUEST_INTENT_MARKET_INVALID")
        if not isinstance(observed["symbol"], str) or not observed["symbol"].strip():
            raise SelfHostedRuntimeError("REQUEST_INTENT_SYMBOL_INVALID")
        try:
            as_of = date.fromisoformat(str(observed["as_of_date"])).isoformat()
        except ValueError as exc:
            raise SelfHostedRuntimeError("REQUEST_INTENT_AS_OF_DATE_INVALID") from exc
        market = str(observed["market"]).strip().upper()
        symbol = str(observed["symbol"]).strip().upper()
        position = _decimal(observed["current_position_pct"], "current_position_pct")
        if not Decimal("0") <= position <= Decimal("100"):
            raise SelfHostedRuntimeError("REQUEST_INTENT_CURRENT_POSITION_OUT_OF_RANGE")
        mismatches = []
        if market != self.expected["market"]:
            mismatches.append("market")
        if symbol != self.expected["symbol"]:
            mismatches.append("symbol")
        if as_of != self.expected["as_of_date"]:
            mismatches.append("as_of_date")
        if position != self.expected["current_position_pct"]:
            mismatches.append("current_position_pct")
        if mismatches:
            raise SelfHostedRuntimeError("REQUEST_INTENT_TRUSTED_CASE_MISMATCH:" + ",".join(mismatches))
        return RequestIntent(
            market=market,
            symbol=symbol,
            as_of_date=as_of,
            current_position_pct=str(position),
            request_type="INVESTMENT_DECISION",
        )


class SelfHostedThesisSemanticProducer:
    """Real local-model callback; result is still untrusted until IIOS admission."""

    producer_type = "LLM_SEMANTIC_PRODUCER"

    def __init__(
        self,
        *,
        client: SelfHostedResponsesClient,
        producer_id: str,
        producer_version: str,
        policy_version: str = SELF_HOSTED_POLICY_VERSION,
    ):
        self.client = client
        self.producer_id = producer_id
        self.producer_version = producer_version
        self.policy_version = policy_version

    def produce(self, request: SemanticRequest) -> Mapping[str, Any]:
        prompt = (
            "You are the IIOS thesis-semantic producer. Analyze only the analyst context and "
            "evidence excerpts supplied below. Return exactly one JSON object shaped as "
            '{"core_projection":{"status":"...","statement":"...","mechanism":"...",'
            '"key_driver_ids":["..."],"falsifiers":["..."],"monitoring_triggers":["..."]}}. '
            "The core_projection keys must be exactly status, statement, mechanism, key_driver_ids, "
            "falsifiers, monitoring_triggers. Allowed status values: "
            + ", ".join(sorted(THESIS_STATUSES))
            + ". Never invent evidence, source IDs, financial figures, forecasts, prices, or driver IDs. "
            "If evidence is insufficient, use UNKNOWN and clearly state uncertainty. Do not output "
            "trade action, position size, valuation, target price, or decision/execution authority. "
            "The deterministic IIOS validators remain authoritative.\n"
            f"Run: {request.run_id}\nCase: {request.case_id}\nInstrument: {request.market}/{request.symbol}/{request.company}\n"
            f"Cutoff: {request.cutoff_date}\nArtifact type: {request.artifact_type}\n"
            "Input refs/hashes: "
            + json.dumps(list(zip(request.input_refs, request.input_hashes)), ensure_ascii=False)
            + "\nAnalyst context and source-located excerpts:\n" + request.prompt
        )
        parsed = self.client.generate_json(prompt)
        if set(parsed) != {"core_projection"}:
            raise SelfHostedRuntimeError("THESIS_OUTPUT_FIELDS_INVALID")
        projection = parsed["core_projection"]
        if not isinstance(projection, Mapping) or set(projection) != THESIS_PROJECTION_FIELDS:
            raise SelfHostedRuntimeError("THESIS_CORE_PROJECTION_FIELDS_INVALID")
        if projection.get("status") not in THESIS_STATUSES:
            raise SelfHostedRuntimeError("THESIS_STATUS_INVALID")
        for field in ("statement", "mechanism"):
            value = projection.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > 8000:
                raise SelfHostedRuntimeError(f"THESIS_{field.upper()}_INVALID")
        for field in ("key_driver_ids", "falsifiers", "monitoring_triggers"):
            values = projection.get(field)
            if not isinstance(values, list) or not values or any(
                not isinstance(item, str) or not item.strip() for item in values
            ):
                raise SelfHostedRuntimeError(f"THESIS_{field.upper()}_INVALID")
        forbidden = {
            "action", "decision_status", "new_capital_allowed", "human_approval_required",
            "auto_execution", "capital_effect", "decision_admission",
            "decision_precedence_rule_id", "decision_pre_admission_action",
        }

        def reject_authority(node: Any) -> None:
            if isinstance(node, Mapping):
                if forbidden.intersection(node.keys()):
                    raise SelfHostedRuntimeError("THESIS_OUTPUT_CONTAINS_AUTHORITY_FIELDS")
                for child in node.values():
                    reject_authority(child)
            elif isinstance(node, (list, tuple)):
                for child in node:
                    reject_authority(child)

        reject_authority(parsed)
        return {"core_projection": dict(projection)}
