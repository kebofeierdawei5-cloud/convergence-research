from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from iios_mvp.canonical_current_price import (
    FileSystemCanonicalCurrentPriceRegistry,
    validate_current_price_binding,
)
from iios_mvp.canonical_independent_forecast import FileSystemCanonicalIndependentForecastRegistry
from iios_mvp.canonical_investment_admission_v01 import (
    ADMITTED_STATUS,
    CanonicalInvestmentAdmissionRecord,
    CanonicalInvestmentAdmissionReference,
    CanonicalInvestmentAdmissionResolver,
    validate_canonical_investment_admission_record,
)
from iios_mvp.canonical_runtime_registry_v01 import CanonicalRuntimeBindings
from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestInterpreterRegistration,
    RequestInterpreterRegistry,
)
from iios_mvp.forecast_valuation_return_lineage_v01 import build_canonical_valuation_output
from iios_mvp.semantic_producer_admission_v01 import ProducerRegistration, ProducerRegistry
from iios_mvp.self_hosted_semantic_runtime_v01 import (
    SELF_HOSTED_POLICY_VERSION,
    SelfHostedRequestInterpreter,
    SelfHostedResponsesClient,
    SelfHostedRuntimeError,
    SelfHostedThesisSemanticProducer,
)


class SelfHostedRuntimeFactoryError(ValueError):
    """Raised when trusted local runtime configuration or admitted records are absent."""


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda _: (_ for _ in ()).throw(
                SelfHostedRuntimeFactoryError("NON_FINITE_JSON_NUMBER")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SelfHostedRuntimeFactoryError("RUNTIME_RECORD_UNREADABLE") from exc
    if not isinstance(value, dict):
        raise SelfHostedRuntimeFactoryError("RUNTIME_RECORD_MUST_BE_OBJECT")
    return value


def _admission_filename(admission_record_hash: str) -> str:
    return sha256(admission_record_hash.encode("utf-8")).hexdigest() + ".admission.json"


class FileSystemCanonicalInvestmentAdmissionResolver(CanonicalInvestmentAdmissionResolver):
    """Read-only resolver for hash-addressed, immutable canonical admission records."""

    def __init__(self, records_root: str | Path):
        self.records_root = Path(records_root).resolve(strict=True)
        if not self.records_root.is_dir():
            raise SelfHostedRuntimeFactoryError("INVESTMENT_ADMISSION_ROOT_NOT_DIRECTORY")

    def resolve(
        self,
        reference: Mapping[str, Any],
        *,
        expected_domain: str,
        case_id: str,
        market: str,
        symbol: str,
        company: str,
        cutoff_date: date,
    ) -> CanonicalInvestmentAdmissionRecord:
        ref = CanonicalInvestmentAdmissionReference.from_mapping(reference)
        if ref.domain != str(expected_domain).strip().upper():
            raise SelfHostedRuntimeFactoryError("INVESTMENT_ADMISSION_DOMAIN_MISMATCH")
        path = self.records_root / _admission_filename(ref.admission_record_hash)
        record_data = _load_json_object(path)
        if not isinstance(record_data.get("evidence_ids"), list):
            raise SelfHostedRuntimeFactoryError("INVESTMENT_ADMISSION_EVIDENCE_IDS_INVALID")
        try:
            record = CanonicalInvestmentAdmissionRecord(
                **{
                    **record_data,
                    "evidence_ids": tuple(str(item) for item in record_data["evidence_ids"]),
                }
            )
            validate_canonical_investment_admission_record(record)
        except (TypeError, ValueError) as exc:
            raise SelfHostedRuntimeFactoryError("INVESTMENT_ADMISSION_RECORD_INVALID") from exc
        if record.status != ADMITTED_STATUS:
            raise SelfHostedRuntimeFactoryError("INVESTMENT_ADMISSION_NOT_ADMITTED")
        if record.reference().to_dict() != ref.to_dict():
            raise SelfHostedRuntimeFactoryError("INVESTMENT_ADMISSION_REFERENCE_MISMATCH")
        expected = {
            "case_id": str(case_id),
            "market": str(market).strip().upper(),
            "symbol": str(symbol).strip().upper(),
            "company": str(company),
            "cutoff_date": date.fromisoformat(str(cutoff_date)).isoformat(),
        }
        actual = {
            "case_id": record.case_id,
            "market": record.market,
            "symbol": record.symbol,
            "company": record.company,
            "cutoff_date": record.cutoff_date,
        }
        if actual != expected:
            raise SelfHostedRuntimeFactoryError("INVESTMENT_ADMISSION_CASE_BINDING_MISMATCH")
        return record


class FileSystemCanonicalValuationOutputResolver:
    """Read-only valuation resolver bound to a canonical VALUATION admission."""

    def __init__(
        self,
        *,
        records_root: str | Path,
        admission_resolver: CanonicalInvestmentAdmissionResolver,
    ):
        self.records_root = Path(records_root).resolve(strict=True)
        if not self.records_root.is_dir():
            raise SelfHostedRuntimeFactoryError("VALUATION_OUTPUT_ROOT_NOT_DIRECTORY")
        self.admission_resolver = admission_resolver

    def resolve_valuation_output(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        company: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = CanonicalInvestmentAdmissionReference.from_mapping(reference)
        if ref.domain != "VALUATION":
            raise SelfHostedRuntimeFactoryError("VALUATION_ADMISSION_REFERENCE_REQUIRED")
        admission = self.admission_resolver.resolve(
            ref,
            expected_domain="VALUATION",
            case_id=case_id,
            market=market,
            symbol=symbol,
            company=company,
            cutoff_date=cutoff_date,
        )
        filename = sha256(ref.admission_record_hash.encode("utf-8")).hexdigest() + ".valuation.json"
        output = _load_json_object(self.records_root / filename)
        try:
            canonical_output = build_canonical_valuation_output(output)
        except (TypeError, ValueError) as exc:
            raise SelfHostedRuntimeFactoryError("VALUATION_OUTPUT_RECORD_INVALID") from exc
        if canonical_output != output:
            raise SelfHostedRuntimeFactoryError("VALUATION_OUTPUT_NOT_CANONICAL")
        if admission.output_hash != output["output_hash"]:
            raise SelfHostedRuntimeFactoryError("VALUATION_OUTPUT_ADMISSION_HASH_MISMATCH")
        identity = {
            "case_id": str(case_id),
            "market": str(market).strip().upper(),
            "symbol": str(symbol).strip().upper(),
            "company": str(company),
            "cutoff_date": date.fromisoformat(str(cutoff_date)).isoformat(),
        }
        actual = {
            "case_id": output["case_id"],
            "market": str(output["market"]).strip().upper(),
            "symbol": str(output["symbol"]).strip().upper(),
            "company": str(output["company"]),
            "cutoff_date": date.fromisoformat(str(output["cutoff_date"])).isoformat(),
        }
        if actual != identity:
            raise SelfHostedRuntimeFactoryError("VALUATION_OUTPUT_CASE_BINDING_MISMATCH")
        return dict(output)


def _require_records(path: Path, pattern: str, reason: str) -> list[Path]:
    if not path.is_dir():
        raise SelfHostedRuntimeFactoryError(reason + "_ROOT_MISSING")
    records = sorted(path.glob(pattern))
    if not records:
        raise SelfHostedRuntimeFactoryError(reason + "_NO_ADMITTED_RECORDS")
    return records


def _bundle_case_context(bundle: Mapping[str, Any]) -> dict[str, Any]:
    case = bundle.get("investment_case")
    if not isinstance(case, Mapping):
        raise SelfHostedRuntimeFactoryError("INVESTMENT_CASE_OBJECT_REQUIRED")
    request = case.get("request")
    if not isinstance(request, Mapping):
        raise SelfHostedRuntimeFactoryError("INVESTMENT_CASE_REQUEST_REQUIRED")
    required_case = ("case_id", "market", "symbol", "company", "cutoff_date", "as_of_date")
    missing = [key for key in required_case if not str(case.get(key, "")).strip()]
    if missing:
        raise SelfHostedRuntimeFactoryError("INVESTMENT_CASE_FIELDS_MISSING:" + ",".join(missing))
    if str(bundle.get("company", "")) != str(case["company"]):
        raise SelfHostedRuntimeFactoryError("BUNDLE_COMPANY_CASE_MISMATCH")
    if str(request.get("market", "")).upper() != str(case["market"]).upper():
        raise SelfHostedRuntimeFactoryError("BUNDLE_REQUEST_MARKET_MISMATCH")
    if str(request.get("symbol", "")).upper() != str(case["symbol"]).upper():
        raise SelfHostedRuntimeFactoryError("BUNDLE_REQUEST_SYMBOL_MISMATCH")
    return {
        "case": case,
        "case_id": str(case["case_id"]),
        "market": str(case["market"]).upper(),
        "symbol": str(case["symbol"]).upper(),
        "company": str(case["company"]),
        "cutoff_date": date.fromisoformat(str(case["cutoff_date"])),
        "request": request,
    }


def create_canonical_runtime(*, bundle: Mapping[str, Any], output_root: str) -> CanonicalRuntimeBindings:
    """Build production adapters only from trusted config and admitted case records.

    No fake data or default provider is created. Missing config or any exact case-bound
    admission record blocks runtime creation before formal decision artifacts can be written.
    """
    context = _bundle_case_context(bundle)
    runtime_root_value = str(os.environ.get("IIOS_HOST_RUNTIME_DATA_ROOT", "")).strip()
    if not runtime_root_value:
        raise SelfHostedRuntimeFactoryError("HOST_RUNTIME_DATA_ROOT_REQUIRED")
    runtime_root = Path(runtime_root_value).expanduser().resolve(strict=True)
    if not runtime_root.is_dir():
        raise SelfHostedRuntimeFactoryError("HOST_RUNTIME_DATA_ROOT_NOT_DIRECTORY")

    price_root = runtime_root / "current_price"
    forecast_root = runtime_root / "independent_forecast"
    admission_root = runtime_root / "investment_admissions"
    valuation_root = runtime_root / "valuation_outputs"
    _require_records(price_root / "current_price_admissions", "*.price.json", "CURRENT_PRICE")
    _require_records(forecast_root / "independent_forecast_admissions", "*.forecast.json", "INDEPENDENT_FORECAST")
    _require_records(admission_root, "*.admission.json", "INVESTMENT_ADMISSION")
    _require_records(valuation_root, "*.valuation.json", "VALUATION_OUTPUT")

    try:
        client = SelfHostedResponsesClient.from_environment(os.environ)
    except SelfHostedRuntimeError as exc:
        raise SelfHostedRuntimeFactoryError(str(exc)) from exc

    current_price_resolver = FileSystemCanonicalCurrentPriceRegistry(price_root)
    independent_forecast_resolver = FileSystemCanonicalIndependentForecastRegistry(forecast_root)
    upstream_authority_resolver = FileSystemCanonicalInvestmentAdmissionResolver(admission_root)
    valuation_output_resolver = FileSystemCanonicalValuationOutputResolver(
        records_root=valuation_root,
        admission_resolver=upstream_authority_resolver,
    )
    case = context["case"]
    price = case.get("current_price_observation")
    if not isinstance(price, Mapping):
        raise SelfHostedRuntimeFactoryError("CANONICAL_CURRENT_PRICE_OBSERVATION_REQUIRED")
    price_reference = {
        "price_observation_id": str(price.get("price_observation_id", "")),
        "admission_record_hash": str(price.get("price_observation_admission_hash", "")),
    }
    try:
        admitted_price = current_price_resolver.resolve_current_price(
            price_reference,
            case_id=context["case_id"],
            market=context["market"],
            symbol=context["symbol"],
            cutoff_date=context["cutoff_date"],
        )
        validate_current_price_binding(price, admitted_price)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise SelfHostedRuntimeFactoryError("CASE_CURRENT_PRICE_NOT_ADMITTED_OR_NOT_BOUND") from exc

    return_gate = case.get("return_gate")
    if not isinstance(return_gate, Mapping):
        raise SelfHostedRuntimeFactoryError("CANONICAL_RETURN_GATE_REQUIRED")
    forecast_ref = return_gate.get("canonical_forecast_ref")
    valuation_ref = return_gate.get("canonical_valuation_ref")
    if not isinstance(forecast_ref, Mapping) or not isinstance(valuation_ref, Mapping):
        raise SelfHostedRuntimeFactoryError("CANONICAL_FORECAST_VALUATION_REFERENCES_REQUIRED")
    try:
        independent_forecast_resolver.resolve_independent_forecast(
            forecast_ref,
            case_id=context["case_id"],
            market=context["market"],
            symbol=context["symbol"],
            cutoff_date=context["cutoff_date"],
        )
        valuation_output_resolver.resolve_valuation_output(
            valuation_ref,
            case_id=context["case_id"],
            market=context["market"],
            symbol=context["symbol"],
            company=context["company"],
            cutoff_date=context["cutoff_date"],
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise SelfHostedRuntimeFactoryError("CASE_FORECAST_VALUATION_RECORDS_NOT_ADMITTED_OR_NOT_BOUND") from exc

    interpreter_id = client.config.provider_id + ":request-interpreter"
    interpreter = SelfHostedRequestInterpreter(
        client=client, expected_case=case, interpreter_id=interpreter_id
    )
    request_registry = RequestInterpreterRegistry((
        RequestInterpreterRegistration(
            interpreter_id=interpreter.interpreter_id,
            interpreter_type=interpreter.interpreter_type,
            interpreter_version=interpreter.interpreter_version,
            policy_version=interpreter.policy_version,
            active=True,
        ),
    ))
    producer_id = client.config.provider_id + ":thesis-semantic"
    producer_version = client.config.provider_version + ":" + client.config.model
    semantic_producer = SelfHostedThesisSemanticProducer(
        client=client,
        producer_id=producer_id,
        producer_version=producer_version,
        policy_version=SELF_HOSTED_POLICY_VERSION,
    )
    producer_registry = ProducerRegistry((
        ProducerRegistration(
            producer_id=semantic_producer.producer_id,
            producer_type=semantic_producer.producer_type,
            producer_version=semantic_producer.producer_version,
            policy_version=semantic_producer.policy_version,
            active=True,
        ),
    ))
    return CanonicalRuntimeBindings(
        request_interpreter=interpreter,
        request_registry=request_registry,
        semantic_producer=semantic_producer,
        producer_registry=producer_registry,
        current_price_resolver=current_price_resolver,
        independent_forecast_resolver=independent_forecast_resolver,
        upstream_authority_resolver=upstream_authority_resolver,
        valuation_output_resolver=valuation_output_resolver,
    )


__all__ = [
    "SelfHostedRuntimeFactoryError",
    "FileSystemCanonicalInvestmentAdmissionResolver",
    "FileSystemCanonicalValuationOutputResolver",
    "create_canonical_runtime",
]
