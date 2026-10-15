from __future__ import annotations

"""Minimal candidate-driven, non-canonical local IIOS pilot.

This is a practical trial path, not a second canonical engine. It uses the
existing research-intake validator and the existing IIOS return/entry-price
solver. Formal admission and canonical Decision code remain unchanged.
"""

import argparse
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import time as _time
import subprocess
import sys
from typing import Any, Mapping

from .decision_kernel_v03 import evaluate_production_decision
from .decision_state_machine_v01 import MIE_POLICY_OPTIONAL_EXPLANATORY
from .local_pilot_portfolio_package_v01 import build_local_pilot_portfolio_package
from .operating_driver_forecast_v01 import evaluate_operating_driver_forecast, render_operating_driver_section
from .valuation_transmission_v01 import (
    VALUATION_TRANSMISSION_SCHEMA,
    evaluate_valuation_transmission,
    render_valuation_transmission_section,
)
from .investment_core_contract_v03 import (
    BUY_ENTRY_RETURN_CUSHION_THRESHOLD,
    FUNDAMENTAL_TARGET_ANNUALIZED_RETURN,
    SCENARIOS,
    calculate_return_metrics,
)
from .research_intake import build_research_case

PILOT_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-0.1"
PILOT_ANALYSIS_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-ANALYSIS-0.1"
PILOT_STATUS = "PILOT_NON_CANONICAL"
PILOT_RECEIPT_SCHEMA = "IIOS-LOCAL-PILOT-RUN-RECORD-0.1"
SHANGHAI = timezone(timedelta(hours=8))
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRICE_ASSURANCE = "OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED"
BUNDLE_FILENAMES = ("input.json", "analysis.json", "report.md")
REPLAY_COMPARISON_FIELDS = (
    "schema_version",
    "status",
    "case",
    "price_input",
    "evidence_register",
    "referenced_evidence_ids",
    "unresolved_evidence_references",
    "after_cutoff_evidence_references",
    "uncertain_timing_evidence_references",
    "assessment",
    "forecast_valuation",
    "operating_driver_forecast",
    "valuation_transmission",
    "operator_valuation_context",
    "price_zone_sensitivity",
    "decision_parameters",
    "portfolio_package",
    "return_metrics",
    "return_metrics_reason",
    "thesis_break_stress_review",
    "notes_price_conflicts",
    "decision",
    "governance",
    "notes",
)


_ORIGINAL_INPUT = input


class LocalInvestmentPilotError(ValueError):
    """Bad local pilot input or unavailable pilot output."""


def _number(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_NUMERIC") from exc
    if not result.is_finite():
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_FINITE")
    return result


def _positive(value: Any, field: str) -> Decimal:
    result = _number(value, field)
    if result <= 0:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_POSITIVE")
    return result


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError) as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_YYYY_MM_DD") from exc


def _datetime(value: Any, field: str, *, allow_date_only: bool = True) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise LocalInvestmentPilotError(f"{field}_REQUIRED")
    if allow_date_only and len(raw) == 10:
        return datetime.combine(_date(raw, field), time.min, tzinfo=SHANGHAI)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_ISO_DATETIME") from exc
    if parsed.tzinfo is None:
        raise LocalInvestmentPilotError(f"{field}_MUST_INCLUDE_TIMEZONE")
    return parsed.astimezone(SHANGHAI)


def _normalize_guided_symbol(value: Any, market: str) -> str:
    """Normalize common retail quote prefixes without weakening the core symbol contract."""
    raw = str(value or "").strip().upper().replace(" ", "")
    if market == "CN-A":
        match = re.fullmatch(r"(SH|SZ|BJ)(\d{6})", raw)
        if match:
            return f"{match.group(2)}.{match.group(1)}"
    elif market == "HK":
        match = re.fullmatch(r"HK(\d{4,5})", raw)
        if match:
            return f"{match.group(1)}.HK"
    return raw


def _previous_weekday(value: date) -> date:
    """Return the prior Monday-Friday date; exchange holidays still need operator checking."""
    candidate = value - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def _outside_repo(path: str | Path, field: str, *, must_exist: bool = False) -> Path:
    raw = Path(path).expanduser()
    if must_exist and not raw.is_file():
        raise LocalInvestmentPilotError(f"{field}_MUST_BE_A_FILE")
    resolved = raw.resolve(strict=must_exist)
    try:
        resolved.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return resolved
    raise LocalInvestmentPilotError(f"{field}_MUST_BE_OUTSIDE_REPOSITORY")


def _private_dir(path: str | Path, field: str) -> Path:
    root = _outside_repo(path, field)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _write_local(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def _fingerprint_file(path: Path) -> dict[str, Any]:
    """Return SHA-256 and byte size for one regular output file."""
    digest = hashlib.sha256()
    byte_size = 0
    try:
        with path.open("rb") as stream:
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
                byte_size += len(block)
    except OSError as exc:
        raise LocalInvestmentPilotError(f"RUN_BUNDLE_FILE_UNREADABLE:{path.name}") from exc
    return {"sha256": digest.hexdigest(), "byte_size": byte_size}


def _verify_run_bundle(run_path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify a local pilot receipt's hashes against the exact input/analysis/report bytes."""
    try:
        run_dir = Path(run_path).expanduser().resolve(strict=True)
    except OSError as exc:
        raise LocalInvestmentPilotError("RUN_BUNDLE_DIRECTORY_NOT_FOUND") from exc
    if not run_dir.is_dir():
        raise LocalInvestmentPilotError("RUN_BUNDLE_DIRECTORY_REQUIRED")
    try:
        run_dir.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise LocalInvestmentPilotError("RUN_BUNDLE_MUST_BE_OUTSIDE_REPOSITORY")

    receipt_path = run_dir / "pilot_receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LocalInvestmentPilotError("RUN_RECEIPT_MISSING") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalInvestmentPilotError("RUN_RECEIPT_UNREADABLE") from exc
    if not isinstance(receipt, Mapping) or receipt.get("receipt_schema") != PILOT_RECEIPT_SCHEMA:
        raise LocalInvestmentPilotError("RUN_RECEIPT_SCHEMA_MISMATCH")
    if receipt.get("status") != PILOT_STATUS:
        raise LocalInvestmentPilotError("RUN_RECEIPT_NOT_PILOT_NON_CANONICAL")
    if str(receipt.get("pilot_id") or "") != run_dir.name:
        raise LocalInvestmentPilotError("RUN_RECEIPT_PILOT_ID_MISMATCH")
    for key, expected_name in (
        ("input_file", "input.json"),
        ("analysis_file", "analysis.json"),
        ("report_file", "report.md"),
    ):
        if receipt.get(key) != expected_name:
            raise LocalInvestmentPilotError(f"RUN_RECEIPT_FILENAME_MISMATCH:{key}")

    manifest = receipt.get("file_manifest")
    if not isinstance(manifest, Mapping):
        raise LocalInvestmentPilotError("RUN_BUNDLE_HASH_MANIFEST_MISSING")
    for filename in BUNDLE_FILENAMES:
        expected = manifest.get(filename)
        if not isinstance(expected, Mapping):
            raise LocalInvestmentPilotError(f"RUN_BUNDLE_HASH_MISSING:{filename}")
        expected_hash = str(expected.get("sha256") or "")
        expected_size = expected.get("byte_size")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or not isinstance(expected_size, int) or expected_size < 0:
            raise LocalInvestmentPilotError(f"RUN_BUNDLE_HASH_RECORD_INVALID:{filename}")
        actual = _fingerprint_file(run_dir / filename)
        if actual != {"sha256": expected_hash, "byte_size": expected_size}:
            raise LocalInvestmentPilotError(f"RUN_BUNDLE_HASH_MISMATCH:{filename}")
    return dict(receipt), {name: dict(manifest[name]) for name in BUNDLE_FILENAMES}


def verify_local_pilot_bundle(run_path: str | Path) -> dict[str, Any]:
    """Read-only check of a run's input, analysis and report against its receipt."""
    receipt, manifest = _verify_run_bundle(run_path)
    return {
        "status": "PILOT_BUNDLE_HASH_CHECK_PASS",
        "pilot_id": receipt["pilot_id"],
        "hash_algorithm": "SHA-256",
        "verified_files": [
            {"name": name, "byte_size": manifest[name]["byte_size"], "sha256": manifest[name]["sha256"]}
            for name in BUNDLE_FILENAMES
        ],
        "formal_decision_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }


def _replay_comparison(previous_analysis: Mapping[str, Any], recomputed_analysis: Mapping[str, Any]) -> dict[str, Any]:
    """Compare stable decision-material fields while ignoring the volatile run ID."""
    mismatched = []
    for field in REPLAY_COMPARISON_FIELDS:
        before = json.dumps(_safe(previous_analysis.get(field)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        after = json.dumps(_safe(recomputed_analysis.get(field)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if before != after:
            mismatched.append(field)
    return {
        "mode": "DECISION_MATERIAL_FIELDS_V1",
        "status": "MATCH" if not mismatched else "MISMATCH",
        "hash_verification": "PASS",
        "prior_pilot_id": previous_analysis.get("pilot_id"),
        "compared_fields": list(REPLAY_COMPARISON_FIELDS),
        "mismatched_fields": mismatched,
    }


def _status(value: Any, allowed: set[str]) -> str:
    item = str(value or "UNKNOWN").strip().upper()
    return item if item in allowed else "UNKNOWN"


def _items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _records(value: Any) -> list[Any]:
    """Preserve structured records in the machine-readable analysis while accepting plain text."""
    if not isinstance(value, list):
        return []
    result: list[Any] = []
    for item in value:
        if isinstance(item, Mapping):
            result.append(dict(item))
        elif str(item).strip():
            result.append(str(item).strip())
    return result


def _humanize_item(value: Any) -> str:
    """Render either a string or a structured assumption/risk record as readable Chinese prose."""
    if not isinstance(value, Mapping):
        return " ".join(str(value or "").splitlines()).strip() or "未提供"
    item = value
    identifier = str(item.get("assumption_id") or item.get("risk_id") or item.get("id") or "").strip()
    name = str(item.get("name") or item.get("title") or item.get("driver") or item.get("description") or "").strip()
    parts: list[str] = []
    prefix = "｜".join(part for part in (identifier, name) if part)
    if prefix:
        parts.append(prefix)
    values = item.get("values")
    if isinstance(values, Mapping) and values:
        parts.append("参数：" + "；".join(f"{key}={_humanize_item(val)}" for key, val in values.items()))
    elif item.get("value_cny_per_share") not in (None, ""):
        parts.append(f"每股金额：{item['value_cny_per_share']} CNY")
    for key, label in (
        ("severity", "严重程度"), ("likelihood", "发生可能性"), ("confidence", "置信度"),
        ("classification", "类别"), ("not_a_fact", "非事实声明"),
    ):
        if item.get(key) not in (None, ""):
            parts.append(f"{label}：{_humanize_item(item[key])}")
    for key, label in (
        ("summary", "摘要"), ("basis", "依据"), ("rationale", "理由"),
        ("description", "说明"), ("monitoring_trigger", "监控触发条件"),
    ):
        if item.get(key) not in (None, "") and not (key == "description" and name == str(item.get(key))):
            parts.append(f"{label}：{' '.join(str(item[key]).splitlines()).strip()}")
    refs = item.get("evidence_refs")
    if isinstance(refs, list) and refs:
        parts.append("证据引用：" + "、".join(str(ref) for ref in refs))
    if not parts:
        return "；".join(f"{key}={_humanize_item(val)}" for key, val in item.items())
    return "。".join(parts)


def _source_ref_markdown(value: Any) -> str:
    """Keep terminal punctuation outside a URL so Markdown does not absorb it into the link."""
    raw = str(value or "UNKNOWN").strip()
    if raw.lower().startswith(("https://", "http://")):
        return f"<{raw}>"
    return f"`{raw}`"


def _format_text_block(value: Any) -> list[str]:
    """Normalize embedded list markers/newlines in AI-authored multiline fields."""
    raw = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    groups: list[tuple[str, list[str]]] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            groups.append(("paragraph", [" ".join(paragraph)]))
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            groups.append(("list", list_items))
            list_items = []

    for raw_line in raw.split("\n"):
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list()
            continue
        match = re.match(r"^(?:[-*+]\s+|\d+\s*[.)]\s+)(.+)$", line)
        if match:
            flush_paragraph()
            list_items.append(match.group(1).strip())
        else:
            flush_list()
            paragraph.append(line)
    flush_paragraph()
    flush_list()

    rendered: list[str] = []
    for kind, contents in groups:
        if rendered:
            rendered.append("")
        if kind == "list":
            rendered.extend(f"- {line}" for line in contents)
        else:
            rendered.append(contents[0])
    return rendered or ["未提供"]


def _resolve_cutoff_timestamp(case_raw: Mapping[str, Any], cutoff: date) -> tuple[datetime, str | None]:
    """Keep legacy date-only semantics unless an explicit, same-date timezone-aware instant is supplied."""
    cutoff_start = datetime.combine(cutoff, time.min, tzinfo=SHANGHAI)
    raw = str(case_raw.get("as_of_timestamp") or "").strip()
    if not raw:
        return cutoff_start, None
    instant = _datetime(raw, "AS_OF_TIMESTAMP", allow_date_only=False)
    if instant.date() != cutoff:
        raise LocalInvestmentPilotError("AS_OF_TIMESTAMP_DATE_MUST_MATCH_AS_OF_DATE")
    return instant, instant.isoformat()


def _validate_guided_observation_date(
    observation: date, cutoff: date, *, cutoff_timestamp: datetime | None = None
) -> date:
    """Require a weekday observation date and preserve strict point-in-time cutoff semantics."""
    if observation.weekday() >= 5:
        raise LocalInvestmentPilotError(
            "PRICE_OBSERVATION_MUST_BE_TRADING_WEEKDAY: 输入日期是周六或周日；"
            "A 股/港股常规收盘价应填写实际交易日日期。程序不会把周末日期自动改成周五。"
        )
    if cutoff_timestamp is None:
        if observation >= cutoff:
            raise LocalInvestmentPilotError(
                "PRICE_OBSERVATION_MUST_PRECEDE_DATE_ONLY_CUTOFF: "
                "日期级截止按截止日 00:00（+08:00）处理；同日行情请在向导选择“2 = 截止日收盘后”。"
            )
        return observation
    if observation > cutoff:
        raise LocalInvestmentPilotError("PRICE_OBSERVATION_AFTER_TIMESTAMP_CUTOFF")
    return observation


def _latest_weekday_on_or_before(value: date) -> date:
    """Return a weekday no later than value; exchange holiday calendars are not checked."""
    candidate = value
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def _guided_cutoff_timestamp(
    cutoff: date, mode: str, custom_timestamp: str = ""
) -> tuple[datetime, str | None]:
    """Offer safe, labeled cutoff choices; common users never need to type timezone syntax."""
    if mode == "1":
        return _resolve_cutoff_timestamp({}, cutoff)
    if mode == "2":
        raw = f"{cutoff.isoformat()}T15:30:00+08:00"
        return _resolve_cutoff_timestamp({"as_of_timestamp": raw}, cutoff)
    if mode == "3":
        if not str(custom_timestamp or "").strip():
            raise LocalInvestmentPilotError("CUSTOM_AS_OF_TIMESTAMP_REQUIRED")
        return _resolve_cutoff_timestamp({"as_of_timestamp": custom_timestamp}, cutoff)
    raise LocalInvestmentPilotError("CUTOFF_MODE_MUST_BE_1_2_OR_3")



def _collect_refs(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"evidence_refs", "source_refs", "evidence_ids", "source_ids"} and isinstance(item, list):
                result.update(str(row).strip() for row in item if str(row).strip())
            else:
                result.update(_collect_refs(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_collect_refs(item))
    return result



def _find_note_price_conflicts(notes: Any, structured_price: Decimal) -> list[str]:
    """Flag explicitly labelled price claims in free text that differ from price_input.price."""
    text = str(notes or "")
    pattern = re.compile(
        r"(?:当前价(?:格)?|现价|股价|收盘价|手动提供(?:的)?(?:价格|股价)?|"
        r"人工输入(?:的)?(?:价格|股价)?|报价)\s*(?:(?:为|是|[:：=])\s*)?(\d+(?:\.\d+)?)"
    )
    conflicts: list[str] = []
    for match in pattern.finditer(text):
        try:
            quoted = Decimal(match.group(1))
        except InvalidOperation:
            continue
        if quoted.is_finite() and quoted != structured_price:
            rendered = format(quoted, "f")
            if rendered not in conflicts:
                conflicts.append(rendered)
    return conflicts


def _prepare_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != PILOT_SCHEMA:
        raise LocalInvestmentPilotError("PILOT_INPUT_SCHEMA_MISMATCH")
    case_raw = payload.get("case")
    price_raw = payload.get("price_input")
    if not isinstance(case_raw, Mapping) or not isinstance(price_raw, Mapping):
        raise LocalInvestmentPilotError("CASE_AND_PRICE_INPUT_REQUIRED")
    company = str(case_raw.get("company") or "").strip()
    if not company:
        raise LocalInvestmentPilotError("COMPANY_REQUIRED")
    market = str(case_raw.get("market") or "CN-A")
    symbol = str(case_raw.get("symbol") or "").strip()
    cutoff = _date(case_raw.get("as_of_date"), "AS_OF_DATE")
    cutoff_instant, cutoff_timestamp = _resolve_cutoff_timestamp(case_raw, cutoff)
    position_raw = str(case_raw.get("current_position_pct", "0"))
    case = build_research_case(symbol, cutoff.isoformat(), position_raw, market=market)
    position = str(case["request"]["current_position_pct"])
    normalized_market = case["request"]["market"]
    currency = str(case_raw.get("currency") or ("CNY" if normalized_market == "CN-A" else "HKD")).upper()
    if currency != ("CNY" if normalized_market == "CN-A" else "HKD"):
        raise LocalInvestmentPilotError("CURRENCY_DOES_NOT_MATCH_MARKET")

    price = _positive(price_raw.get("price"), "CURRENT_PRICE")
    observation = _date(price_raw.get("observation_date"), "PRICE_OBSERVATION_DATE")
    if observation.weekday() >= 5:
        raise LocalInvestmentPilotError(
            "PRICE_OBSERVATION_MUST_BE_TRADING_WEEKDAY: 输入日期是周六或周日；"
            "A 股/港股常规收盘价应填写实际交易日日期。"
        )
    known_at = _datetime(price_raw.get("known_at"), "PRICE_KNOWN_AT", allow_date_only=False)
    price_issues: list[str] = []
    if known_at.date() != observation:
        price_issues.append("PRICE_KNOWN_AT_DATE_MISMATCH")
    if observation > cutoff:
        price_issues.append("PRICE_OBSERVATION_AFTER_CUTOFF")
    if known_at > cutoff_instant:
        price_issues.append(
            "PRICE_KNOWN_AFTER_EXPLICIT_TIMESTAMP_CUTOFF"
            if cutoff_timestamp else "PRICE_KNOWN_AFTER_DATE_ONLY_CUTOFF"
        )
    if str(price_raw.get("assurance_label") or "") != PRICE_ASSURANCE:
        raise LocalInvestmentPilotError("PRICE_MUST_REMAIN_OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED")
    claims = _items(price_raw.get("sources_claimed"))
    if not claims:
        raise LocalInvestmentPilotError("PRICE_SOURCE_CLAIM_REQUIRED")

    sources: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for row in payload.get("evidence_register") or []:
        if not isinstance(row, Mapping):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if not source_id or source_id in source_ids:
            continue
        source_ids.add(source_id)
        known_text = str(row.get("known_at") or "").strip()
        source_time_status = "UNKNOWN"
        if known_text:
            try:
                if len(known_text) == 10:
                    # A calendar date on the cutoff day does not establish whether the
                    # source was known before the cutoff instant. Never infer midnight.
                    known_date = _date(known_text, f"{source_id}_KNOWN_AT")
                    if known_date < cutoff:
                        source_time_status = "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
                    elif known_date > cutoff:
                        source_time_status = "AFTER_CUTOFF"
                    else:
                        source_time_status = "KNOWN_AT_PRECISION_INSUFFICIENT"
                else:
                    source_time = _datetime(known_text, f"{source_id}_KNOWN_AT")
                    source_time_status = (
                        "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
                        if source_time <= cutoff_instant else "AFTER_CUTOFF"
                    )
            except LocalInvestmentPilotError:
                source_time_status = "KNOWN_AT_INVALID"
        sources.append({
            "source_id": source_id,
            "title": str(row.get("title") or "未提供标题"),
            "source_class": str(row.get("source_class") or "UNKNOWN"),
            "source_ref": str(row.get("source_ref") or "UNKNOWN"),
            "known_at": known_text or None,
            "time_status": source_time_status,
            "summary": str(row.get("summary") or "未提供事实摘要"),
            "raw_sha256_claimed": row.get("raw_sha256_claimed"),
            "formal_evidence_pit_admission": False,
        })

    raw_assessment = payload.get("assessment") if isinstance(payload.get("assessment"), Mapping) else {}
    allowed_assessment = {
        "trust": {"PASS", "REVALIDATION", "FAIL", "UNKNOWN"},
        "reality": {"PASS", "CONDITIONAL", "BLOCKED", "UNKNOWN"},
        "quality": {"PASS", "CONDITIONAL", "BLOCKED", "UNKNOWN"},
        "thesis": {"INTACT", "WATCH", "BROKEN", "UNKNOWN"},
        "market_implied_expectation": {"PASS", "NOT_IDENTIFIABLE", "OUTSIDE_HISTORICAL_SUPPORT", "UNKNOWN", "BLOCKED", "AMBIGUOUS", "INCOMPATIBLE"},
        "expectation_gap": {"PASS", "UNKNOWN", "BLOCKED", "AMBIGUOUS", "INCOMPATIBLE"},
        "risk": {"PASS", "FAIL", "UNKNOWN"},
    }
    assessment: dict[str, Any] = {}
    for name, states in allowed_assessment.items():
        raw = raw_assessment.get(name) if isinstance(raw_assessment.get(name), Mapping) else {}
        assessment[name] = dict(raw)
        assessment[name]["status"] = _status(raw.get("status"), states)
        assessment[name]["summary"] = str(raw.get("summary") or "")
    assessment["expectation_gap"]["direction"] = _status(
        assessment["expectation_gap"].get("direction"),
        {"POSITIVE", "NEUTRAL", "NEGATIVE", "UNKNOWN"},
    )
    assessment["thesis"]["break_conditions"] = _items(assessment["thesis"].get("break_conditions"))
    assessment["thesis"]["reassessment_triggers"] = _items(assessment["thesis"].get("reassessment_triggers"))
    assessment["risk"]["items"] = _records(assessment["risk"].get("items"))
    value_drivers = raw_assessment.get("value_drivers") or []
    assessment["value_drivers"] = [
        {
            "rank": int(item.get("rank", index)),
            "driver": str(item.get("driver") or "未命名价值驱动因素"),
            "impact": _status(item.get("impact"), {"POSITIVE", "NEGATIVE", "MIXED", "UNKNOWN"}),
            "rationale": str(item.get("rationale") or ""),
            "evidence_refs": _items(item.get("evidence_refs")),
        }
        for index, item in enumerate(value_drivers, start=1) if isinstance(item, Mapping)
    ]
    assessment["thesis"]["core_statement"] = str(assessment["thesis"].get("core_statement") or "")
    assessment["thesis"]["drivers"] = assessment["thesis"].get("drivers") if isinstance(assessment["thesis"].get("drivers"), list) else []

    forecast_raw = payload.get("forecast_valuation") if isinstance(payload.get("forecast_valuation"), Mapping) else {}
    raw_driver_forecast = payload.get("operating_driver_forecast")
    raw_valuation_transmission = payload.get("valuation_transmission")
    raw_operator_valuation_context = payload.get("operator_valuation_context")
    stress_raw = forecast_raw.get("thesis_break_stress")
    stress_raw = stress_raw if isinstance(stress_raw, Mapping) else {}
    forecast = {
        "model": str(forecast_raw.get("model") or "UNKNOWN"),
        "model_rationale": str(forecast_raw.get("model_rationale") or ""),
        "entry_value_reference_per_share": forecast_raw.get("entry_value_reference_per_share"),
        "probabilities_calibrated": forecast_raw.get("probabilities_calibrated") is True,
        "assumptions": _records(forecast_raw.get("assumptions")),
        "scenarios": forecast_raw.get("scenarios") if isinstance(forecast_raw.get("scenarios"), Mapping) else {},
        "thesis_break_stress": {
            "failure_trigger": str(stress_raw.get("failure_trigger") or ""),
            "operating_impact": str(stress_raw.get("operating_impact") or ""),
            "valuation_method": str(stress_raw.get("valuation_method") or ""),
            "terminal_value_per_share": stress_raw.get("terminal_value_per_share"),
            "cash_distributions_per_share": str(stress_raw.get("cash_distributions_per_share", "0")),
            "rationale": str(stress_raw.get("rationale") or ""),
            "evidence_refs": _items(stress_raw.get("evidence_refs")),
        },
    }
    parameters_raw = payload.get("decision_parameters") if isinstance(payload.get("decision_parameters"), Mapping) else {}
    try:
        horizon = int(parameters_raw.get("horizon_years", 1))
    except (TypeError, ValueError):
        horizon = 1
    if horizon not in (1, 2, 3):
        horizon = 1
    override = parameters_raw.get("horizon_override", False)
    override_basis = parameters_raw.get("horizon_override_basis") if isinstance(parameters_raw.get("horizon_override_basis"), list) else []
    rationale = str(parameters_raw.get("horizon_selection_rationale") or "默认以 1 年作为年化回报参考期限。")
    if horizon == 3:
        allowed_basis = {"MAJOR_INDUSTRY_LEADER", "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX"}
        if override is not True or not override_basis or any(item not in allowed_basis for item in override_basis):
            horizon = 1
            override = False
            override_basis = []
            rationale += " 3 年覆盖条件不足，已退回默认 1 年。"
    elif override is not False or override_basis:
        override = False
        override_basis = []
        rationale += " 期限覆盖未通过条件检查，已使用默认期限规则。"
    try:
        required_return = max(
            FUNDAMENTAL_TARGET_ANNUALIZED_RETURN,
            _number(parameters_raw.get("required_return_annualized", "0.15"), "REQUIRED_RETURN"),
        )
    except LocalInvestmentPilotError:
        required_return = FUNDAMENTAL_TARGET_ANNUALIZED_RETURN
    try:
        max_loss = _number(parameters_raw.get("max_loss_pct", "25"), "MAX_LOSS_PCT")
        if max_loss < 0 or max_loss >= 100:
            max_loss = Decimal("25")
    except LocalInvestmentPilotError:
        max_loss = Decimal("25")

    # Resolve every structured evidence reference from assessment and valuation inputs,
    # before any structured risk/assumption objects are rendered for human readers.
    references = _collect_refs({
        "assessment": raw_assessment,
        "forecast_valuation": forecast_raw,
        "operating_driver_forecast": raw_driver_forecast,
        "valuation_transmission": raw_valuation_transmission,
    })
    unknown_refs = sorted(references - source_ids)
    after_cutoff_refs = [
        source["source_id"] for source in sources
        if source["source_id"] in references and source["time_status"] == "AFTER_CUTOFF"
    ]
    uncertain_timing_refs = [
        source["source_id"] for source in sources
        if source["source_id"] in references
        and source["time_status"] in {"UNKNOWN", "KNOWN_AT_INVALID", "KNOWN_AT_PRECISION_INSUFFICIENT"}
    ]
    operating_driver_forecast = evaluate_operating_driver_forecast(
        raw_driver_forecast,
        evidence_register=sources,
        unresolved_evidence_ids=unknown_refs,
        after_cutoff_evidence_ids=after_cutoff_refs,
        uncertain_timing_evidence_ids=uncertain_timing_refs,
    )
    allowed_model_families = {"EPS_MULTIPLE", "FCF_DCF", "DDM", "SOTP", "RNPV", "OTHER", "UNKNOWN"}
    operator_context_raw = raw_operator_valuation_context if isinstance(raw_operator_valuation_context, Mapping) else {}
    selected_model_family = str(operator_context_raw.get("selected_model_family") or "UNKNOWN").strip().upper()
    if selected_model_family not in allowed_model_families:
        selected_model_family = "UNKNOWN"
    baseline_includes_raw = operator_context_raw.get("baseline_includes_project")
    baseline_includes_project = baseline_includes_raw if isinstance(baseline_includes_raw, bool) else None
    operator_valuation_context = {
        "selected_model_family": selected_model_family,
        "baseline_includes_project": baseline_includes_project,
        "input_owner": "OPERATOR",
    }
    valuation_transmission = evaluate_valuation_transmission(
        raw_valuation_transmission,
        operating_driver_forecast=operating_driver_forecast,
        forecast_valuation=forecast,
        operator_context=operator_valuation_context,
        evidence_register=sources,
        unresolved_evidence_ids=unknown_refs,
        after_cutoff_evidence_ids=after_cutoff_refs,
        uncertain_timing_evidence_ids=uncertain_timing_refs,
    )
    if valuation_transmission.get("applied_to_per_share_scenarios") is True:
        original_scenarios = forecast.get("scenarios") if isinstance(forecast.get("scenarios"), Mapping) else {}
        adjusted_scenarios = {
            key: dict(value) if isinstance(value, Mapping) else value
            for key, value in original_scenarios.items()
        }
        for scenario_name in SCENARIOS:
            scenario_row = adjusted_scenarios.get(scenario_name)
            bridge_row = valuation_transmission.get("scenarios", {}).get(scenario_name, {})
            if isinstance(scenario_row, dict) and isinstance(bridge_row, Mapping):
                scenario_row["b5_baseline_terminal_value_per_share"] = scenario_row.get("terminal_value_per_share")
                scenario_row["terminal_value_per_share"] = bridge_row.get("adjusted_terminal_value_per_share")
                scenario_row["b5_transmission_applied"] = True
        forecast["scenarios"] = adjusted_scenarios
        forecast["b5_baseline_entry_value_reference_per_share"] = forecast.get("entry_value_reference_per_share")
        forecast["entry_value_reference_per_share"] = valuation_transmission.get("entry_value_reference_adjusted_per_share")
    return {
        "case": {
            "case_id": case["case_id"], "company": company, "market": normalized_market,
            "symbol": case["request"]["symbol"], "currency": currency, "as_of_date": cutoff.isoformat(),
            "as_of_timestamp": cutoff_timestamp,
            "cutoff_semantics": "EXPLICIT_TIMESTAMP" if cutoff_timestamp else "DATE_ONLY_START_OF_DAY",
            "current_position_pct": position, "venue_hint": case["security_identity"]["venue_hint"],
            "venue_hint_is_evidence": False,
        },
        "price_input": {
            "price": format(price, "f"), "currency": currency, "observation_date": observation.isoformat(),
            "known_at": known_at.isoformat(), "assurance_label": PRICE_ASSURANCE, "sources_claimed": claims,
            "pit_time_status": "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY" if not price_issues else "PRICE_NOT_PIT_QUALIFIED",
            "pit_issues": price_issues, "source_origin_verified": False, "source_use_rights_verified": False,
            "canonical_price_admission": False,
        },
        "evidence_register": sources,
        "assessment": assessment,
        "forecast_valuation": forecast,
        "operating_driver_forecast": operating_driver_forecast,
        "valuation_transmission": valuation_transmission,
        "operator_valuation_context": operator_valuation_context,
        "decision_parameters": {
            "horizon_years": horizon, "horizon_override": override, "horizon_override_basis": override_basis,
            "horizon_selection_rationale": rationale, "required_return_annualized": format(required_return, "f"),
            "fundamental_target_annualized_return": format(FUNDAMENTAL_TARGET_ANNUALIZED_RETURN, "f"),
            "entry_return_cushion_threshold": format(BUY_ENTRY_RETURN_CUSHION_THRESHOLD, "f"),
            "max_loss_pct": format(max_loss, "f"),
        },
        "referenced_evidence_ids": sorted(references),
        "unresolved_evidence_references": unknown_refs,
        "after_cutoff_evidence_references": after_cutoff_refs,
        "uncertain_timing_evidence_references": uncertain_timing_refs,
        "notes_price_conflicts": _find_note_price_conflicts(payload.get("notes"), price),
        "notes": str(payload.get("notes") or ""),
        "operator_portfolio_context": (
            dict(payload["operator_portfolio_context"])
            if isinstance(payload.get("operator_portfolio_context"), Mapping)
            else None
        ),
    }


def _return_metrics(prepared: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if prepared["price_input"]["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        return None, "PRICE_NOT_PIT_QUALIFIED"
    forecast = prepared["forecast_valuation"]
    anchor = forecast.get("entry_value_reference_per_share")
    scenarios = forecast.get("scenarios") or {}
    if anchor in (None, "") or not isinstance(scenarios, Mapping) or set(scenarios) != set(SCENARIOS):
        return None, "ENTRY_REFERENCE_OR_BEAR_BASE_BULL_SCENARIOS_MISSING"
    rows: dict[str, Any] = {}
    for name in SCENARIOS:
        row = scenarios.get(name)
        if not isinstance(row, Mapping):
            return None, f"{name.upper()}_SCENARIO_MISSING"
        if row.get("probability") in (None, "") or row.get("terminal_value_per_share") in (None, "") or not str(row.get("rationale") or "").strip():
            return None, f"{name.upper()}_SCENARIO_INPUTS_INCOMPLETE"
        rows[name] = {
            "probability": str(row["probability"]),
            "terminal_value_per_share": str(row["terminal_value_per_share"]),
            "cash_distributions_per_share": str(row.get("cash_distributions_per_share", "0")),
            "probability_rationale": str(row["rationale"]),
        }
    try:
        scenario_wealth = {
            name: _number(rows[name]["terminal_value_per_share"], f"SCENARIO_{name}_TERMINAL")
            + _number(rows[name]["cash_distributions_per_share"], f"SCENARIO_{name}_DISTRIBUTIONS")
            for name in SCENARIOS
        }
    except LocalInvestmentPilotError as exc:
        return None, f"SCENARIO_CALCULATION_INCOMPLETE:{exc}"
    if not (
        scenario_wealth["bear"] <= scenario_wealth["base"] <= scenario_wealth["bull"]
    ):
        return None, "SCENARIO_WEALTH_ORDERING_INCONSISTENT"

    params = prepared["decision_parameters"]
    gate = {
        "entry_price": prepared["price_input"]["price"],
        "entry_value_reference": str(anchor),
        "horizon_years": str(params["horizon_years"]),
        "horizon_override": params["horizon_override"],
        "horizon_override_basis": params["horizon_override_basis"],
        "horizon_selection_rationale": params["horizon_selection_rationale"],
        "buy_entry_return_cushion_threshold": params["entry_return_cushion_threshold"],
        "fundamental_target_annualized_return": params["fundamental_target_annualized_return"],
        "required_return_annualized": params["required_return_annualized"],
        "lineage_version": "PILOT_NON_CANONICAL_MODEL_INPUTS",
        "canonical_forecast_ref": {"status": "PILOT_NON_CANONICAL"},
        "canonical_valuation_ref": {"status": "PILOT_NON_CANONICAL"},
        "scenarios": rows,
    }
    try:
        result = calculate_return_metrics(gate, max_loss_pct=params["max_loss_pct"])
        return _safe(result), None
    except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
        return None, f"SCENARIO_CALCULATION_INCOMPLETE:{exc}"


def _price_zone_sensitivity(
    prepared: Mapping[str, Any],
    return_metrics: Mapping[str, Any] | None,
    return_metrics_reason: str | None,
) -> dict[str, Any]:
    """Explain existing price caps and recompute 90/100/110% prices with the existing solver."""
    currency = str((prepared.get("case") or {}).get("currency") or "UNKNOWN")
    current_raw = (prepared.get("price_input") or {}).get("price")
    try:
        current = _positive(current_raw, "B6_CURRENT_PRICE")
    except LocalInvestmentPilotError:
        current = None

    if return_metrics is None or current is None:
        reason = return_metrics_reason or ("CURRENT_PRICE_INVALID" if current is None else "RETURN_METRICS_UNKNOWN")
        return {
            "schema_version": "IIOS-PRICE-ZONE-SENSITIVITY-0.1",
            "status": "UNKNOWN",
            "price_screen_only": True,
            "decision_action_changed": False,
            "currency": currency,
            "current_price": format(current, "f") if current is not None else None,
            "target_entry_price": None,
            "entry_value_reference_per_share": None,
            "binding_constraint": {"code": "UNKNOWN", "label": "未知", "price_cap": None, "tied_constraints": []},
            "current_price_zone": "UNKNOWN",
            "current_price_vs_reference": "UNKNOWN",
            "price_caps": [],
            "sensitivity_ladder": [
                {
                    "multiplier": multiplier, "price": None, "status": "UNKNOWN",
                    "expected_annualized_return": None, "entry_return_cushion": None, "bear_return": None,
                    "buy_entry_return_cushion_pass": None, "fundamental_target_pass": None,
                    "required_return_pass": None, "risk_pass": None, "return_gate_pass": None,
                    "target_entry_price_for_entry_cushion": None, "target_entry_price_for_return": None,
                    "target_entry_price_for_required_return": None, "target_entry_price_for_risk": None,
                    "issues": [reason],
                }
                for multiplier in ("0.90", "1.00", "1.10")
            ],
            "issues": [reason],
            "interpretation": "价格层未能完成计算；UNKNOWN 不表示价格合理或可买。",
        }

    anchor_raw = (prepared.get("forecast_valuation") or {}).get("entry_value_reference_per_share")
    try:
        anchor = _positive(anchor_raw, "B6_ENTRY_VALUE_REFERENCE")
    except LocalInvestmentPilotError:
        anchor = None

    cap_specs = (
        ("entry_cushion_15pct", "15% 入场回报安全垫", return_metrics.get("target_entry_price_for_entry_cushion")),
        ("annualized_return_15pct", "预期年化回报 ≥ 15%", return_metrics.get("target_entry_price_for_return")),
        ("required_return", "预期年化回报 ≥ Required Return", return_metrics.get("target_entry_price_for_required_return")),
        ("bear_loss_risk", "Bear 损失不超过风险上限", return_metrics.get("target_entry_price_for_risk")),
    )
    caps: list[dict[str, Any]] = []
    for code, label, raw_value in cap_specs:
        try:
            value = _number(raw_value, f"B6_{code}") if raw_value is not None else None
        except LocalInvestmentPilotError:
            value = None
        caps.append({"code": code, "label": label, "price_cap": format(value, "f") if value is not None else None})
    usable_caps = [row for row in caps if row["price_cap"] is not None]
    if not usable_caps:
        binding = {"code": "UNKNOWN", "label": "未知", "price_cap": None, "tied_constraints": []}
        target_cap = None
        status = "PARTIAL"
        issues = ["NO_VALID_PRICE_CAPS"]
    else:
        target_cap = min(Decimal(row["price_cap"]) for row in usable_caps)
        tied = [row for row in usable_caps if Decimal(row["price_cap"]) == target_cap]
        binding = {
            "code": tied[0]["code"] if len(tied) == 1 else "TIED_CONSTRAINTS",
            "label": "；".join(row["label"] for row in tied),
            "price_cap": format(target_cap, "f"),
            "tied_constraints": [row["code"] for row in tied],
        }
        status = "CALCULATED"
        issues = []

    if target_cap is None:
        current_zone = "UNKNOWN"
    elif current <= target_cap:
        current_zone = "AT_OR_BELOW_ALL_GATES_ENTRY_PRICE"
    elif anchor is not None and current <= anchor:
        current_zone = "ABOVE_ENTRY_CAP_BUT_AT_OR_BELOW_REFERENCE_VALUE"
    elif anchor is not None and current > anchor:
        current_zone = "ABOVE_REFERENCE_VALUE"
    else:
        current_zone = "ABOVE_ENTRY_CAP_REFERENCE_UNKNOWN"
    if anchor is None:
        current_vs_reference = "UNKNOWN"
    elif current <= anchor:
        current_vs_reference = "AT_OR_BELOW_REFERENCE_VALUE"
    else:
        current_vs_reference = "ABOVE_REFERENCE_VALUE"

    prepared_price = prepared.get("price_input") if isinstance(prepared.get("price_input"), Mapping) else {}
    sensitivity: list[dict[str, Any]] = []
    for multiplier in ("0.90", "1.00", "1.10"):
        p = current * Decimal(multiplier)
        variant = dict(prepared)
        variant_price = dict(prepared_price)
        variant_price["price"] = format(p, "f")
        variant["price_input"] = variant_price
        metrics, reason = _return_metrics(variant)
        if metrics is None:
            sensitivity.append({
                "multiplier": multiplier, "price": format(p, "f"), "status": "UNKNOWN",
                "expected_annualized_return": None, "entry_return_cushion": None, "bear_return": None,
                "buy_entry_return_cushion_pass": None, "fundamental_target_pass": None,
                "required_return_pass": None, "risk_pass": None, "return_gate_pass": None,
                "target_entry_price_for_entry_cushion": None, "target_entry_price_for_return": None,
                "target_entry_price_for_required_return": None, "target_entry_price_for_risk": None,
                "issues": [reason or "SENSITIVITY_RETURN_CALCULATION_UNKNOWN"],
            })
        else:
            sensitivity.append({
                "multiplier": multiplier, "price": format(p, "f"), "status": "CALCULATED",
                "expected_annualized_return": metrics.get("expected_annualized_return"),
                "entry_return_cushion": metrics.get("entry_return_cushion"),
                "bear_return": metrics.get("bear_return"),
                "buy_entry_return_cushion_pass": metrics.get("buy_entry_return_cushion_pass"),
                "fundamental_target_pass": metrics.get("fundamental_target_pass"),
                "required_return_pass": metrics.get("required_return_pass"),
                "risk_pass": metrics.get("risk_pass"), "return_gate_pass": metrics.get("return_gate_pass"),
                "target_entry_price_for_entry_cushion": metrics.get("target_entry_price_for_entry_cushion"),
                "target_entry_price_for_return": metrics.get("target_entry_price_for_return"),
                "target_entry_price_for_required_return": metrics.get("target_entry_price_for_required_return"),
                "target_entry_price_for_risk": metrics.get("target_entry_price_for_risk"),
                "issues": [],
            })
    midpoint = next((row for row in sensitivity if row["multiplier"] == "1.00"), None)
    if midpoint and midpoint.get("status") == "CALCULATED":
        for key in ("expected_annualized_return", "entry_return_cushion", "bear_return"):
            if Decimal(str(midpoint[key])) != Decimal(str(return_metrics[key])):
                issues.append(f"CURRENT_PRICE_SENSITIVITY_MISMATCH:{key}")
                status = "REVIEW_REQUIRED"
                break

    return {
        "schema_version": "IIOS-PRICE-ZONE-SENSITIVITY-0.1",
        "status": status, "price_screen_only": True, "decision_action_changed": False,
        "currency": currency, "current_price": format(current, "f"),
        "target_entry_price": format(target_cap, "f") if target_cap is not None else None,
        "entry_value_reference_per_share": format(anchor, "f") if anchor is not None else None,
        "binding_constraint": binding, "current_price_zone": current_zone,
        "current_price_vs_reference": current_vs_reference, "price_caps": caps,
        "sensitivity_ladder": sensitivity, "issues": issues,
        "interpretation": "本节仅解释价格层约束，不构成 BUY/ADD/HOLD 指令，也不覆盖 Trust、Thesis、MIE/预期差、组合限制或其他既有决策门槛。",
    }


def _render_price_zone_sensitivity_section(result: Mapping[str, Any]) -> list[str]:
    """Render B6 price-zone and three-point sensitivity in Chinese."""
    row = result if isinstance(result, Mapping) else {}
    lines = [
        "", "### B6：当前价格区间与约束敏感性（仅价格层，不是买入指令）", "",
        f"- 计算状态：**{row.get('status', 'UNKNOWN')}**",
        f"- 当前价：{row.get('current_price') or 'UNKNOWN'} {row.get('currency', '')}",
        f"- 共同约束下目标入场价上限：{row.get('target_entry_price') or 'UNKNOWN'} {row.get('currency', '')}",
        f"- 当前价格区间：{row.get('current_price_zone', 'UNKNOWN')}",
        f"- 相对安全边际参考价值：{row.get('current_price_vs_reference', 'UNKNOWN')}；参考价值 {row.get('entry_value_reference_per_share') or 'UNKNOWN'} {row.get('currency', '')}",
        f"- 当前起作用的最低入场价约束：{(row.get('binding_constraint') or {}).get('label', 'UNKNOWN')}；对应上限 {(row.get('binding_constraint') or {}).get('price_cap') or 'UNKNOWN'} {row.get('currency', '')}",
        "", "#### 各价格约束上限",
    ]
    caps = row.get("price_caps") if isinstance(row.get("price_caps"), list) else []
    if caps:
        for item in caps:
            lines.append(f"- {item.get('label', item.get('code', 'UNKNOWN'))}：{item.get('price_cap') or 'UNKNOWN'} {row.get('currency', '')}")
    else:
        lines.append("- 无可用价格约束上限；回报或估值数据不足。")
    lines.extend(["", "#### 当前价的 90% / 100% / 110% 情景"])
    ladder = row.get("sensitivity_ladder") if isinstance(row.get("sensitivity_ladder"), list) else []
    for item in ladder:
        label = f"{Decimal(item['multiplier']) * 100:.0f}%"
        if item.get("status") != "PASS":
            lines.append(f"- {label} 当前价 = {item.get('price') or 'UNKNOWN'}：UNKNOWN（{'; '.join(item.get('issues') or [])}）")
            continue
        lines.extend([
            f"- {label} 当前价 = {item.get('price')} {row.get('currency', '')}",
            f"  预期年化回报 {item.get('expected_annualized_return')}；入场回报安全垫 {item.get('entry_return_cushion')}；Bear 回报 {item.get('bear_return')}",
            "  价格门槛："
            + f"安全垫≥15% {item.get('buy_entry_return_cushion_pass')}；"
            + f"年化回报≥15% {item.get('fundamental_target_pass')}；"
            + f"Required Return {item.get('required_return_pass')}；Bear 风险上限 {item.get('risk_pass')}；"
            + f"全部价格门槛 {item.get('return_gate_pass')}",
            "  对应价格上限："
            + f"安全垫 {item.get('target_entry_price_for_entry_cushion') or 'UNKNOWN'}；"
            + f"年化回报15% {item.get('target_entry_price_for_return') or 'UNKNOWN'}；"
            + f"Required Return {item.get('target_entry_price_for_required_return') or 'UNKNOWN'}；"
            + f"Bear 风险 {item.get('target_entry_price_for_risk') or 'UNKNOWN'}",
        ])
    lines.extend([
        "", "- 解释边界：以上仅说明价格本身是否满足现有回报/风险上限。即使全部价格门槛通过，Trust、Thesis、MIE/预期差、正式证据和组合约束等任一既有条件未知/阻塞时，不能据此升级投资行动.", "",
    ])
    if row.get("issues"):
        lines.extend(["#### B6 待复核问题", ""])
        lines.extend(f"- {issue}" for issue in row["issues"])
    return lines




def _thesis_break_stress_review(prepared: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an independent, non-probability-weighted thesis-break stress case."""
    forecast = prepared["forecast_valuation"]
    stress = forecast.get("thesis_break_stress")
    if not isinstance(stress, Mapping) or not any(
        stress.get(field) not in (None, "", [])
        for field in (
            "failure_trigger", "operating_impact", "valuation_method",
            "terminal_value_per_share", "rationale", "evidence_refs",
        )
    ):
        return {
            "status": "MISSING",
            "issues": ["THESIS_BREAK_STRESS_MISSING"],
            "stress_terminal_wealth": None,
            "stress_total_return": None,
            "stress_downside_pct": None,
            "probability_weighted": False,
        }

    issues: list[str] = []
    bear = (forecast.get("scenarios") or {}).get("bear")
    required_bear_fields = ("failure_trigger", "operating_impact", "valuation_mechanism")
    if not isinstance(bear, Mapping) or any(
        not str(bear.get(field) or "").strip() for field in required_bear_fields
    ):
        issues.append("BEAR_FAILURE_PATH_INCOMPLETE")

    required_stress_fields = ("failure_trigger", "operating_impact", "valuation_method", "rationale")
    if any(not str(stress.get(field) or "").strip() for field in required_stress_fields):
        issues.append("THESIS_BREAK_STRESS_INPUTS_INCOMPLETE")

    stress_wealth: Decimal | None = None
    try:
        terminal_raw = stress.get("terminal_value_per_share")
        if terminal_raw in (None, ""):
            raise LocalInvestmentPilotError("STRESS_TERMINAL_VALUE_MISSING")
        terminal = _number(terminal_raw, "THESIS_BREAK_STRESS_TERMINAL")
        distributions = _number(
            stress.get("cash_distributions_per_share", "0"),
            "THESIS_BREAK_STRESS_DISTRIBUTIONS",
        )
        if terminal < 0 or distributions < 0:
            raise LocalInvestmentPilotError("THESIS_BREAK_STRESS_VALUES_MUST_BE_NONNEGATIVE")
        stress_wealth = terminal + distributions
    except LocalInvestmentPilotError:
        issues.append("THESIS_BREAK_STRESS_VALUE_INVALID")

    bear_wealth: Decimal | None = None
    if stress_wealth is not None:
        try:
            if not isinstance(bear, Mapping):
                raise LocalInvestmentPilotError("BEAR_SCENARIO_MISSING")
            bear_terminal = _number(bear.get("terminal_value_per_share"), "BEAR_TERMINAL")
            bear_distributions = _number(
                bear.get("cash_distributions_per_share", "0"),
                "BEAR_DISTRIBUTIONS",
            )
            if bear_terminal < 0 or bear_distributions < 0:
                raise LocalInvestmentPilotError("BEAR_VALUES_MUST_BE_NONNEGATIVE")
            bear_wealth = bear_terminal + bear_distributions
        except LocalInvestmentPilotError:
            issues.append("THESIS_BREAK_STRESS_BEAR_COMPARISON_UNAVAILABLE")
        if bear_wealth is not None and stress_wealth >= bear_wealth:
            issues.append("THESIS_BREAK_STRESS_NOT_MORE_SEVERE_THAN_BEAR")

    stress_return: Decimal | None = None
    stress_downside_pct: Decimal | None = None
    price_input = prepared["price_input"]
    if stress_wealth is not None and price_input["pit_time_status"] == "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        entry = _positive(price_input["price"], "CURRENT_PRICE")
        stress_return = stress_wealth / entry - Decimal("1")
        stress_downside_pct = (Decimal("1") - stress_wealth / entry) * Decimal("100")

    return {
        "status": "PASS" if not issues else "REVIEW_REQUIRED",
        "issues": issues,
        "stress_terminal_wealth": stress_wealth,
        "bear_terminal_wealth_for_comparison": bear_wealth,
        "stress_total_return": stress_return,
        "stress_downside_pct": stress_downside_pct,
        "probability_weighted": False,
    }



def _decision(
    prepared: Mapping[str, Any],
    metrics: Mapping[str, Any] | None,
    reason: str | None,
    stress_review: Mapping[str, Any] | None = None,
    portfolio_package: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Route the provisional pilot through the frozen IIOS decision-policy kernel.

    This is still a non-canonical preview: semantic fields originate in an
    operator/AI research response, formal Thesis Admission is absent, and portfolio
    constraints plus a complete BUY/ADD package are not collected by this pilot.
    Those absent gates must remain visible rather than being fabricated as PASS.
    """
    a = prepared["assessment"]
    c = prepared["case"]
    p = prepared["price_input"]
    issues: list[str] = []
    for name in ("trust", "reality", "quality", "thesis", "market_implied_expectation", "expectation_gap", "risk"):
        valid = "INTACT" if name == "thesis" else "PASS"
        if a[name]["status"] != valid:
            issues.append(f"{name.upper()}_{a[name]['status']}")
    if a["expectation_gap"]["direction"] != "POSITIVE":
        issues.append(f"EXPECTATION_GAP_DIRECTION_{a['expectation_gap']['direction']}")
    if not prepared["evidence_register"]:
        issues.append("EVIDENCE_REGISTER_EMPTY")
    if prepared["unresolved_evidence_references"]:
        issues.append("UNRESOLVED_EVIDENCE_REFERENCES")
    if prepared["after_cutoff_evidence_references"]:
        issues.append("REFERENCED_EVIDENCE_AFTER_CUTOFF")
    if prepared["uncertain_timing_evidence_references"]:
        issues.append("REFERENCED_EVIDENCE_TIMING_UNCERTAIN")
    if p["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        issues.append("PRICE_NOT_PIT_QUALIFIED")
    if prepared.get("notes_price_conflicts"):
        issues.append("OPERATOR_NOTE_PRICE_CONFLICTS_WITH_PRICE_INPUT")
    if reason == "SCENARIO_WEALTH_ORDERING_INCONSISTENT":
        issues.append("SCENARIO_WEALTH_ORDERING_INCONSISTENT")
    if stress_review:
        issues.extend(issue for issue in (stress_review.get("issues") or []) if issue not in issues)

    # Input/provenance faults are distinct from economic assessment states.
    validation_blockers = {
        "EVIDENCE_REGISTER_EMPTY",
        "UNRESOLVED_EVIDENCE_REFERENCES",
        "REFERENCED_EVIDENCE_AFTER_CUTOFF",
        "REFERENCED_EVIDENCE_TIMING_UNCERTAIN",
        "PRICE_NOT_PIT_QUALIFIED",
        "OPERATOR_NOTE_PRICE_CONFLICTS_WITH_PRICE_INPUT",
        "SCENARIO_WEALTH_ORDERING_INCONSISTENT",
        "BEAR_FAILURE_PATH_INCOMPLETE",
        "THESIS_BREAK_STRESS_INPUTS_INCOMPLETE",
        "THESIS_BREAK_STRESS_VALUE_INVALID",
        "THESIS_BREAK_STRESS_BEAR_COMPARISON_UNAVAILABLE",
        "THESIS_BREAK_STRESS_NOT_MORE_SEVERE_THAN_BEAR",
        "THESIS_BREAK_STRESS_MISSING",
    }
    validation_pass = not any(issue in validation_blockers for issue in issues)

    # Operator-entered package fields may inform this preview only after the
    # existing risk/portfolio contract has structurally validated them. They
    # never create formal portfolio admission or execution authority.
    position_pct = Decimal(c["current_position_pct"])
    package = portfolio_package or {}
    contract_ready = package.get("risk_portfolio_contract_status") == "STRUCTURAL_VALIDATION_PASS_NOT_ADMITTED"
    readiness = package.get("contract_readiness") if isinstance(package.get("contract_readiness"), Mapping) else {}
    portfolio_status = "UNKNOWN"
    if package.get("constraint_status") == "BLOCKED":
        portfolio_status = "BLOCKED"
    elif package.get("constraint_status") == "PASS" and contract_ready and readiness.get("package_ready"):
        portfolio_status = "PASS"
    thesis_admission_status = "NOT_ADMITTED"
    buy_add_package_complete = bool(contract_ready and readiness.get("package_ready"))
    can_add = bool(package.get("can_add") is True and portfolio_status == "PASS")
    expected_return = (
        None if metrics is None
        else Decimal(str(metrics["expected_annualized_return"]))
    )
    value_driver_status = (
        "PASS" if a["value_drivers"] and all(
            row["impact"] != "UNKNOWN" and str(row.get("rationale") or "").strip()
            for row in a["value_drivers"]
        ) else "UNKNOWN"
    )
    valuation_status = (
        "PASS" if metrics is not None
        and prepared["forecast_valuation"].get("entry_value_reference_per_share") not in (None, "")
        else "UNKNOWN"
    )
    forecast_status = "PASS" if metrics is not None else "UNKNOWN"
    risk_gate_pass = bool(
        metrics is not None
        and metrics.get("risk_pass", False)
        and a["risk"]["status"] == "PASS"
        and stress_review is not None
        and stress_review.get("status") == "PASS"
    )

    core_policy = evaluate_production_decision(
        validation_pass=validation_pass,
        trust_status=a["trust"]["status"],
        thesis_status=a["thesis"]["status"],
        reality_status=a["reality"]["status"],
        quality_gate_status=a["quality"]["status"],
        value_driver_status=value_driver_status,
        valuation_status=valuation_status,
        forecast_status=forecast_status,
        thesis_admission_status=thesis_admission_status,
        risk_status=a["risk"]["status"],
        portfolio_status=portfolio_status,
        position_pct=position_pct,
        gap_status=a["expectation_gap"]["status"],
        gap_positive=a["expectation_gap"]["direction"] == "POSITIVE",
        expected_annualized_return=expected_return,
        return_gate_pass=bool(metrics is not None and metrics.get("return_gate_pass", False)),
        risk_gate_pass=risk_gate_pass,
        can_add=can_add,
        package_complete=buy_add_package_complete,
        return_metrics_ready=metrics is not None,
        mie_policy=MIE_POLICY_OPTIONAL_EXPLANATORY,
        mie_material_contradiction=False,
    )

    # Keep the price screen useful without converting a non-canonical response into
    # an authorized investment action.
    price_screen_pass = bool(metrics is not None and metrics.get("return_gate_pass", False))
    if metrics is None:
        price_screen_status = "UNKNOWN"
        price_screen_action = "PRICE_SCREEN_UNRESOLVED"
    elif price_screen_pass:
        price_screen_status = "CURRENT_PRICE_AT_OR_BELOW_RETURN_RISK_CEILING"
        price_screen_action = "PRICE_SCREEN_PASS"
    else:
        price_screen_status = "CURRENT_PRICE_ABOVE_RETURN_RISK_CEILING"
        price_screen_action = "PRICE_SCREEN_FAIL"

    core_reason_text = {
        "RETURN_OR_CASE_VALIDATION_UNRESOLVED": "输入、截止时点、引用或回报计算存在未解决问题。",
        "TRUST_NOT_PASS_REQUIRES_REVIEW": "Trust 未达到 PASS，按 IIOS 决策优先级要求人工复核。",
        "THESIS_BROKEN": "投资论点被标记为失效；当前输入尚未完成正式准入，需人工重新评估。",
        "THESIS_UNKNOWN": "投资论点状态未知，不能形成确定行动。",
        "RISK_UNKNOWN": "风险状态未知，不能形成确定行动。",
        "RISK_GATE_FAILED": "风险门槛未通过。",
        "PORTFOLIO_CONSTRAINT_UNKNOWN": "当前流程没有可用的组合容量/仓位约束状态，不能批准新增资金或加仓。",
        "PORTFOLIO_CONSTRAINT_BLOCKED": "组合约束阻止新增资金。",
        "THESIS_ADMISSION_NOT_VALID": "试运行研究结果尚未形成正式 Thesis Admission。",
        "BUY_ADD_POSITION_PACKAGE_INCOMPLETE": "缺少完整入场区间、初始/目标/最大仓位及监控触发条件包。",
        "PRIMARY_VALUATION_NOT_ADMITTED": "估值仅是试运行假设，尚未形成正式估值准入。",
        "INDEPENDENT_FORECAST_NOT_ADMITTED": "情景是试运行假设，尚未形成正式独立预测准入。",
        "POSITIVE_EXPECTATION_GAP_AND_RETURN_PRICE_GATES_PASS": "价格/回报筛选通过，但此路径不授权交易。",
        "CURRENT_PRICE_ABOVE_TARGET_ENTRY_PRICE": "当前价未通过回报/风险入场门槛。",
        "FUNDAMENTAL_RETURN_OR_REQUIRED_RETURN_GATE_FAILED": "回报门槛未通过。",
        "POSITIVE_EXPECTATION_GAP_UNRESOLVED": "预期差不可识别或尚未完成判断。",
        "NO_POSITIVE_EXPECTATION_GAP": "没有通过的正向预期差。",
        "REALITY_GATE_NOT_PASS": "经营现实判断尚未达到 PASS。",
        "QUALITY_GATE_UNRESOLVED": "经济质量仍是有条件或未知状态。",
        "QUALITY_GATE_FAILED": "经济质量门槛未通过。",
        "VALUE_DRIVER_GATE_NOT_PASS": "价值驱动因素尚未完整。",
    }
    primary_reason = core_policy["primary_reason"]
    reason_text = core_reason_text.get(
        primary_reason,
        "核心决策策略要求复核；当前结论只是非正式研究预演。",
    )
    final_action = core_policy["action"]
    extra_gates: list[str] = []
    if not validation_pass:
        extra_gates.append("CORE_POLICY_LOCAL_VALIDATION_NOT_PASS")
    extra_gates.append(f"CORE_POLICY_{primary_reason}")
    if core_policy["action"] in {"BUY", "ADD", "EXIT", "REDUCE"}:
        final_action = "REVIEW_REQUIRED"
        reason_text = "策略内核预演出现资本行动，但当前研究输入没有正式 Thesis/Forecast/Valuation Admission；已降级为人工复核。"
        extra_gates.append("NON_CANONICAL_SEMANTICS_CANNOT_AUTHORIZE_CAPITAL_ACTION")
    if not buy_add_package_complete:
        extra_gates.append("BUY_ADD_PACKAGE_NOT_PROVIDED")
    if portfolio_status == "UNKNOWN":
        extra_gates.append(
            "PORTFOLIO_CONSTRAINT_NOT_PROVIDED"
            if not package or package.get("status") == "NOT_PROVIDED"
            else "PORTFOLIO_CONSTRAINT_OR_PACKAGE_UNRESOLVED"
        )
    if thesis_admission_status != "ADMITTED":
        extra_gates.append("FORMAL_THESIS_ADMISSION_NOT_CREATED")

    issues = list(dict.fromkeys(issues + extra_gates))
    return {
        "status": PILOT_STATUS,
        "provisional_action": final_action,
        "reason": reason_text,
        "gating_issues": issues,
        "price_screen_status": price_screen_status,
        "price_screen_action": price_screen_action,
        "core_policy_evaluation": {
            "status": "PILOT_POLICY_PREVIEW_NOT_CANONICAL",
            "policy_input_class": "OPERATOR_AI_RESEARCH_RESPONSE_NOT_FORMALLY_ADMITTED",
            "decision_kernel_version": core_policy["decision_kernel_version"],
            "decision_policy_version": core_policy["decision_policy_version"],
            "precedence_version": core_policy["precedence_version"],
            "action": core_policy["action"],
            "effective_pilot_action": final_action,
            "capital_action_downgraded": core_policy["action"] in {"BUY", "ADD", "EXIT", "REDUCE"},
            "kernel_new_capital_allowed": bool(core_policy["new_capital_allowed"]),
            "primary_reason": primary_reason,
            "decision_scope": core_policy["decision_scope"],
            "portfolio_status": portfolio_status,
            "thesis_admission_status": thesis_admission_status,
            "buy_add_package_complete": buy_add_package_complete,
            "formal_decision_created": False,
            "execution_authorized": False,
        },
        "human_approval_required": True,
        "formal_decision_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }

def _render_report(analysis: Mapping[str, Any]) -> str:
    c, p = analysis["case"], analysis["price_input"]
    a, f, calc, d = analysis["assessment"], analysis["forecast_valuation"], analysis["return_metrics"], analysis["decision"]
    params = analysis["decision_parameters"]
    package = analysis.get("portfolio_package") if isinstance(analysis.get("portfolio_package"), Mapping) else {}
    portfolio_lines = [
        "",
        "### 补充：组合风险预算与条件仓位包",
        "",
        f"- 仓位包状态：**{package.get('status', 'NOT_PROVIDED')}**",
        f"- 组合约束状态：{package.get('constraint_status', 'UNKNOWN')}；操作者新增资金许可：{package.get('can_add', False)}",
        f"- 组合可承受该标的论点失效损失：{str(package.get('portfolio_risk_budget_pct_nav')) + '% NAV' if package.get('portfolio_risk_budget_pct_nav') is not None else '未提供'}",
        f"- 操作者入场区间：{('—'.join(package.get('entry_zone')) + ' ' + c['currency']) if package.get('entry_zone') else '未提供'}；当前价格区间位置：{package.get('current_price_zone_status', 'UNKNOWN')}",
        f"- Thesis-break stress 每股期末财富：{package.get('stress_terminal_wealth_per_share') if package.get('stress_terminal_wealth_per_share') is not None else 'UNKNOWN'} {c['currency']}",
        f"- 在入场区间上沿的 stress 损失：{str(package.get('stress_loss_at_entry_zone_high_pct')) + '%' if package.get('stress_loss_at_entry_zone_high_pct') is not None else 'UNKNOWN'}",
        f"- 风险预算推导仓位上限：{str(package.get('risk_budget_max_position_pct')) + '%' if package.get('risk_budget_max_position_pct') is not None else '不约束/UNKNOWN'}；集中度上限：{str(package.get('policy_max_position_pct')) + '%' if package.get('policy_max_position_pct') is not None else '未提供'}",
        f"- 风险预算后条件最大仓位：{str(package.get('effective_max_position_pct')) + '%' if package.get('effective_max_position_pct') is not None else 'UNKNOWN'}；条件初始仓位：{str(package.get('conditional_initial_position_pct')) + '%' if package.get('conditional_initial_position_pct') is not None else 'UNKNOWN'}；条件目标仓位：{str(package.get('conditional_target_position_pct')) + '%' if package.get('conditional_target_position_pct') is not None else 'UNKNOWN'}",
        f"- 当前仓位是否高于推导上限：{package.get('current_position_over_effective_max') if package.get('current_position_over_effective_max') is not None else 'UNKNOWN'}",
        f"- 条件建议仓位：{str(package.get('conditional_proposed_position_pct')) + '%' if package.get('conditional_proposed_position_pct') is not None else '无（至少一个门槛未满足）'}；本次实际获准新增仓位：0%",
        f"- 风险/组合合同：{package.get('risk_portfolio_contract_status', 'NOT_CREATED')}；合同结构验证不等于正式准入。",
        f"- 说明：{package.get('reason', '未提供个人组合约束；组合状态维持 UNKNOWN。')}",
        "- 本节仅为非正式条件测算；不会自动减仓或加仓，也不替代正式 Thesis/证据/估值准入及人工批准。",
    ]
    stress = f.get("thesis_break_stress") if isinstance(f.get("thesis_break_stress"), Mapping) else {}
    stress_review = analysis.get("thesis_break_stress_review") or {}
    conflicts = analysis.get("notes_price_conflicts") or []
    price_consistency_line = (
        f"- 带标签的备注股价一致性：**CONFLICT** — 检测到 {'、'.join(str(item) for item in conflicts)}，"
        f"但唯一计算用价为 {p['price']} {c['currency']}；本次必须 REVIEW_REQUIRED。"
        if conflicts else
        "- 带标签的备注股价一致性：未发现与结构化当前价冲突的明确表述；所有回报计算仅使用上方结构化当前价。"
    )
    lines = [
        f"# IIOS 本地投资研究试运行：{c['company']}（{c['symbol']}）",
        "",
        f"- 运行等级：**{PILOT_STATUS}**",
        f"- 分析截止：{c.get('as_of_timestamp') or (c['as_of_date'] + ' 00:00:00+08:00（日期级截止）')}；当前价：{p['price']} {c['currency']}（观察日 {p['observation_date']}，价格可获得时点 {p['known_at']}）",
        price_consistency_line,
        f"- 当前持仓：{c['current_position_pct']}%",
        "",
        "> 这是个人使用的本地试运行报告，不是正式 canonical Decision。人工价格/AI 分析/来源摘要未完成正式证据准入；建议只供人工审阅，不会自动下单。",
        "",
        "## 一、建议与回报筛选",
        "",
        f"- 试运行建议：**{d['provisional_action']}**",
        f"- 理由：{d['reason']}",
        f"- 价格层独立筛选：{d.get('price_screen_action', 'UNKNOWN')}；状态：{d['price_screen_status']}",
        f"- 核心决策策略预演：{d.get('core_policy_evaluation', {}).get('action', 'NOT_RUN')} → 有效试运行建议 {d.get('core_policy_evaluation', {}).get('effective_pilot_action', d['provisional_action'])} / {d.get('core_policy_evaluation', {}).get('primary_reason', 'UNKNOWN')}",
        "- 注意：策略预演使用非正式研究输入；本次未创建正式 Decision。组合约束和仓位包状态见下一节；正式 Thesis Admission 与人工审批仍未完成。",
        f"- 预期年化回报：{calc['expected_annualized_return'] if calc else 'UNKNOWN'}",
        f"- 15% 年化门槛：{calc['fundamental_target_pass'] if calc else 'UNKNOWN'}",
        f"- Required Return：{params['required_return_annualized']}；结果：{calc['required_return_pass'] if calc else 'UNKNOWN'}",
        f"- 共同约束下目标入场价上限：{calc['target_entry_price'] if calc else 'UNKNOWN'}",
        f"- 最大 Bear 损失约束：{params['max_loss_pct']}%",
        *_render_price_zone_sensitivity_section(analysis.get("price_zone_sensitivity") or {}),
        *portfolio_lines,
        "",
        "## 二、Trust / Reality / Quality",
        "",
        f"- Trust：{a['trust']['status']} — {a['trust'].get('summary') or '未知'}",
        f"- Reality：{a['reality']['status']} — {a['reality'].get('summary') or '未知'}",
        f"- Quality：{a['quality']['status']} — {a['quality'].get('summary') or '未知'}",
        "",
        "## 三、Thesis 与价值驱动因素",
        "",
        f"- Thesis 状态：{a['thesis']['status']}",
        "",
        "### 核心论点",
        "",
    ]
    lines.extend(_format_text_block(a["thesis"].get("core_statement")))
    lines.extend(["", "### 价值驱动因素", ""])
    drivers = sorted(a["value_drivers"], key=lambda x: (x["rank"], x["driver"]))
    if drivers:
        for display_rank, item in enumerate(drivers, start=1):
            lines.extend([
                f"**价值驱动因素 {display_rank}：{item['driver']}**（影响：{item['impact']}）",
                f"   {item['rationale'] or '未提供理由。'}",
            ])
            if item.get("evidence_refs"):
                lines.append("   证据引用：" + "、".join(item["evidence_refs"]))
            lines.append("")
    else:
        lines.extend(["价值驱动因素未提供。", ""])
    lines.extend(["### Thesis 失效条件", ""])
    lines.extend(f"- {x}" for x in a["thesis"]["break_conditions"]) if a["thesis"]["break_conditions"] else lines.append("- 未提供。")
    lines.extend(["", "### 重新评估触发器", ""])
    lines.extend(f"- {x}" for x in a["thesis"]["reassessment_triggers"]) if a["thesis"]["reassessment_triggers"] else lines.append("- 未提供。")
    lines.extend([
        "",
        "## 四、Forecast / Valuation",
        "",
        f"- 模型：{f['model']}",
        f"- 模型选择理由：{f['model_rationale'] or '未提供'}",
        f"- 安全边际参考价值：{f.get('entry_value_reference_per_share') or 'UNKNOWN'} {c['currency']}/股",
        f"- 情景概率是否校准：{'是' if f['probabilities_calibrated'] else '否 / 未校准'}",
        "",
    ])
    scenarios = f.get("scenarios") if isinstance(f.get("scenarios"), Mapping) else {}
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        lines.extend([
            f"### {label} 情景",
            "",
            f"- 情景概率：{row.get('probability', 'UNKNOWN')}",
            f"- 期末每股价值：{row.get('terminal_value_per_share', 'UNKNOWN')} {c['currency']}",
            f"- 每股现金分配：{row.get('cash_distributions_per_share', '0')} {c['currency']}",
            f"- 情景理由：{' '.join(str(row.get('rationale') or '未提供').splitlines()).strip()}",
            *(
                [
                    f"- 下行情景触发条件：{' '.join(str(row.get('failure_trigger') or '未提供').splitlines()).strip()}",
                    f"- 经营影响路径：{' '.join(str(row.get('operating_impact') or '未提供').splitlines()).strip()}",
                    f"- 估值传导机制：{' '.join(str(row.get('valuation_mechanism') or '未提供').splitlines()).strip()}",
                ] if name == "bear" else []
            ),
            "",
        ])
    stress_terminal_display = stress.get("terminal_value_per_share")
    stress_terminal_display = "UNKNOWN" if stress_terminal_display in (None, "") else stress_terminal_display
    stress_distribution_display = stress.get("cash_distributions_per_share")
    stress_distribution_display = "UNKNOWN" if stress_distribution_display in (None, "") else stress_distribution_display
    stress_wealth = stress_review.get("stress_terminal_wealth")
    stress_return = stress_review.get("stress_total_return")
    stress_downside = stress_review.get("stress_downside_pct")
    lines.extend([
        "### 独立论点失效压力测试（不纳入 Bear/Base/Bull 概率加权）",
        "",
        f"- 校验状态：{stress_review.get('status', 'MISSING')}",
        f"- 失效触发条件：{' '.join(str(stress.get('failure_trigger') or '未提供').splitlines()).strip()}",
        f"- 经营影响路径：{' '.join(str(stress.get('operating_impact') or '未提供').splitlines()).strip()}",
        f"- 估值方法：{' '.join(str(stress.get('valuation_method') or '未提供').splitlines()).strip()}",
        f"- 压力期末每股价值：{stress_terminal_display} {c['currency']}",
        f"- 压力情景每股现金分配：{stress_distribution_display} {c['currency']}",
        f"- 压力期末总财富：{stress_wealth if stress_wealth is not None else 'UNKNOWN'} {c['currency']}/股",
        f"- 按当前输入价计算的压力回报：{stress_return if stress_return is not None else 'UNKNOWN'}",
        f"- 对应压力下跌幅度：{stress_downside if stress_downside is not None else 'UNKNOWN'}%",
        "- 这是一项独立、非概率加权压力测试；不能将其混入概率加权预期回报。无法量化、缺少 Bear 失败路径或未比 Bear 更悲观时，系统要求 REVIEW_REQUIRED。",
        f"- 压力测试理由：{' '.join(str(stress.get('rationale') or '未提供').splitlines()).strip()}",
        "",
    ])
    if calc:
        lines.extend([
            "- 概率加权终值：" + str(calc["expected_terminal_wealth"]) + f" {c['currency']}/股",
            "- 预期总回报：" + str(calc["expected_total_return"]),
            "- 入场安全边际：" + str(calc["margin_of_safety"]),
            "- Bear 情景回报：" + str(calc["bear_return"]),
            "- 回报门槛入场上限：" + str(calc["target_entry_price_for_return"]),
            "- 风险约束入场上限：" + str(calc.get("target_entry_price_for_risk")),
            "",
        ])
    else:
        lines.extend([f"回报计算尚未完成：{analysis['return_metrics_reason'] or '情景输入不足'}。", ""])
    lines.extend(["### 估值假设", ""])
    assumptions = f.get("assumptions") if isinstance(f.get("assumptions"), list) else []
    if assumptions:
        for item in assumptions:
            lines.append("- " + _humanize_item(item))
    else:
        lines.append("- 未提供；不得将其解释为市场一致预期。")
    lines.extend(render_operating_driver_section(
        analysis.get("operating_driver_forecast") or {},
        f.get("scenarios") if isinstance(f.get("scenarios"), Mapping) else {},
        c["currency"],
    ))
    lines.extend(render_valuation_transmission_section(
        analysis.get("valuation_transmission") or {},
        c["currency"],
    ))
    lines.extend([
        "",
        "## 五、MIE 与预期差",
        "",
        f"- MIE：{a['market_implied_expectation']['status']} — {a['market_implied_expectation'].get('summary') or '未知'}",
        f"- 预期差：{a['expectation_gap']['status']} / {a['expectation_gap']['direction']} — {a['expectation_gap'].get('summary') or '未知'}",
        "- 若 MIE 无法识别或缺乏历史支持，不以内部估值代替市场隐含预期。",
        "",
        "## 六、风险与证据引用核对",
        "",
        f"- 风险状态：{a['risk']['status']} — {a['risk'].get('summary') or '未知'}",
    ])
    risk_items = a["risk"].get("items") or []
    if risk_items:
        for item in risk_items:
            lines.append("- " + _humanize_item(item))
    else:
        lines.append("- 具体风险清单未提供。")
    lines.extend([
        "",
        f"- 价格 assurance：{p['assurance_label']}",
        f"- 价格时间状态：{p['pit_time_status']}",
        "- 日期字段的时间检查不证明来源真实性、原始字节完整性或使用权。",
        "",
        "### 证据引用解析状态",
        "",
    ])
    evidence_rows = analysis.get("evidence_register") or []
    evidence_by_id = {
        str(row.get("source_id")): row
        for row in evidence_rows
        if isinstance(row, Mapping) and row.get("source_id")
    }
    referenced = sorted(set(analysis.get("referenced_evidence_ids") or []))
    unresolved = sorted(set(analysis.get("unresolved_evidence_references") or []))
    lines.append(f"- 结构化引用 ID 数：{len(referenced)}；在来源登记表中找到记录：{len([ref for ref in referenced if ref in evidence_by_id])}；未解析：{len(unresolved)}。")
    if referenced:
        for ref in referenced:
            if ref in evidence_by_id:
                row = evidence_by_id[ref]
                source_ref = _source_ref_markdown(row.get("source_ref"))
                lines.append(
                    f"- **{ref}**：已登记，尚未完成正式证据准入；时间状态：{row.get('time_status', 'UNKNOWN')}；来源：{source_ref}。"
                )
            else:
                lines.append(f"- **{ref}**：**未解析**。本次输入没有该 ID 对应的 evidence_register 记录，不能将正文描述视为完成来源核验。")
    else:
        lines.append("- 未发现结构化证据引用 ID；这不等于没有引用事实，也不表示证据链已完成。")
    lines.extend(["", "### 来源登记记录", ""])
    if evidence_rows:
        for row in evidence_rows:
            lines.extend([
                f"- **{row['source_id']} — {row['title']}**",
                f"  类型：{row['source_class']}；known_at：{row['known_at'] or 'UNKNOWN'}；时间状态：{row['time_status']}。",
                f"  来源位置：{_source_ref_markdown(row['source_ref'])}。",
                f"  摘要：{' '.join(str(row['summary']).splitlines()).strip()}",
                "  正式证据准入：未完成。",
                "",
            ])
    else:
        lines.append("- 来源登记表为空；所有正文中的证据编号如无登记记录，均不能视为已解析。")
    lines.extend(["## 七、需人工处理的问题", ""])
    issue_explanations = {
        "OPERATOR_NOTE_PRICE_CONFLICTS_WITH_PRICE_INPUT": (
            "操作者备注包含与结构化当前价不一致的明确股价表述；回报计算只使用结构化价格，但必须先更正或确认备注。"
        ),
        "SCENARIO_WEALTH_ORDERING_INCONSISTENT": (
            "Bear/Base/Bull 情景期末总财富未按 Bear ≤ Base ≤ Bull 排列；不要把该组概率加权回报用于投资判断。"
        ),
        "BEAR_FAILURE_PATH_INCOMPLETE": (
            "Bear 情景缺少明确的失效触发条件、经营影响路径或估值传导机制，尚未证明覆盖核心投资论点失败。"
        ),
        "THESIS_BREAK_STRESS_MISSING": (
            "缺少独立的论点失效压力测试；不得仅凭概率加权回报超过门槛判断投资论点已通过。"
        ),
        "THESIS_BREAK_STRESS_INPUTS_INCOMPLETE": (
            "独立论点失效压力测试缺少触发条件、经营影响、估值方法或推理说明。"
        ),
        "THESIS_BREAK_STRESS_VALUE_INVALID": (
            "独立论点失效压力测试缺少有效的非负期末价值/现金分配金额，压力回报不能核算。"
        ),
        "THESIS_BREAK_STRESS_BEAR_COMPARISON_UNAVAILABLE": (
            "无法将独立压力情景与 Bear 情景的期末总财富进行比较。"
        ),
        "THESIS_BREAK_STRESS_NOT_MORE_SEVERE_THAN_BEAR": (
            "独立压力情景的期末总财富并不低于 Bear 情景，不能作为更严重的独立下行情景。"
        ),
        "REFERENCED_EVIDENCE_TIMING_UNCERTAIN": (
            "被引用来源缺少可靠的截止前已知时点；日期精度不足或时间字段缺失/无效，不能用它支持 BUY/ADD。"
        ),
    }
    lines.extend(
        f"- {issue}：{issue_explanations[issue]}" if issue in issue_explanations else f"- {issue}"
        for issue in d["gating_issues"]
    ) if d["gating_issues"] else lines.append("- 所提供的试运行门槛均通过；仍需检查原始来源和估值假设。")
    lines.extend([
        "",
        "## 八、治理边界",
        "",
        "- 不创建正式 Evidence/PIT、Forecast/Valuation Admission、Decision Admission 或 Machine Publication。",
        "- 本地 run-record 不等同于 canonical IIOS_RUN_RECEIPT。",
        "- 人工最终审批必需；自动执行关闭。",
        "",
    ])
    if analysis.get("notes"):
        lines.extend(["## 操作者备注", ""])
        lines.extend(_format_text_block(analysis["notes"]))
        lines.append("")
    # Keep markdown portable: no pipe tables; remove repeated blank lines and trailing whitespace.
    cleaned: list[str] = []
    for line in lines:
        line = str(line).rstrip()
        if not line and (not cleaned or not cleaned[-1]):
            continue
        cleaned.append(line)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned) + "\n"


def _analyse(payload: Mapping[str, Any], run_id: str) -> tuple[dict[str, Any], str]:
    prepared = _prepare_input(payload)
    metrics, reason = _return_metrics(prepared)
    stress_review = _thesis_break_stress_review(prepared)
    price_zone_sensitivity = _price_zone_sensitivity(prepared, metrics, reason)
    portfolio_package = build_local_pilot_portfolio_package(
        operator_context=prepared.get("operator_portfolio_context"),
        case=prepared["case"],
        price_input=prepared["price_input"],
        decision_parameters=prepared["decision_parameters"],
        assessment=prepared["assessment"],
        forecast_valuation=prepared["forecast_valuation"],
        return_metrics=metrics,
        stress_review=stress_review,
        evidence_register=prepared["evidence_register"],
        unresolved_evidence_ids=prepared["unresolved_evidence_references"],
        after_cutoff_evidence_ids=prepared["after_cutoff_evidence_references"],
        uncertain_timing_evidence_ids=prepared["uncertain_timing_evidence_references"],
    )
    decision = _decision(prepared, metrics, reason, stress_review, portfolio_package)
    analysis = {
        "schema_version": PILOT_ANALYSIS_SCHEMA,
        "runner_version": "IIOS-LOCAL-PILOT-0.1",
        "pilot_id": run_id,
        "status": PILOT_STATUS,
        "case": prepared["case"],
        "price_input": prepared["price_input"],
        "evidence_register": prepared["evidence_register"],
        "referenced_evidence_ids": prepared["referenced_evidence_ids"],
        "unresolved_evidence_references": prepared["unresolved_evidence_references"],
        "after_cutoff_evidence_references": prepared["after_cutoff_evidence_references"],
        "uncertain_timing_evidence_references": prepared["uncertain_timing_evidence_references"],
        "assessment": prepared["assessment"],
        "forecast_valuation": prepared["forecast_valuation"],
        "operating_driver_forecast": prepared["operating_driver_forecast"],
        "valuation_transmission": prepared["valuation_transmission"],
        "operator_valuation_context": prepared["operator_valuation_context"],
        "decision_parameters": prepared["decision_parameters"],
        "portfolio_package": portfolio_package,
        "return_metrics": metrics,
        "price_zone_sensitivity": price_zone_sensitivity,
        "return_metrics_reason": reason,
        "thesis_break_stress_review": stress_review,
        "notes_price_conflicts": prepared["notes_price_conflicts"],
        "decision": decision,
        "governance": {
            "status": PILOT_STATUS, "source_origin_verified": False,
            "source_use_rights_verified": False, "formal_evidence_pit_admission": False,
            "formal_forecast_created": False, "formal_valuation_admission": False,
            "formal_decision_created": False, "canonical_publication_created": False,
            "canonical_run_receipt_created": False, "human_approval_required": True,
            "execution_authorized": False, "auto_execution": False,
        },
        "notes": prepared["notes"],
    }
    return analysis, _render_report(analysis)


def _write_run(
    input_path: Path, output_root: Path, *, replay_of: str | None = None
) -> dict[str, Any]:
    try:
        input_text = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LocalInvestmentPilotError("PILOT_INPUT_FILE_UNREADABLE") from exc

    previous_analysis: dict[str, Any] | None = None
    if replay_of:
        if replay_of in {".", ".."} or Path(replay_of).name != replay_of or "/" in replay_of:
            raise LocalInvestmentPilotError("REPLAY_PILOT_ID_INVALID")
        prior_dir = (output_root / replay_of).resolve(strict=True)
        if prior_dir.parent != output_root.resolve():
            raise LocalInvestmentPilotError("REPLAY_RUN_MUST_BE_DIRECT_CHILD_OF_OUTPUT_ROOT")
        previous_receipt, previous_manifest = _verify_run_bundle(prior_dir)
        source = input_path.resolve(strict=True)
        if source != (prior_dir / "input.json").resolve(strict=True):
            raise LocalInvestmentPilotError("REPLAY_INPUT_MUST_BE_THE_VERIFIED_PRIOR_INPUT")
        if _fingerprint_file(source) != previous_manifest["input.json"]:
            raise LocalInvestmentPilotError("REPLAY_INPUT_HASH_CHANGED_AFTER_VERIFICATION")
        try:
            previous_analysis = json.loads((prior_dir / "analysis.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LocalInvestmentPilotError("REPLAY_PRIOR_ANALYSIS_UNREADABLE") from exc
        if not isinstance(previous_analysis, dict) or previous_analysis.get("pilot_id") != previous_receipt.get("pilot_id"):
            raise LocalInvestmentPilotError("REPLAY_PRIOR_ANALYSIS_PILOT_ID_MISMATCH")

    payload = json.loads(input_text)
    symbol = str((payload.get("case") or {}).get("symbol") or "candidate").replace(".", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"local-pilot-{symbol}-{stamp}"
    analysis, report = _analyse(payload, run_id)
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    _write_local(run_dir / "input.json", input_text)
    _write_local(run_dir / "analysis.json", json.dumps(_safe(analysis), ensure_ascii=False, indent=2, allow_nan=False))
    _write_local(run_dir / "report.md", report)

    file_manifest = {name: _fingerprint_file(run_dir / name) for name in BUNDLE_FILENAMES}
    replay_comparison = _replay_comparison(previous_analysis, analysis) if previous_analysis is not None else None
    receipt = {
        "receipt_schema": PILOT_RECEIPT_SCHEMA,
        "status": PILOT_STATUS,
        "pilot_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "replay_of": replay_of,
        "input_file": "input.json",
        "analysis_file": "analysis.json",
        "report_file": "report.md",
        "file_manifest": file_manifest,
        "replay_comparison": replay_comparison,
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }
    _write_local(run_dir / "pilot_receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2))
    if os.name != "nt":
        run_dir.chmod(0o700)
    if replay_of:
        result_status = "PILOT_REPLAY_MATCHED" if replay_comparison and replay_comparison["status"] == "MATCH" else "PILOT_REPLAY_MISMATCH"
    else:
        result_status = "PILOT_CREATED"
    return {
        "status": result_status,
        "pilot_id": run_id,
        "provisional_action": analysis["decision"]["provisional_action"],
        "replay_of": replay_of,
        "replay_comparison": replay_comparison,
        "run_dir": str(run_dir),
        "report_path": str(run_dir / "report.md"),
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "auto_execution": False,
    }

def run_local_investment_pilot(*, input_path: str | Path, output_root: str | Path, replay_of: str | None = None) -> dict[str, Any]:
    source = _outside_repo(input_path, "PILOT_INPUT_PATH", must_exist=True)
    root = _private_dir(output_root, "PILOT_OUTPUT_ROOT")
    return _write_run(source, root, replay_of=replay_of)


def _template(
    *, company: str, symbol: str, market: str, as_of_date: str, current_position_pct: str,
    price: str, price_observation_date: str, price_known_at: str, price_source_claim: str,
    as_of_timestamp: str | None = None,
) -> dict[str, Any]:
    seed = build_research_case(symbol, as_of_date, current_position_pct, market=market)
    cutoff = _date(as_of_date, "AS_OF_DATE")
    _cutoff_instant, normalized_cutoff_timestamp = _resolve_cutoff_timestamp(
        {"as_of_timestamp": as_of_timestamp}, cutoff
    )
    currency = "CNY" if seed["request"]["market"] == "CN-A" else "HKD"
    _positive(price, "CURRENT_PRICE")
    observation = _date(price_observation_date, "PRICE_OBSERVATION_DATE")
    known_at = _datetime(price_known_at, "PRICE_KNOWN_AT", allow_date_only=False)
    if known_at.date() != observation:
        raise LocalInvestmentPilotError("PRICE_KNOWN_AT_DATE_MUST_MATCH_OBSERVATION_DATE")
    if not str(price_source_claim or "").strip():
        raise LocalInvestmentPilotError("PRICE_SOURCE_CLAIM_REQUIRED")
    return {
        "schema_version": PILOT_SCHEMA,
        "case": {
            "company": company, "market": seed["request"]["market"], "symbol": seed["request"]["symbol"],
            "currency": currency, "as_of_date": seed["temporal_scope"]["cutoff_date"],
            "as_of_timestamp": normalized_cutoff_timestamp,
            "cutoff_semantics": "EXPLICIT_TIMESTAMP" if normalized_cutoff_timestamp else "DATE_ONLY_START_OF_DAY",
            "current_position_pct": seed["decision_context"]["current_position_pct"],
        },
        "price_input": {
            "price": str(price), "currency": currency, "observation_date": observation.isoformat(),
            "known_at": known_at.isoformat(), "assurance_label": PRICE_ASSURANCE,
            "sources_claimed": [str(price_source_claim).strip()],
        },
        "evidence_register": [],
        "assessment": {
            "trust": {"status": "UNKNOWN", "summary": "尚未完成信任审查", "evidence_refs": []},
            "reality": {"status": "UNKNOWN", "summary": "尚未完成经营现实审查", "evidence_refs": []},
            "quality": {"status": "UNKNOWN", "summary": "尚未完成经济质量审查", "evidence_refs": []},
            "thesis": {"status": "UNKNOWN", "core_statement": "", "drivers": [], "break_conditions": [], "reassessment_triggers": [], "evidence_refs": []},
            "value_drivers": [],
            "market_implied_expectation": {"status": "NOT_IDENTIFIABLE", "summary": "尚未足够识别市场隐含预期", "evidence_refs": []},
            "expectation_gap": {"status": "UNKNOWN", "direction": "UNKNOWN", "summary": "尚未验证预期差", "evidence_refs": []},
            "risk": {"status": "UNKNOWN", "summary": "尚未完成风险审查", "items": []},
        },
        "forecast_valuation": {
            "model": "UNKNOWN", "model_rationale": "", "entry_value_reference_per_share": None,
            "probabilities_calibrated": False, "assumptions": [],
            "scenarios": {
                "bear": {
                    "probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0",
                    "rationale": "", "failure_trigger": "", "operating_impact": "", "valuation_mechanism": "",
                },
                "base": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
                "bull": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": "0", "rationale": ""},
            },
            "thesis_break_stress": {
                "failure_trigger": "", "operating_impact": "", "valuation_method": "",
                "terminal_value_per_share": None, "cash_distributions_per_share": "0",
                "rationale": "", "evidence_refs": [],
            },
        },
        "valuation_transmission": {
            "schema_version": VALUATION_TRANSMISSION_SCHEMA,
            "model_family": "UNKNOWN",
            "valuation_model_name": "UNKNOWN",
            "earnings_period": "UNKNOWN",
            "summary": "未完成 B5 经营结果到每股估值的传导；若模型类别、期间、项目归属、存量业务替代或稀释股数不可识别，应保留 NOT_LINKED。",
            "scenarios": {
                "bear": {
                    "ownership_ratio": {"value": None, "unit": "ratio", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                    "displaced_existing_after_tax_profit_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；须扣除存量业务被替代的税后归属利润"},
                    "basic_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；按实际普通股股数填写"},
                    "convertible_bond_incremental_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；可明确为 0，但须说明转股口径"},
                    "other_dilution_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；可明确为 0，但须说明口径"},
                    "pe_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；须与主估值模型一致"}
                },
                "base": {
                    "ownership_ratio": {"value": None, "unit": "ratio", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                    "displaced_existing_after_tax_profit_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；须扣除存量业务被替代的税后归属利润"},
                    "basic_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；按实际普通股股数填写"},
                    "convertible_bond_incremental_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；可明确为 0，但须说明转股口径"},
                    "other_dilution_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；可明确为 0，但须说明口径"},
                    "pe_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；须与主估值模型一致"}
                },
                "bull": {
                    "ownership_ratio": {"value": None, "unit": "ratio", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                    "displaced_existing_after_tax_profit_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；须扣除存量业务被替代的税后归属利润"},
                    "basic_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；按实际普通股股数填写"},
                    "convertible_bond_incremental_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；可明确为 0，但须说明转股口径"},
                    "other_dilution_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；可明确为 0，但须说明口径"},
                    "pe_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；须与主估值模型一致"}
                }
            }
        },
        "operator_valuation_context": {
            "selected_model_family": "UNKNOWN",
            "baseline_includes_project": None,
            "input_owner": "OPERATOR"
        },
        "operating_driver_forecast": {
            "schema_version": "IIOS-OPERATING-DRIVER-FORECAST-0.1",
            "scope": "UNKNOWN",
            "status": "UNKNOWN",
            "actuals_period": "UNKNOWN",
            "forecast_period": "UNKNOWN",
            "summary": "尚未完成经营驱动因素分析；请解释已识别与不可识别的驱动。",
            "product_lines": [],
            "scenarios": {
            "bear": {
                "product_lines": [],
                "fixed_cash_opex_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "depreciation_amortization_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "finance_cost_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "tax_rate": {"value": None, "unit": "ratio", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "cash_capex_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "change_working_capital_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"}
            },
            "base": {
                "product_lines": [],
                "fixed_cash_opex_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "depreciation_amortization_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "finance_cost_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "tax_rate": {"value": None, "unit": "ratio", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "cash_capex_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "change_working_capital_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"}
            },
            "bull": {
                "product_lines": [],
                "fixed_cash_opex_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "depreciation_amortization_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "finance_cost_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "tax_rate": {"value": None, "unit": "ratio", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "cash_capex_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"},
                "change_working_capital_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "未知；不得猜测"}
            }
            },
            "limitations": [],
        },
        "decision_parameters": {
            "horizon_years": 1, "horizon_override": False, "horizon_override_basis": [],
            "horizon_selection_rationale": "默认使用 1 年年化回报；符合例外条件时才显式切换为 3 年。",
            "required_return_annualized": "0.15", "max_loss_pct": "25",
        },
        "notes": "缺失信息保留 UNKNOWN / NOT_IDENTIFIABLE，不要编造。请在截止时点内优先引用公告、财报和交易所资料。",
    }


def create_pilot_template(
    *, company: str, symbol: str, market: str, as_of_date: str, current_position_pct: str,
    price: str, price_observation_date: str, price_known_at: str, price_source_claim: str,
    template_root: str | Path, as_of_timestamp: str | None = None,
) -> dict[str, Any]:
    root = _private_dir(template_root, "PILOT_TEMPLATE_ROOT")
    payload = _template(
        company=company, symbol=symbol, market=market, as_of_date=as_of_date,
        current_position_pct=current_position_pct, price=price, price_observation_date=price_observation_date,
        price_known_at=price_known_at, price_source_claim=price_source_claim,
        as_of_timestamp=as_of_timestamp,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    token = str(payload["case"]["symbol"]).replace(".", "-")
    input_path = root / f"pilot-input-{token}-{stamp}.json"
    prompt_path = root / f"pilot-prompt-{token}-{stamp}.md"
    _write_local(input_path, json.dumps(payload, ensure_ascii=False, indent=2))
    prompt = (
        "你是 IIOS 的个人股票研究助手。请主动联网检索并完成截止时点内的研究，不要要求用户先上传这份模板或另外寻找公告。"
        "模板 JSON 将直接附在本提示中。先从公司/交易所/监管机构公开资料取证，再判断 Trust、Reality、Quality、Thesis、价值驱动、"
        "估值与预期差、风险。返回时必须保留 schema_version、case、price_input 原样不变，只补研究字段。"
        "证据应给出可直接打开的来源 URL、标题、发布日期/已知时点与事实摘要；优先使用公司定期报告、公告、交易所与监管文件。"
        "不得为了填满字段编造事实、URL、财务数字或所谓市场一致预期。对于 MIE，不具备可核实的一致预期/市场定价证据时，明确使用 NOT_IDENTIFIABLE 并解释原因。"
        "请用可解释的显式假设建立 Bear/Base/Bull 数值情景；情景是估算而非已披露事实，说明盈利/利润率/销量等驱动及估值倍数来源。"
        "概率之和必须为 1；期末总财富次序必须 Bear ≤ Base ≤ Bull。若无法有根据地估算某情景，请明确报告其不可识别及缺少什么依据，不要捏造。"
        "Bear 必须明确写 failure_trigger、operating_impact 和 valuation_mechanism；若论点依赖盈利恢复，Bear 必须检验恢复失败。"
        "独立 thesis_break_stress 必须另行量化失效后的每股期末价值和现金分配，并明确估值方法、触发条件、经营影响与理由；不参与概率加权，且须比 Bear 更悲观。"
        "不要在 notes 中重述与 price_input.price 不同的现价；当前股价只取结构化 price_input。不能将人工价格标为已验证。"
        "未知事实用 UNKNOWN，并解释缺口；研究结论可以是 REVIEW_REQUIRED，但不可以把整个结构留空。只返回一个完整 JSON 对象，不要输出代码围栏或额外说明。"
    )
    b5_transmission_instructions = (
        "\n\nB5 估值传导要求（IIOS-VALUATION-TRANSMISSION-0.1）："
        "必须保留 valuation_transmission 节点和 Bear/Base/Bull 三个情景。valuation_model_name 必须逐字匹配 forecast_valuation.model；model_family 必须准确分类为 EPS_MULTIPLE、FCF_DCF、DDM、SOTP、RNPV、OTHER 或 UNKNOWN；earnings_period 必须与 operating_driver_forecast.forecast_period 完全一致。"
        "operator_valuation_context 是操作者拥有的字段，必须原样保留模板中的 UNKNOWN/null，不得替操作者选择估值模型或判断原估值是否已包含项目；操作者稍后会在本地独立确认。"
        "本批只有 EPS_MULTIPLE 适配器可传导。每个情景必须提供 ownership_ratio、displaced_existing_after_tax_profit_cny、basic_shares、convertible_bond_incremental_shares、other_dilution_shares、pe_multiple_x，均用 {value,unit,data_class,basis,evidence_refs,note} 结构。"
        "ownership_ratio 是 0–1 的比例；被替代存量业务税后归属利润为非负 CNY；股数单位 shares，填写实际普通股数量而非百万股；可转债潜在新增股数和其他稀释股数可明确为 0，但须说明依据。P/E 倍数单位 x。"
        "事实/发行人预测必须有可解析且截止时间兼容的 evidence_refs；分析假设须标为 ANALYST_ASSUMPTION 并解释依据，不能伪装成事实。缺少项目税后净利润、所有权比例、存量业务蚕食、股数/可转债稀释、期间或模型一致性时保持 NOT_LINKED。"
        "仅当操作者明确确认现有 Bear/Base/Bull 每股终值及入场价值锚均不含该项目时，方可将稀释口径增量加到三个情景，并以 Base 增量同步调整入场价值锚；如已经包含则只显示敏感性、不重复相加；如不确定则不修改原估值。论点失效压力测试不自动加回项目价值。"
    )
    driver_instructions = (
        "\n\n经营驱动因素树要求（IIOS-OPERATING-DRIVER-FORECAST-0.1）："
        "必须保留 operating_driver_forecast 节点。scope 可为 PROJECT_INCREMENTAL、PRODUCT_LINE、COMPANY_WIDE 或 UNKNOWN。"
        "product_lines 为按产品/服务行分别列出的数组，每行含 product_id、product_name、capacity_tonnes_per_year 和 historical_actuals。"
        "historical_actuals 含 production_tonnes、sales_volume_tonnes、net_asp_cny_per_tonne、variable_cost_cny_per_tonne。historical_actuals 中可参与计算的历史数据只能标为 OBSERVED_ACTUAL；发行人计划或分析假设不得混进历史实际。"
        "Bear/Base/Bull 各自含 product_lines；每行使用同样四个度量：production_tonnes、sales_volume_tonnes、net_asp_cny_per_tonne、variable_cost_cny_per_tonne。前瞻情景输入只允许 ISSUER_FORECAST 或 ANALYST_ASSUMPTION；不得把 OBSERVED_ACTUAL 标签直接挪入前瞻情景。未知时保留 UNKNOWN。"
        "每个度量都使用对象 {value,unit,data_class,basis,evidence_refs,note}；data_class 只能为 OBSERVED_ACTUAL、ISSUER_FORECAST、ANALYST_ASSUMPTION、UNKNOWN。"
        "未知值必须 value=null 且 data_class=UNKNOWN；事实/发行人预测必须列出能直接支撑该数字的 evidence_refs，无法把来源和口径对齐时不要把数字标成事实。"
        "产品容量单位 tonnes/year；产量与销量 tonnes；净售价和单位变动成本 CNY/tonne；现金费用/折旧/融资成本/资本开支/营运资金变动 CNY；tax_rate 是 0 至 1 之间的比例。"
        "Bear/Base/Bull 另含 fixed_cash_opex_cny、depreciation_amortization_cny、finance_cost_cny、tax_rate、cash_capex_cny、change_working_capital_cny。固定现金运营费用不得重复包含折旧。"
        "收入按销售量×净售价，不得用产量或总产品收入反推净售价；变动成本按销售量×单位变动成本。change_working_capital_cny 为正表示占用现金，负数表示释放。"
        "产能利用率只有在 actuals_period/forecast_period 明确为完整年度（例如 2026FY）且产量与年度产能口径一致时才计算；季度、半年、多年度或口径不明一律 UNKNOWN，不能拿部分期间产量直接除以年度产能。"
        "若没有同口径产销量、实际净售价或单位成本，务必保留 UNKNOWN；可以另列清晰标记为 ISSUER_FORECAST 或 ANALYST_ASSUMPTION 的情景值，但不得将这些值称为已实现结果。"
        "报告产品收入结构、产能利用率（只有同期间产量与年产能可比时才计算）、EBITDA、EBIT、税前利润、净利润和自由现金流代理，并列出缺失驱动与估值传导限制。"
        "该经营桥不会自动替代每股 Bear/Base/Bull 估值；不清楚项目增量利润、存量业务替代/蚕食、税后归属利润和稀释股数时，不计算项目 EPS 或每股估值贡献。"
    )
    if symbol.replace(".SH", "").replace(".SZ", "") == "605016":
        driver_instructions += (
            "\n\n百龙创园（605016）专属注意：国内功能糖干燥扩产项目与泰国智慧工厂必须分开；尽可能按异麦芽酮糖粉体、低聚半乳糖粉体、乳果糖粉体分别列行。"
            "既有产品收入除以产量不是已验证的实际 ASP，因为收入取决于销量且受库存、粉液形态、规格与产品组合影响。"
            "公开申报中的设计产能、预测单价/净利润及 7,800/10,400/13,000 吨爬坡计划只能按发行人预测或计划标注，不能当作实际产销量或已实现利润。"
            "项目年份第 3/4/5 年与自然年释放计划存在 RAMP_CALENDAR_BASIS_UNRECONCILED 待核口径；不要自行强行对齐，解释缺少的正式投产日、月度产量、产品销量、净成交价、单位成本、转固/折旧及营运资金证据。"
            "若本次截止日晚于历史公开材料，必须检索截止日前最新公开披露后再判断项目当前状态；不要把旧的调试阶段描述直接外推到新截止日。"
        )
    prompt += driver_instructions
    prompt += b5_transmission_instructions
    _write_local(prompt_path, prompt + "\n")
    return {
        "status": "PILOT_TEMPLATE_CREATED", "input_template": str(input_path),
        "analysis_prompt": str(prompt_path), "private_local_storage": True,
        "formal_decision_created": False,
    }



def _extract_json_object(text: str) -> dict[str, Any]:
    """Accept plain JSON or one JSON object wrapped in a ChatGPT code fence."""
    raw = str(text or "").strip()
    if not raw:
        raise LocalInvestmentPilotError("CHATGPT_JSON_EMPTY")
    raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, count=1, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```\s*$", "", raw, count=1)
    start = raw.find("{")
    if start < 0:
        raise LocalInvestmentPilotError("CHATGPT_JSON_OBJECT_NOT_FOUND")
    try:
        value, _end = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError as exc:
        raise LocalInvestmentPilotError("CHATGPT_JSON_INVALID_COPY_THE_COMPLETE_JSON_OBJECT") from exc
    if not isinstance(value, dict):
        raise LocalInvestmentPilotError("CHATGPT_JSON_OBJECT_REQUIRED")
    return value


def _read_json_response_file(path: str | Path) -> dict[str, Any]:
    """Read the full ChatGPT response from a UTF-8 file, not the terminal input buffer."""
    response_path = Path(path).expanduser()
    try:
        raw = response_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LocalInvestmentPilotError("CHATGPT_RESPONSE_FILE_NOT_FOUND") from exc
    except OSError as exc:
        raise LocalInvestmentPilotError("CHATGPT_RESPONSE_FILE_READ_FAILED") from exc
    if not raw.strip():
        raise LocalInvestmentPilotError("CHATGPT_RESPONSE_FILE_EMPTY")
    return _extract_json_object(raw)


def _response_file_signature(path: str | Path) -> tuple[int, int, str] | None:
    """Return a content-aware signature so even same-size saves are detected."""
    response_path = Path(path).expanduser()
    try:
        content = response_path.read_bytes()
        stat = response_path.stat()
    except OSError:
        return None
    # Content hash makes detection robust even on filesystems whose timestamp
    # precision is too coarse to distinguish two quick saves of equal length.
    return stat.st_size, stat.st_mtime_ns, hashlib.sha256(content).hexdigest()


def _wait_for_response_file_change(
    path: str | Path,
    *,
    previous_signature: tuple[int, int, str] | None,
    poll_interval: float = 0.25,
    stable_seconds: float = 0.75,
) -> tuple[int, int, str]:
    """Wait until a non-empty response file changes and remains stable.

    The operator can save the ChatGPT JSON in TextEdit and the wizard resumes
    automatically. Pressing Enter is optional; Ctrl-C cancels the wait.
    """
    response_path = Path(path).expanduser()
    candidate: tuple[int, int, str] | None = None
    candidate_since = 0.0
    try:
        can_read_terminal = bool(sys.stdin.isatty())
    except (AttributeError, OSError):
        can_read_terminal = False

    while True:
        current = _response_file_signature(response_path)
        now = _time.monotonic()
        if current is not None and current[0] > 0 and current != previous_signature:
            if current != candidate:
                candidate = current
                candidate_since = now
            elif now - candidate_since >= stable_seconds:
                return current
        else:
            candidate = None
            candidate_since = 0.0

        if can_read_terminal:
            try:
                ready, _, _ = select.select([sys.stdin], [], [], poll_interval)
            except (OSError, ValueError):
                can_read_terminal = False
                _time.sleep(poll_interval)
                continue
            if ready:
                # Consume Enter so it cannot answer an unrelated later prompt.
                sys.stdin.readline()
                latest = _response_file_signature(response_path)
                if latest is None or latest[0] == 0 or latest == previous_signature:
                    print("尚未检测到结果文件的新内容；请确认已在 TextEdit 按 Command+S 保存。继续等待文件更新。", flush=True)
        else:
            _time.sleep(poll_interval)



def _assert_response_preserves_operator_inputs(
    template_path: str | Path, payload: Mapping[str, Any]
) -> None:
    """Fail closed if the AI response changes operator-owned case or price fields."""
    path = Path(template_path).expanduser()
    try:
        template = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LocalInvestmentPilotError("OPERATOR_INPUT_TEMPLATE_NOT_FOUND") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalInvestmentPilotError("OPERATOR_INPUT_TEMPLATE_UNREADABLE") from exc

    mismatched_sections = [
        field for field in ("case", "price_input", "operator_valuation_context")
        if payload.get(field) != template.get(field)
    ]
    if mismatched_sections:
        sections = ", ".join(mismatched_sections)
        raise LocalInvestmentPilotError(
            "CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS: "
            + sections
            + "; 请将本地输入模板中的这些字段原样复制回结果 JSON 并保存后重试。"
            + " 本次分析尚未生成，系统不会静默接受 AI 改写的标的、截止时点或人工股价。"
        )


def _validate_guided_research_response(payload: Mapping[str, Any]) -> None:
    """Reject a mostly untouched template before creating a misleading empty report."""
    missing: list[str] = []

    evidence = payload.get("evidence_register")
    source_rows = evidence if isinstance(evidence, list) else []
    has_usable_source = any(
        isinstance(row, Mapping)
        and all(str(row.get(key) or "").strip() for key in ("source_id", "title", "source_ref", "known_at", "summary"))
        and str(row.get("source_ref") or "").strip().upper() not in {"UNKNOWN", "N/A", "NONE"}
        for row in source_rows
    )
    if not has_usable_source:
        missing.append("至少一条可追溯来源（source_id/title/source_ref/known_at/summary）")

    assessment = payload.get("assessment")
    if not isinstance(assessment, Mapping):
        assessment = {}
    required_summaries = (
        ("trust", "尚未完成信任审查", "Trust 结论与理由"),
        ("reality", "尚未完成经营现实审查", "Reality 结论与理由"),
        ("quality", "尚未完成经济质量审查", "Quality 结论与理由"),
        ("market_implied_expectation", "尚未足够识别市场隐含预期", "MIE 判断与理由"),
        ("expectation_gap", "尚未验证预期差", "预期差判断与理由"),
        ("risk", "尚未完成风险审查", "主要风险与理由"),
    )
    for key, placeholder, label in required_summaries:
        section = assessment.get(key)
        section = section if isinstance(section, Mapping) else {}
        summary = str(section.get("summary") or "").strip()
        if not summary or summary == placeholder:
            missing.append(label)

    thesis = assessment.get("thesis")
    thesis = thesis if isinstance(thesis, Mapping) else {}
    for key, label in (
        ("core_statement", "核心投资论点"),
        ("drivers", "Thesis 价值驱动因素"),
        ("break_conditions", "Thesis 失效条件"),
        ("reassessment_triggers", "重新评估触发器"),
    ):
        value = thesis.get(key)
        if isinstance(value, list):
            filled = any(str(item or "").strip() for item in value)
        else:
            filled = bool(str(value or "").strip())
        if not filled:
            missing.append(label)
    value_drivers = assessment.get("value_drivers")
    if not isinstance(value_drivers, list) or not value_drivers:
        missing.append("价值驱动因素排序")
    risk = assessment.get("risk")
    risk_items = risk.get("items") if isinstance(risk, Mapping) else None
    if not isinstance(risk_items, list) or not risk_items:
        missing.append("结构化风险清单")

    valuation = payload.get("forecast_valuation")
    valuation = valuation if isinstance(valuation, Mapping) else {}
    if not str(valuation.get("model_rationale") or "").strip():
        missing.append("估值模型选择理由")
    assumptions = valuation.get("assumptions")
    if not isinstance(assumptions, list) or not any(str(item or "").strip() for item in assumptions):
        missing.append("估值假设（无法估值时写明原因与缺口）")
    entry_reference = valuation.get("entry_value_reference_per_share")
    if entry_reference in (None, ""):
        missing.append("安全边际参考价值/每股估值锚点")

    scenarios = valuation.get("scenarios")
    scenarios = scenarios if isinstance(scenarios, Mapping) else {}
    for scenario_name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        scenario = scenarios.get(scenario_name)
        scenario = scenario if isinstance(scenario, Mapping) else {}
        if not str(scenario.get("rationale") or "").strip():
            missing.append(f"{label} 情景分析理由")
        for key, field_label in (
            ("probability", "情景概率"),
            ("terminal_value_per_share", "期末每股价值"),
            ("cash_distributions_per_share", "每股现金分配"),
        ):
            if scenario.get(key) in (None, ""):
                missing.append(f"{label}{field_label}")
    bear = scenarios.get("bear")
    bear = bear if isinstance(bear, Mapping) else {}
    for key, label in (
        ("failure_trigger", "Bear 失效触发条件"),
        ("operating_impact", "Bear 经营影响路径"),
        ("valuation_mechanism", "Bear 估值传导机制"),
    ):
        if not str(bear.get(key) or "").strip():
            missing.append(label)

    drivers = payload.get("operating_driver_forecast")
    drivers = drivers if isinstance(drivers, Mapping) else {}
    if drivers.get("schema_version") != "IIOS-OPERATING-DRIVER-FORECAST-0.1":
        missing.append("经营驱动因素树 schema_version")
    driver_summary = str(drivers.get("summary") or "").strip()
    if not driver_summary or driver_summary == "尚未完成经营驱动因素分析；请解释已识别与不可识别的驱动。":
        missing.append("经营驱动因素树结论与不可识别缺口说明")
    scenario_tree = drivers.get("scenarios")
    scenario_tree = scenario_tree if isinstance(scenario_tree, Mapping) else {}
    for name in ("bear", "base", "bull"):
        if not isinstance(scenario_tree.get(name), Mapping):
            missing.append(f"经营驱动因素树 {name.upper()} 情景结构")
    if not isinstance(drivers.get("product_lines"), list):
        missing.append("经营驱动因素树 product_lines 数组")

    transmission = payload.get("valuation_transmission")
    transmission = transmission if isinstance(transmission, Mapping) else {}
    if transmission.get("schema_version") != VALUATION_TRANSMISSION_SCHEMA:
        missing.append("B5 valuation_transmission schema_version")
    transmission_summary = str(transmission.get("summary") or "").strip()
    if not transmission_summary or transmission_summary == "未完成 B5 经营结果到每股估值的传导；若模型类别、期间、项目归属、存量业务替代或稀释股数不可识别，应保留 NOT_LINKED。":
        missing.append("B5 估值传导结论/未知项说明")
    transmission_scenarios = transmission.get("scenarios")
    transmission_scenarios = transmission_scenarios if isinstance(transmission_scenarios, Mapping) else {}
    for name in ("bear", "base", "bull"):
        scenario = transmission_scenarios.get(name)
        if not isinstance(scenario, Mapping):
            missing.append(f"B5 {name.upper()} 估值传导情景结构")
            continue
        for key in (
            "ownership_ratio", "displaced_existing_after_tax_profit_cny", "basic_shares",
            "convertible_bond_incremental_shares", "other_dilution_shares", "pe_multiple_x",
        ):
            if not isinstance(scenario.get(key), Mapping):
                missing.append(f"B5 {name.upper()} {key} 结构")
    for key in ("model_family", "valuation_model_name", "earnings_period"):
        if not str(transmission.get(key) or "").strip():
            missing.append(f"B5 {key}")

    stress = valuation.get("thesis_break_stress")
    stress = stress if isinstance(stress, Mapping) else {}
    for key, label in (
        ("failure_trigger", "独立压力测试失效触发条件"),
        ("operating_impact", "独立压力测试经营影响路径"),
        ("valuation_method", "独立压力测试估值方法"),
        ("rationale", "独立压力测试推理"),
    ):
        if not str(stress.get(key) or "").strip():
            missing.append(label)
    for key, label in (
        ("terminal_value_per_share", "独立压力测试期末每股价值"),
        ("cash_distributions_per_share", "独立压力测试每股现金分配"),
    ):
        if stress.get(key) in (None, ""):
            missing.append(label)

    if missing:
        labels = "；".join(dict.fromkeys(missing))
        raise LocalInvestmentPilotError(
            "CHATGPT_RESPONSE_INCOMPLETE：研究回答仍有空白或保留模板占位内容："
            + labels
            + "。本次尚未生成报告。请直接补齐当前已打开的 pilot-chatgpt-response JSON 文件并保存，再回到终端按回车；不用重跑向导，也不要把 JSON 粘贴到终端。"
        )


def _build_response_repair_prompt(
    *, original_prompt: str, response_path: str | Path, validation_error: str
) -> str:
    """Build a one-paste repair request so the user does not manually edit dozens of JSON fields."""
    path = Path(response_path).expanduser()
    try:
        previous_response = path.read_text(encoding="utf-8")
    except OSError:
        previous_response = ""
    return (
        "上一轮 IIOS 股票研究回答未通过本地格式/完整性校验。请修复并重新完成研究，不要让用户手工编辑 JSON。"
        "\n\n【校验反馈】\n" + validation_error
        + "\n\n【必须遵守】\n"
        "1. 以下是本次唯一基准模板与全部研究要求。必须完整保留 schema_version、case、price_input 的所有值，尤其人工股价、观察日、known_at、截止时点和 assurance_label。"
        "2. 不要要求用户上传模板或额外寻找公告；请主动联网搜索截止时点前公开可访问的公司公告、交易所披露与监管文件。"
        "3. 修复缺失结构字段并填写数值估值情景、经营驱动因素树和 B5 估值传导结构；研究假设和事实来源要分开。不得编造来源、财务数字或市场一致预期。"
        "4. 如果确实无法识别，字段仍要保留结构，并在 summary/rationale 中具体解释未知原因、证据缺口及需要人工确认的事项。"
        "5. 请返回一个完整 JSON 对象，不要代码围栏和 JSON 以外的文字。"
        + "\n\n【原始研究提示及完整基准模板】\n" + original_prompt
        + "\n\n【上次失败的完整回答，请在此基础上修复】\n" + previous_response
    )


def _read_operator_prompt(prompt: str) -> str:
    """Read an operator prompt from a controlling terminal even when stdin is a Python heredoc.

    The dedicated 605016 launcher executes its Python driver from stdin. In that
    mode, builtin input() sees the already-consumed source stream and raises
    EOFError. When using the real builtin with non-interactive stdin, read from
    /dev/tty instead. Tests that replace builtin input() keep their normal path.
    """
    if not sys.stdin.isatty() and input is _ORIGINAL_INPUT:
        try:
            with open("/dev/tty", "r+", encoding="utf-8", buffering=1) as tty:
                tty.write(prompt)
                tty.flush()
                raw = tty.readline()
        except OSError as exc:
            raise LocalInvestmentPilotError(
                "INTERACTIVE_TERMINAL_UNAVAILABLE: 无法从 /dev/tty 读取交互输入。"
                "请在 macOS Terminal 中启动 .command 文件，而不是以无终端的后台/重定向方式运行。"
            ) from exc
        if raw == "":
            raise LocalInvestmentPilotError(
                "INTERACTIVE_TERMINAL_INPUT_CLOSED: 终端输入已关闭；尚未完成组合预算输入。"
            )
        return raw
    return input(prompt)


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = _read_operator_prompt(f"{prompt}{suffix}: ").strip()
        if raw:
            return raw
        if default is not None:
            return default
        print("这一项需要填写。")



def _ask_operator_portfolio_context() -> dict[str, Any] | None:
    """Collect operator-owned portfolio limits; default into this step to avoid accidental skips."""
    print("\n个人组合与仓位包（建议填写）")
    print("直接回车默认进入填写；如确实暂时不填写，请明确输入 0。跳过后组合约束保持 UNKNOWN，不生成条件仓位。")
    print("填写的数据保存在本机私有输入中，不会上传 GitHub；它们也不会授权实际交易。")
    while True:
        choice = _ask("是否填写组合风险预算和仓位限制？0 = 明确跳过，1 = 填写", "1")
        if choice in {"0", "1"}:
            break
        print("请输入 0 或 1。")
    if choice == "0":
        return None

    print("组合约束状态：1 = 已核实 PASS，2 = BLOCKED，3 = UNKNOWN")
    while True:
        status_choice = _ask("组合约束状态 1/2/3", "3")
        if status_choice in {"1", "2", "3"}:
            break
        print("请输入 1、2 或 3。")
    constraint_status = {"1": "PASS", "2": "BLOCKED", "3": "UNKNOWN"}[status_choice]
    if constraint_status != "PASS":
        print("组合约束未通过；保留当前状态，不采集条件仓位，也不会允许新增资金。")
        return {"constraint_status": constraint_status, "can_add": False}

    while True:
        can_add_choice = _ask("按你的真实现金与组合限制，是否允许增加该标的风险敞口？1 = 是，0 = 否", "0")
        if can_add_choice in {"0", "1"}:
            break
        print("请输入 0 或 1。")

    def ask_percent(prompt: str) -> str:
        while True:
            raw = _ask(prompt)
            try:
                value = _number(raw, "PERCENT_INPUT")
                if value < 0 or value > 100:
                    raise LocalInvestmentPilotError("百分比必须在 0 到 100 之间。")
                return format(value, "f")
            except (LocalInvestmentPilotError, ValueError) as exc:
                print(f"输入无效：{exc}。请填写 0 到 100 之间的百分比。")

    def ask_positive(prompt: str) -> str:
        while True:
            raw = _ask(prompt)
            try:
                return format(_positive(raw, "PRICE_ZONE"), "f")
            except LocalInvestmentPilotError as exc:
                print(f"输入无效：{exc}。请填写大于 0 的价格。")

    risk_budget = ask_percent("论点失效压力情景下，该标的最多允许损失组合净资产的百分比（例如 1）")
    while True:
        low = ask_positive("你愿意考虑入场的价格区间下沿")
        high = ask_positive("你愿意考虑入场的价格区间上沿")
        if Decimal(low) <= Decimal(high):
            break
        print("入场区间下沿不得高于上沿，请重新输入两个价格。")
    while True:
        initial = ask_percent("初始建仓占组合净资产百分比（例如 1）")
        target = ask_percent("目标仓位占组合净资产百分比（例如 4）")
        maximum = ask_percent("允许的最大单股仓位占组合净资产百分比（例如 8）")
        if Decimal(initial) <= Decimal(target) <= Decimal(maximum):
            break
        print("仓位必须满足：初始仓位 ≤ 目标仓位 ≤ 最大仓位。请重新输入三个百分比。")

    return {
        "constraint_status": constraint_status,
        "can_add": can_add_choice == "1",
        "risk_budget_pct_nav": risk_budget,
        "entry_zone_low": low,
        "entry_zone_high": high,
        "initial_position_pct": initial,
        "target_position_pct": target,
        "max_position_pct": maximum,
    }


def _ask_operator_valuation_context() -> dict[str, Any]:
    """Collect the primary model choice and project-in-baseline scope from the operator, not the AI."""
    print("\nB5 主估值模型确认（由你选择，不让 AI 替你选模型）")
    print("  1 = EPS / 市盈率倍数（本批支持项目增量传导）")
    print("  2 = DCF / 自由现金流折现")
    print("  3 = DDM / 股利折现")
    print("  4 = SOTP / 分部估值")
    print("  5 = RNPV / 风险调整净现值")
    print("  6 = 其他模型")
    print("  0 = 暂不确认（不进行 B5 每股传导）")
    choices = {
        "1": "EPS_MULTIPLE",
        "2": "FCF_DCF",
        "3": "DDM",
        "4": "SOTP",
        "5": "RNPV",
        "6": "OTHER",
        "0": "UNKNOWN",
    }
    while True:
        choice = _ask("你确认本次主估值模型类型 0–6", "0")
        if choice in choices:
            break
        print("请输入 0 到 6。")
    family = choices[choice]
    baseline_includes_project: bool | None = None
    if family == "EPS_MULTIPLE":
        print("请确认报告中的每股终值和安全边际估值锚是否已经包含此项目/扩产的价值。")
        print("  1 = 已包含（不可再叠加）")
        print("  2 = 明确不包含（符合条件时可传导增量）")
        print("  0 = 无法确认（保持原估值，不叠加）")
        while True:
            scope_choice = _ask("原估值的项目包含范围 0/1/2", "0")
            if scope_choice in {"0", "1", "2"}:
                break
            print("请输入 0、1 或 2。")
        baseline_includes_project = {"0": None, "1": True, "2": False}[scope_choice]
    return {
        "selected_model_family": family,
        "baseline_includes_project": baseline_includes_project,
        "input_owner": "OPERATOR",
    }


def run_guided_wizard(
    *,
    template_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    """Run guided research using a dedicated file for the potentially large ChatGPT JSON."""
    template_root = template_root or (Path.home() / ".iios-private" / "local-pilot" / "inputs")
    output_root = output_root or (Path.home() / ".iios-private" / "local-pilot" / "runs")
    today = date.today()
    print("\nIIOS 投资分析｜简易向导")
    print("填写标的和价格后，程序会打开 ChatGPT；完成回答后保存到指定 JSON 文件，报告自动生成。")
    company = _ask("公司名称")
    symbol_input = _ask("股票代码（可输入 SZ002810、002810.SZ 或 002810）")
    market_choice = _ask("市场：1 = A 股，2 = 港股", "1")
    if market_choice not in {"1", "2"}:
        raise LocalInvestmentPilotError("MARKET_CHOICE_MUST_BE_1_OR_2")
    market = "CN-A" if market_choice == "1" else "HK"
    symbol = _normalize_guided_symbol(symbol_input, market)
    while True:
        try:
            cutoff = _date(_ask("分析截止日 YYYY-MM-DD", today.isoformat()), "AS_OF_DATE")
            break
        except LocalInvestmentPilotError as exc:
            print(f"日期格式错误：{exc}。请按 YYYY-MM-DD 输入，例如 2026-10-12。")

    print("\n请选择分析截止口径（默认按收盘后分析，无需手写时区）：")
    print("  1 = 严格日期级截止：截止日 00:00（+08:00），只能使用此前日期已知的信息")
    print("  2 = 收盘后分析（推荐默认）：自动使用截止日 15:30（+08:00），允许截止日收盘价")
    print("  3 = 自定义时点：仅特殊情况使用，例如 2026-10-12T15:30:00+08:00")
    while True:
        cutoff_mode = _ask("分析截止口径 1/2/3", "2")
        custom_cutoff = ""
        if cutoff_mode == "3":
            custom_cutoff = _ask(
                "自定义截止时点（必须含时区，例如 2026-10-12T15:30:00+08:00）"
            )
        try:
            cutoff_instant, cutoff_timestamp = _guided_cutoff_timestamp(
                cutoff, cutoff_mode, custom_cutoff
            )
            break
        except LocalInvestmentPilotError as exc:
            print(f"截止口径输入有误：{exc}")
            print("请选 1、2 或 3；普通收盘后分析通常选择 2，不要只输入日期。")

    while True:
        position = _ask("当前持仓百分比（例如空仓填 0）", "0")
        try:
            build_research_case(symbol, cutoff.isoformat(), position, market=market)
            break
        except (LocalInvestmentPilotError, ValueError, TypeError) as exc:
            print(f"持仓比例不合法：{exc}。请按百分比填写，例如 0 或 10。")

    while True:
        price = _ask("你核实的股价（必须大于 0）")
        try:
            _positive(price, "CURRENT_PRICE")
            break
        except LocalInvestmentPilotError as exc:
            print(f"股价输入不合法：{exc}。请只输入价格数字，例如 19.74。")

    # No holiday-calendar lookup is performed; weekends are rejected below.
    default_price_date = (
        _latest_weekday_on_or_before(cutoff)
        if cutoff_timestamp else _previous_weekday(cutoff)
    ).isoformat()
    while True:
        date_rule = (
            "不得晚于截止日；选择 2 时可以填写截止日当天"
            if cutoff_timestamp else "必须早于分析截止日"
        )
        try:
            observation = _date(
                _ask(f"该价格观察日期 YYYY-MM-DD（{date_rule}）", default_price_date),
                "PRICE_OBSERVATION_DATE",
            )
            _validate_guided_observation_date(
                observation, cutoff, cutoff_timestamp=cutoff_instant if cutoff_timestamp else None
            )
            break
        except LocalInvestmentPilotError as exc:
            print(f"价格观察日期不合法：{exc}")
            print("请填写真实交易日；本程序不会把周末自动改成交易日，也不会自动修改截止日期。")
    default_known_at = datetime.combine(observation, time(15, 0), tzinfo=SHANGHAI).isoformat()
    print("\n价格时点：1 = 收盘价/按 15:00 处理（默认）；2 = 非收盘价/指定实际时点")
    time_mode = _ask("价格时点 1/2", "1")
    if time_mode == "1":
        known_at = default_known_at
    else:
        while True:
            known_at = _ask(
                "价格可获得时间（必须包含时区，例如 2026-10-12T13:30:00+08:00）"
            )
            try:
                parsed_known_at = _datetime(known_at, "PRICE_KNOWN_AT", allow_date_only=False)
                if parsed_known_at.date() != observation:
                    raise LocalInvestmentPilotError("PRICE_KNOWN_AT_DATE_MUST_MATCH_OBSERVATION_DATE")
                if parsed_known_at > cutoff_instant:
                    raise LocalInvestmentPilotError("PRICE_KNOWN_AFTER_CUTOFF_TIMESTAMP")
                known_at = parsed_known_at.isoformat()
                break
            except LocalInvestmentPilotError as exc:
                print(f"价格可获得时点不符合截止约束：{exc}")
                print("请检查日期与截止时点。")
    source_claim = f"用户手动提供的 {price}；按 {'收盘价 15:00' if time_mode == '1' else '操作者指定时点'} 处理；未从交易所或行情供应商独立核验"
    print("\n请核对：")
    print(f"  {company} / {symbol} / {market}")
    if symbol != symbol_input.strip().upper().replace(" ", ""):
        print(f"  股票代码已规范化：{symbol_input} → {symbol}")
    cutoff_display = cutoff_timestamp or (cutoff.isoformat() + " 00:00:00+08:00（日期级截止）")
    print(f"  分析截止 {cutoff_display}；价格 {price}；观察日 {observation.isoformat()}；持仓 {position}%")
    print(f"  价格时间：{known_at}；价格来源：人工输入、未独立核验。")
    if _ask("确认并继续？1 = 继续，0 = 退出", "1") != "1":
        return {"status": "CANCELLED", "formal_decision_created": False}

    template_result = create_pilot_template(
        company=company,
        symbol=symbol,
        market=market,
        as_of_date=cutoff.isoformat(),
        current_position_pct=position,
        price=price,
        price_observation_date=observation.isoformat(),
        price_known_at=known_at,
        price_source_claim=source_claim,
        template_root=template_root,
        as_of_timestamp=cutoff_timestamp,
    )
    template_path = Path(template_result["input_template"])
    prompt_path = Path(template_result["analysis_prompt"])
    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    prompt = (
        prompt_path.read_text(encoding="utf-8")
        + "\n\n【本次完整 JSON 模板——无需上传单独模板文件】\n"
        + json.dumps(template_payload, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n\n【执行要求】\n"
        + "基于上方模板直接研究并填充同一个 JSON 对象。优先联网搜索并核对截止时点前的公司公告、定期报告、交易所披露、监管文件；"
        + "不要求操作者另行上传公告或模板。来源登记至少填写 source_id、title、source_class、source_ref（可直接打开的 URL）、published_at、known_at、summary。"
        + "最多优先列出 8 条对结论最重要的来源，确保每条来源真实且支持对应事实；不知道的时间明确写 UNKNOWN。"
        + "必须完成 Trust、Reality、Quality、Thesis、价值驱动因素排序、风险清单、MIE/预期差、估值模型和假设、Bear/Base/Bull 数值情景以及独立 thesis_break_stress。"
        + "请填写 entry_value_reference_per_share，以及三种情景各自 probability、terminal_value_per_share、cash_distributions_per_share、rationale；概率合计为 1。"
        + "请填写 thesis_break_stress 的 failure_trigger、operating_impact、valuation_method、terminal_value_per_share、cash_distributions_per_share、rationale，且其期末总财富必须低于 Bear。"
        + "不要只原样返回模板，不允许把核心研究字段全部留空。若无法识别必须具体解释原因和证据缺口；数字估值可以建立透明、可追责的假设，但不得把假设伪装为披露事实。"
        + "严格保留 schema_version、case、price_input 原样不变，尤其不得更改人工股价、观察日期、known_at 或 price assurance 标签。"
        + "只返回完整 JSON，不要代码围栏或额外说明。"
    )

    private_inputs = _private_dir(template_root, "PILOT_TEMPLATE_ROOT")
    response_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    response_path = private_inputs / f"pilot-chatgpt-response-{symbol.replace('.', '-')}-{response_stamp}.json"
    _write_local(response_path, "")
    initial_response_signature = _response_file_signature(response_path)

    if sys.platform == "darwin":
        # The prompt is copied to the clipboard; the large response is always handed off via a file.
        subprocess.run(["pbcopy"], input=prompt, text=True, check=True, timeout=5)
        subprocess.run(["open", "https://chatgpt.com/"], check=False, timeout=5)
        subprocess.run(["open", "-a", "TextEdit", str(response_path)], check=False, timeout=5)
        print("\n已打开 ChatGPT 和 JSON 结果文件；完整输入模板与研究指令已复制到剪贴板，无需另行上传模板文件。")
    else:
        print("\n研究提示（已包含本次完整 JSON 模板）：\n" + prompt)

    print(f"\nChatGPT 完整回答的保存位置：\n{response_path}")
    print("操作步骤（只需在 ChatGPT 与这个结果文件之间复制一次）：")
    print("  1. 在已打开的 ChatGPT 对话中粘贴剪贴板中的完整研究提示并发送；提示里已经包含本次 JSON 模板，不用上传模板或另找公告。")
    print("  2. 复制 ChatGPT 返回的完整 JSON，覆盖上面已打开的 JSON 结果文件并保存。")
    print("  3. 回到本终端按回车。不要把 JSON 粘贴到终端，也不要手工填写 JSON 字段。")
    if sys.platform == "darwin":
        print("  提示：JSON 文件已用 TextEdit 打开；粘贴后按 Command+S 保存。")

    previous_response_signature = initial_response_signature
    while True:
        print(
            "\n等待 ChatGPT 完整 JSON 保存到结果文件；保存后会自动读取（无需按回车）。",
            flush=True,
        )
        print("如需立即检查也可按回车；按 Control-C 退出。", flush=True)
        response_signature = _wait_for_response_file_change(
            response_path,
            previous_signature=previous_response_signature,
        )
        print("已检测到结果文件更新且写入稳定，正在读取并校验……", flush=True)
        try:
            payload = _read_json_response_file(response_path)
            _assert_response_preserves_operator_inputs(template_path, payload)
            _prepare_input(payload)
            _validate_guided_research_response(payload)
            break
        except (OSError, ValueError, KeyError, TypeError) as exc:
            previous_response_signature = response_signature
            print(f"暂未继续：{exc}", flush=True)
            if isinstance(exc, LocalInvestmentPilotError) and not str(exc).startswith(
                ("CHATGPT_RESPONSE_FILE_READ_FAILED", "CHATGPT_RESPONSE_FILE_NOT_FOUND")
            ):
                repair_prompt = _build_response_repair_prompt(
                    original_prompt=prompt, response_path=response_path, validation_error=str(exc)
                )
                if sys.platform == "darwin":
                    try:
                        subprocess.run(["pbcopy"], input=repair_prompt, text=True, check=True, timeout=5)
                        print("\n已将自动修复提示复制到剪贴板。请切回已打开的 ChatGPT 对话，直接粘贴并发送；")
                        print("然后复制新的完整 JSON 覆盖同一个结果文件并保存；系统会自动检测新版本。")
                        print("不需要手工修改几十个 JSON 字段，也不需要重新填写公司和股价。", flush=True)
                    except (OSError, subprocess.SubprocessError):
                        print("\n无法自动复制修复提示；请切回结果文件修正后保存，系统将自动重试。按 Control-C 可退出。", flush=True)
                else:
                    print("\n自动修复提示：\n" + repair_prompt, flush=True)
            print(f"当前响应文件：{response_path}", flush=True)
            print("无需重新填写标的；修正文件并保存后会自动重试；按 Control-C 可退出。", flush=True)

    # Validate the response before collecting any optional operator-only
    # portfolio inputs. AI research output never gets to author these limits.
    _prepare_input(payload)
    portfolio_context = _ask_operator_portfolio_context()
    if portfolio_context is not None:
        payload["operator_portfolio_context"] = portfolio_context
    payload["operator_valuation_context"] = _ask_operator_valuation_context()
    private_inputs = _private_dir(template_root, "PILOT_TEMPLATE_ROOT")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    completed = private_inputs / f"pilot-completed-{symbol.replace('.', '-')}-{stamp}.json"
    _write_local(completed, json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    result = run_local_investment_pilot(input_path=completed, output_root=output_root)
    print("\n分析完成：")
    print(json.dumps(_safe(result), ensure_ascii=False, indent=2))
    report_path = result.get("report_path")
    if report_path and sys.platform == "darwin":
        subprocess.run(["open", str(report_path)], check=False, timeout=5)
    print("\n下次分析另一个标的，只需双击同一个启动器。")
    return result



def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local candidate-driven IIOS pilot; non-canonical.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--wizard", action="store_true", help="run the simple guided investment workflow")
    modes.add_argument("--create-template", action="store_true")
    modes.add_argument("--input", help="run a completed private pilot input JSON")
    modes.add_argument("--replay-run", help="verify a prior bundle then recompute and compare decision-material fields")
    modes.add_argument("--check-run", help="read-only SHA-256 check of a local run bundle")
    parser.add_argument("--template-root", default=str(Path.home() / ".iios-private" / "local-pilot" / "inputs"))
    parser.add_argument("--output-root", default=str(Path.home() / ".iios-private" / "local-pilot" / "runs"))
    parser.add_argument("--company")
    parser.add_argument("--symbol")
    parser.add_argument("--market", default="CN-A")
    parser.add_argument("--as-of")
    parser.add_argument("--as-of-timestamp", help="optional explicit ISO 8601 cutoff instant with timezone")
    parser.add_argument("--position", default="0")
    parser.add_argument("--price")
    parser.add_argument("--price-date")
    parser.add_argument("--price-known-at")
    parser.add_argument("--price-source-claim")
    args = parser.parse_args(argv)
    try:
        if args.wizard:
            result = run_guided_wizard(template_root=args.template_root, output_root=args.output_root)
        elif args.create_template:
            required = {
                "--company": args.company, "--symbol": args.symbol, "--as-of": args.as_of,
                "--price": args.price, "--price-date": args.price_date,
                "--price-known-at": args.price_known_at, "--price-source-claim": args.price_source_claim,
            }
            missing = [key for key, value in required.items() if not value]
            if missing:
                parser.error("--create-template requires " + ", ".join(missing))
            result = create_pilot_template(
                company=args.company, symbol=args.symbol, market=args.market, as_of_date=args.as_of,
                current_position_pct=args.position, price=args.price, price_observation_date=args.price_date,
                price_known_at=args.price_known_at, price_source_claim=args.price_source_claim,
                template_root=args.template_root, as_of_timestamp=args.as_of_timestamp,
            )
        elif args.input:
            result = run_local_investment_pilot(input_path=args.input, output_root=args.output_root)
        elif args.check_run:
            result = verify_local_pilot_bundle(args.check_run)
        else:
            prior = Path(args.replay_run).expanduser().resolve()
            if not prior.is_dir():
                raise LocalInvestmentPilotError("REPLAY_RUN_DIRECTORY_REQUIRED")
            expected_root = Path(args.output_root).expanduser().resolve()
            if prior.parent != expected_root:
                raise LocalInvestmentPilotError("REPLAY_RUN_MUST_BE_DIRECT_CHILD_OF_OUTPUT_ROOT; set --output-root to its parent")
            result = run_local_investment_pilot(
                input_path=prior / "input.json", output_root=args.output_root, replay_of=prior.name
            )
        print(json.dumps(_safe(result), ensure_ascii=False, indent=2))
        return 0
    except (LocalInvestmentPilotError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
