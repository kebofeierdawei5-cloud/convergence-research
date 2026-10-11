from __future__ import annotations

"""Candidate-driven, local-only IIOS pilot.

This path is deliberately non-canonical. It reuses IIOS's deterministic return
and entry-price calculation, but it never creates canonical Evidence/PIT
admission, Decision Admission, Machine Publication, or IIOS_RUN_RECEIPT.
"""

import argparse
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from typing import Any, Mapping

from .investment_core_contract_v03 import (
    BUY_ENTRY_RETURN_CUSHION_THRESHOLD,
    FUNDAMENTAL_TARGET_ANNUALIZED_RETURN,
    SCENARIOS,
    calculate_return_metrics,
)
from .research_intake import build_research_case

PILOT_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-0.1"
PILOT_ANALYSIS_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-ANALYSIS-0.1"
PILOT_RECEIPT_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-RECEIPT-0.1"
PILOT_RUNNER_VERSION = "IIOS-LOCAL-INVESTMENT-PILOT-RUNNER-0.1"
PILOT_STATUS = "PILOT_NON_CANONICAL"
SHANGHAI = timezone(timedelta(hours=8))
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_CLASSES = {
    "OFFICIAL_EXCHANGE",
    "ISSUER_PRIMARY",
    "REGULATOR_PRIMARY",
    "OFFICIAL_DATABASE",
    "PUBLIC_SECONDARY",
    "OPERATOR_SUPPLIED",
    "UNKNOWN",
}
TRUST_STATES = {"PASS", "REVALIDATION", "FAIL", "UNKNOWN"}
ASSESSMENT_STATES = {"PASS", "CONDITIONAL", "BLOCKED", "UNKNOWN"}
THESIS_STATES = {"INTACT", "WATCH", "BROKEN", "UNKNOWN"}
MIE_STATES = {
    "PASS", "NOT_IDENTIFIABLE", "OUTSIDE_HISTORICAL_SUPPORT", "UNKNOWN",
    "BLOCKED", "AMBIGUOUS", "INCOMPATIBLE",
}
GAP_STATES = {"PASS", "UNKNOWN", "BLOCKED", "AMBIGUOUS", "INCOMPATIBLE"}
GAP_DIRECTIONS = {"POSITIVE", "NEUTRAL", "NEGATIVE", "UNKNOWN"}
PRICE_ASSURANCE = "OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED"


class LocalInvestmentPilotError(ValueError):
    """An invalid pilot input or private bundle."""


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_json_object(raw: bytes, *, reason: str) -> dict[str, Any]:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise LocalInvestmentPilotError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                LocalInvestmentPilotError("NON_FINITE_JSON_NUMBER")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalInvestmentPilotError(reason) from exc
    if not isinstance(value, dict):
        raise LocalInvestmentPilotError("JSON_OBJECT_REQUIRED")
    return value


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_NUMERIC") from exc
    if not result.is_finite():
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_FINITE")
    return result


def _positive(value: Any, field: str) -> Decimal:
    result = _decimal(value, field)
    if result <= 0:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_POSITIVE")
    return result


def _local_datetime(value: Any, field: str, *, allow_date_only: bool = True) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise LocalInvestmentPilotError(f"{field}_REQUIRED")
    if allow_date_only and len(raw) == 10:
        try:
            day = date.fromisoformat(raw)
        except ValueError as exc:
            raise LocalInvestmentPilotError(f"{field}_MUST_BE_ISO_DATE_OR_DATETIME") from exc
        return datetime.combine(day, time.min, tzinfo=SHANGHAI)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_ISO_DATETIME") from exc
    if parsed.tzinfo is None:
        raise LocalInvestmentPilotError(f"{field}_MUST_INCLUDE_TIMEZONE")
    return parsed.astimezone(SHANGHAI)


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_YYYY_MM_DD") from exc


def _outside_repository(path: str | Path, field: str, *, must_exist: bool = False) -> Path:
    raw = Path(path).expanduser()
    if raw.is_symlink():
        raise LocalInvestmentPilotError(f"{field}_MUST_NOT_BE_SYMLINK")
    if must_exist and not raw.is_file():
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_REGULAR_FILE")
    resolved = raw.resolve(strict=must_exist)
    try:
        resolved.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return resolved
    raise LocalInvestmentPilotError(f"{field}_MUST_BE_OUTSIDE_REPOSITORY")


def _prepare_private_directory(path: str | Path, field: str) -> Path:
    raw = Path(path).expanduser()
    if raw.is_symlink():
        raise LocalInvestmentPilotError(f"{field}_MUST_NOT_BE_SYMLINK")
    resolved = _outside_repository(raw, field)
    was_present = resolved.exists()
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    if resolved.is_symlink() or not resolved.is_dir():
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_DIRECTORY")
    if os.name != "nt":
        mode = stat.S_IMODE(resolved.stat().st_mode)
        if was_present and mode & 0o077:
            raise LocalInvestmentPilotError(f"{field}_PERMISSIONS_TOO_OPEN")
        if mode & 0o077:
            raise LocalInvestmentPilotError(f"{field}_PERMISSIONS_TOO_OPEN")
    return resolved


def _write_private_file(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    if os.name != "nt" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        path.unlink(missing_ok=True)
        raise LocalInvestmentPilotError("PRIVATE_FILE_PERMISSIONS_TOO_OPEN")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _list_of_text(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_ARRAY_OF_STRINGS")
    return [item.strip() for item in value if item.strip()]


def _status(value: Any, allowed: set[str], field: str, default: str = "UNKNOWN") -> str:
    normalized = str(value or default).strip().upper()
    if normalized not in allowed:
        raise LocalInvestmentPilotError(f"{field}_INVALID:{normalized}")
    return normalized


def _source_register(source_rows: Any, cutoff: date) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if source_rows is None:
        source_rows = []
    if not isinstance(source_rows, list):
        raise LocalInvestmentPilotError("EVIDENCE_REGISTER_MUST_BE_ARRAY")
    seen: set[str] = set()
    clean_rows: list[dict[str, Any]] = []
    after_cutoff: list[str] = []
    unknown_time: list[str] = []
    cutoff_start = datetime.combine(cutoff, time.min, tzinfo=SHANGHAI)
    for index, item in enumerate(source_rows):
        if not isinstance(item, Mapping):
            raise LocalInvestmentPilotError(f"EVIDENCE_REGISTER_ROW_{index}_MUST_BE_OBJECT")
        source_id = _text(item.get("source_id"))
        if not source_id:
            raise LocalInvestmentPilotError(f"EVIDENCE_REGISTER_ROW_{index}_SOURCE_ID_REQUIRED")
        if source_id in seen:
            raise LocalInvestmentPilotError("EVIDENCE_SOURCE_ID_DUPLICATE")
        seen.add(source_id)
        source_class = str(item.get("source_class") or "UNKNOWN").strip().upper()
        if source_class not in SOURCE_CLASSES:
            raise LocalInvestmentPilotError(f"EVIDENCE_SOURCE_CLASS_INVALID:{source_id}")
        known_at = _text(item.get("known_at"))
        time_status = "UNKNOWN"
        if known_at:
            try:
                parsed = _local_datetime(known_at, f"{source_id}.known_at")
                if parsed <= cutoff_start:
                    time_status = "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
                else:
                    time_status = "AFTER_CUTOFF_EXCLUDED_FROM_PIT"
                    after_cutoff.append(source_id)
            except LocalInvestmentPilotError:
                time_status = "KNOWN_AT_INVALID"
                unknown_time.append(source_id)
        else:
            unknown_time.append(source_id)
        hash_claim = _text(item.get("raw_sha256_claimed")) or None
        if hash_claim is not None and not _SHA256_RE.fullmatch(hash_claim):
            raise LocalInvestmentPilotError(f"EVIDENCE_SHA256_FORMAT_INVALID:{source_id}")
        clean_rows.append({
            "source_id": source_id,
            "title": _text(item.get("title")) or "未提供标题",
            "source_class": source_class,
            "source_ref": _text(item.get("source_ref")) or "UNKNOWN",
            "published_at": _text(item.get("published_at")) or None,
            "known_at": known_at or None,
            "time_status": time_status,
            "summary": _text(item.get("summary")) or "未提供事实摘要",
            "raw_sha256_claimed": hash_claim,
            "raw_bytes_verified": False,
            "formal_evidence_pit_admission": False,
        })
    return clean_rows, after_cutoff, unknown_time


def _collect_references(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"evidence_refs", "source_refs", "evidence_ids", "source_ids"} and isinstance(item, list):
                found.update(str(row).strip() for row in item if str(row).strip())
            else:
                found.update(_collect_references(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_references(item))
    return found


def _normalise_assessment(raw: Any) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise LocalInvestmentPilotError("ASSESSMENT_MUST_BE_OBJECT")
    trust = dict(raw.get("trust") or {})
    reality = dict(raw.get("reality") or {})
    quality = dict(raw.get("quality") or {})
    thesis = dict(raw.get("thesis") or {})
    mie = dict(raw.get("market_implied_expectation") or {})
    gap = dict(raw.get("expectation_gap") or {})
    risk = dict(raw.get("risk") or {})
    drivers = raw.get("value_drivers") or []
    if not isinstance(drivers, list):
        raise LocalInvestmentPilotError("VALUE_DRIVERS_MUST_BE_ARRAY")
    for i, driver in enumerate(drivers):
        if not isinstance(driver, Mapping):
            raise LocalInvestmentPilotError(f"VALUE_DRIVER_{i}_MUST_BE_OBJECT")
    trust["status"] = _status(trust.get("status"), TRUST_STATES, "TRUST_STATUS")
    reality["status"] = _status(reality.get("status"), ASSESSMENT_STATES, "REALITY_STATUS")
    quality["status"] = _status(quality.get("status"), ASSESSMENT_STATES, "QUALITY_STATUS")
    thesis["status"] = _status(thesis.get("status"), THESIS_STATES, "THESIS_STATUS")
    mie["status"] = _status(mie.get("status"), MIE_STATES, "MIE_STATUS")
    gap["status"] = _status(gap.get("status"), GAP_STATES, "EXPECTATION_GAP_STATUS")
    gap["direction"] = _status(gap.get("direction"), GAP_DIRECTIONS, "EXPECTATION_GAP_DIRECTION")
    risk["status"] = _status(risk.get("status"), {"PASS", "FAIL", "UNKNOWN"}, "RISK_STATUS")
    risk["max_loss_pct"] = _text(risk.get("max_loss_pct")) or "UNKNOWN"
    thesis["drivers"] = thesis.get("drivers") if isinstance(thesis.get("drivers"), list) else []
    thesis["break_conditions"] = _list_of_text(thesis.get("break_conditions"), "THESIS_BREAK_CONDITIONS")
    thesis["reassessment_triggers"] = _list_of_text(thesis.get("reassessment_triggers"), "REASSESSMENT_TRIGGERS")
    for item in (thesis["drivers"]):
        if not isinstance(item, Mapping):
            raise LocalInvestmentPilotError("THESIS_DRIVERS_MUST_BE_OBJECTS")
    clean_drivers: list[dict[str, Any]] = []
    for i, item in enumerate(drivers, start=1):
        clean = dict(item)
        clean["rank"] = int(clean.get("rank", i))
        clean["driver"] = _text(clean.get("driver")) or "未命名价值驱动因素"
        clean["impact"] = _status(
            clean.get("impact"), {"POSITIVE", "NEGATIVE", "MIXED", "UNKNOWN"},
            f"VALUE_DRIVER_{i}_IMPACT",
        )
        clean["rationale"] = _text(clean.get("rationale"))
        clean["evidence_refs"] = _list_of_text(clean.get("evidence_refs"), f"VALUE_DRIVER_{i}_EVIDENCE_REFS")
        clean_drivers.append(clean)
    return {
        "trust": trust,
        "reality": reality,
        "quality": quality,
        "thesis": thesis,
        "value_drivers": clean_drivers,
        "market_implied_expectation": mie,
        "expectation_gap": gap,
        "risk": risk,
    }


def _validate_pilot_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != PILOT_SCHEMA:
        raise LocalInvestmentPilotError("PILOT_INPUT_SCHEMA_MISMATCH")
    allowed_top = {
        "schema_version", "case", "price_input", "evidence_register", "assessment",
        "forecast_valuation", "decision_parameters", "notes",
    }
    extra = sorted(set(payload) - allowed_top)
    if extra:
        raise LocalInvestmentPilotError(f"UNSUPPORTED_TOP_LEVEL_FIELDS:{extra}")
    case_input = payload.get("case")
    price_input = payload.get("price_input")
    if not isinstance(case_input, Mapping) or not isinstance(price_input, Mapping):
        raise LocalInvestmentPilotError("CASE_AND_PRICE_INPUT_OBJECTS_REQUIRED")
    company = _text(case_input.get("company"))
    if not company:
        raise LocalInvestmentPilotError("COMPANY_NAME_REQUIRED")
    market = _text(case_input.get("market") or "CN-A")
    symbol = _text(case_input.get("symbol"))
    as_of = _date(case_input.get("as_of_date"), "AS_OF_DATE")
    position = _text(case_input.get("current_position_pct") if "current_position_pct" in case_input else "0")
    # Reuse the canonical research-intake contract for A/H symbol, market, cutoff,
    # and position normalization. The returned evidence plan remains pending.
    case_seed = build_research_case(symbol, as_of.isoformat(), position, market=market)
    position_pct = _decimal(case_seed["request"]["current_position_pct"], "CURRENT_POSITION_PCT")
    currency = _text(case_input.get("currency") or ("CNY" if case_seed["request"]["market"] == "CN-A" else "HKD")).upper()
    expected_currency = "CNY" if case_seed["request"]["market"] == "CN-A" else "HKD"
    if currency != expected_currency:
        raise LocalInvestmentPilotError("CURRENCY_DOES_NOT_MATCH_MARKET")
    price = _positive(price_input.get("price"), "CURRENT_PRICE")
    observation_date = _date(price_input.get("observation_date"), "PRICE_OBSERVATION_DATE")
    known_at = _local_datetime(price_input.get("known_at"), "PRICE_KNOWN_AT", allow_date_only=False)
    cutoff_start = datetime.combine(as_of, time.min, tzinfo=SHANGHAI)
    price_time_status = "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY"
    price_issues: list[str] = []
    if known_at.date() != observation_date:
        price_issues.append("PRICE_KNOWN_AT_DATE_MISMATCH")
    if observation_date > as_of:
        price_issues.append("PRICE_OBSERVATION_AFTER_CUTOFF")
    if known_at > cutoff_start:
        price_issues.append("PRICE_KNOWN_AFTER_DATE_ONLY_CUTOFF")
    if price_issues:
        price_time_status = "PRICE_NOT_PIT_QUALIFIED"
    assurance = _text(price_input.get("assurance_label"))
    if assurance != PRICE_ASSURANCE:
        raise LocalInvestmentPilotError("PRICE_ASSURANCE_MUST_REMAIN_OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED")
    source_claims = _list_of_text(price_input.get("sources_claimed"), "PRICE_SOURCE_CLAIMS")
    if not source_claims:
        raise LocalInvestmentPilotError("PRICE_SOURCE_CLAIMS_REQUIRED")
    sources, after_cutoff_sources, unknown_time_sources = _source_register(payload.get("evidence_register"), as_of)
    assessment = _normalise_assessment(payload.get("assessment"))
    referenced = _collect_references(assessment)
    source_ids = {row["source_id"] for row in sources}
    unresolved_references = sorted(referenced - source_ids)
    price_model = payload.get("forecast_valuation")
    if price_model is None:
        price_model = {}
    if not isinstance(price_model, Mapping):
        raise LocalInvestmentPilotError("FORECAST_VALUATION_MUST_BE_OBJECT")
    forecast_valuation = dict(price_model)
    forecast_valuation["model"] = _text(forecast_valuation.get("model")) or "UNKNOWN"
    forecast_valuation["model_rationale"] = _text(forecast_valuation.get("model_rationale"))
    forecast_valuation["entry_value_reference_per_share"] = _text(
        forecast_valuation.get("entry_value_reference_per_share")
    ) or None
    forecast_valuation["probabilities_calibrated"] = forecast_valuation.get("probabilities_calibrated") is True
    forecast_valuation["probability_calibration_basis"] = _text(
        forecast_valuation.get("probability_calibration_basis")
    )
    forecast_valuation["assumptions"] = _list_of_text(
        forecast_valuation.get("assumptions"), "FORECAST_ASSUMPTIONS"
    )
    forecast_valuation["scenarios"] = forecast_valuation.get("scenarios") or {}
    if not isinstance(forecast_valuation["scenarios"], Mapping):
        raise LocalInvestmentPilotError("FORECAST_SCENARIOS_MUST_BE_OBJECT")
    parameters = dict(payload.get("decision_parameters") or {})
    horizon_years = parameters.get("horizon_years", 1)
    try:
        horizon_numeric = int(horizon_years)
    except (TypeError, ValueError) as exc:
        raise LocalInvestmentPilotError("HORIZON_YEARS_INVALID") from exc
    if horizon_numeric not in (1, 2, 3):
        raise LocalInvestmentPilotError("HORIZON_YEARS_MUST_BE_1_TO_3")
    horizon_override = parameters.get("horizon_override", False)
    basis = parameters.get("horizon_override_basis") or []
    rationale = _text(parameters.get("horizon_selection_rationale") or "IIOS 默认以 1 年作为年化回报参考期限。")
    if not isinstance(horizon_override, bool) or not isinstance(basis, list):
        raise LocalInvestmentPilotError("HORIZON_OVERRIDE_FIELDS_INVALID")
    if horizon_numeric == 3:
        if horizon_override is not True or not basis:
            raise LocalInvestmentPilotError("THREE_YEAR_HORIZON_REQUIRES_EXPLICIT_OVERRIDE_AND_REASON")
        if any(value not in {"MAJOR_INDUSTRY_LEADER", "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX"} for value in basis):
            raise LocalInvestmentPilotError("THREE_YEAR_HORIZON_OVERRIDE_BASIS_INVALID")
    elif horizon_override or basis:
        raise LocalInvestmentPilotError("HORIZON_OVERRIDE_ONLY_ALLOWED_FOR_THREE_YEARS")
    required_return = _decimal(parameters.get("required_return_annualized", "0.15"), "REQUIRED_RETURN_ANNUALIZED")
    if required_return < FUNDAMENTAL_TARGET_ANNUALIZED_RETURN:
        raise LocalInvestmentPilotError("REQUIRED_RETURN_CANNOT_BE_BELOW_15_PERCENT_CORE_HURDLE")
    max_loss = _decimal(parameters.get("max_loss_pct", assessment["risk"]["max_loss_pct"] if assessment["risk"]["max_loss_pct"] != "UNKNOWN" else "25"), "MAX_LOSS_PCT")
    if max_loss < 0 or max_loss >= 100:
        raise LocalInvestmentPilotError("MAX_LOSS_PCT_MUST_BE_IN_0_TO_100_EXCLUSIVE")
    return {
        "case": {
            "case_id": case_seed["case_id"],
            "company": company,
            "market": case_seed["request"]["market"],
            "symbol": case_seed["request"]["symbol"],
            "currency": currency,
            "as_of_date": as_of.isoformat(),
            "current_position_pct": format(position_pct, "f"),
            "venue_hint": case_seed["security_identity"]["venue_hint"],
            "venue_hint_is_evidence": False,
            "case_status": "PILOT_CASE_NOT_FORMALLY_ADMITTED",
        },
        "price_input": {
            "price": format(price, "f"),
            "currency": currency,
            "observation_date": observation_date.isoformat(),
            "known_at": known_at.isoformat(),
            "assurance_label": PRICE_ASSURANCE,
            "sources_claimed": source_claims,
            "pit_time_status": price_time_status,
            "pit_issues": price_issues,
            "source_origin_verified": False,
            "source_vintage_verified": False,
            "source_use_rights_verified": False,
            "canonical_price_admission": False,
        },
        "evidence_register": sources,
        "assessment": assessment,
        "forecast_valuation": forecast_valuation,
        "decision_parameters": {
            "horizon_years": horizon_numeric,
            "horizon_override": horizon_override,
            "horizon_override_basis": [str(x) for x in basis],
            "horizon_selection_rationale": rationale,
            "required_return_annualized": format(required_return, "f"),
            "fundamental_target_annualized_return": format(FUNDAMENTAL_TARGET_ANNUALIZED_RETURN, "f"),
            "entry_return_cushion_threshold": format(BUY_ENTRY_RETURN_CUSHION_THRESHOLD, "f"),
            "max_loss_pct": format(max_loss, "f"),
        },
        "notes": _text(payload.get("notes")),
        "unresolved_evidence_references": unresolved_references,
        "after_cutoff_sources": after_cutoff_sources,
        "unknown_time_sources": unknown_time_sources,
    }


def _return_metrics(prepared: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    price_input = prepared["price_input"]
    forecast = prepared["forecast_valuation"]
    if price_input["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        return None, "PRICE_NOT_PIT_QUALIFIED"
    anchor = forecast.get("entry_value_reference_per_share")
    if anchor is None:
        return None, "ENTRY_VALUE_REFERENCE_MISSING"
    try:
        anchor_value = _positive(anchor, "ENTRY_VALUE_REFERENCE_PER_SHARE")
    except LocalInvestmentPilotError:
        return None, "ENTRY_VALUE_REFERENCE_INVALID"
    scenario_input = forecast.get("scenarios")
    if not isinstance(scenario_input, Mapping) or set(scenario_input) != set(SCENARIOS):
        return None, "BEAR_BASE_BULL_SCENARIOS_REQUIRED"
    return_gate_scenarios: dict[str, Any] = {}
    populated = 0
    for scenario_name in SCENARIOS:
        row = scenario_input.get(scenario_name)
        if not isinstance(row, Mapping):
            return None, f"{scenario_name.upper()}_SCENARIO_MISSING"
        probability = row.get("probability")
        terminal = row.get("terminal_value_per_share")
        distribution = row.get("cash_distributions_per_share", "0")
        rationale = _text(row.get("rationale"))
        if probability is None or terminal is None or not rationale:
            return None, f"{scenario_name.upper()}_SCENARIO_INPUTS_INCOMPLETE"
        populated += 1
        return_gate_scenarios[scenario_name] = {
            "probability": str(probability),
            "terminal_value_per_share": str(terminal),
            "cash_distributions_per_share": str(distribution),
            "probability_rationale": rationale,
        }
    if populated != 3:
        return None, "BEAR_BASE_BULL_SCENARIOS_REQUIRED"
    params = prepared["decision_parameters"]
    return_gate = {
        "entry_price": price_input["price"],
        "entry_value_reference": format(anchor_value, "f"),
        "horizon_years": str(params["horizon_years"]),
        "horizon_override": params["horizon_override"],
        "horizon_override_basis": params["horizon_override_basis"],
        "horizon_selection_rationale": params["horizon_selection_rationale"],
        "buy_entry_return_cushion_threshold": params["entry_return_cushion_threshold"],
        "fundamental_target_annualized_return": params["fundamental_target_annualized_return"],
        "required_return_annualized": params["required_return_annualized"],
        # This pilot calls the existing deterministic return solver directly. These
        # records are model inputs only, not canonical Forecast/Valuation references.
        "lineage_version": "PILOT_NON_CANONICAL_MODEL_INPUTS",
        "canonical_forecast_ref": {"status": "PILOT_NON_CANONICAL"},
        "canonical_valuation_ref": {"status": "PILOT_NON_CANONICAL"},
        "scenarios": return_gate_scenarios,
    }
    try:
        metrics = calculate_return_metrics(return_gate, max_loss_pct=params["max_loss_pct"])
    except (ValueError, KeyError, TypeError) as exc:
        raise LocalInvestmentPilotError(f"RETURN_SCENARIO_CALCULATION_FAILED:{exc}") from exc
    return _json_safe(metrics), None


def _provisional_decision(prepared: Mapping[str, Any], metrics: Mapping[str, Any] | None, metrics_reason: str | None) -> dict[str, Any]:
    assessment = prepared["assessment"]
    case = prepared["case"]
    price_input = prepared["price_input"]
    trust = assessment["trust"]["status"]
    thesis = assessment["thesis"]["status"]
    issues: list[str] = []
    if not prepared["evidence_register"]:
        issues.append("EVIDENCE_REGISTER_EMPTY")
    if trust != "PASS":
        issues.append(f"TRUST_STATUS_{trust}")
    if assessment["reality"]["status"] != "PASS":
        issues.append(f"REALITY_STATUS_{assessment['reality']['status']}")
    if assessment["quality"]["status"] != "PASS":
        issues.append(f"QUALITY_STATUS_{assessment['quality']['status']}")
    if thesis != "INTACT":
        issues.append(f"THESIS_STATUS_{thesis}")
    if assessment["market_implied_expectation"]["status"] != "PASS":
        issues.append(f"MIE_STATUS_{assessment['market_implied_expectation']['status']}")
    if assessment["expectation_gap"]["status"] != "PASS":
        issues.append(f"EXPECTATION_GAP_STATUS_{assessment['expectation_gap']['status']}")
    if assessment["expectation_gap"]["direction"] != "POSITIVE":
        issues.append(f"EXPECTATION_GAP_DIRECTION_{assessment['expectation_gap']['direction']}")
    if assessment["risk"]["status"] != "PASS":
        issues.append(f"RISK_STATUS_{assessment['risk']['status']}")
    if prepared["unresolved_evidence_references"]:
        issues.append("UNRESOLVED_EVIDENCE_REFERENCES")
    if prepared["after_cutoff_sources"]:
        issues.append("REFERENCED_SOURCE_AFTER_CUTOFF")
    if prepared["unknown_time_sources"]:
        issues.append("SOURCE_KNOWN_AT_MISSING_OR_INVALID")
    if price_input["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        issues.append("PRICE_NOT_PIT_QUALIFIED")
    if trust == "FAIL":
        action = "NO-BUY"
        reason = "Trust failure blocks new risk; this is not an automatic sell instruction."
    elif thesis == "BROKEN":
        action = "REVIEW_REQUIRED"
        reason = "Thesis marked broken; existing holdings require explicit human reassessment."
    elif metrics is None:
        action = "REVIEW_REQUIRED"
        reason = f"No decision-grade price/return screen can be produced: {metrics_reason or 'UNKNOWN'}."
    elif not metrics.get("return_gate_pass", False):
        action = "NO-BUY" if Decimal(case["current_position_pct"]) == 0 else "REVIEW_REQUIRED"
        reason = "Current price fails at least one required return, entry-cushion or bear-loss threshold under the supplied scenario assumptions."
    elif issues:
        action = "REVIEW_REQUIRED"
        reason = "Price screen passes under the supplied assumptions, but one or more core evidence/assessment gates remain open."
    else:
        action = "BUY" if Decimal(case["current_position_pct"]) == 0 else "ADD"
        reason = "All supplied pilot conditions pass; provisional action remains subject to human review and is not a canonical Decision."
    return {
        "status": PILOT_STATUS,
        "provisional_action": action,
        "reason": reason,
        "gating_issues": issues,
        "price_screen_status": (
            "CURRENT_PRICE_AT_OR_BELOW_RETURN_RISK_CEILING"
            if metrics is not None and Decimal(price_input["price"]) <= Decimal(str(metrics["target_entry_price"]))
            else "CURRENT_PRICE_ABOVE_RETURN_RISK_CEILING"
            if metrics is not None
            else "UNKNOWN"
        ),
        "human_approval_required": True,
        "human_final_decision_required": True,
        "auto_execution": False,
        "execution_authorized": False,
        "formal_decision_created": False,
    }


def _fmt(value: Any, missing: str = "未知 / UNKNOWN") -> str:
    if value is None or value == "":
        return missing
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _render_report(analysis: Mapping[str, Any]) -> str:
    case = analysis["case"]
    price = analysis["price_input"]
    assess = analysis["assessment"]
    calc = analysis["return_metrics"]
    decision = analysis["decision"]
    forecast = analysis["forecast_valuation"]
    params = analysis["decision_parameters"]
    lines = [
        f"# IIOS 本地投资研究试运行报告：{case['company']}（{case['symbol']}）",
        "",
        f"- 试运行 ID：{analysis['pilot_id']}",
        f"- 市场 / 标的：{case['market']} / {case['symbol']}",
        f"- 分析截止：{case['as_of_date']}（日期型截止按上海时间当日 00:00 解释）",
        f"- 当前价：{price['price']} {case['currency']}；观察日期 {price['observation_date']}",
        f"- 当前持仓：{case['current_position_pct']}%",
        f"- 路径状态：**{PILOT_STATUS}**",
        "",
        "> 本报告用于个人本地实际运行测试。人工价格、来源摘要和 AI/操作者评估均未形成正式 Evidence/PIT、Forecast、Valuation Admission、Decision Admission 或 canonical Run Receipt。报告给出的动作仅是试运行建议，最终决定由人作出，不会自动交易。",
        "",
        "## 1. 结论摘要",
        "",
        f"- 试运行建议：**{decision['provisional_action']}**",
        f"- 判断理由：{decision['reason']}",
        f"- 价格筛选：{decision['price_screen_status']}",
        f"- 预期年化回报：{_fmt(calc.get('expected_annualized_return') if calc else None)}",
        f"- 15% 年化目标：{_fmt(calc.get('fundamental_target_pass') if calc else None)}",
        f"- Required Return（{params['required_return_annualized']}）：{_fmt(calc.get('required_return_pass') if calc else None)}",
        f"- 目标入场价上限：{_fmt(calc.get('target_entry_price') if calc else None)}",
        f"- 当前价低于 / 高于入场价上限：{_fmt(decision.get('price_screen_status'))}",
        f"- 风险状态：{assess['risk']['status']}；Bear 损失上限：{params['max_loss_pct']}%",
        "",
        "## 2. Trust / Reality / Quality",
        "",
        f"- Trust：{assess['trust']['status']} — {_fmt(assess['trust'].get('summary'))}",
        f"- Reality：{assess['reality']['status']} — {_fmt(assess['reality'].get('summary'))}",
        f"- Quality：{assess['quality']['status']} — {_fmt(assess['quality'].get('summary'))}",
        "",
        "## 3. Thesis 与价值驱动因素",
        "",
        f"- Thesis 状态：{assess['thesis']['status']}",
        f"- 核心投资论点：{_fmt(assess['thesis'].get('core_statement'))}",
        "",
        "### 价值驱动因素排序",
        "",
    ]
    if assess["value_drivers"]:
        for item in sorted(assess["value_drivers"], key=lambda row: row["rank"]):
            refs = ", ".join(item.get("evidence_refs") or []) or "未绑定来源"
            lines.append(f"{item['rank']}. **{item['driver']}**（{item['impact']}）：{_fmt(item.get('rationale'))}；来源引用：{refs}")
    else:
        lines.append("当前没有已录入的价值驱动因素。")
    lines += ["", "### Thesis 失效条件", ""]
    lines.extend(f"- {item}" for item in assess["thesis"]["break_conditions"]) if assess["thesis"]["break_conditions"] else lines.append("- 未提供；不得把空列表解释为没有风险。")
    lines += ["", "### 重新评估触发器", ""]
    lines.extend(f"- {item}" for item in assess["thesis"]["reassessment_triggers"]) if assess["thesis"]["reassessment_triggers"] else lines.append("- 未提供。")
    lines += [
        "",
        "## 4. Forecast / Valuation / Return",
        "",
        f"- 模型：{_fmt(forecast.get('model'))}",
        f"- 模型选择理由：{_fmt(forecast.get('model_rationale'))}",
        f"- 入场安全边际参考价值：{_fmt(forecast.get('entry_value_reference_per_share'))} {case['currency']}/股",
        f"- 独立情景概率是否校准：{'是' if forecast.get('probabilities_calibrated') else '否 / 尚未校准'}",
        "",
        "| 情景 | 概率 | 期末每股价值 | 现金分配 | 估算依据 |",
        "|---|---:|---:|---:|---|",
    ]
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = forecast.get("scenarios", {}).get(name) or {}
        lines.append(
            f"| {label} | {_fmt(row.get('probability'))} | {_fmt(row.get('terminal_value_per_share'))} | "
            f"{_fmt(row.get('cash_distributions_per_share', '0'))} | {_fmt(row.get('rationale'))} |"
        )
    if calc:
        lines += [
            "",
            "| 回报 / 风险指标 | 结果 |",
            "|---|---:|",
            f"| 概率加权终值 | {calc['expected_terminal_wealth']} {case['currency']}/股 |",
            f"| 预期总回报 | {calc['expected_total_return']} |",
            f"| 预期年化回报（H={params['horizon_years']}Y） | {calc['expected_annualized_return']} |",
            f"| 入场安全边际 | {calc['margin_of_safety']} |",
            f"| Bear 情景回报 | {calc['bear_return']} |",
            f"| 回报门槛对应的入场价上限 | {calc['target_entry_price_for_return']} |",
            f"| 风险约束对应的入场价上限 | {_fmt(calc.get('target_entry_price_for_risk'))} |",
            f"| **共同约束下的目标入场价上限** | **{calc['target_entry_price']}** |",
        ]
    else:
        lines += ["", f"价格 / 回报计算未完成：{analysis['return_metrics_reason'] or '模型输入不完整'}。"]
    lines += [
        "",
        "### 主要模型假设",
        "",
    ]
    lines.extend(f"- {item}" for item in forecast.get("assumptions", [])) if forecast.get("assumptions") else lines.append("- 未提供。情景价值仅为模型输入，不是市场一致预期。")
    lines += [
        "",
        "## 5. 市场隐含预期（MIE）与预期差",
        "",
        f"- MIE 可识别状态：{assess['market_implied_expectation']['status']}",
        f"- MIE 结论：{_fmt(assess['market_implied_expectation'].get('summary'))}",
        f"- 预期差状态：{assess['expectation_gap']['status']}",
        f"- 预期差方向：{assess['expectation_gap']['direction']}",
        f"- 预期差论据：{_fmt(assess['expectation_gap'].get('summary'))}",
        "",
        "若 MIE 的可行解集合、可识别性、稳定性或历史支持不足，应保留 UNKNOWN / NOT_IDENTIFIABLE，而不是用内在价值上行替代市场隐含预期。",
        "",
        "## 6. 风险与组合约束",
        "",
        f"- 风险状态：{assess['risk']['status']}",
        f"- 风险说明：{_fmt(assess['risk'].get('summary'))}",
    ]
    risk_items = assess["risk"].get("items") or []
    if risk_items:
        lines.extend(f"- {item}" for item in risk_items)
    else:
        lines.append("- 未提供具体风险清单。")
    lines += [
        f"- 当前持仓：{case['current_position_pct']}%",
        f"- 最大 Bear 损失约束：{params['max_loss_pct']}%",
        "",
        "## 7. 来源与截止时点",
        "",
        f"- 价格 assurance：{price['assurance_label']}；已知时点校验：{price['pit_time_status']}",
        "- 以上只表示时间字段符合 / 不符合本次试运行截止条件，不证明行情来源原始字节、数据使用权或来源身份。",
        "",
        "| 来源 ID | 类型 | 标题 | known_at | 截止校验 | 摘要 |",
        "|---|---|---|---|---|---|",
    ]
    if analysis["evidence_register"]:
        for item in analysis["evidence_register"]:
            lines.append(
                f"| {item['source_id']} | {item['source_class']} | {item['title']} | "
                f"{_fmt(item.get('known_at'))} | {item['time_status']} | {item['summary']} |"
            )
    else:
        lines.append("| — | — | 未提供来源清单 | UNKNOWN | UNKNOWN | 未提供来源事实；结论必须保持审慎 |")
    lines += [
        "",
        "来源引用不等于正式 Evidence/PIT Admission。来源字节未在本流程中重新下载、核验或准入。",
        "",
        "## 8. 需要人工补齐 / 复核的问题",
        "",
    ]
    issues = decision["gating_issues"]
    if issues:
        lines.extend(f"- {item}" for item in issues)
    else:
        lines.append("- 试运行输入所声明的关键模块状态均满足当前 provisional gate；仍须人工检查模型假设与原始来源。")
    if analysis.get("notes"):
        lines += ["", "## 操作者备注", "", analysis["notes"]]
    lines += [
        "",
        "## 9. 非正式化声明",
        "",
        "- 运行等级：PILOT_NON_CANONICAL；试运行输出不是正式 IIOS Decision。",
        "- 正式 Evidence/PIT Admission：未创建；来源使用权与原始字节未独立核验。",
        "- 正式 Forecast / Valuation Admission：未创建；输入情景是假设而非准入对象。",
        "- canonical Machine Publication / IIOS_RUN_RECEIPT：未创建。本地文件回放收据不是正式 Run Receipt。",
        "- 人工最终审批：必需；自动下单与自动执行：关闭。",
        "",
    ]
    return "\n".join(lines)


def _build_artifacts(input_raw: bytes) -> tuple[str, bytes, bytes, bytes, dict[str, Any]]:
    payload = _parse_json_object(input_raw, reason="PILOT_INPUT_JSON_INVALID")
    prepared = _validate_pilot_input(payload)
    metrics, metric_reason = _return_metrics(prepared)
    decision = _provisional_decision(prepared, metrics, metric_reason)
    input_sha = _sha256(input_raw)
    pilot_id = "local-pilot-" + _sha256(_canonical({
        "runner_version": PILOT_RUNNER_VERSION,
        "input_sha256": input_sha,
    }))[:24]
    analysis = {
        "schema_version": PILOT_ANALYSIS_SCHEMA,
        "runner_version": PILOT_RUNNER_VERSION,
        "pilot_id": pilot_id,
        "status": PILOT_STATUS,
        "input_sha256": input_sha,
        "case": prepared["case"],
        "price_input": prepared["price_input"],
        "evidence_register": prepared["evidence_register"],
        "assessment": prepared["assessment"],
        "forecast_valuation": prepared["forecast_valuation"],
        "decision_parameters": prepared["decision_parameters"],
        "return_metrics": metrics,
        "return_metrics_reason": metric_reason,
        "decision": decision,
        "evidence_pit_summary": {
            "source_count": len(prepared["evidence_register"]),
            "after_cutoff_source_ids": prepared["after_cutoff_sources"],
            "unknown_or_invalid_known_at_source_ids": prepared["unknown_time_sources"],
            "unresolved_source_references": prepared["unresolved_evidence_references"],
            "source_bytes_verified": False,
            "source_origin_verified": False,
            "source_use_rights_verified": False,
            "formal_evidence_pit_admission": False,
        },
        "governance": {
            "status": PILOT_STATUS,
            "canonical_price_admission": False,
            "formal_evidence_pit_admission": False,
            "formal_semantic_admission": False,
            "formal_forecast_created": False,
            "formal_valuation_admission": False,
            "formal_decision_created": False,
            "canonical_publication_created": False,
            "canonical_run_receipt_created": False,
            "pilot_receipt_created": True,
            "human_approval_required": True,
            "execution_authorized": False,
            "auto_execution": False,
        },
    }
    analysis_raw = _canonical(analysis) + b"\n"
    report_raw = _render_report(analysis).encode("utf-8")
    receipt = {
        "receipt_schema": PILOT_RECEIPT_SCHEMA,
        "status": PILOT_STATUS,
        "pilot_id": pilot_id,
        "runner_version": PILOT_RUNNER_VERSION,
        "input_sha256": input_sha,
        "analysis_file_sha256": _sha256(analysis_raw),
        "report_file_sha256": _sha256(report_raw),
        "integrity_scope": "LOCAL_REPLAY_OF_THE_EXACT_INPUT_AND_DETERMINISTIC_OUTPUTS_ONLY",
        "price_values_in_receipt": False,
        "source_claims_in_receipt": False,
        "source_origin_verified": False,
        "source_vintage_verified": False,
        "source_use_rights_verified": False,
        "formal_evidence_pit_admission": False,
        "formal_decision_created": False,
        "canonical_publication_created": False,
        "canonical_run_receipt_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }
    receipt_raw = _canonical(receipt) + b"\n"
    return pilot_id, analysis_raw, report_raw, receipt_raw, receipt


def _read_regular_child(directory: Path, name: str) -> bytes:
    path = directory / name
    if path.is_symlink() or not path.is_file():
        raise LocalInvestmentPilotError(f"BUNDLE_FILE_MISSING_OR_SYMLINK:{name}")
    return path.read_bytes()


def verify_local_pilot_bundle(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise LocalInvestmentPilotError("PILOT_BUNDLE_MUST_BE_DIRECTORY_NOT_SYMLINK")
    root = _outside_repository(root, "PILOT_BUNDLE_PATH", must_exist=True)
    input_raw = _read_regular_child(root, "input.json")
    stored_analysis = _read_regular_child(root, "analysis.json")
    stored_report = _read_regular_child(root, "report.md")
    receipt_raw = _read_regular_child(root, "pilot_receipt.json")
    receipt = _parse_json_object(receipt_raw, reason="PILOT_RECEIPT_JSON_INVALID")
    expected_id, expected_analysis, expected_report, _expected_receipt, _receipt_obj = _build_artifacts(input_raw)
    if stored_analysis != expected_analysis:
        raise LocalInvestmentPilotError("PILOT_ANALYSIS_REPLAY_MISMATCH")
    if stored_report != expected_report:
        raise LocalInvestmentPilotError("PILOT_REPORT_REPLAY_MISMATCH")
    if receipt.get("pilot_id") != expected_id or receipt.get("input_sha256") != _sha256(input_raw):
        raise LocalInvestmentPilotError("PILOT_RECEIPT_INPUT_BINDING_MISMATCH")
    if receipt.get("analysis_file_sha256") != _sha256(stored_analysis):
        raise LocalInvestmentPilotError("PILOT_RECEIPT_ANALYSIS_HASH_MISMATCH")
    if receipt.get("report_file_sha256") != _sha256(stored_report):
        raise LocalInvestmentPilotError("PILOT_RECEIPT_REPORT_HASH_MISMATCH")
    for flag in (
        "source_origin_verified",
        "source_vintage_verified",
        "source_use_rights_verified",
        "formal_evidence_pit_admission",
        "formal_decision_created",
        "canonical_publication_created",
        "canonical_run_receipt_created",
        "execution_authorized",
        "auto_execution",
    ):
        if receipt.get(flag) is not False:
            raise LocalInvestmentPilotError(f"PILOT_RECEIPT_FORBIDDEN_FLAG:{flag}")
    if os.name != "nt":
        if stat.S_IMODE(root.stat().st_mode) & 0o077:
            raise LocalInvestmentPilotError("PILOT_BUNDLE_DIRECTORY_PERMISSIONS_TOO_OPEN")
        for name in ("input.json", "analysis.json", "report.md", "pilot_receipt.json"):
            if stat.S_IMODE((root / name).stat().st_mode) & 0o077:
                raise LocalInvestmentPilotError(f"PILOT_BUNDLE_FILE_PERMISSIONS_TOO_OPEN:{name}")
    return {
        "status": "PILOT_REPLAY_PASS",
        "pilot_id": expected_id,
        "analysis_file_sha256": _sha256(stored_analysis),
        "report_file_sha256": _sha256(stored_report),
        "receipt_file_sha256": _sha256(receipt_raw),
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "auto_execution": False,
        "run_dir": str(root),
    }


def run_local_investment_pilot(*, input_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    input_file = _outside_repository(input_path, "PILOT_INPUT_PATH", must_exist=True)
    input_raw = input_file.read_bytes()
    pilot_id, analysis_raw, report_raw, receipt_raw, _receipt = _build_artifacts(input_raw)
    root = _prepare_private_directory(output_root, "PILOT_OUTPUT_ROOT")
    run_dir = root / pilot_id
    if run_dir.exists() or run_dir.is_symlink():
        replay = verify_local_pilot_bundle(run_dir)
        return {**replay, "status": "PILOT_REUSED_IDENTICAL_INPUT", "replay_status": "PILOT_REPLAY_PASS"}
    temp = Path(tempfile.mkdtemp(prefix=".pilot-tmp-", dir=str(root)))
    try:
        if os.name != "nt":
            os.chmod(temp, 0o700)
        _write_private_file(temp / "input.json", input_raw)
        _write_private_file(temp / "analysis.json", analysis_raw)
        _write_private_file(temp / "report.md", report_raw)
        _write_private_file(temp / "pilot_receipt.json", receipt_raw)
        if run_dir.exists() or run_dir.is_symlink():
            raise LocalInvestmentPilotError("PILOT_OUTPUT_RUN_ALREADY_EXISTS_RACE")
        os.rename(temp, run_dir)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    replay = verify_local_pilot_bundle(run_dir)
    return {
        **replay,
        "status": "PILOT_CREATED",
        "replay_status": replay["status"],
        "provisional_action": json.loads(analysis_raw.decode("utf-8"))["decision"]["provisional_action"],
        "run_dir": str(run_dir),
    }


def _build_template(
    *, company: str, symbol: str, market: str, as_of_date: str, current_position_pct: str,
    price: str, price_observation_date: str, price_known_at: str, price_source_claim: str,
) -> dict[str, Any]:
    seed = build_research_case(symbol, as_of_date, current_position_pct, market=market)
    currency = "CNY" if seed["request"]["market"] == "CN-A" else "HKD"
    _positive(price, "CURRENT_PRICE")
    observation = _date(price_observation_date, "PRICE_OBSERVATION_DATE")
    known_at = _local_datetime(price_known_at, "PRICE_KNOWN_AT", allow_date_only=False)
    if known_at.date() != observation:
        raise LocalInvestmentPilotError("PRICE_KNOWN_AT_DATE_MUST_MATCH_OBSERVATION_DATE")
    if not _text(price_source_claim):
        raise LocalInvestmentPilotError("PRICE_SOURCE_CLAIM_REQUIRED")
    return {
        "schema_version": PILOT_SCHEMA,
        "case": {
            "company": _text(company),
            "market": seed["request"]["market"],
            "symbol": seed["request"]["symbol"],
            "currency": currency,
            "as_of_date": seed["temporal_scope"]["cutoff_date"],
            "current_position_pct": seed["decision_context"]["current_position_pct"],
        },
        "price_input": {
            "price": str(price),
            "currency": currency,
            "observation_date": observation.isoformat(),
            "known_at": known_at.isoformat(),
            "assurance_label": PRICE_ASSURANCE,
            "sources_claimed": [_text(price_source_claim)],
        },
        "evidence_register": [],
        "assessment": {
            "trust": {"status": "UNKNOWN", "summary": "尚未完成信任审查", "evidence_refs": []},
            "reality": {"status": "UNKNOWN", "summary": "尚未完成公司经营现实审查", "evidence_refs": []},
            "quality": {"status": "UNKNOWN", "summary": "尚未完成经济质量审查", "evidence_refs": []},
            "thesis": {
                "status": "UNKNOWN",
                "core_statement": "",
                "drivers": [],
                "break_conditions": [],
                "reassessment_triggers": [],
                "evidence_refs": [],
            },
            "value_drivers": [],
            "market_implied_expectation": {
                "status": "NOT_IDENTIFIABLE",
                "summary": "尚未提供足够历史价格 / 估值观察以识别 MIE",
                "evidence_refs": [],
            },
            "expectation_gap": {
                "status": "UNKNOWN",
                "direction": "UNKNOWN",
                "summary": "未验证独立预测与市场隐含预期之间的差异",
                "evidence_refs": [],
            },
            "risk": {"status": "UNKNOWN", "summary": "尚未完成风险审查", "max_loss_pct": "25", "items": []},
        },
        "forecast_valuation": {
            "model": "UNKNOWN",
            "model_rationale": "",
            "entry_value_reference_per_share": None,
            "probabilities_calibrated": False,
            "probability_calibration_basis": "",
            "assumptions": [],
            "scenarios": {
                "bear": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
                "base": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
                "bull": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
            },
        },
        "decision_parameters": {
            "horizon_years": 1,
            "horizon_override": False,
            "horizon_override_basis": [],
            "horizon_selection_rationale": "默认以 1 年作为年化回报参考期限；只有重要行业龙头或重大投资/资本开支周期才显式覆盖为 3 年。",
            "required_return_annualized": "0.15",
            "max_loss_pct": "25",
        },
        "notes": "请补入截至 cutoff 的事实、独立预测及 MIE 评估。未知数据应保留 UNKNOWN / NOT_IDENTIFIABLE，不得编造。",
    }


def _prompt_text(template_path: Path) -> str:
    return (
        "IIOS 本地投资试运行：结构化研究输入填写说明\n\n"
        "请在本地打开 pilot-input JSON，并向 AI 提供该 JSON、你已取得的公司公告/财报事实摘要和来源链接。"
        "要求 AI 返回完整 JSON，不得添加新顶层字段，必须保留 schema_version、case 和 price_input 不变。\n\n"
        "填写 assessment 中的 Trust、Reality、Quality、Thesis、价值驱动排序、MIE、预期差和风险。"
        "对每个事实/判断尽可能填 evidence_refs，引用 evidence_register.source_id。"
        "给出 Bear/Base/Bull 三情景概率、期末每股价值、现金分配、逐项理由及入场安全边际参考价值。"
        "当前价只来自操作者输入，不能把 price_input.assurance_label 改成来源已验证；人工价格不等于正式行情准入。\n\n"
        "严格规则：资料不够时填写 UNKNOWN / NOT_IDENTIFIABLE，不能为了满足 schema 编造数字；"
        "MIE 只有在可行解集合、可识别性、稳定性与历史支持均足够时才可标 PASS。"
        "Scenario probabilities 是主观假设时必须保持 probabilities_calibrated=false，并披露假设。"
        "正式 Decision、正式 Evidence/PIT、canonical Run Receipt、交易授权一律不创建。\n\n"
        f"本地输入文件：{template_path}\n"
        "将 AI 返回的 JSON 保存为该文件或另存后通过 --input 指定；不要把包含实际价格/来源细节的 JSON 提交 GitHub。"
    )


def create_pilot_template(
    *, company: str, symbol: str, market: str, as_of_date: str, current_position_pct: str,
    price: str, price_observation_date: str, price_known_at: str, price_source_claim: str,
    template_root: str | Path,
) -> dict[str, Any]:
    root = _prepare_private_directory(template_root, "PILOT_TEMPLATE_ROOT")
    template = _build_template(
        company=company, symbol=symbol, market=market, as_of_date=as_of_date,
        current_position_pct=current_position_pct, price=price,
        price_observation_date=price_observation_date, price_known_at=price_known_at,
        price_source_claim=price_source_claim,
    )
    case_token = str(template["case"]["symbol"]).replace(".", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    input_path = root / f"pilot-input-{case_token}-{stamp}.json"
    prompt_path = root / f"pilot-prompt-{case_token}-{stamp}.md"
    _write_private_file(input_path, json.dumps(template, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8") + b"\n")
    try:
        _write_private_file(prompt_path, _prompt_text(input_path).encode("utf-8"))
    except Exception:
        input_path.unlink(missing_ok=True)
        raise
    return {
        "status": "PILOT_TEMPLATE_CREATED",
        "input_template": str(input_path),
        "analysis_prompt": str(prompt_path),
        "case_id": f"RC-{template['case']['market']}-{template['case']['symbol'].replace('.', '-')}-{template['case']['as_of_date'].replace('-', '')}",
        "template_has_real_price": True,
        "private_storage_required": True,
        "formal_decision_created": False,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local candidate-driven IIOS research pilot; non-canonical and analysis-only."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--create-template", action="store_true", help="create private input JSON and prompt for one A/H candidate")
    modes.add_argument("--input", help="run a completed private pilot input JSON")
    modes.add_argument("--replay-run", help="recompute and verify one prior private pilot output directory")
    parser.add_argument("--template-root", default=str(Path.home() / ".iios-private" / "local-pilot" / "inputs"))
    parser.add_argument("--output-root", default=str(Path.home() / ".iios-private" / "local-pilot" / "runs"))
    parser.add_argument("--company")
    parser.add_argument("--symbol")
    parser.add_argument("--market", default="CN-A")
    parser.add_argument("--as-of")
    parser.add_argument("--position", default="0")
    parser.add_argument("--price")
    parser.add_argument("--price-date")
    parser.add_argument("--price-known-at")
    parser.add_argument("--price-source-claim")
    args = parser.parse_args(argv)
    try:
        if args.create_template:
            required = {
                "--company": args.company,
                "--symbol": args.symbol,
                "--as-of": args.as_of,
                "--price": args.price,
                "--price-date": args.price_date,
                "--price-known-at": args.price_known_at,
                "--price-source-claim": args.price_source_claim,
            }
            missing = [flag for flag, value in required.items() if not value]
            if missing:
                parser.error("--create-template requires " + ", ".join(missing))
            result = create_pilot_template(
                company=args.company, symbol=args.symbol, market=args.market, as_of_date=args.as_of,
                current_position_pct=args.position, price=args.price, price_observation_date=args.price_date,
                price_known_at=args.price_known_at, price_source_claim=args.price_source_claim,
                template_root=args.template_root,
            )
        elif args.input:
            result = run_local_investment_pilot(input_path=args.input, output_root=args.output_root)
        else:
            result = verify_local_pilot_bundle(args.replay_run)
        print(json.dumps(_json_safe(result), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (LocalInvestmentPilotError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
