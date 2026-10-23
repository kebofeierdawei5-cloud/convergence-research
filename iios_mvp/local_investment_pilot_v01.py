from __future__ import annotations

"""Minimal candidate-driven, non-canonical local IIOS pilot.

This is a practical trial path, not a second canonical engine. It uses the
existing research-intake validator and the existing IIOS return/entry-price
solver. Formal admission and canonical Decision code remain unchanged.
"""

import argparse
import copy
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
from typing import Any, Mapping
from urllib.parse import urlsplit

from .decision_kernel_v03 import evaluate_production_decision
from .decision_state_machine_v01 import MIE_POLICY_OPTIONAL_EXPLANATORY
from .local_pilot_portfolio_package_v01 import build_local_pilot_portfolio_package
from .operating_driver_forecast_v01 import evaluate_operating_driver_forecast, render_operating_driver_section
from .sotp_valuation_v01 import evaluate_sotp_valuation, render_sotp_valuation_section
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
EPS_MULTIPLE_VALUATION_SCHEMA = "IIOS-EPS-MULTIPLE-VALUATION-0.1"
EPS_MULTIPLE_VALUATION_METHOD = "EPS_PER_SHARE_X_PE_MULTIPLE"
EPS_EARNINGS_BRIDGE_SCHEMA = "IIOS-EPS-EARNINGS-BRIDGE-0.1"
EPS_EARNINGS_BRIDGE_METHOD = "B4_NET_PROFIT_PROXY_MINUS_NCI_PLUS_ADJUSTMENTS_DIVIDED_BY_DILUTED_SHARES"
EPS_EPS_MATCH_TOLERANCE = Decimal("0.005")
SHANGHAI = timezone(timedelta(hours=8))
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRICE_ASSURANCE = "OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED"
BUNDLE_FILENAMES = ("input.json", "analysis.json", "report.md")
RAW_RESEARCH_RESPONSE_FILENAME = "chatgpt_response_raw.txt"
LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA = "IIOS-LOCAL-RESEARCH-RESPONSE-PROVENANCE-0.1"
_RESEARCH_RESPONSE_PRESENT_STATUSES = {
    "CAPTURED_RAW_CHATGPT_RESPONSE",
    "INHERITED_FROM_VERIFIED_PRIOR_RUN",
}
_RESEARCH_RESPONSE_ABSENT_STATUSES = {
    "NOT_CAPTURED_DIRECT_OR_LEGACY_INPUT",
    "NOT_AVAILABLE_IN_LEGACY_PARENT_RUN",
}
REPLAY_COMPARISON_FIELDS = (
    "schema_version",
    "status",
    "case",
    "price_input",
    "evidence_register",
    "duplicate_evidence_ids",
    "untraceable_evidence_ids",
    "untraceable_evidence_fields",
    "referenced_evidence_ids",
    "unresolved_evidence_references",
    "after_cutoff_evidence_references",
    "uncertain_timing_evidence_references",
    "assessment",
    "forecast_valuation",
    "operating_driver_forecast",
    "valuation_transmission",
    "sotp_valuation",
    "eps_multiple_valuation",
    "eps_earnings_bridge",
    "operator_valuation_context",
    "valuation_model_consistency",
    "valuation_timing",
    "price_zone_sensitivity",
    "research_response_provenance",
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


def _fingerprint_bytes(content: bytes) -> dict[str, Any]:
    """Return SHA-256 and byte size for an immutable in-memory byte sequence."""
    return {"sha256": hashlib.sha256(content).hexdigest(), "byte_size": len(content)}


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
    allowed_names = set(BUNDLE_FILENAMES) | {RAW_RESEARCH_RESPONSE_FILENAME}
    unexpected_names = sorted(str(name) for name in set(manifest) - allowed_names)
    if unexpected_names:
        raise LocalInvestmentPilotError(
            "RUN_BUNDLE_HASH_MANIFEST_HAS_UNEXPECTED_FILES:" + ",".join(unexpected_names)
        )
    manifest_names = list(BUNDLE_FILENAMES)
    if RAW_RESEARCH_RESPONSE_FILENAME in manifest:
        manifest_names.append(RAW_RESEARCH_RESPONSE_FILENAME)
    for filename in manifest_names:
        expected = manifest.get(filename)
        if not isinstance(expected, Mapping):
            raise LocalInvestmentPilotError(f"RUN_BUNDLE_HASH_MISSING:{filename}")
        expected_hash = str(expected.get("sha256") or "")
        expected_size = expected.get("byte_size")
        if (
            not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
        ):
            raise LocalInvestmentPilotError(f"RUN_BUNDLE_HASH_RECORD_INVALID:{filename}")
        file_path = run_dir / filename
        if file_path.is_symlink() or not file_path.is_file():
            raise LocalInvestmentPilotError(f"RUN_BUNDLE_FILE_MISSING_OR_SYMLINK:{filename}")
        actual = _fingerprint_file(file_path)
        if actual != {"sha256": expected_hash, "byte_size": expected_size}:
            raise LocalInvestmentPilotError(f"RUN_BUNDLE_HASH_MISMATCH:{filename}")

    provenance = receipt.get("research_response_provenance")
    if RAW_RESEARCH_RESPONSE_FILENAME in manifest:
        if not isinstance(provenance, Mapping) or provenance.get("status") not in _RESEARCH_RESPONSE_PRESENT_STATUSES:
            raise LocalInvestmentPilotError("RUN_RESEARCH_RESPONSE_PROVENANCE_MISSING_OR_INVALID")
        response_fingerprint = manifest[RAW_RESEARCH_RESPONSE_FILENAME]
        if (
            provenance.get("file") != RAW_RESEARCH_RESPONSE_FILENAME
            or provenance.get("sha256") != response_fingerprint.get("sha256")
            or provenance.get("byte_size") != response_fingerprint.get("byte_size")
        ):
            raise LocalInvestmentPilotError("RUN_RESEARCH_RESPONSE_PROVENANCE_HASH_MISMATCH")
    elif isinstance(provenance, Mapping) and provenance.get("status") in _RESEARCH_RESPONSE_PRESENT_STATUSES:
        raise LocalInvestmentPilotError("RUN_RESEARCH_RESPONSE_FILE_MISSING_FROM_MANIFEST")
    elif provenance is not None and (
        not isinstance(provenance, Mapping)
        or provenance.get("schema_version") != LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA
        or provenance.get("status") not in _RESEARCH_RESPONSE_ABSENT_STATUSES
        or any(provenance.get(field) is not None for field in ("file", "sha256", "byte_size"))
    ):
        raise LocalInvestmentPilotError("RUN_RESEARCH_RESPONSE_PROVENANCE_INVALID")

    try:
        input_payload = json.loads((run_dir / "input.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalInvestmentPilotError("RUN_INPUT_UNREADABLE_FOR_RESPONSE_PROVENANCE") from exc
    input_provenance = input_payload.get("_local_research_response_provenance") if isinstance(input_payload, Mapping) else None
    if RAW_RESEARCH_RESPONSE_FILENAME in manifest:
        if (
            not isinstance(input_provenance, Mapping)
            or input_provenance.get("schema_version") != LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA
            or input_provenance.get("status") != "CAPTURED_RAW_CHATGPT_RESPONSE"
            or not isinstance(input_provenance.get("source_filename"), str)
            or not input_provenance.get("source_filename")
            or Path(input_provenance["source_filename"]).name != input_provenance["source_filename"]
            or "/" in input_provenance["source_filename"]
            or "\\" in input_provenance["source_filename"]
            or input_provenance.get("sha256") != manifest[RAW_RESEARCH_RESPONSE_FILENAME].get("sha256")
            or input_provenance.get("byte_size") != manifest[RAW_RESEARCH_RESPONSE_FILENAME].get("byte_size")
        ):
            raise LocalInvestmentPilotError("RUN_INPUT_RESEARCH_RESPONSE_PROVENANCE_MISMATCH")
    elif (
        isinstance(input_payload, Mapping)
        and "_local_research_response_provenance" in input_payload
        and input_provenance is not None
    ):
        # The field's presence with a non-null value is a claim even when malformed.
        # Only absent/null claims may follow the legacy no-capture path.
        raise LocalInvestmentPilotError("RUN_INPUT_CLAIMS_RESEARCH_RESPONSE_WITHOUT_CAPTURE")
    return dict(receipt), {name: dict(manifest[name]) for name in manifest_names}


def verify_local_pilot_bundle(run_path: str | Path) -> dict[str, Any]:
    """Read-only check of a run's input, analysis and report against its receipt."""
    receipt, manifest = _verify_run_bundle(run_path)
    return {
        "status": "PILOT_BUNDLE_HASH_CHECK_PASS",
        "pilot_id": receipt["pilot_id"],
        "hash_algorithm": "SHA-256",
        "verified_files": [
            {"name": name, "byte_size": manifest[name]["byte_size"], "sha256": manifest[name]["sha256"]}
            for name in (*BUNDLE_FILENAMES, *((RAW_RESEARCH_RESPONSE_FILENAME,) if RAW_RESEARCH_RESPONSE_FILENAME in manifest else ()))
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


def _assessment_status_for_report(section: Mapping[str, Any]) -> str:
    """Show both the conservative gate status and any non-canonical source label."""
    status = str(section.get("status") or "UNKNOWN")
    source_label = str(section.get("status_input") or "").strip().upper()
    if source_label and source_label != status:
        return f"{status}（输入标签 {source_label}；已按本地决策枚举归一化）"
    return status


def _items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        rendered = _humanize_item(item) if isinstance(item, Mapping) else str(item).strip()
        if rendered:
            result.append(rendered)
    return result


def _is_identifiable_evidence_text(value: Any) -> bool:
    """Reject blank and placeholder-only source locators/context from resolving citations."""
    raw = str(value or "").strip()
    if not raw:
        return False
    normalized = re.sub(r"[^A-Z0-9]+", "_", raw.upper()).strip("_")
    placeholders = {
        "UNKNOWN", "N_A", "NA", "NONE", "NULL", "NOT_IDENTIFIABLE",
        "UNIDENTIFIABLE", "UNSPECIFIED", "NOT_SPECIFIED", "TBD", "NOT_PROVIDED",
        "NOT_AVAILABLE", "UNAVAILABLE", "UNVERIFIED", "UNCONFIRMED", "NOT_KNOWN",
        "UNKNOWN_SOURCE", "SOURCE_UNKNOWN", "NO_SOURCE", "NO_LOCATOR", "MISSING",
        "UNRESOLVED", "NOT_ADMITTED", "NOT_VERIFIED",
    }
    chinese_placeholders = {
        "未知", "不详", "不明确", "未提供", "未提供标题", "未提供事实摘要",
        "未提供依据", "无依据", "暂无依据", "概率未知", "来源未知", "缺失", "待补充", "待核实",
        "未命名价值驱动因素",
    }
    return normalized not in placeholders and raw not in chinese_placeholders


def _risk_item_severity_is_identifiable(value: Any) -> bool:
    """Only explicit, recognized ordinal severity values qualify for a complete risk row."""
    raw = str(value or "").strip()
    normalized = re.sub(r"[^A-Z0-9]+", "_", raw.upper()).strip("_")
    allowed = {
        "CRITICAL", "VERY_HIGH", "HIGH", "MEDIUM_HIGH",
        "MEDIUM", "MEDIUM_LOW", "LOW", "VERY_LOW",
    }
    chinese_aliases = {"极高", "高", "中高", "中", "中低", "低"}
    return normalized in allowed or raw in chinese_aliases


def _risk_item_is_identifiable(item: Any) -> bool:
    """Require a stable ID, recognized severity, descriptive detail and monitoring trigger."""
    if not isinstance(item, Mapping):
        return _is_identifiable_evidence_text(item)
    identity_fields = ("name", "title", "driver", "description", "summary")
    detail_fields = (
        "summary", "description", "rationale", "operating_impact", "valuation_mechanism"
    )
    has_identity = any(_is_identifiable_evidence_text(item.get(key)) for key in identity_fields)
    has_detail = any(_is_identifiable_evidence_text(item.get(key)) for key in detail_fields)
    has_monitoring_trigger = _is_identifiable_evidence_text(
        item.get("monitoring_trigger") or item.get("trigger")
    )
    has_risk_id = _is_identifiable_evidence_text(item.get("risk_id"))
    has_severity = _risk_item_severity_is_identifiable(item.get("severity"))
    return has_identity and has_detail and has_monitoring_trigger and has_risk_id and has_severity


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
        ("condition", "条件"), ("measurement", "验证方法"), ("effect", "影响"),
        ("trigger", "触发条件"), ("metric", "监控指标"), ("threshold", "触发阈值"),
        ("decision_effect", "决策影响"),
        ("summary", "摘要"), ("basis", "依据"), ("rationale", "理由"),
        ("description", "说明"), ("monitoring_trigger", "监控触发条件"),
        ("operating_impact", "经营影响"), ("valuation_mechanism", "估值传导机制"),
    ):
        if item.get(key) not in (None, "") and not (key == "description" and name == str(item.get(key))):
            parts.append(f"{label}：{' '.join(str(item[key]).splitlines()).strip()}")
    refs = item.get("evidence_refs")
    if isinstance(refs, list) and refs:
        parts.append("证据引用：" + "、".join(str(ref) for ref in refs))
    if not parts:
        return "；".join(f"{key}={_humanize_item(val)}" for key, val in item.items())
    # These are labeled fields, not separate paragraphs; join them with semicolons
    # so sentence-final punctuation in source prose does not become doubled periods.
    return "；".join(parts)


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


def _link_b4_cost_ratio_assumptions(
    raw_driver_forecast: Any, forecast_valuation: Mapping[str, Any]
) -> tuple[Any, list[dict[str, Any]]]:
    """Reuse the exact scenario COGS ratio already stated in valuation assumptions.

    This is a same-case assumption link, not a new estimate or a source-fact upgrade.
    Explicit B4 values supplied by the operator/model are never overwritten.
    """
    if not isinstance(raw_driver_forecast, Mapping):
        return raw_driver_forecast, []
    assumptions = forecast_valuation.get("assumptions")
    assumptions = assumptions if isinstance(assumptions, list) else []
    candidates: dict[str, list[dict[str, Any]]] = {name: [] for name in SCENARIOS}
    for assumption in assumptions:
        if not isinstance(assumption, Mapping):
            continue
        data_class = str(assumption.get("data_class") or "UNKNOWN").strip().upper()
        if data_class not in {"ANALYST_ASSUMPTION", "ISSUER_FORECAST"}:
            continue
        values = assumption.get("values")
        if not isinstance(values, Mapping):
            continue
        for scenario_name in SCENARIOS:
            key = f"{scenario_name}_cost_of_revenue_ratio"
            if values.get(key) not in (None, ""):
                candidates[scenario_name].append({
                    "value": values[key],
                    "data_class": data_class,
                    "assumption_id": str(assumption.get("assumption_id") or ""),
                    "assumption_name": str(assumption.get("name") or ""),
                    "basis": str(assumption.get("basis") or "").strip(),
                })

    linked = dict(raw_driver_forecast)
    scenarios = linked.get("scenarios")
    scenarios = dict(scenarios) if isinstance(scenarios, Mapping) else {}
    links: list[dict[str, Any]] = []
    for scenario_name in SCENARIOS:
        row = scenarios.get(scenario_name)
        if not isinstance(row, Mapping):
            continue
        scenario_row = dict(row)
        if "cost_of_revenue_ratio" in scenario_row:
            continue
        options = candidates[scenario_name]
        unusable_basis_options = [
            item for item in options
            if not _is_identifiable_evidence_text(item.get("basis"))
        ]
        options = [
            item for item in options
            if _is_identifiable_evidence_text(item.get("basis"))
        ]
        for unusable in unusable_basis_options:
            links.append({
                "scenario": scenario_name,
                "field": "cost_of_revenue_ratio",
                "status": "ASSUMPTION_BASIS_NOT_IDENTIFIABLE_NOT_LINKED",
                "source_assumption_id": unusable["assumption_id"] or None,
                "source_assumption_name": unusable["assumption_name"] or None,
                "basis": unusable["basis"] or None,
                "issues": ["ASSUMPTION_BASIS_NOT_IDENTIFIABLE"],
            })
        distinct_values = {str(item["value"]) for item in options}
        if len(distinct_values) != 1:
            if len(distinct_values) > 1:
                links.append({
                    "scenario": scenario_name,
                    "field": "cost_of_revenue_ratio",
                    "status": "CONFLICTING_VALUATION_ASSUMPTIONS_NOT_LINKED",
                    "candidate_values": sorted(distinct_values),
                })
            continue
        source = options[0]
        value = source["value"]
        source_label = " ".join(
            part for part in (source["assumption_id"], source["assumption_name"]) if part
        ) or "forecast_valuation.assumptions"
        basis = (
            f"复用估值假设 {source_label} 中同一情景的成本率 {value}；"
            "不另行估计，以保持 B4 与主估值桥的假设一致。"
        )
        if source["basis"]:
            basis += f" 原假设依据：{source['basis']}"
        scenario_row["cost_of_revenue_ratio"] = {
            "value": value,
            "unit": "ratio",
            "data_class": source["data_class"],
            "basis": basis,
            "evidence_refs": [],
            "note": "由同一主估值情景假设交叉引用；不是实际结果或额外独立证据。",
        }
        scenarios[scenario_name] = scenario_row
        links.append({
            "scenario": scenario_name,
            "field": "cost_of_revenue_ratio",
            "status": "LINKED_SAME_SCENARIO_ASSUMPTION",
            "source_assumption_id": source["assumption_id"] or None,
            "source_assumption_name": source["assumption_name"] or None,
            "value": str(value),
            "data_class": source["data_class"],
        })
    linked["scenarios"] = scenarios
    return linked, links


def _reconcile_b4_valuation_bridge(
    driver_forecast: Mapping[str, Any], forecast_valuation: Mapping[str, Any]
) -> dict[str, Any]:
    """Cross-check overlapping aggregate operating metrics without conflating FCF definitions."""
    driver_scenarios = driver_forecast.get("scenarios")
    driver_scenarios = driver_scenarios if isinstance(driver_scenarios, Mapping) else {}
    valuation_scenarios = forecast_valuation.get("scenarios")
    valuation_scenarios = valuation_scenarios if isinstance(valuation_scenarios, Mapping) else {}
    if not any(
        isinstance(row, Mapping) and isinstance(row.get("operating_financial_bridge"), Mapping)
        for row in valuation_scenarios.values()
    ):
        return {
            "schema_version": "IIOS-B4-VALUATION-BRIDGE-RECONCILIATION-0.1",
            "status": "NOT_PROVIDED",
            "scenarios": {},
            "excluded_metrics": [],
            "formal_admission_created": False,
            "decision_authority": False,
        }
    field_pairs = (
        ("revenue_cny", "revenue_cny"),
        ("variable_cost_cny", "cost_of_revenue_cny"),
        ("contribution_after_variable_cost_cny", "gross_profit_cny"),
        ("fixed_cash_opex_cny", "fixed_cash_opex_cny"),
        ("ebitda_cny", "ebitda_cny"),
        ("depreciation_amortization_cny", "depreciation_amortization_cny"),
        ("ebit_cny", "ebit_cny"),
        ("finance_cost_cny", "finance_cost_cny"),
        ("profit_before_tax_cny", "pretax_profit_cny"),
        ("tax_rate", "tax_rate"),
        ("net_profit_cny", "net_profit_proxy_cny"),
        ("cash_capex_cny", "cash_capex_cny"),
        ("change_working_capital_cny", "change_working_capital_cny"),
    )
    scenario_results: dict[str, Any] = {}
    all_match = True
    any_mismatch = False
    for scenario_name in SCENARIOS:
        driver_row = driver_scenarios.get(scenario_name)
        driver_row = driver_row if isinstance(driver_row, Mapping) else {}
        valuation_row = valuation_scenarios.get(scenario_name)
        valuation_row = valuation_row if isinstance(valuation_row, Mapping) else {}
        bridge = valuation_row.get("operating_financial_bridge")
        bridge = bridge if isinstance(bridge, Mapping) else {}
        checks: list[dict[str, Any]] = []
        for driver_field, valuation_field in field_pairs:
            left, right = driver_row.get(driver_field), bridge.get(valuation_field)
            if left in (None, "") or right in (None, ""):
                checks.append({
                    "driver_field": driver_field, "valuation_field": valuation_field,
                    "status": "NOT_COMPARABLE", "driver_value": left, "valuation_value": right,
                })
                all_match = False
                continue
            try:
                left_num, right_num = Decimal(str(left)), Decimal(str(right))
            except (InvalidOperation, ValueError):
                left_num = right_num = None
            if left_num is None or right_num is None:
                check_status = "NOT_COMPARABLE"
                all_match = False
            else:
                tolerance = Decimal("0.000001") if driver_field == "tax_rate" else Decimal("1")
                check_status = "MATCH" if abs(left_num - right_num) <= tolerance else "MISMATCH"
                if check_status == "MISMATCH":
                    any_mismatch = True
                    all_match = False
            checks.append({
                "driver_field": driver_field, "valuation_field": valuation_field,
                "status": check_status, "driver_value": left, "valuation_value": right,
            })
        scenario_results[scenario_name] = {
            "status": (
                "MISMATCH" if any(item["status"] == "MISMATCH" for item in checks)
                else "MATCH" if checks and all(item["status"] == "MATCH" for item in checks)
                else "PARTIAL"
            ),
            "checks": checks,
        }
    status = "MISMATCH" if any_mismatch else "MATCH" if all_match else "PARTIAL"
    return {
        "schema_version": "IIOS-B4-VALUATION-BRIDGE-RECONCILIATION-0.1",
        "status": status,
        "scenarios": scenario_results,
        "excluded_metrics": [{
            "field": "free_cash_flow_proxy_cny",
            "reason": (
                "B4 使用 EBIT 税后现金流口径（unlevered proxy）；主估值 financial bridge "
                "使用 net_profit_proxy + D&A − CapEx − 营运资金（含融资成本影响）。"
                "两者口径不同，不应要求数值相等。"
            ),
        }],
        "formal_admission_created": False,
        "decision_authority": False,
    }


PRIMARY_MODEL_FAMILIES = frozenset({
    "EPS_MULTIPLE", "FCF_DCF", "DDM", "SOTP", "RNPV", "OTHER", "UNKNOWN",
})
_B5_PROJECT_TRANSMISSION_ACCEPTED = frozenset({
    "APPLIED_TO_PER_SHARE_SCENARIOS",
    "CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT",
})


def _normalize_model_family(value: Any) -> str:
    family = str(value or "UNKNOWN").strip().upper()
    return family if family in PRIMARY_MODEL_FAMILIES else "UNKNOWN"


def _infer_model_family_from_name(value: Any) -> str:
    """Infer only when the model name exposes a known family marker; never trust family self-label alone."""
    name = str(value or "").strip().upper()
    if not name:
        return "UNKNOWN"
    words = set(re.findall(r"[A-Z0-9]+", name))
    normalized = re.sub(r"[^A-Z0-9]+", " ", name).strip()
    if "SOTP" in words or "SUM OF THE PARTS" in normalized or "SUM OF PARTS" in normalized:
        return "SOTP"
    if "RNPV" in words or "R NPV" in normalized or "RISK ADJUSTED NPV" in normalized:
        return "RNPV"
    if "DDM" in words or "DIVIDEND DISCOUNT" in normalized:
        return "DDM"
    if "FCF_DCF" in name or ("FCF" in words and "DCF" in words):
        return "FCF_DCF"
    if "DCF" in words or "DISCOUNTED CASH FLOW" in normalized:
        return "FCF_DCF"
    if "OTHER" in words and len(words) <= 3:
        return "OTHER"
    if (
        "EPS_MULTIPLE" in name
        or ("EPS" in words and ("PE" in words or "MULTIPLE" in words or re.search(r"\bP\s*/\s*E\b", name)))
    ):
        return "EPS_MULTIPLE"
    return "UNKNOWN"


def _eps_source_domain_class_matches(source: Mapping[str, Any]) -> bool:
    """Return true only for a supported primary class matched to its official domain."""
    source_class = str(source.get("source_class") or "").strip().upper()
    domain_status = str(source.get("source_domain_class_status") or "").strip().upper()
    return (
        source_class == "EXCHANGE_PRIMARY"
        and domain_status == "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    ) or (
        source_class == "REGULATOR_PRIMARY"
        and domain_status == "OFFICIAL_REGULATOR_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    )


def _evaluate_eps_earnings_bridge(
    raw: Any, *, selected_model_family: Any, expected_forecast_period: Any,
    expected_terminal_date: Any, expected_currency: Any,
    operating_driver_forecast: Mapping[str, Any],
    valuation_transmission: Mapping[str, Any],
    operator_baseline_includes_project: bool | None,
    evidence_register: list[dict[str, Any]],
    unresolved_evidence_ids: list[str] | set[str] | None = None,
    after_cutoff_evidence_ids: list[str] | set[str] | None = None,
    uncertain_timing_evidence_ids: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Reconcile forecast EPS to B4 company-wide net-profit proxy and diluted shares."""
    def result(status: str, scenarios: Mapping[str, Any] | None = None,
               issues: list[str] | None = None, *, period: str | None = None,
               terminal_date: str | None = None, currency: str | None = None) -> dict[str, Any]:
        clean_issues = list(dict.fromkeys(str(item) for item in (issues or []) if str(item).strip()))
        eligible = status in {
            "CALCULATED", "ASSUMPTION_ONLY", "MIXED_CALCULATED_AND_ASSUMPTION_ONLY",
        }
        return {
            "schema_version": EPS_EARNINGS_BRIDGE_SCHEMA,
            "status": status,
            "method": EPS_EARNINGS_BRIDGE_METHOD,
            "forecast_period": period,
            "valuation_terminal_date": terminal_date,
            "currency": currency,
            "scenarios": dict(scenarios or {}),
            "issues": clean_issues,
            "primary_eps_price_calculation_eligible": eligible,
            "formal_evidence_pit_admission_created": False,
            "formal_forecast_admission_created": False,
            "decision_authority": False,
        }

    if str(selected_model_family or "UNKNOWN").strip().upper() != "EPS_MULTIPLE":
        return result("NOT_SELECTED")
    currency = str(expected_currency or "").strip().upper()
    period = str(expected_forecast_period or "").strip().upper()
    terminal_date = str(expected_terminal_date or "").strip()
    if currency not in {"CNY", "HKD"}:
        return result("NOT_LINKED", issues=[f"EPS_BRIDGE_CURRENCY_NOT_SUPPORTED:{currency or 'UNKNOWN'}"])
    if not isinstance(raw, Mapping) or raw.get("schema_version") != EPS_MULTIPLE_VALUATION_SCHEMA:
        return result("NOT_LINKED", issues=["EPS_BRIDGE_INPUT_SCHEMA_MISSING_OR_INVALID"])
    if not _is_identifiable_evidence_text(period) or not _is_identifiable_evidence_text(terminal_date):
        return result("NOT_LINKED", issues=["EPS_BRIDGE_FORECAST_PERIOD_OR_TERMINAL_DATE_UNKNOWN"])
    inputs = raw.get("scenarios")
    if not isinstance(inputs, Mapping) or set(inputs) != set(SCENARIOS):
        return result("NOT_LINKED", issues=["EPS_BRIDGE_REQUIRES_BEAR_BASE_BULL"])

    if currency == "HKD":
        # B4 monetary outputs are denominated in CNY and no FX-conversion contract
        # exists in this pilot. Preserve explicit HKD analyst assumptions without
        # pretending the CNY company-wide earnings proxy can produce HKD EPS.
        assumption_rows: dict[str, Any] = {}
        for name in SCENARIOS:
            row = inputs.get(name)
            eps_raw = row.get("eps_per_share") if isinstance(row, Mapping) else None
            if not isinstance(eps_raw, Mapping):
                assumption_rows[name] = {
                    "status": "NOT_LINKED",
                    "issues": [f"{name.upper()}_EPS_OBJECT_REQUIRED"],
                    "declared_eps_per_share": None,
                    "calculated_eps_per_share": None,
                    "eps_match": False,
                    "formal_evidence_pit_admission": False,
                }
                continue
            try:
                if str(eps_raw.get("data_class") or "").strip().upper() != "ANALYST_ASSUMPTION":
                    raise ValueError(f"{name.upper()}_HKD_ISSUER_EPS_BRIDGE_REQUIRES_FX_CONTRACT")
                if str(eps_raw.get("unit") or "").strip().lower() != "hkd/share":
                    raise ValueError(f"{name.upper()}_EPS_UNIT_MISMATCH")
                declared = _positive(eps_raw.get("value"), f"{name.upper()}_DECLARED_EPS")
                basis = str(eps_raw.get("basis") or "").strip()
                derivation = str(eps_raw.get("assumption_derivation") or "").strip()
                if not _is_identifiable_evidence_text(basis) or not _is_identifiable_evidence_text(derivation):
                    raise ValueError(f"{name.upper()}_ANALYST_ASSUMPTION_DERIVATION_NOT_IDENTIFIABLE")
                assumption_rows[name] = {
                    "status": "ASSUMPTION_ONLY",
                    "declared_eps_per_share": format(declared, "f"),
                    "calculated_eps_per_share": None,
                    "absolute_difference_per_share": None,
                    "rounding_tolerance_per_share": format(EPS_EPS_MATCH_TOLERANCE, "f"),
                    "eps_match": None,
                    "derivation_class": "ANALYST_ASSUMPTION",
                    "assumption_derivation": derivation,
                    "basis": basis,
                    "evidence_refs": list(eps_raw.get("evidence_refs") or []),
                    "note": "B4 金额口径为 CNY，当前没有可用的 FX 传导合同；保留 HKD 分析假设，不伪造 CNY 到 HKD 的 EPS 桥。",
                    "formal_evidence_pit_admission": False,
                }
            except (ValueError, LocalInvestmentPilotError) as exc:
                assumption_rows[name] = {
                    "status": "NOT_LINKED",
                    "issues": [str(exc)],
                    "declared_eps_per_share": None,
                    "calculated_eps_per_share": None,
                    "absolute_difference_per_share": None,
                    "rounding_tolerance_per_share": format(EPS_EPS_MATCH_TOLERANCE, "f"),
                    "eps_match": False,
                    "formal_evidence_pit_admission": False,
                }
        hkd_statuses = [str((assumption_rows.get(name) or {}).get("status")) for name in SCENARIOS]
        if all(value == "ASSUMPTION_ONLY" for value in hkd_statuses):
            return {
                **result("ASSUMPTION_ONLY", assumption_rows, period=period, terminal_date=terminal_date, currency=currency),
                "summary": "HKD EPS 仅保留为明确的分析假设；B4 的 CNY 金额未经过未经授权的汇率换算。",
            }
        return {
            **result("NOT_LINKED", assumption_rows, [
                "HKD_COMPANY_EPS_BRIDGE_UNAVAILABLE_WITHOUT_EXPLICIT_FX_CONTRACT"
            ], period=period, terminal_date=terminal_date, currency=currency),
            "summary": "HKD 公司盈利桥需要显式、期间匹配且可审计的汇率合同；不把 CNY 盈利代理直接除以 HKD 股数。",
        }

    evidence = {
        str(item.get("source_id")): item for item in evidence_register
        if isinstance(item, Mapping) and item.get("source_id")
    }
    unresolved = set(unresolved_evidence_ids or [])
    after = set(after_cutoff_evidence_ids or [])
    uncertain = set(uncertain_timing_evidence_ids or [])

    def normalized_refs(raw_measure: Mapping[str, Any], *, label: str, data_class: str) -> list[str]:
        refs_raw = raw_measure.get("evidence_refs") or []
        if not isinstance(refs_raw, list):
            raise ValueError(f"{label}_EVIDENCE_REFS_INVALID")
        refs = list(dict.fromkeys(str(ref).strip() for ref in refs_raw if str(ref).strip()))
        if data_class == "ISSUER_FORECAST" and not refs:
            raise ValueError(f"{label}_ISSUER_FORECAST_EVIDENCE_REQUIRED")
        for ref in refs:
            source = evidence.get(ref)
            if (
                source is None or ref in unresolved or ref in after or ref in uncertain
                or source.get("time_status") != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
            ):
                raise ValueError(f"{label}_EVIDENCE_NOT_CUTOFF_COMPATIBLE:{ref}")
            if data_class == "ISSUER_FORECAST" and not _eps_source_domain_class_matches(source):
                raise ValueError(f"{label}_ISSUER_FORECAST_SOURCE_CLASS_OR_DOMAIN_NOT_VERIFIED:{ref}")
        return refs

    def typed_measure(
        raw_measure: Any, *, label: str, required_unit: str, expected_period: str,
        required_measure: str | None = None, signed: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(raw_measure, Mapping):
            raise ValueError(f"{label}_OBJECT_REQUIRED")
        if str(raw_measure.get("unit") or "").strip().lower() != required_unit.lower():
            raise ValueError(f"{label}_UNIT_MISMATCH")
        measure_name = str(raw_measure.get("measure") or "").strip().upper()
        if required_measure and measure_name != required_measure:
            raise ValueError(f"{label}_MEASURE_MISMATCH:{measure_name or 'UNKNOWN'}")
        if str(raw_measure.get("forecast_period") or "").strip().upper() != expected_period:
            raise ValueError(f"{label}_FORECAST_PERIOD_MISMATCH")
        data_class = str(raw_measure.get("data_class") or "").strip().upper()
        if data_class not in {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}:
            raise ValueError(f"{label}_DATA_CLASS_INVALID")
        basis = str(raw_measure.get("basis") or "").strip()
        if not _is_identifiable_evidence_text(basis):
            raise ValueError(f"{label}_BASIS_NOT_IDENTIFIABLE")
        number = (
            _number(raw_measure.get("value"), label)
            if signed or required_measure == "NON_CONTROLLING_INTERESTS_AFTER_TAX"
            else _positive(raw_measure.get("value"), label)
        )
        refs = normalized_refs(raw_measure, label=label, data_class=data_class)
        return {
            "value": format(number, "f"),
            "unit": required_unit,
            "measure": measure_name or required_measure,
            "data_class": data_class,
            "basis": basis,
            "evidence_refs": refs,
            "forecast_period": expected_period,
            "note": str(raw_measure.get("note") or ""),
            "formal_evidence_pit_admission": False,
        }

    driver_scenarios = operating_driver_forecast.get("scenarios")
    driver_scenarios = driver_scenarios if isinstance(driver_scenarios, Mapping) else {}
    driver_scope = str(operating_driver_forecast.get("scope") or "UNKNOWN").strip().upper()
    b5_status = str(valuation_transmission.get("status") or "UNKNOWN").strip().upper()
    scenario_outputs: dict[str, Any] = {}
    issues: list[str] = []
    for name in SCENARIOS:
        try:
            row = inputs[name]
            if not isinstance(row, Mapping):
                raise ValueError(f"{name.upper()}_EPS_BRIDGE_SCENARIO_OBJECT_REQUIRED")
            eps_raw = row.get("eps_per_share")
            if not isinstance(eps_raw, Mapping):
                raise ValueError(f"{name.upper()}_EPS_OBJECT_REQUIRED")
            declared_class = str(eps_raw.get("data_class") or "").strip().upper()
            if declared_class not in {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}:
                raise ValueError(f"{name.upper()}_EPS_DATA_CLASS_INVALID")
            eps_basis = str(eps_raw.get("basis") or "").strip()
            if not _is_identifiable_evidence_text(eps_basis):
                raise ValueError(f"{name.upper()}_EPS_BASIS_NOT_IDENTIFIABLE")
            if str(eps_raw.get("unit") or "").strip().lower() != f"{currency}/share".lower():
                raise ValueError(f"{name.upper()}_EPS_UNIT_MISMATCH")
            declared_eps = _positive(eps_raw.get("value"), f"{name.upper()}_DECLARED_EPS")
            eps_refs = normalized_refs(eps_raw, label=f"{name.upper()}_EPS", data_class=declared_class)
            raw_bridge = eps_raw.get("earnings_bridge")
            if raw_bridge is None:
                derivation = str(eps_raw.get("assumption_derivation") or "").strip()
                if declared_class == "ANALYST_ASSUMPTION" and _is_identifiable_evidence_text(derivation):
                    scenario_outputs[name] = {
                        "status": "ASSUMPTION_ONLY",
                        "declared_eps_per_share": format(declared_eps, "f"),
                        "calculated_eps_per_share": None,
                        "absolute_difference_per_share": None,
                        "rounding_tolerance_per_share": format(EPS_EPS_MATCH_TOLERANCE, "f"),
                        "eps_match": None,
                        "derivation_class": "ANALYST_ASSUMPTION",
                        "assumption_derivation": derivation,
                        "basis": eps_basis,
                        "evidence_refs": eps_refs,
                        "note": "未提供可复核的 B4 净利润归属桥与同期间加权平均稀释股数；该 EPS 仅作为明确标记的分析假设。",
                        "formal_evidence_pit_admission": False,
                    }
                    continue
                if declared_class == "ISSUER_FORECAST":
                    raise ValueError(f"{name.upper()}_ISSUER_FORECAST_EARNINGS_BRIDGE_REQUIRED")
                raise ValueError(f"{name.upper()}_ANALYST_ASSUMPTION_DERIVATION_NOT_IDENTIFIABLE")

            if not isinstance(raw_bridge, Mapping):
                raise ValueError(f"{name.upper()}_EPS_EARNINGS_BRIDGE_OBJECT_INVALID")
            if raw_bridge.get("schema_version") != EPS_EARNINGS_BRIDGE_SCHEMA:
                raise ValueError(f"{name.upper()}_EPS_EARNINGS_BRIDGE_SCHEMA_MISMATCH")
            if str(raw_bridge.get("calculation_method") or "").strip().upper() != EPS_EARNINGS_BRIDGE_METHOD:
                raise ValueError(f"{name.upper()}_EPS_EARNINGS_BRIDGE_METHOD_UNSUPPORTED")
            if str(raw_bridge.get("forecast_period") or "").strip().upper() != period:
                raise ValueError(f"{name.upper()}_EPS_BRIDGE_FORECAST_PERIOD_MISMATCH")
            if str(raw_bridge.get("valuation_terminal_date") or "").strip() != terminal_date:
                raise ValueError(f"{name.upper()}_EPS_BRIDGE_TERMINAL_DATE_MISMATCH")
            if str(raw_bridge.get("scope") or "").strip().upper() != "COMPANY_WIDE":
                raise ValueError(f"{name.upper()}_EPS_BRIDGE_SCOPE_MUST_BE_COMPANY_WIDE")
            if driver_scope != "COMPANY_WIDE":
                raise ValueError(f"{name.upper()}_EPS_BRIDGE_CANNOT_USE_NON_COMPANY_WIDE_B4:{driver_scope}")
            if str(operating_driver_forecast.get("forecast_period") or "").strip().upper() != period:
                raise ValueError(f"{name.upper()}_B4_EPS_BRIDGE_PERIOD_MISMATCH")
            driver_row = driver_scenarios.get(name)
            if not isinstance(driver_row, Mapping) or driver_row.get("financial_outputs_decision_usable") is not True:
                raise ValueError(f"{name.upper()}_B4_COMPANY_WIDE_NET_PROFIT_PROXY_NOT_USABLE")
            try:
                b4_net_profit_proxy = _positive(driver_row.get("net_profit_cny"), f"{name.upper()}_B4_NET_PROFIT_PROXY")
            except LocalInvestmentPilotError:
                raise ValueError(f"{name.upper()}_B4_NET_PROFIT_PROXY_UNKNOWN_OR_NONPOSITIVE")

            project_treatment = str(raw_bridge.get("project_profit_treatment") or "").strip().upper()
            if project_treatment not in {
                "INCLUDED_IN_COMPANY_WIDE_BASELINE",
                "EXCLUDED_FROM_COMPANY_WIDE_BASELINE",
                "NO_PROJECT_INCREMENTAL_ADJUSTMENT",
            }:
                raise ValueError(f"{name.upper()}_PROJECT_PROFIT_TREATMENT_NOT_IDENTIFIABLE")
            if project_treatment == "INCLUDED_IN_COMPANY_WIDE_BASELINE":
                if operator_baseline_includes_project is not True:
                    raise ValueError(f"{name.upper()}_PROJECT_BASELINE_INCLUSION_NOT_OPERATOR_CONFIRMED")
                if b5_status == "APPLIED_TO_PER_SHARE_SCENARIOS":
                    raise ValueError(f"{name.upper()}_PROJECT_INCREMENTAL_PROFIT_DOUBLE_COUNT_RISK")
            elif project_treatment == "EXCLUDED_FROM_COMPANY_WIDE_BASELINE":
                if operator_baseline_includes_project is not False:
                    raise ValueError(f"{name.upper()}_PROJECT_BASELINE_EXCLUSION_NOT_OPERATOR_CONFIRMED")
                if b5_status not in {"APPLIED_TO_PER_SHARE_SCENARIOS", "PENDING_VALIDATION"}:
                    raise ValueError(f"{name.upper()}_PROJECT_INCREMENTAL_NOT_TRANSMITTED_FROM_EXCLUDED_BASELINE")
            elif b5_status == "APPLIED_TO_PER_SHARE_SCENARIOS":
                raise ValueError(f"{name.upper()}_PROJECT_TREATMENT_CONTRADICTS_B5_INCREMENT")

            nci = typed_measure(
                raw_bridge.get("non_controlling_interests_after_tax"),
                label=f"{name.upper()}_NON_CONTROLLING_INTERESTS",
                required_unit=currency,
                expected_period=period,
                required_measure="NON_CONTROLLING_INTERESTS_AFTER_TAX",
                signed=False,
            )
            other_adjustment = typed_measure(
                raw_bridge.get("other_after_tax_attribution_adjustment"),
                label=f"{name.upper()}_OTHER_AFTER_TAX_ATTRIBUTION_ADJUSTMENT",
                required_unit=currency,
                expected_period=period,
                required_measure="OTHER_AFTER_TAX_ATTRIBUTION_ADJUSTMENT",
                signed=True,
            )
            shares = typed_measure(
                raw_bridge.get("diluted_shares"),
                label=f"{name.upper()}_WEIGHTED_AVERAGE_DILUTED_SHARES",
                required_unit="shares",
                expected_period=period,
                required_measure="WEIGHTED_AVERAGE_DILUTED_SHARES",
                signed=False,
            )
            if _number(nci["value"], f"{name.upper()}_NCI") < 0:
                raise ValueError(f"{name.upper()}_NON_CONTROLLING_INTERESTS_MUST_BE_NONNEGATIVE")
            if b5_status in {"APPLIED_TO_PER_SHARE_SCENARIOS", "CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT"}:
                b5_rows = valuation_transmission.get("scenarios")
                b5_rows = b5_rows if isinstance(b5_rows, Mapping) else {}
                b5_row = b5_rows.get(name)
                b5_row = b5_row if isinstance(b5_row, Mapping) else {}
                b5_shares = b5_row.get("diluted_shares")
                if not isinstance(b5_shares, Mapping) or b5_shares.get("value") in (None, ""):
                    raise ValueError(f"{name.upper()}_B5_DILUTED_SHARES_NOT_RECONCILED")
                if _positive(b5_shares.get("value"), f"{name.upper()}_B5_DILUTED_SHARES") != _positive(shares["value"], f"{name.upper()}_EPS_DILUTED_SHARES"):
                    raise ValueError(f"{name.upper()}_EPS_B5_DILUTED_SHARE_DENOMINATOR_MISMATCH")

            nci_value = _number(nci["value"], f"{name.upper()}_NCI")
            other_value = _number(other_adjustment["value"], f"{name.upper()}_OTHER_ADJUSTMENT")
            attributable_net_profit = b4_net_profit_proxy - nci_value + other_value
            if attributable_net_profit <= 0:
                raise ValueError(f"{name.upper()}_NET_PROFIT_ATTRIBUTABLE_TO_LISTED_SHAREHOLDERS_NOT_POSITIVE")
            share_count = _positive(shares["value"], f"{name.upper()}_DILUTED_SHARES")
            calculated_eps = attributable_net_profit / share_count
            difference = abs(calculated_eps - declared_eps)
            eps_match = difference <= EPS_EPS_MATCH_TOLERANCE
            scenario_status = "CALCULATED" if eps_match else "EPS_MISMATCH"
            scenario_outputs[name] = {
                "status": scenario_status,
                "forecast_period": period,
                "valuation_terminal_date": terminal_date,
                "scope": "COMPANY_WIDE",
                "project_profit_treatment": project_treatment,
                "b4_net_profit_proxy_cny": format(b4_net_profit_proxy, "f"),
                "non_controlling_interests": nci,
                "other_after_tax_attribution_adjustment": other_adjustment,
                "net_profit_attributable_to_listed_shareholders": {
                    "value": format(attributable_net_profit, "f"),
                    "unit": currency,
                    "measure": "NET_PROFIT_ATTRIBUTABLE_TO_LISTED_COMPANY_SHAREHOLDERS",
                    "formula": "B4_NET_PROFIT_PROXY - NON_CONTROLLING_INTERESTS + OTHER_AFTER_TAX_ATTRIBUTION_ADJUSTMENT",
                    "arithmetic": f"{b4_net_profit_proxy} - {nci_value} + ({other_value}) = {attributable_net_profit}",
                },
                "diluted_shares": shares,
                "declared_eps_per_share": format(declared_eps, "f"),
                "calculated_eps_per_share": format(calculated_eps, "f"),
                "absolute_difference_per_share": format(difference, "f"),
                "rounding_tolerance_per_share": format(EPS_EPS_MATCH_TOLERANCE, "f"),
                "eps_match": eps_match,
                "formula": "NET_PROFIT_ATTRIBUTABLE_TO_LISTED_COMPANY_SHAREHOLDERS / WEIGHTED_AVERAGE_DILUTED_SHARES",
                "arithmetic": f"{attributable_net_profit} {currency} / {share_count} shares = {calculated_eps} {currency}/share",
                "declared_eps_evidence_refs": eps_refs,
                "formal_evidence_pit_admission": False,
            }
            if not eps_match:
                issues.append(
                    f"{name.upper()}_DECLARED_EPS_DOES_NOT_MATCH_NET_PROFIT_ATTRIBUTABLE_DIVIDED_BY_DILUTED_SHARES"
                )
        except (ValueError, LocalInvestmentPilotError) as exc:
            issue = str(exc)
            issues.append(issue)
            scenario_outputs[name] = {
                "status": "NOT_LINKED",
                "declared_eps_per_share": None,
                "calculated_eps_per_share": None,
                "absolute_difference_per_share": None,
                "rounding_tolerance_per_share": format(EPS_EPS_MATCH_TOLERANCE, "f"),
                "eps_match": False,
                "issues": [issue],
                "formal_evidence_pit_admission": False,
            }

    statuses = [str((scenario_outputs.get(name) or {}).get("status") or "NOT_LINKED") for name in SCENARIOS]
    if any(status == "EPS_MISMATCH" for status in statuses):
        overall = "EPS_MISMATCH"
    elif all(status == "CALCULATED" for status in statuses):
        overall = "CALCULATED"
    elif all(status == "ASSUMPTION_ONLY" for status in statuses):
        overall = "ASSUMPTION_ONLY"
    elif all(status in {"CALCULATED", "ASSUMPTION_ONLY"} for status in statuses):
        overall = "MIXED_CALCULATED_AND_ASSUMPTION_ONLY"
    else:
        overall = "NOT_LINKED"
    if overall in {"CALCULATED", "ASSUMPTION_ONLY", "MIXED_CALCULATED_AND_ASSUMPTION_ONLY"}:
        summary = {
            "CALCULATED": "Bear/Base/Bull EPS 已与 B4 整公司净利润代理、上市公司股东归属调整和同期间加权平均稀释股数完成算术核对。",
            "ASSUMPTION_ONLY": "Bear/Base/Bull EPS 均明确标为分析假设，但未提供可独立复算的公司净利润/稀释股数桥。",
            "MIXED_CALCULATED_AND_ASSUMPTION_ONLY": "EPS 同时包含可复算的净利润/稀释股数情景与明确标记的分析假设情景；请逐情景审阅。",
        }[overall]
    elif overall == "EPS_MISMATCH":
        summary = "至少一个情景的申报 EPS 与净利润归属桥 ÷ 加权平均稀释股数不一致；主估值价格链已阻断，没有静默覆盖任一数字。"
    else:
        summary = "EPS 到整公司净利润、上市公司股东归属调整和同期间加权平均稀释股数的传导链不完整或不可协调；主估值价格链应保持 UNKNOWN。"
    return {
        **result(overall, scenario_outputs, issues, period=period, terminal_date=terminal_date, currency=currency),
        "summary": summary,
    }


def _evaluate_primary_eps_multiple_valuation(
    raw: Any, *, selected_model_family: Any, expected_forecast_period: Any,
    expected_terminal_date: Any, expected_currency: Any,
    evidence_register: list[dict[str, Any]],
    eps_earnings_bridge: Mapping[str, Any] | None = None,
    unresolved_evidence_ids: list[str] | set[str] | None = None,
    after_cutoff_evidence_ids: list[str] | set[str] | None = None,
    uncertain_timing_evidence_ids: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Recompute scenario terminal values from typed EPS and P/E inputs."""
    def blocked(status: str, issue: str = "", summary: str = "") -> dict[str, Any]:
        return {"schema_version": EPS_MULTIPLE_VALUATION_SCHEMA, "status": status,
                "method": EPS_MULTIPLE_VALUATION_METHOD, "selected_for_primary_model": False,
                "summary": summary or "没有生成可用于主估值的完整复算结果。",
                "forecast_period": None, "valuation_terminal_date": None, "scenarios": {},
                "issues": [issue] if issue else [], "formal_valuation_admission_created": False,
                "decision_authority": False}
    if str(selected_model_family or "UNKNOWN").strip().upper() != "EPS_MULTIPLE":
        return blocked("NOT_SELECTED", summary="操作者未选择 EPS_MULTIPLE；适配器不参与主估值。")
    currency = str(expected_currency or "").strip().upper()
    if currency not in {"CNY", "HKD"}:
        return blocked("CURRENCY_NOT_SUPPORTED", f"EPS_MULTIPLE_CURRENCY_NOT_SUPPORTED:{currency or 'UNKNOWN'}")
    if not isinstance(raw, Mapping) or raw.get("schema_version") != EPS_MULTIPLE_VALUATION_SCHEMA:
        return blocked("INPUT_MISSING_OR_SCHEMA_MISMATCH", "EPS_MULTIPLE_INPUT_OBJECT_OR_SCHEMA_INVALID")
    if str(raw.get("calculation_method") or "").strip().upper() != EPS_MULTIPLE_VALUATION_METHOD:
        return blocked("METHOD_UNSUPPORTED", "EPS_MULTIPLE_METHOD_UNSUPPORTED")
    summary = str(raw.get("summary") or "").strip()
    if not _is_identifiable_evidence_text(summary):
        return blocked("RATIONALE_NOT_IDENTIFIABLE", "EPS_MULTIPLE_SUMMARY_NOT_IDENTIFIABLE")
    period = str(raw.get("forecast_period") or "").strip().upper()
    expected_period = str(expected_forecast_period or "").strip().upper()
    terminal_date = str(raw.get("valuation_terminal_date") or "").strip()
    expected_date = str(expected_terminal_date or "").strip()
    if (
        not _is_identifiable_evidence_text(period)
        or not _is_identifiable_evidence_text(expected_period)
        or period != expected_period
    ):
        return blocked("PERIOD_MISMATCH", "EPS_MULTIPLE_FORECAST_PERIOD_MISMATCH")
    if (
        not _is_identifiable_evidence_text(terminal_date)
        or not _is_identifiable_evidence_text(expected_date)
        or terminal_date != expected_date
    ):
        return blocked("TERMINAL_DATE_MISMATCH", "EPS_MULTIPLE_TERMINAL_DATE_MISMATCH")
    inputs = raw.get("scenarios")
    if not isinstance(inputs, Mapping) or set(inputs) != set(SCENARIOS):
        return blocked("SCENARIOS_INCOMPLETE", "EPS_MULTIPLE_REQUIRES_BEAR_BASE_BULL")
    evidence = {str(item.get("source_id")): item for item in evidence_register
                if isinstance(item, Mapping) and item.get("source_id")}
    unresolved, after, uncertain = (set(unresolved_evidence_ids or []),
                                    set(after_cutoff_evidence_ids or []),
                                    set(uncertain_timing_evidence_ids or []))
    outputs: dict[str, Any] = {}
    try:
        for name in SCENARIOS:
            row = inputs[name]
            if not isinstance(row, Mapping) or not _is_identifiable_evidence_text(row.get("rationale")):
                raise ValueError(f"{name.upper()}_RATIONALE_NOT_IDENTIFIABLE")
            measures: dict[str, Any] = {}
            for key, unit in (("eps_per_share", f"{currency}/share"), ("pe_multiple_x", "x")):
                measure = row.get(key)
                if not isinstance(measure, Mapping):
                    raise ValueError(f"{name.upper()}_{key.upper()}_OBJECT_REQUIRED")
                if str(measure.get("unit") or "").strip().lower() != unit.lower():
                    raise ValueError(f"{name.upper()}_{key.upper()}_UNIT_MISMATCH")
                data_class = str(measure.get("data_class") or "").strip().upper()
                if data_class not in {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}:
                    raise ValueError(f"{name.upper()}_{key.upper()}_DATA_CLASS_INVALID")
                if key == "eps_per_share":
                    bridge_data = eps_earnings_bridge if isinstance(eps_earnings_bridge, Mapping) else {}
                    bridge_rows = bridge_data.get("scenarios") if isinstance(bridge_data.get("scenarios"), Mapping) else {}
                    bridge_row = bridge_rows.get(name) if isinstance(bridge_rows.get(name), Mapping) else {}
                    bridge_status = str(bridge_row.get("status") or "NOT_LINKED").upper()
                    allowed_bridge_statuses = {"CALCULATED", "ASSUMPTION_ONLY"}
                    if bridge_status not in allowed_bridge_statuses:
                        raise ValueError(f"{name.upper()}_EPS_EARNINGS_BRIDGE_NOT_ELIGIBLE:{bridge_status}")
                    if data_class == "ISSUER_FORECAST" and bridge_status != "CALCULATED":
                        raise ValueError(f"{name.upper()}_ISSUER_FORECAST_EPS_REQUIRES_CALCULATED_EARNINGS_BRIDGE")
                    if data_class == "ANALYST_ASSUMPTION" and bridge_status == "ASSUMPTION_ONLY":
                        derivation = str(measure.get("assumption_derivation") or "").strip()
                        if not _is_identifiable_evidence_text(derivation):
                            raise ValueError(f"{name.upper()}_ANALYST_ASSUMPTION_DERIVATION_NOT_IDENTIFIABLE")
                basis = str(measure.get("basis") or "").strip()
                if not _is_identifiable_evidence_text(basis):
                    raise ValueError(f"{name.upper()}_{key.upper()}_BASIS_NOT_IDENTIFIABLE")
                number = _positive(measure.get("value"), f"{name.upper()}_{key.upper()}")
                refs_raw = measure.get("evidence_refs") or []
                if not isinstance(refs_raw, list):
                    raise ValueError(f"{name.upper()}_{key.upper()}_EVIDENCE_REFS_INVALID")
                refs = list(dict.fromkeys(str(ref).strip() for ref in refs_raw if str(ref).strip()))
                if data_class == "ISSUER_FORECAST" and not refs:
                    raise ValueError(f"{name.upper()}_{key.upper()}_ISSUER_FORECAST_EVIDENCE_REQUIRED")
                for ref in refs:
                    source = evidence.get(ref)
                    if (source is None or ref in unresolved or ref in after or ref in uncertain
                            or source.get("time_status") != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"):
                        raise ValueError(f"{name.upper()}_{key.upper()}_EVIDENCE_NOT_CUTOFF_COMPATIBLE:{ref}")
                    if data_class == "ISSUER_FORECAST" and not _eps_source_domain_class_matches(source):
                        raise ValueError(f"{name.upper()}_{key.upper()}_ISSUER_FORECAST_SOURCE_CLASS_OR_DOMAIN_NOT_VERIFIED:{ref}")
                measures[key] = {"value": format(number, "f"), "unit": unit, "data_class": data_class,
                                 "basis": basis, "evidence_refs": refs, "note": str(measure.get("note") or ""),
                                 "formal_evidence_pit_admission": False}
                if key == "eps_per_share":
                    measures[key]["assumption_derivation"] = str(measure.get("assumption_derivation") or "").strip()
                    bridge_data = eps_earnings_bridge if isinstance(eps_earnings_bridge, Mapping) else {}
                    bridge_rows = bridge_data.get("scenarios") if isinstance(bridge_data.get("scenarios"), Mapping) else {}
                    measures[key]["earnings_bridge_status"] = str((bridge_rows.get(name) or {}).get("status") or "NOT_LINKED")
            eps = _number(measures["eps_per_share"]["value"], f"{name.upper()}_EPS")
            pe = _number(measures["pe_multiple_x"]["value"], f"{name.upper()}_PE")
            terminal = eps * pe
            bridge_data = eps_earnings_bridge if isinstance(eps_earnings_bridge, Mapping) else {}
            bridge_rows = bridge_data.get("scenarios") if isinstance(bridge_data.get("scenarios"), Mapping) else {}
            bridge_row = bridge_rows.get(name) if isinstance(bridge_rows.get(name), Mapping) else {}
            outputs[name] = {"rationale": str(row.get("rationale") or "").strip(),
                             "eps_per_share": measures["eps_per_share"], "pe_multiple_x": measures["pe_multiple_x"],
                             "earnings_bridge": dict(bridge_row),
                             "calculation": {"formula": "EPS_PER_SHARE × PE_MULTIPLE",
                                             "arithmetic": f"{eps} × {pe} = {terminal}"},
                             "terminal_value_per_share": format(terminal, "f")}
    except (ValueError, LocalInvestmentPilotError) as exc:
        return blocked("INPUT_INCOMPLETE_OR_INVALID", str(exc))
    terminals = {name: _number(outputs[name]["terminal_value_per_share"], name) for name in SCENARIOS}
    if not terminals["bear"] <= terminals["base"] <= terminals["bull"]:
        return blocked("SCENARIO_ORDERING_INCONSISTENT", "EPS_MULTIPLE_SCENARIO_ORDERING_INCONSISTENT")
    return {"schema_version": EPS_MULTIPLE_VALUATION_SCHEMA, "status": "CALCULATED",
            "method": EPS_MULTIPLE_VALUATION_METHOD, "selected_for_primary_model": True,
            "summary": "本地适配器独立复算 Bear/Base/Bull 每股终值 = 结构化 EPS × P/E；不从自由文本反推 EPS/P/E。",
            "analyst_supplied_summary_unverified": summary, "forecast_period": period,
            "valuation_terminal_date": terminal_date, "currency": currency, "scenarios": outputs,
            "issues": [], "formal_valuation_admission_created": False, "decision_authority": False}


def _render_eps_earnings_bridge_section(result: Mapping[str, Any], currency: str) -> list[str]:
    data = result if isinstance(result, Mapping) else {}
    lines = [
        "",
        "### EPS 来源与净利润/稀释股数传导核对",
        "",
        f"- 桥接状态：**{data.get('status', 'UNKNOWN')}**；期间 / 终值日：{data.get('forecast_period') or 'UNKNOWN'} / {data.get('valuation_terminal_date') or 'UNKNOWN'}",
        f"- 是否允许进入 EPS_MULTIPLE 价格计算：{data.get('primary_eps_price_calculation_eligible', False)}",
        f"- 说明：{data.get('summary') or 'EPS 桥接未完成。'}",
        f"- 匹配容差：每股绝对差异不超过 {data.get('scenarios', {}).get('base', {}).get('rounding_tolerance_per_share', '0.005')} {currency}/share；超出容差不覆盖申报 EPS，而是阻断主价格计算。",
        "- 证据边界：官方交易所/监管域名与类别匹配不等于内容核实，也不等于正式 Evidence/PIT 准入。",
        "",
    ]
    scenarios = data.get("scenarios") if isinstance(data.get("scenarios"), Mapping) else {}
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        lines.extend([f"**{label} 情景 EPS 桥接：{row.get('status', 'NOT_LINKED')}**"])
        if row.get("status") == "ASSUMPTION_ONLY":
            lines.extend([
                f"- 申报 EPS：{row.get('declared_eps_per_share') or 'UNKNOWN'} {currency}/share",
                f"- 分析假设推导：{row.get('assumption_derivation') or 'UNKNOWN'}",
                f"- 依据：{row.get('basis') or 'UNKNOWN'}",
                "- 未提供完整的 B4 整公司净利润归属桥与同期间加权平均稀释股数；该数值仅是分析假设，不是已核实发行人预测。",
                "",
            ])
            continue
        if row.get("status") in {"CALCULATED", "EPS_MISMATCH"}:
            profit = row.get("net_profit_attributable_to_listed_shareholders")
            profit = profit if isinstance(profit, Mapping) else {}
            shares = row.get("diluted_shares")
            shares = shares if isinstance(shares, Mapping) else {}
            lines.extend([
                f"- B4 整公司净利润代理：{row.get('b4_net_profit_proxy_cny') or 'UNKNOWN'} {currency}",
                f"- 非控股股东损益扣减：{(row.get('non_controlling_interests') or {}).get('value', 'UNKNOWN')} {currency}",
                f"- 其他税后归属调整：{(row.get('other_after_tax_attribution_adjustment') or {}).get('value', 'UNKNOWN')} {currency}",
                f"- 上市公司股东归属净利润：{profit.get('arithmetic') or 'UNKNOWN'}",
                f"- 加权平均稀释股数：{shares.get('value', 'UNKNOWN')} shares；期间：{shares.get('forecast_period', 'UNKNOWN')}",
                f"- 计算 EPS：{row.get('arithmetic') or 'UNKNOWN'}",
                f"- 申报 EPS / 计算 EPS / 绝对差异：{row.get('declared_eps_per_share') or 'UNKNOWN'} / {row.get('calculated_eps_per_share') or 'UNKNOWN'} / {row.get('absolute_difference_per_share') or 'UNKNOWN'}",
                f"- 项目利润处理：{row.get('project_profit_treatment') or 'UNKNOWN'}",
            ])
            if row.get("status") == "EPS_MISMATCH":
                lines.append("- **不一致：申报 EPS 与净利润/稀释股数复算差异超过容差；主估值、回报、目标入场价与 B6 应保持 UNKNOWN。**")
            lines.append("")
        else:
            for issue in row.get("issues") or []:
                lines.append(f"- 未解决：{issue}")
            if not row.get("issues"):
                lines.append("- 缺少足以重建此情景的净利润归属、稀释股数或期间/来源链。")
            lines.append("")
    if data.get("issues"):
        lines.extend(["#### EPS 桥接未解决问题", ""] + [f"- {item}" for item in data.get("issues") or []])
        lines.append("")
    lines.extend([
        "- 方法边界：B4 的净利润代理不是自动确认的归母净利润；本地仅按明示的非控股股东损益与其他税后归属调整复算。",
        "- 决策边界：桥接算术与时点/来源类别检查不创建正式预测、估值准入、Decision 或交易授权。",
        "",
    ])
    return lines


def _render_primary_eps_multiple_section(result: Mapping[str, Any], currency: str) -> list[str]:
    data = result if isinstance(result, Mapping) else {}
    lines = ["", "### EPS_MULTIPLE：每股盈利 × 市盈率的主估值计算链", "",
             f"- 计算状态：**{data.get('status', 'UNKNOWN')}**；方法：{data.get('method', EPS_MULTIPLE_VALUATION_METHOD)}",
             f"- 是否由操作者选为主模型：{data.get('selected_for_primary_model', False)}",
             f"- 预测期间 / 估值终点：{data.get('forecast_period') or 'UNKNOWN'} / {data.get('valuation_terminal_date') or 'UNKNOWN'}",
             f"- 说明：{data.get('summary') or '未计算'}",
             "- 边界：本计算只证明明示 EPS 与 P/E 的乘法可复算，不证明预测可信、P/E 校准充分或正式估值准入。",
             "- 正式估值准入：未创建；本结果不创建 Decision 或交易授权。", ""]
    scenarios = data.get("scenarios") if isinstance(data.get("scenarios"), Mapping) else {}
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        eps = row.get("eps_per_share") if isinstance(row.get("eps_per_share"), Mapping) else {}
        pe = row.get("pe_multiple_x") if isinstance(row.get("pe_multiple_x"), Mapping) else {}
        lines.extend([f"**{label} 情景**", f"- 情景理由：{row.get('rationale') or 'UNKNOWN'}",
                      f"- EPS：{eps.get('value', 'UNKNOWN')} {eps.get('unit', currency + '/share')}；依据：{eps.get('basis', 'UNKNOWN')}",
                      f"- P/E：{pe.get('value', 'UNKNOWN')}x；依据：{pe.get('basis', 'UNKNOWN')}",
                      f"- 本地复算：{(row.get('calculation') or {}).get('arithmetic', 'UNKNOWN')}",
                      f"- 每股终值：{row.get('terminal_value_per_share') or 'UNKNOWN'} {currency}", ""])
    if data.get("issues"):
        lines.extend(["#### EPS_MULTIPLE 未解决问题", ""] + [f"- {item}" for item in data.get("issues") or []])
    return lines


def _build_valuation_model_consistency(
    *,
    operator_model_family: Any,
    forecast_model_family: Any,
    model_name: Any,
    model_rationale: Any,
    operating_driver_forecast: Mapping[str, Any],
    valuation_transmission: Mapping[str, Any],
    sotp_calculation_status: Any = "NOT_SELECTED",
    eps_multiple_calculation_status: Any = "NOT_SELECTED",
    eps_multiple_calculation_issues: list[str] | None = None,
) -> dict[str, Any]:
    """Keep the primary model identity and its selection rationale independently identifiable."""
    selected = _normalize_model_family(operator_model_family)
    calculated = _normalize_model_family(forecast_model_family)
    name = str(model_name or "").strip() or "UNKNOWN"
    inferred_from_name = _infer_model_family_from_name(name)
    scope = str(operating_driver_forecast.get("scope") or "UNKNOWN").strip().upper()
    transmission_status = str(valuation_transmission.get("status") or "NOT_LINKED").strip().upper()
    issues: list[str] = []
    if selected == "UNKNOWN":
        status = "OPERATOR_MODEL_NOT_CONFIRMED"
        issues.append("OPERATOR_SELECTED_MODEL_FAMILY_UNKNOWN")
    elif calculated == "UNKNOWN":
        status = "CALCULATION_MODEL_FAMILY_UNKNOWN"
        issues.append("FORECAST_VALUATION_MODEL_FAMILY_UNKNOWN")
    elif selected != calculated:
        status = "MODEL_FAMILY_MISMATCH"
        issues.append("OPERATOR_MODEL_FAMILY_DIFFERS_FROM_CALCULATION_MODEL_FAMILY")
    elif name.upper() in {"", "UNKNOWN", "NONE", "NULL"}:
        status = "CALCULATION_MODEL_NAME_UNKNOWN"
        issues.append("FORECAST_VALUATION_MODEL_NAME_UNKNOWN")
    elif inferred_from_name == "UNKNOWN":
        status = "CALCULATION_MODEL_NAME_FAMILY_NOT_IDENTIFIABLE"
        issues.append("FORECAST_VALUATION_MODEL_NAME_DOES_NOT_IDENTIFY_MODEL_FAMILY")
    elif inferred_from_name != calculated:
        status = "CALCULATION_MODEL_NAME_FAMILY_MISMATCH"
        issues.append("FORECAST_VALUATION_MODEL_NAME_CONFLICTS_WITH_DECLARED_CALCULATION_FAMILY")
    else:
        status = "MATCH"
    model_rationale_identifiable = _is_identifiable_evidence_text(model_rationale)
    if selected == "SOTP" and str(sotp_calculation_status or "UNKNOWN").upper() != "CALCULATED":
        # The operator's selected SOTP must actually be calculated. Preserve any
        # model-family/name mismatch as a diagnostic issue, but make the missing
        # SOTP calculation the primary blocker for return/entry-price/B6 output.
        if "SOTP_ADAPTER_NOT_CALCULATED" not in issues:
            issues.append("SOTP_ADAPTER_NOT_CALCULATED")
        status = "SOTP_CALCULATION_NOT_ELIGIBLE"
    if selected == "EPS_MULTIPLE" and eps_multiple_calculation_issues:
        issues.extend(str(issue) for issue in eps_multiple_calculation_issues if str(issue).strip())
    if selected == "EPS_MULTIPLE" and str(eps_multiple_calculation_status or "UNKNOWN").upper() != "CALCULATED":
        if "EPS_MULTIPLE_ADAPTER_NOT_CALCULATED" not in issues:
            issues.append("EPS_MULTIPLE_ADAPTER_NOT_CALCULATED")
        status = "EPS_MULTIPLE_CALCULATION_NOT_ELIGIBLE"
    if not model_rationale_identifiable:
        issues.append("FORECAST_VALUATION_MODEL_RATIONALE_NOT_IDENTIFIABLE")
        if status == "MATCH":
            status = "MODEL_RATIONALE_NOT_IDENTIFIABLE"
    eligible = status == "MATCH"
    baseline_confirmed_included = valuation_transmission.get("baseline_includes_project") is True
    sotp_primary_calculated = calculated == "SOTP" and str(sotp_calculation_status or "UNKNOWN").upper() == "CALCULATED"
    if (
        eligible
        and not sotp_primary_calculated
        and scope != "COMPANY_WIDE"
        and transmission_status not in _B5_PROJECT_TRANSMISSION_ACCEPTED
        and not baseline_confirmed_included
    ):
        eligible = False
        status = "OPERATING_SCOPE_OR_B5_TRANSMISSION_NOT_RESOLVED"
        issues.append(
            "B5_TRANSMISSION_NOT_ACCEPTED_OUTSIDE_EXPLICIT_COMPANY_WIDE_SCOPE"
        )
    elif (
        eligible
        and not sotp_primary_calculated
        and scope != "COMPANY_WIDE"
        and transmission_status not in _B5_PROJECT_TRANSMISSION_ACCEPTED
        and baseline_confirmed_included
    ):
        # B5 is an optional incremental bridge. If the operator confirms that
        # the existing per-share baseline already includes the project, an
        # incomplete/unapplied counterfactual bridge must not invalidate that
        # unchanged primary valuation. Preserve an explicit diagnostic while
        # keeping the independently verified model identity as the price basis.
        status = "MATCH_BASELINE_PROJECT_INCLUDED_B5_DIAGNOSTIC_ONLY"
        issues.append("B5_NOT_APPLIED_BASELINE_CONFIRMED_PROJECT_INCLUDED")
    return {
        "schema_version": "IIOS-PRIMARY-VALUATION-MODEL-CONSISTENCY-0.1",
        "status": status,
        "operator_selected_model_family": selected,
        "calculation_model_family": calculated,
        "calculation_model_name": name,
        "model_rationale_identifiable": model_rationale_identifiable,
        "model_name_inferred_family": inferred_from_name,
        "model_family_name_crosscheck": (
            "MATCH" if inferred_from_name == calculated and inferred_from_name != "UNKNOWN"
            else "NOT_IDENTIFIABLE" if inferred_from_name == "UNKNOWN"
            else "MISMATCH"
        ),
        "operating_forecast_scope": scope,
        "valuation_transmission_status": transmission_status,
        "sotp_calculation_status": str(sotp_calculation_status or "NOT_SELECTED").upper(),
        "eps_multiple_calculation_status": str(eps_multiple_calculation_status or "NOT_SELECTED").upper(),
        "primary_model_price_calculation_eligible": eligible,
        "scenario_values_role": "PRIMARY_MODEL" if eligible else "ALTERNATIVE_OR_UNRESOLVED_ONLY",
        "issues": issues,
        "formal_decision_created": False,
        "decision_authority": False,
    }


def _build_valuation_timing(
    *,
    cutoff_date: Any,
    forecast_period: Any,
    valuation_terminal_date: Any,
    valuation_terminal_date_basis: Any,
) -> dict[str, Any]:
    """Bind annualization to the explicit valuation endpoint, not a nominal horizon label."""
    cutoff_text = str(cutoff_date or "").strip()
    period = str(forecast_period or "UNKNOWN").strip().upper()
    terminal_text = str(valuation_terminal_date or "").strip()
    issues: list[str] = []
    cutoff: date | None = None
    terminal: date | None = None
    try:
        cutoff = date.fromisoformat(cutoff_text)
    except (TypeError, ValueError):
        issues.append("VALUATION_CUTOFF_DATE_INVALID")
    terminal_basis = str(valuation_terminal_date_basis or "").strip()
    if not terminal_text:
        issues.append("VALUATION_TERMINAL_DATE_MISSING")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", terminal_text):
        issues.append("VALUATION_TERMINAL_DATE_INVALID")
    else:
        try:
            terminal = date.fromisoformat(terminal_text)
        except ValueError:
            issues.append("VALUATION_TERMINAL_DATE_INVALID")

    basis_token = re.sub(r"[^A-Z0-9]+", "_", terminal_basis.upper()).strip("_")
    if not terminal_basis:
        issues.append("VALUATION_TERMINAL_DATE_BASIS_MISSING")
    elif basis_token in {
        "", "UNKNOWN", "N_A", "NA", "NONE", "NULL", "NOT_IDENTIFIABLE",
        "UNIDENTIFIABLE", "UNSPECIFIED", "NOT_SPECIFIED", "TBD", "NOT_PROVIDED",
        "NOT_AVAILABLE", "UNAVAILABLE", "UNVERIFIED", "UNCONFIRMED", "NOT_KNOWN",
        "BASIS_UNKNOWN", "UNKNOWN_BASIS",
    }:
        # A non-empty sentinel is not evidence of what the terminal date represents.
        # Keep the downstream return/entry-price solver fail-closed.
        issues.append("VALUATION_TERMINAL_DATE_BASIS_NOT_IDENTIFIABLE")

    fiscal = re.fullmatch(r"(\d{4})FY", period)
    rolling = re.fullmatch(
        r"NTM_(\d{4}-\d{2}-\d{2})_TO_(\d{4}-\d{2}-\d{2})",
        period,
    )
    period_alignment = "NOT_IDENTIFIABLE"
    if fiscal is not None:
        period_alignment = "YEAR_COMPATIBLE_FISCAL_END_EXPLICIT_BUT_NOT_INDEPENDENTLY_VERIFIED"
        if terminal is not None:
            fiscal_year = int(fiscal.group(1))
            # Fiscal years may end in the named calendar year or in the following
            # calendar year; the date itself must be explicit in the model response.
            if terminal.year not in {fiscal_year, fiscal_year + 1}:
                issues.append("VALUATION_TERMINAL_DATE_FORECAST_PERIOD_MISMATCH")
                period_alignment = "MISMATCH_OR_INVALID"
    elif rolling is not None:
        # Explicit rolling-12-month forecasts are compatible with a one-year
        # decision horizon when their dates align with the cutoff and terminal.
        # Dates establish the arithmetic window, not the truth of the forecast.
        rolling_issues: list[str] = []
        try:
            rolling_start = date.fromisoformat(rolling.group(1))
            rolling_end = date.fromisoformat(rolling.group(2))
        except ValueError:
            rolling_issues.append("FORECAST_NTM_PERIOD_DATES_INVALID")
        else:
            if cutoff is None or rolling_start != cutoff.fromordinal(cutoff.toordinal() + 1):
                rolling_issues.append("FORECAST_NTM_PERIOD_START_MISMATCH")
            if terminal is None or rolling_end != terminal:
                rolling_issues.append("VALUATION_TERMINAL_DATE_FORECAST_PERIOD_MISMATCH")
            period_days = (rolling_end - rolling_start).days + 1
            if period_days not in {365, 366}:
                rolling_issues.append("FORECAST_NTM_PERIOD_NOT_ONE_YEAR")
        issues.extend(rolling_issues)
        period_alignment = (
            "ROLLING_12_MONTHS_EXPLICIT_DATES_ALIGNED_NOT_INDEPENDENTLY_VERIFIED"
            if not rolling_issues else "MISMATCH_OR_INVALID"
        )
    else:
        issues.append("FORECAST_FY_PERIOD_NOT_IDENTIFIABLE")

    elapsed_days: int | None = None
    year_fraction: str | None = None
    if cutoff is not None and terminal is not None:
        elapsed_days = (terminal - cutoff).days
        if elapsed_days <= 0:
            issues.append("VALUATION_TERMINAL_DATE_NOT_AFTER_CUTOFF")
        else:
            year_fraction = format(Decimal(elapsed_days) / Decimal("365"), "f")

    status = issues[0] if issues else "PASS"
    return {
        "schema_version": "IIOS-VALUATION-TIMING-0.1",
        "status": status,
        "cutoff_date": cutoff.isoformat() if cutoff else cutoff_text or None,
        "forecast_period": period or "UNKNOWN",
        "valuation_terminal_date": terminal.isoformat() if terminal else None,
        "valuation_terminal_date_basis": terminal_basis or None,
        "period_alignment_status": period_alignment,
        "elapsed_calendar_days": elapsed_days,
        "day_count_convention": "ACT/365F_DATE_ONLY",
        "annualization_year_fraction": year_fraction,
        "annualized_return_formula": "(expected_terminal_wealth / current_price) ** (1 / annualization_year_fraction) - 1",
        "return_hurdle_entry_price_formula": "expected_terminal_wealth / (1 + target_annualized_return) ** annualization_year_fraction",
        "issues": issues,
        "formal_decision_created": False,
        "decision_authority": False,
    }



_OFFICIAL_EXCHANGE_DOMAINS = (
    "sse.com.cn",
    "szse.cn",
    "cninfo.com.cn",
    "hkexnews.hk",
    "hkex.com.hk",
)
_OFFICIAL_REGULATOR_DOMAINS = (
    "csrc.gov.cn",
    "chinatax.gov.cn",
    "gov.cn",
    "mof.gov.cn",
    "pbc.gov.cn",
    "samr.gov.cn",
    "ndrc.gov.cn",
    "miit.gov.cn",
)


def _host_under_domains(host: str, domains: tuple[str, ...]) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def _primary_source_domain_check(source_ref: Any, source_class: Any) -> dict[str, Any]:
    """Conservative URL-host/class consistency check; never formal evidence admission."""
    declared = str(source_class or "UNKNOWN").strip().upper()
    ref = str(source_ref or "").strip()
    try:
        parsed = urlsplit(ref)
        host = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        parsed = None
        host = ""
    if parsed is None or parsed.scheme.lower() not in {"http", "https"} or not host:
        return {
            "host": host or None,
            "status": "SOURCE_URL_INVALID",
            "cash_distribution_eligible": False,
        }
    exchange_host = _host_under_domains(host, _OFFICIAL_EXCHANGE_DOMAINS)
    regulator_host = _host_under_domains(host, _OFFICIAL_REGULATOR_DOMAINS)
    if declared == "EXCHANGE_PRIMARY" and exchange_host:
        status = "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    elif declared == "REGULATOR_PRIMARY" and regulator_host:
        status = "OFFICIAL_REGULATOR_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    elif declared == "ISSUER_PRIMARY":
        status = (
            "SOURCE_CLASS_DOMAIN_MISMATCH"
            if exchange_host or regulator_host
            else "ISSUER_DOMAIN_NOT_INDEPENDENTLY_VERIFIED"
        )
    elif declared in {"EXCHANGE_PRIMARY", "REGULATOR_PRIMARY"}:
        status = "SOURCE_CLASS_DOMAIN_MISMATCH" if exchange_host or regulator_host else "DOMAIN_NOT_ALLOWLISTED_AS_PRIMARY"
    else:
        status = "SOURCE_CLASS_NOT_PRIMARY"
    return {
        "host": host,
        "status": status,
        "cash_distribution_eligible": status in {
            "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED",
            "OFFICIAL_REGULATOR_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED",
        },
    }


def _normalize_cash_distribution_review(raw_review: Any, evidence_register: list[dict[str, Any]]) -> dict[str, Any]:
    """Preserve analyst claims while preventing model-supplied text from asserting verification."""
    if not isinstance(raw_review, Mapping):
        return {}
    review = dict(raw_review)
    analyst_summary = str(review.get("summary") or "")
    review["analyst_supplied_summary_unverified"] = analyst_summary
    review["formal_evidence_pit_admission"] = False
    refs = _items(review.get("evidence_refs"))
    evidence_by_id = {
        str(row.get("source_id")): row for row in evidence_register
        if isinstance(row, Mapping) and row.get("source_id")
    }
    acceptable_time_status = "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
    has_identifiable_summary = _is_identifiable_evidence_text(analyst_summary)
    referenced = [evidence_by_id.get(str(ref)) for ref in refs]
    all_primary_domains_match = bool(refs) and all(
        source is not None and source.get("cash_distribution_primary_domain_eligible") is True
        for source in referenced
    )
    all_cutoff_compatible = bool(refs) and all(
        source is not None and source.get("time_status") == acceptable_time_status
        for source in referenced
    )
    if not has_identifiable_summary:
        validation_status = "REVIEW_SUMMARY_NOT_IDENTIFIABLE"
        qualified_summary = analyst_summary
    elif not refs:
        validation_status = "EVIDENCE_REFERENCES_MISSING"
        qualified_summary = "模型输入未提供可解析的现金分配核查证据引用；未来现金分配状态尚未核实，正式证据准入未完成。"
    elif not all_primary_domains_match:
        validation_status = "BLOCKED_SOURCE_DOMAIN_CLASS_OR_CUTOFF_REVIEW"
        qualified_summary = "模型输入声称的现金分配状态未通过官方交易所/监管域名与来源类别一致性检查；未获准作为已核实现金流，正式证据准入未完成。"
    elif not all_cutoff_compatible:
        validation_status = "BLOCKED_SOURCE_DOMAIN_CLASS_OR_CUTOFF_REVIEW"
        qualified_summary = "引用来源的域名/类别检查通过，但披露时点与研究截止时点的兼容性尚未解决；不得表述为已核实，正式证据准入未完成。"
    else:
        validation_status = "OFFICIAL_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
        qualified_summary = "引用 URL 主机名与官方交易所/监管域及声明类别匹配，但链接内容真实性、公告发布时间与正式证据准入仍未全部独立确认；不得将模型声明表述为已核实。"
    review["source_validation_status"] = validation_status
    review["summary"] = qualified_summary
    return review


def _neutralize_stale_model_confirmation_language(
    forecast: dict[str, Any], operator_context: Mapping[str, Any]
) -> None:
    """Do not let old AI-draft wording contradict a later explicit operator confirmation."""
    rationale = str(forecast.get("model_rationale") or "")
    if not rationale:
        forecast["model_rationale_status"] = "MODEL_RATIONALE_NOT_PROVIDED"
        return
    patterns = (
        re.compile(r"操作者.{0,12}(?:尚待|仍待|待|尚需|需要|尚未).{0,12}(?:本地)?确认", re.IGNORECASE),
        re.compile(r"\b(?:operator|user)\b.{0,24}\b(?:pending|awaiting|needs? to)\b.{0,16}\bconfirmation\b", re.IGNORECASE),
    )
    if operator_context.get("selection_confirmed") is True:
        original = rationale
        for pattern in patterns:
            rationale = pattern.sub(
                "【旧稿待确认措辞已按本次本地操作者确认记录清理】", rationale
            )
        if rationale != original:
            forecast["model_rationale_original_untrusted"] = original
            forecast["model_rationale"] = rationale
            forecast["model_rationale_status"] = "STALE_OPERATOR_CONFIRMATION_LANGUAGE_NEUTRALIZED"
            return
    forecast["model_rationale_status"] = "AS_PROVIDED"


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
    duplicate_source_ids: set[str] = set()
    untraceable_evidence_fields: dict[str, list[str]] = {}
    for row in payload.get("evidence_register") or []:
        if not isinstance(row, Mapping):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if not source_id:
            continue
        if source_id in source_ids:
            # A repeated ID is ambiguous even if the first row looks usable.
            # Preserve the first row for display, but prevent references to this
            # ID from being treated as uniquely resolved.
            duplicate_source_ids.add(source_id)
            continue
        source_ids.add(source_id)
        invalid_source_fields = [
            field for field in ("title", "source_ref", "summary")
            if not _is_identifiable_evidence_text(row.get(field))
        ]
        if invalid_source_fields:
            untraceable_evidence_fields[source_id] = invalid_source_fields
        known_at_original = str(row.get("known_at") or "").strip()
        published_at_original = str(row.get("published_at") or "").strip()
        known_text = known_at_original
        known_at_precision = "DATE_ONLY" if len(known_text) == 10 else "TIMESTAMP_OR_OFFSET_DATETIME"
        explicit_date_only_unknown_time = re.fullmatch(
            r"(\d{4}-\d{2}-\d{2})\s*[;；,，]\s*"
            r"(?:确切发布时间|确切披露时间|具体披露时分|具体披露时间|披露时分|披露时间|具体时分|具体时间|时分|时间|exact time|time(?: of day)?)\s*"
            r"(?:[:：]\s*)?(?:UNKNOWN|未知|不详|not known)",
            known_at_original,
            flags=re.IGNORECASE,
        )
        if explicit_date_only_unknown_time:
            # A dated official disclosure with unknown clock time remains a
            # date-level fact; never upgrade its precision to midnight.
            known_text = explicit_date_only_unknown_time.group(1)
            known_at_precision = "DATE_ONLY_EXPLICIT_TIME_UNKNOWN"
        source_time_status = "UNKNOWN"
        time_basis = "UNKNOWN"
        if known_text:
            try:
                if len(known_text) == 10:
                    # A date before the cutoff day is compatible with the cutoff,
                    # but this pilot still does not formally admit PIT evidence.
                    known_date = _date(known_text, f"{source_id}_KNOWN_AT")
                    if known_date < cutoff:
                        source_time_status = "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
                        time_basis = "KNOWN_AT_DATE_ONLY"
                    elif known_date > cutoff:
                        source_time_status = "AFTER_CUTOFF"
                        time_basis = "KNOWN_AT_DATE_ONLY"
                    else:
                        source_time_status = "KNOWN_AT_PRECISION_INSUFFICIENT"
                        time_basis = "KNOWN_AT_DATE_ONLY"
                else:
                    source_time = _datetime(known_text, f"{source_id}_KNOWN_AT")
                    source_time_status = (
                        "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
                        if source_time <= cutoff_instant else "AFTER_CUTOFF"
                    )
                    time_basis = "KNOWN_AT_TIMESTAMP"
            except LocalInvestmentPilotError:
                unknown_clock_annotation = bool(re.search(
                    r"(?:UNKNOWN|未知|不详|确切更新时间未知|更新时间UNKNOWN|检索时可访问)",
                    known_at_original,
                    flags=re.IGNORECASE,
                ))
                source_time_status = "UNKNOWN" if unknown_clock_annotation else "KNOWN_AT_INVALID"
                time_basis = "TIME_NOT_IDENTIFIABLE" if unknown_clock_annotation else "KNOWN_AT_INVALID"
        # If a model supplies a separate, parseable official publication date,
        # use it only as date-level compatibility evidence when known_at itself
        # is unavailable/unknown. Keep both raw fields so the fallback is auditable.
        published_date = None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", published_at_original):
            try:
                published_date = _date(published_at_original, f"{source_id}_PUBLISHED_AT")
            except LocalInvestmentPilotError:
                published_date = None
        if published_date is not None and source_time_status in {"UNKNOWN", "KNOWN_AT_INVALID"}:
            if published_date < cutoff:
                source_time_status = "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
            elif published_date > cutoff:
                source_time_status = "AFTER_CUTOFF"
            else:
                source_time_status = "KNOWN_AT_PRECISION_INSUFFICIENT"
            time_basis = "PUBLISHED_DATE_ONLY_FALLBACK"
        domain_check = _primary_source_domain_check(row.get("source_ref"), row.get("source_class"))
        sources.append({
            "source_id": source_id,
            "title": str(row.get("title") or "未提供标题"),
            "source_class": str(row.get("source_class") or "UNKNOWN"),
            "source_ref": str(row.get("source_ref") or "UNKNOWN"),
            "source_url_host": domain_check["host"],
            "source_domain_class_status": domain_check["status"],
            "cash_distribution_primary_domain_eligible": domain_check["cash_distribution_eligible"],
            "known_at": known_text or None,
            "known_at_original": known_at_original or None,
            "published_at": published_at_original or None,
            "known_at_precision": known_at_precision if known_text else "UNKNOWN",
            "time_status": source_time_status,
            "time_basis": time_basis,
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
    status_aliases = {
        "trust": {"PASS_WITH_LIMITATIONS": "REVALIDATION"},
        "reality": {"SUPPORTED_WITH_MATERIAL_CAVEATS": "CONDITIONAL"},
        "quality": {"HIGH_QUALITY_WITH_CYCLICAL_AND_POLICY_RISKS": "CONDITIONAL"},
        "thesis": {"CONDITIONALLY_VALID": "WATCH"},
        # This means the analyst's own case does not clear the return hurdle;
        # it is not a measured market-implied expectation gap.
        "expectation_gap": {"ANALYST_CASE_INDICATES_INSUFFICIENT_RETURN": "UNKNOWN"},
        # MATERIAL describes risk severity, not an explicit PASS/FAIL gate result.
        "risk": {"MATERIAL": "UNKNOWN"},
    }
    assessment: dict[str, Any] = {}
    for name, states in allowed_assessment.items():
        raw = raw_assessment.get(name) if isinstance(raw_assessment.get(name), Mapping) else {}
        assessment[name] = dict(raw)
        raw_status = str(raw.get("status") or "UNKNOWN").strip().upper()
        normalized_status = status_aliases.get(name, {}).get(raw_status, raw_status)
        assessment[name]["status_input"] = raw_status
        normalized_status = _status(normalized_status, states)
        summary = str(raw.get("summary") or "")
        # Thesis uses core_statement as its required explanatory field; the other
        # assessment sections use summary. Do not apply a summary-only check to Thesis.
        explanation = (
            raw.get("core_statement") if name == "thesis"
            else raw.get("summary")
        )
        explanation_identifiable = _is_identifiable_evidence_text(explanation)
        assessment[name]["summary"] = summary
        assessment[name]["evidence_refs"] = _items(raw.get("evidence_refs"))
        assessment[name]["status_issues"] = (
            [] if explanation_identifiable else ["ASSESSMENT_EXPLANATION_NOT_IDENTIFIABLE"]
        )
        # Do not let a machine status such as PASS/INTACT survive when its
        # accompanying explanation is empty or only an UNKNOWN/TBD placeholder.
        assessment[name]["status"] = (
            normalized_status if explanation_identifiable else "UNKNOWN"
        )
    direction_aliases = {
        "CURRENT_PRICE_ABOVE_RISK_ADJUSTED_ENTRY_REFERENCE": "NEGATIVE",
    }
    raw_direction = str(assessment["expectation_gap"].get("direction") or "UNKNOWN").strip().upper()
    assessment["expectation_gap"]["direction_input"] = raw_direction
    assessment["expectation_gap"]["direction"] = _status(
        direction_aliases.get(raw_direction, raw_direction),
        {"POSITIVE", "NEUTRAL", "NEGATIVE", "UNKNOWN"},
    )
    assessment["thesis"]["break_conditions"] = _items(assessment["thesis"].get("break_conditions"))
    assessment["thesis"]["reassessment_triggers"] = _items(assessment["thesis"].get("reassessment_triggers"))
    thesis_quality_issues: list[str] = []
    if assessment["thesis"]["status"] == "INTACT":
        break_conditions = assessment["thesis"]["break_conditions"]
        reassessment_triggers = assessment["thesis"]["reassessment_triggers"]
        if not break_conditions or any(not _is_identifiable_evidence_text(item) for item in break_conditions):
            thesis_quality_issues.append("BREAK_CONDITIONS_NOT_IDENTIFIABLE")
        if not reassessment_triggers or any(not _is_identifiable_evidence_text(item) for item in reassessment_triggers):
            thesis_quality_issues.append("REASSESSMENT_TRIGGERS_NOT_IDENTIFIABLE")
        if thesis_quality_issues:
            assessment["thesis"]["status"] = "UNKNOWN"
            status_issues = list(assessment["thesis"].get("status_issues") or [])
            status_issues.extend(thesis_quality_issues)
            assessment["thesis"]["status_issues"] = list(dict.fromkeys(status_issues))
    assessment["risk"]["items"] = _records(assessment["risk"].get("items"))
    risk_items_missing_monitoring_trigger = False
    normalized_risk_items = list(assessment["risk"]["items"])
    for index, item in enumerate(normalized_risk_items):
        if not isinstance(item, Mapping):
            continue
        # Earlier guided research used "trigger" for the same per-risk monitoring
        # condition. Preserve compatibility while standardizing the analysis schema.
        if item.get("monitoring_trigger") in (None, "") and item.get("trigger") not in (None, ""):
            item = dict(item)
            item["monitoring_trigger"] = item["trigger"]
            item["monitoring_trigger_source_field"] = "trigger"
            normalized_risk_items[index] = item
        if not _is_identifiable_evidence_text(item.get("monitoring_trigger")):
            risk_items_missing_monitoring_trigger = True
            risk_item = dict(item)
            risk_item["status"] = "UNKNOWN"
            risk_item_issues = list(risk_item.get("status_issues") or [])
            risk_item_issues.append("RISK_ITEM_MONITORING_TRIGGER_NOT_IDENTIFIABLE")
            risk_item["status_issues"] = list(dict.fromkeys(risk_item_issues))
            normalized_risk_items[index] = risk_item
        else:
            risk_item = dict(item)
            risk_item.setdefault("status", "PASS")
            normalized_risk_items[index] = risk_item
    risk_items_missing_id = False
    risk_items_missing_severity = False
    for index, item in enumerate(normalized_risk_items):
        if not isinstance(item, Mapping):
            continue
        item_issues = list(item.get("status_issues") or [])
        if not _is_identifiable_evidence_text(item.get("risk_id")):
            risk_items_missing_id = True
            item_issues.append("RISK_ITEM_ID_NOT_IDENTIFIABLE")
        if not _risk_item_severity_is_identifiable(item.get("severity")):
            risk_items_missing_severity = True
            item_issues.append("RISK_ITEM_SEVERITY_NOT_IDENTIFIABLE")
        if item_issues:
            item = dict(item)
            item["status"] = "UNKNOWN"
            item["status_issues"] = list(dict.fromkeys(item_issues))
            normalized_risk_items[index] = item
    assessment["risk"]["items"] = normalized_risk_items
    invalid_risk_items = [
        item for item in assessment["risk"]["items"]
        if not _risk_item_is_identifiable(item)
    ]
    risk_status_issues = list(assessment["risk"].get("status_issues") or [])
    if not assessment["risk"]["items"] or invalid_risk_items:
        if assessment["risk"]["status"] == "PASS":
            assessment["risk"]["status"] = "UNKNOWN"
        risk_status_issues.append("ITEMS_NOT_IDENTIFIABLE")
    if risk_items_missing_monitoring_trigger:
        risk_status_issues.append("RISK_ITEM_MONITORING_TRIGGER_NOT_IDENTIFIABLE")
    if risk_items_missing_id:
        risk_status_issues.append("RISK_ITEM_ID_NOT_IDENTIFIABLE")
    if risk_items_missing_severity:
        risk_status_issues.append("RISK_ITEM_SEVERITY_NOT_IDENTIFIABLE")
    legacy_plain_text_risk_items = [
        item for item in assessment["risk"]["items"]
        if not isinstance(item, Mapping)
    ]
    if legacy_plain_text_risk_items:
        # Keep text visible for legacy readers, but text alone cannot prove that
        # each risk has its own evidence and actionable monitoring trigger.
        if assessment["risk"]["status"] == "PASS":
            assessment["risk"]["status"] = "UNKNOWN"
        risk_status_issues.append("ITEMS_REQUIRE_STRUCTURED_MONITORING")

    risk_ids: dict[str, list[int]] = {}
    for index, item in enumerate(assessment["risk"]["items"]):
        if not isinstance(item, Mapping):
            continue
        raw_risk_id = item.get("risk_id")
        if raw_risk_id in (None, ""):
            continue
        normalized_risk_id = str(raw_risk_id).strip().upper()
        if not _is_identifiable_evidence_text(normalized_risk_id):
            continue
        risk_ids.setdefault(normalized_risk_id, []).append(index)
    duplicate_risk_ids = {
        risk_id: indices for risk_id, indices in risk_ids.items() if len(indices) > 1
    }
    if duplicate_risk_ids:
        for risk_id, indices in duplicate_risk_ids.items():
            for index in indices:
                item = dict(assessment["risk"]["items"][index])
                item["status"] = "UNKNOWN"
                item_issues = list(item.get("status_issues") or [])
                item_issues.append("DUPLICATE_RISK_ID_NOT_IDENTIFIABLE")
                item["status_issues"] = list(dict.fromkeys(item_issues))
                assessment["risk"]["items"][index] = item
        if assessment["risk"]["status"] == "PASS":
            assessment["risk"]["status"] = "UNKNOWN"
        risk_status_issues.append("DUPLICATE_RISK_ID_NOT_IDENTIFIABLE")
    assessment["risk"]["status_issues"] = list(dict.fromkeys(risk_status_issues))

    value_drivers = raw_assessment.get("value_drivers") or []
    assessment["value_drivers"] = []
    for index, item in enumerate(value_drivers, start=1):
        if not isinstance(item, Mapping):
            continue
        driver = str(item.get("driver") or item.get("name") or item.get("title") or "未命名价值驱动因素")
        raw_rank = item.get("rank", index)
        try:
            numeric_rank = Decimal(str(raw_rank))
            if not numeric_rank.is_finite() or numeric_rank < 1 or numeric_rank != numeric_rank.to_integral_value():
                raise ValueError("RANK_NOT_POSITIVE_INTEGER")
            rank = int(numeric_rank)
        except (InvalidOperation, TypeError, ValueError, OverflowError):
            # Keep rendering/replay stable without pretending the supplied rank was valid.
            rank = index
            rank_invalid = True
        else:
            rank_invalid = False
        # Status such as OBSERVED_AND_FORECAST is not an impact direction.
        # Keep it for display/audit, but do not infer POSITIVE or a passing gate.
        impact = _status(item.get("impact"), {"POSITIVE", "NEGATIVE", "MIXED", "UNKNOWN"})
        driver_type = str(item.get("type") or item.get("driver_type") or item.get("category") or "").strip()
        # Accept the current prompt's documented aliases without losing the
        # source wording: older/research-facing inputs use observed_basis and
        # transmission, while the normalized analysis schema uses
        # historical_evidence and valuation_transmission.
        historical_evidence = str(
            item.get("historical_evidence") or item.get("historical_basis")
            or item.get("observed_basis") or item.get("historical_observation") or ""
        ).strip()
        valuation_transmission = str(
            item.get("valuation_transmission") or item.get("transmission")
            or item.get("value_transmission") or ""
        ).strip()
        unresolved_inputs = _items(item.get("unresolved_inputs"))
        rationale = str(
            item.get("rationale") or item.get("summary") or item.get("mechanism")
            or valuation_transmission or ""
        )
        driver_issues: list[str] = []
        if rank_invalid:
            driver_issues.append("RANK_NOT_IDENTIFIABLE")
        if not _is_identifiable_evidence_text(driver):
            driver_issues.append("DRIVER_NAME_NOT_IDENTIFIABLE")
        if impact == "UNKNOWN":
            driver_issues.append("IMPACT_NOT_IDENTIFIABLE")
        if not _is_identifiable_evidence_text(rationale):
            driver_issues.append("RATIONALE_NOT_IDENTIFIABLE")
        if not _is_identifiable_evidence_text(historical_evidence):
            driver_issues.append("HISTORICAL_EVIDENCE_NOT_IDENTIFIABLE")
        if not _is_identifiable_evidence_text(valuation_transmission):
            driver_issues.append("VALUATION_TRANSMISSION_NOT_IDENTIFIABLE")
        assessment["value_drivers"].append({
            "rank": rank,
            "driver": driver,
            "driver_type": driver_type,
            "historical_evidence": historical_evidence,
            "valuation_transmission": valuation_transmission,
            "unresolved_inputs": unresolved_inputs,
            "source_status": str(item.get("status") or "UNKNOWN"),
            "impact": impact,
            "rationale": rationale,
            "evidence_refs": _items(item.get("evidence_refs")),
            "status": "PASS" if not driver_issues else "UNKNOWN",
            "status_issues": driver_issues,
        })
    rank_counts: dict[int, int] = {}
    for driver in assessment["value_drivers"]:
        rank_counts[driver["rank"]] = rank_counts.get(driver["rank"], 0) + 1
    for driver in assessment["value_drivers"]:
        if rank_counts[driver["rank"]] > 1:
            driver["status"] = "UNKNOWN"
            driver_issues = list(driver.get("status_issues") or [])
            driver_issues.append("DUPLICATE_RANK_NOT_IDENTIFIABLE")
            driver["status_issues"] = list(dict.fromkeys(driver_issues))
    assessment["thesis"]["core_statement"] = str(assessment["thesis"].get("core_statement") or "")
    assessment["thesis"]["drivers"] = assessment["thesis"].get("drivers") if isinstance(assessment["thesis"].get("drivers"), list) else []

    forecast_raw = payload.get("forecast_valuation") if isinstance(payload.get("forecast_valuation"), Mapping) else {}
    cash_distribution_review = _normalize_cash_distribution_review(
        forecast_raw.get("cash_distribution_review"), sources
    )
    raw_driver_forecast = payload.get("operating_driver_forecast")
    raw_valuation_transmission = payload.get("valuation_transmission")
    raw_sotp_valuation = payload.get("sotp_valuation")
    raw_eps_multiple_valuation = payload.get("eps_multiple_valuation")
    raw_operator_valuation_context = payload.get("operator_valuation_context")
    stress_raw = forecast_raw.get("thesis_break_stress")
    stress_raw = stress_raw if isinstance(stress_raw, Mapping) else {}
    forecast = {
        "model": str(forecast_raw.get("model") or "UNKNOWN"),
        "model_family": _normalize_model_family(forecast_raw.get("model_family")),
        "model_rationale": str(forecast_raw.get("model_rationale") or ""),
        "valuation_terminal_date": forecast_raw.get("valuation_terminal_date"),
        "valuation_terminal_date_basis": str(forecast_raw.get("valuation_terminal_date_basis") or ""),
        "entry_value_reference_per_share": forecast_raw.get("entry_value_reference_per_share"),
        "probabilities_calibrated": forecast_raw.get("probabilities_calibrated") is True,
        "assumptions": _records(forecast_raw.get("assumptions")),
        "cash_distribution_review": cash_distribution_review,
        "scenarios": forecast_raw.get("scenarios") if isinstance(forecast_raw.get("scenarios"), Mapping) else {},
        "thesis_break_stress": {
            "failure_trigger": str(stress_raw.get("failure_trigger") or ""),
            "operating_impact": str(stress_raw.get("operating_impact") or ""),
            "valuation_method": str(stress_raw.get("valuation_method") or ""),
            "terminal_value_per_share": stress_raw.get("terminal_value_per_share"),
            "cash_distributions_per_share": (
                str(stress_raw.get("cash_distributions_per_share"))
                if stress_raw.get("cash_distributions_per_share") is not None else None
            ),
            "rationale": str(stress_raw.get("rationale") or ""),
            "evidence_refs": _items(stress_raw.get("evidence_refs")),
        },
    }
    raw_driver_forecast, linked_cost_ratio_assumptions = _link_b4_cost_ratio_assumptions(
        raw_driver_forecast, forecast
    )
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
        requested_required_return = _number(
            parameters_raw.get("required_return_annualized", "0.15"),
            "REQUIRED_RETURN",
        )
    except LocalInvestmentPilotError as exc:
        # A present but malformed policy value is not the same as an omitted
        # legacy field/default. Do not silently loosen the user's hurdle.
        raise LocalInvestmentPilotError("REQUIRED_RETURN_POLICY_INVALID") from exc
    # Keep the operator's Required Return distinct from the fixed 15%
    # fundamental annualized-return hurdle. The return solver applies both
    # independent caps; raising a lower opportunity-cost benchmark to 15% here
    # would misstate the benchmark and its pass/fail result.
    required_return = requested_required_return
    try:
        max_loss = _number(parameters_raw.get("max_loss_pct", "25"), "MAX_LOSS_PCT")
    except LocalInvestmentPilotError as exc:
        raise LocalInvestmentPilotError("MAX_LOSS_PCT_POLICY_INVALID") from exc
    if max_loss < 0 or max_loss >= 100:
        raise LocalInvestmentPilotError("MAX_LOSS_PCT_OUT_OF_RANGE")

    # Resolve every structured evidence reference from assessment and valuation inputs,
    # before any structured risk/assumption objects are rendered for human readers.
    references = _collect_refs({
        "assessment": raw_assessment,
        "forecast_valuation": forecast_raw,
        "operating_driver_forecast": raw_driver_forecast,
        "valuation_transmission": raw_valuation_transmission,
        "sotp_valuation": raw_sotp_valuation,
    })
    unknown_refs = sorted(
        (references - source_ids)
        | (references & duplicate_source_ids)
        | (references & set(untraceable_evidence_fields))
    )
    after_cutoff_refs = [
        source["source_id"] for source in sources
        if source["source_id"] in references and source["time_status"] == "AFTER_CUTOFF"
    ]
    uncertain_timing_refs = [
        source["source_id"] for source in sources
        if source["source_id"] in references
        and source["time_status"] in {"UNKNOWN", "KNOWN_AT_INVALID", "KNOWN_AT_PRECISION_INSUFFICIENT"}
    ]

    # Each ranked driver is a decision-relevant claim of its own; section-level
    # Thesis citations cannot silently stand in for evidence linked to each row.
    for driver in assessment["value_drivers"]:
        refs = _items(driver.get("evidence_refs"))
        refs_unresolved = (
            not refs
            or any(ref not in source_ids for ref in refs)
            or bool(set(refs) & set(unknown_refs))
            or bool(set(refs) & set(after_cutoff_refs))
            or bool(set(refs) & set(uncertain_timing_refs))
        )
        if refs_unresolved:
            driver["status"] = "UNKNOWN"
            driver_issues = list(driver.get("status_issues") or [])
            driver_issues.append("DRIVER_EVIDENCE_LINK_NOT_RESOLVED")
            driver["status_issues"] = list(dict.fromkeys(driver_issues))

    # Structured risk items are separate decision-relevant claims. A general Risk
    # section citation cannot silently resolve an item's missing/broken own citation.
    unresolved_risk_item_refs: list[str] = []
    normalized_risk_items = list(assessment["risk"].get("items") or [])
    for index, item in enumerate(normalized_risk_items, start=1):
        if not isinstance(item, Mapping):
            # Legacy plain-text risk lists remain supported under section-level evidence.
            continue
        refs = _items(item.get("evidence_refs"))
        refs_unresolved = (
            not refs
            or any(ref not in source_ids for ref in refs)
            or bool(set(refs) & set(unknown_refs))
            or bool(set(refs) & set(after_cutoff_refs))
            or bool(set(refs) & set(uncertain_timing_refs))
        )
        if refs_unresolved:
            risk_item = dict(item)
            risk_item["status"] = "UNKNOWN"
            risk_item_issues = list(risk_item.get("status_issues") or [])
            risk_item_issues.append("RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED")
            risk_item["status_issues"] = list(dict.fromkeys(risk_item_issues))
            normalized_risk_items[index - 1] = risk_item
            label = str(item.get("risk_id") or item.get("name") or item.get("title") or f"ITEM_{index}")
            unresolved_risk_item_refs.append(label)
    assessment["risk"]["items"] = normalized_risk_items
    if unresolved_risk_item_refs:
        risk_status_issues = list(assessment["risk"].get("status_issues") or [])
        risk_status_issues.append("RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED")
        if "PASS" == assessment["risk"].get("status"):
            assessment["risk"]["status"] = "UNKNOWN"
        assessment["risk"]["status_issues"] = list(dict.fromkeys(risk_status_issues))

    # A section-level PASS must not override a child risk row whose own status
    # is UNKNOWN, FAIL, or unsupported. Preserve the supplied row status for audit,
    # but downgrade the overall assessment and surface a canonical issue.
    normalized_risk_items = list(assessment["risk"].get("items") or [])
    nonpassing_risk_items = []
    for index, item in enumerate(normalized_risk_items):
        if not isinstance(item, Mapping):
            continue
        item_status = str(item.get("status") or "UNKNOWN").strip().upper()
        if item_status == "PASS":
            continue
        nonpassing_risk_items.append(item)
        if not list(item.get("status_issues") or []):
            item = dict(item)
            item["status_issues"] = ["RISK_ITEM_STATUS_NOT_PASS"]
            normalized_risk_items[index] = item
    if nonpassing_risk_items:
        assessment["risk"]["items"] = normalized_risk_items
        risk_status_issues = list(assessment["risk"].get("status_issues") or [])
        risk_status_issues.append("RISK_ITEM_STATUS_NOT_PASS")
        if assessment["risk"].get("status") == "PASS":
            assessment["risk"]["status"] = "UNKNOWN"
        assessment["risk"]["status_issues"] = list(dict.fromkeys(risk_status_issues))

    # A passing Trust/Reality/Quality/MIE/Expectation Gap/Risk claim, or an INTACT
    # Thesis, must be linked to at least one uniquely resolved, cutoff-compatible
    # evidence ID. A source elsewhere in the register is not support for every gate.
    for name in allowed_assessment:
        section = assessment[name]
        status = section.get("status")
        requires_evidence = status == "PASS" or (name == "thesis" and status == "INTACT")
        if not requires_evidence:
            continue
        refs = _items(section.get("evidence_refs"))
        refs_unresolved = (
            not refs
            or any(ref not in source_ids for ref in refs)
            or bool(set(refs) & set(unknown_refs))
            or bool(set(refs) & set(after_cutoff_refs))
            or bool(set(refs) & set(uncertain_timing_refs))
        )
        if refs_unresolved:
            section["status"] = "UNKNOWN"
            status_issues = list(section.get("status_issues") or [])
            status_issues.append("ASSESSMENT_PASS_EVIDENCE_LINK_NOT_RESOLVED")
            section["status_issues"] = list(dict.fromkeys(status_issues))
    operating_driver_forecast = evaluate_operating_driver_forecast(
        raw_driver_forecast,
        evidence_register=sources,
        unresolved_evidence_ids=unknown_refs,
        after_cutoff_evidence_ids=after_cutoff_refs,
        uncertain_timing_evidence_ids=uncertain_timing_refs,
    )
    if linked_cost_ratio_assumptions:
        operating_driver_forecast["cross_node_assumption_links"] = linked_cost_ratio_assumptions
    operating_driver_forecast["valuation_reconciliation"] = _reconcile_b4_valuation_bridge(
        operating_driver_forecast, forecast
    )
    allowed_model_families = {"EPS_MULTIPLE", "FCF_DCF", "DDM", "SOTP", "RNPV", "OTHER", "UNKNOWN"}
    operator_context_raw = raw_operator_valuation_context if isinstance(raw_operator_valuation_context, Mapping) else {}
    selected_model_family = str(operator_context_raw.get("selected_model_family") or "UNKNOWN").strip().upper()
    if selected_model_family not in allowed_model_families:
        selected_model_family = "UNKNOWN"
    selection_source = str(
        operator_context_raw.get("selection_source") or "LEGACY_OPERATOR_INPUT_UNVERIFIED"
    ).strip().upper()
    selection_confirmed = operator_context_raw.get("selection_confirmed") is True
    # A wizard's explicit "0 = 暂不确认" is authoritative: downstream code must
    # not reinterpret any stale/AI-supplied family as an operator confirmation.
    if selection_source == "INTERACTIVE_OPERATOR_PROMPT" and not selection_confirmed:
        selected_model_family = "UNKNOWN"
    baseline_includes_raw = operator_context_raw.get("baseline_includes_project")
    baseline_includes_project = baseline_includes_raw if isinstance(baseline_includes_raw, bool) else None
    operator_valuation_context = {
        "selected_model_family": selected_model_family,
        "baseline_includes_project": baseline_includes_project,
        "input_owner": "OPERATOR",
        "selection_source": selection_source,
        "selection_confirmed": selection_confirmed,
    }
    eps_earnings_bridge = _evaluate_eps_earnings_bridge(
        raw_eps_multiple_valuation,
        selected_model_family=operator_valuation_context["selected_model_family"],
        expected_forecast_period=operating_driver_forecast.get("forecast_period"),
        expected_terminal_date=forecast.get("valuation_terminal_date"),
        expected_currency=currency,
        operating_driver_forecast=operating_driver_forecast,
        valuation_transmission={"status": "PENDING_VALIDATION", "applied_to_per_share_scenarios": False},
        operator_baseline_includes_project=operator_valuation_context["baseline_includes_project"],
        evidence_register=sources,
        unresolved_evidence_ids=unknown_refs,
        after_cutoff_evidence_ids=after_cutoff_refs,
        uncertain_timing_evidence_ids=uncertain_timing_refs,
    )
    eps_multiple_valuation = _evaluate_primary_eps_multiple_valuation(
        raw_eps_multiple_valuation,
        selected_model_family=operator_valuation_context["selected_model_family"],
        expected_forecast_period=operating_driver_forecast.get("forecast_period"),
        expected_terminal_date=forecast.get("valuation_terminal_date"),
        expected_currency=currency,
        evidence_register=sources,
        eps_earnings_bridge=eps_earnings_bridge,
        unresolved_evidence_ids=unknown_refs,
        after_cutoff_evidence_ids=after_cutoff_refs,
        uncertain_timing_evidence_ids=uncertain_timing_refs,
    )
    if (
        operator_valuation_context["selected_model_family"] == "EPS_MULTIPLE"
        and eps_multiple_valuation.get("status") == "CALCULATED"
        and forecast.get("model_family") == "EPS_MULTIPLE"
        and _infer_model_family_from_name(forecast.get("model")) == "EPS_MULTIPLE"
    ):
        original_scenarios = forecast.get("scenarios") if isinstance(forecast.get("scenarios"), Mapping) else {}
        normalized_scenarios = {
            key: dict(value) if isinstance(value, Mapping) else {}
            for key, value in original_scenarios.items()
        }
        for scenario_name in SCENARIOS:
            scenario_row = normalized_scenarios.get(scenario_name, {})
            scenario_row["declared_terminal_value_before_eps_multiple_calculation"] = scenario_row.get("terminal_value_per_share")
            scenario_row["terminal_value_per_share"] = eps_multiple_valuation["scenarios"][scenario_name]["terminal_value_per_share"]
            scenario_row["eps_multiple_calculation_applied"] = True
            normalized_scenarios[scenario_name] = scenario_row
        forecast["scenarios"] = normalized_scenarios
        forecast["declared_entry_value_reference_before_eps_multiple_calculation"] = forecast.get("entry_value_reference_per_share")
        forecast["entry_value_reference_per_share"] = eps_multiple_valuation["scenarios"]["base"]["terminal_value_per_share"]
        # Preserve the analyst's model-selection/fit rationale independently from arithmetic.
        # The separate adapter report carries the local EPS × P/E calculation.
    sotp_valuation = evaluate_sotp_valuation(
        raw_sotp_valuation,
        selected_model_family=operator_valuation_context["selected_model_family"],
        expected_forecast_period=operating_driver_forecast.get("forecast_period"),
        expected_terminal_date=forecast.get("valuation_terminal_date"),
        evidence_register=sources,
        expected_currency=currency,
        unresolved_evidence_ids=unknown_refs,
        after_cutoff_evidence_ids=after_cutoff_refs,
        uncertain_timing_evidence_ids=uncertain_timing_refs,
    )
    if (
        operator_valuation_context["selected_model_family"] == "SOTP"
        and sotp_valuation.get("status") == "CALCULATED"
    ):
        # Only independently recomputed SOTP values can enter the primary price path.
        # Preserve input values as untrusted diagnostics for audit.
        original_scenarios = forecast.get("scenarios") if isinstance(forecast.get("scenarios"), Mapping) else {}
        normalized_scenarios = {
            key: dict(value) if isinstance(value, Mapping) else {}
            for key, value in original_scenarios.items()
        }
        for scenario_name in ("bear", "base", "bull"):
            scenario_row = normalized_scenarios.get(scenario_name, {})
            scenario_row["declared_terminal_value_before_sotp_calculation"] = scenario_row.get("terminal_value_per_share")
            scenario_row["terminal_value_per_share"] = sotp_valuation["scenarios"][scenario_name]["terminal_value_per_share"]
            scenario_row["sotp_calculation_applied"] = True
            normalized_scenarios[scenario_name] = scenario_row
        forecast["scenarios"] = normalized_scenarios
        forecast["declared_entry_value_reference_before_sotp_calculation"] = forecast.get("entry_value_reference_per_share")
        forecast["entry_value_reference_per_share"] = sotp_valuation["scenarios"]["base"]["terminal_value_per_share"]
        forecast["model_rationale_original_untrusted"] = forecast.get("model_rationale")
        forecast["model_rationale"] = (
            "SOTP 终值由本地 SOTP 适配器复算：使用按上市公司股东口径计算、且未扣除未分配母公司层面税后成本的分部净利润分别乘以各自 P/E，"
            "再减资本化母公司税后成本，加减不重复计价的净现金/净负债及其他显式调整，"
            "最后除以稀释后股数；详细输入、期间、证据引用与算术见 sotp_valuation。"
        )
        forecast["model"] = "SOTP (segment attributable net profit x segment P/E plus explicit parent-level adjustments)"
        forecast["model_family"] = "SOTP"
    _neutralize_stale_model_confirmation_language(forecast, operator_valuation_context)
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
    if operator_valuation_context["selected_model_family"] == "EPS_MULTIPLE":
        # Revalidate project inclusion against the actual B5 result after B5 has
        # evaluated its complete input. The initial bridge pass uses PENDING_VALIDATION
        # to avoid a circular dependency: B5 needs the recalculated EPS terminal value.
        final_eps_earnings_bridge = _evaluate_eps_earnings_bridge(
            raw_eps_multiple_valuation,
            selected_model_family=operator_valuation_context["selected_model_family"],
            expected_forecast_period=operating_driver_forecast.get("forecast_period"),
            expected_terminal_date=forecast.get("valuation_terminal_date"),
            expected_currency=currency,
            operating_driver_forecast=operating_driver_forecast,
            valuation_transmission=valuation_transmission,
            operator_baseline_includes_project=operator_valuation_context["baseline_includes_project"],
            evidence_register=sources,
            unresolved_evidence_ids=unknown_refs,
            after_cutoff_evidence_ids=after_cutoff_refs,
            uncertain_timing_evidence_ids=uncertain_timing_refs,
        )
        eps_earnings_bridge = final_eps_earnings_bridge
        eps_multiple_valuation = _evaluate_primary_eps_multiple_valuation(
            raw_eps_multiple_valuation,
            selected_model_family=operator_valuation_context["selected_model_family"],
            expected_forecast_period=operating_driver_forecast.get("forecast_period"),
            expected_terminal_date=forecast.get("valuation_terminal_date"),
            expected_currency=currency,
            evidence_register=sources,
            eps_earnings_bridge=eps_earnings_bridge,
            unresolved_evidence_ids=unknown_refs,
            after_cutoff_evidence_ids=after_cutoff_refs,
            uncertain_timing_evidence_ids=uncertain_timing_refs,
        )
        if eps_multiple_valuation.get("status") != "CALCULATED":
            # Do not leave an EPS×P/E number in the primary terminal-value slot after
            # the final B5/project-inclusion revalidation invalidates the EPS bridge.
            scenario_rows = forecast.get("scenarios") if isinstance(forecast.get("scenarios"), Mapping) else {}
            restored_rows = {
                key: dict(value) if isinstance(value, Mapping) else value
                for key, value in scenario_rows.items()
            }
            for scenario_name in SCENARIOS:
                row = restored_rows.get(scenario_name)
                if not isinstance(row, dict):
                    continue
                if "declared_terminal_value_before_eps_multiple_calculation" in row:
                    row["terminal_value_per_share"] = row.get("declared_terminal_value_before_eps_multiple_calculation")
                row.pop("eps_multiple_calculation_applied", None)
                row.pop("b5_baseline_terminal_value_per_share", None)
                row.pop("b5_transmission_applied", None)
            forecast["scenarios"] = restored_rows
            forecast["entry_value_reference_per_share"] = forecast.get(
                "declared_entry_value_reference_before_eps_multiple_calculation",
                forecast.get("entry_value_reference_per_share"),
            )
            forecast.pop("b5_baseline_entry_value_reference_per_share", None)
            if valuation_transmission.get("applied_to_per_share_scenarios") is True:
                rejected_status = valuation_transmission.get("status")
                valuation_transmission = dict(valuation_transmission)
                valuation_transmission["pre_eps_bridge_status"] = rejected_status
                valuation_transmission["status"] = "NOT_LINKED_EPS_EARNINGS_BRIDGE_INELIGIBLE"
                valuation_transmission["applied_to_per_share_scenarios"] = False
                valuation_transmission["input_issues"] = list(dict.fromkeys([
                    *(valuation_transmission.get("input_issues") or []),
                    "EPS_EARNINGS_BRIDGE_NOT_ELIGIBLE_AFTER_B5_REVALIDATION",
                ]))
    valuation_model_consistency = _build_valuation_model_consistency(
        operator_model_family=operator_valuation_context["selected_model_family"],
        forecast_model_family=forecast.get("model_family"),
        model_name=forecast.get("model"),
        model_rationale=forecast.get("model_rationale"),
        operating_driver_forecast=operating_driver_forecast,
        valuation_transmission=valuation_transmission,
        sotp_calculation_status=sotp_valuation.get("status", "UNKNOWN"),
        eps_multiple_calculation_status=eps_multiple_valuation.get("status", "UNKNOWN"),
        eps_multiple_calculation_issues=eps_multiple_valuation.get("issues", []),
    )
    valuation_timing = _build_valuation_timing(
        cutoff_date=cutoff.isoformat(),
        forecast_period=operating_driver_forecast.get("forecast_period"),
        valuation_terminal_date=forecast.get("valuation_terminal_date"),
        valuation_terminal_date_basis=forecast.get("valuation_terminal_date_basis"),
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
            "entry_assumption": {
                "schema_version": "IIOS-ENTRY-PRICE-ASSUMPTION-0.1",
                "mode": "HYPOTHETICAL_ENTRY_AT_INPUT_PRICE_ON_CUTOFF_DATE",
                "hypothetical_entry_date": cutoff.isoformat(),
                "price_observation_date": observation.isoformat(),
                "price_observation_vs_cutoff": (
                    "SAME_CALENDAR_DATE" if observation == cutoff
                    else "PRIOR_DATE_REFERENCE" if observation < cutoff
                    else "AFTER_CUTOFF_NOT_ELIGIBLE"
                ),
                "price_known_before_cutoff": known_at < cutoff_instant,
                "actual_execution_status": "NOT_CONFIRMED",
                "actual_execution_confirmed": False,
                "execution_guaranteed": False,
                "dividend_entitlement_status": "CONDITIONAL_ON_HYPOTHETICAL_ENTRY",
                "actual_dividend_entitlement_confirmed": False,
                "note": (
                    "回报/目标入场价是条件性反事实测算，假设在分析截止日以输入参考价格买入；"
                    "price_input 是观测价而非成交回报，不证明实际可按该价格成交，也不证明实际分红权益。"
                ),
            },
        },
        "evidence_register": sources,
        "duplicate_evidence_ids": sorted(duplicate_source_ids),
        "untraceable_evidence_ids": sorted(untraceable_evidence_fields),
        "untraceable_evidence_fields": {
            source_id: fields for source_id, fields in sorted(untraceable_evidence_fields.items())
        },
        "assessment": assessment,
        "forecast_valuation": forecast,
        "eps_multiple_valuation": eps_multiple_valuation,
        "eps_earnings_bridge": eps_earnings_bridge,
        "operating_driver_forecast": operating_driver_forecast,
        "valuation_transmission": valuation_transmission,
        "sotp_valuation": sotp_valuation,
        "operator_valuation_context": operator_valuation_context,
        "valuation_model_consistency": valuation_model_consistency,
        "valuation_timing": valuation_timing,
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
    model_consistency = prepared.get("valuation_model_consistency") or {}
    if model_consistency.get("primary_model_price_calculation_eligible") is not True:
        return None, f"PRIMARY_VALUATION_MODEL_NOT_ELIGIBLE:{model_consistency.get('status', 'UNKNOWN')}"
    valuation_timing = prepared.get("valuation_timing") or {}
    if valuation_timing.get("status") != "PASS":
        return None, f"VALUATION_TIMING_NOT_RESOLVED:{valuation_timing.get('status', 'UNKNOWN')}"
    if prepared["price_input"]["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        return None, "PRICE_NOT_PIT_QUALIFIED"
    forecast = prepared["forecast_valuation"]
    anchor = forecast.get("entry_value_reference_per_share")
    scenarios = forecast.get("scenarios") or {}
    if anchor in (None, "") or not isinstance(scenarios, Mapping) or set(scenarios) != set(SCENARIOS):
        return None, "ENTRY_REFERENCE_OR_BEAR_BASE_BULL_SCENARIOS_MISSING"

    # Zero is only acceptable when the analyst explicitly confirms no future
    # distribution over the holding horizon; positive amounts require dated,
    # evidence-linked cashflows instead of an implicit terminal-date assumption.
    review = forecast.get("cash_distribution_review")
    if not isinstance(review, Mapping):
        return None, "CASH_DISTRIBUTION_REVIEW_NOT_RESOLVED"
    review_status = str(review.get("status") or "UNKNOWN").strip().upper()
    if review_status not in {"KNOWN_FUTURE_DISTRIBUTIONS", "NO_FUTURE_DISTRIBUTIONS_CONFIRMED"}:
        return None, "CASH_DISTRIBUTION_REVIEW_NOT_RESOLVED"
    if not _is_identifiable_evidence_text(review.get("summary")):
        return None, "CASH_DISTRIBUTION_REVIEW_RATIONALE_NOT_IDENTIFIABLE"
    review_refs = _items(review.get("evidence_refs"))
    if not review_refs:
        return None, "CASH_DISTRIBUTION_REVIEW_EVIDENCE_MISSING"
    evidence_by_id = {
        str(item.get("source_id")): item
        for item in (prepared.get("evidence_register") or [])
        if isinstance(item, Mapping) and item.get("source_id")
    }
    blocked_source_ids = (
        set(prepared.get("unresolved_evidence_references") or [])
        | set(prepared.get("after_cutoff_evidence_references") or [])
        | set(prepared.get("uncertain_timing_evidence_references") or [])
    )
    bad_timing = {"UNKNOWN", "KNOWN_AT_INVALID", "KNOWN_AT_PRECISION_INSUFFICIENT", "AFTER_CUTOFF"}
    primary_classes = {"ISSUER_PRIMARY", "EXCHANGE_PRIMARY", "REGULATOR_PRIMARY"}
    for ref in review_refs:
        source = evidence_by_id.get(str(ref))
        if (
            source is None or str(ref) in blocked_source_ids
            or source.get("time_status") in bad_timing
            or str(source.get("source_class") or "").upper() not in primary_classes
        ):
            return None, "CASH_DISTRIBUTION_REVIEW_EVIDENCE_NOT_CUTOFF_COMPATIBLE_PRIMARY"
        if source.get("cash_distribution_primary_domain_eligible") is not True:
            return None, "CASH_DISTRIBUTION_REVIEW_SOURCE_DOMAIN_CLASS_NOT_ACCEPTED"

    cutoff_date = _date((prepared.get("case") or {}).get("as_of_date"), "CASE_AS_OF_DATE")
    try:
        terminal_date = _date(forecast.get("valuation_terminal_date"), "VALUATION_TERMINAL_DATE")
    except LocalInvestmentPilotError:
        return None, "VALUATION_TERMINAL_DATE_NOT_IDENTIFIABLE"
    if terminal_date <= cutoff_date:
        return None, "VALUATION_TERMINAL_DATE_NOT_AFTER_CUTOFF"

    rows: dict[str, Any] = {}
    for name in SCENARIOS:
        row = scenarios.get(name)
        if not isinstance(row, Mapping):
            return None, f"{name.upper()}_SCENARIO_MISSING"
        if row.get("probability") in (None, "") or row.get("terminal_value_per_share") in (None, ""):
            return None, f"{name.upper()}_SCENARIO_INPUTS_INCOMPLETE"
        if row.get("cash_distributions_per_share") in (None, ""):
            return None, f"{name.upper()}_SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED"
        if not _is_identifiable_evidence_text(row.get("rationale")):
            return None, f"{name.upper()}_SCENARIO_PROBABILITY_RATIONALE_NOT_IDENTIFIABLE"
        try:
            distributions = _number(row.get("cash_distributions_per_share"), f"SCENARIO_{name}_DISTRIBUTIONS")
        except LocalInvestmentPilotError:
            return None, f"{name.upper()}_SCENARIO_CASH_DISTRIBUTIONS_INVALID"
        events_raw = row.get("cash_distribution_events") or []
        if not isinstance(events_raw, list):
            return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENTS_INVALID"
        normalized_events: list[dict[str, Any]] = []
        event_total = Decimal("0")
        for index, event in enumerate(events_raw, start=1):
            if not isinstance(event, Mapping):
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_INVALID"
            try:
                amount = _positive(event.get("amount_per_share"), f"{name.upper()}_DISTRIBUTION_{index}_NET_AMOUNT")
                gross_amount = _positive(event.get("gross_amount_per_share"), f"{name.upper()}_DISTRIBUTION_{index}_GROSS_AMOUNT")
                tax_amount = _number(event.get("tax_amount_per_share"), f"{name.upper()}_DISTRIBUTION_{index}_TAX_AMOUNT")
                record_date = _date(event.get("record_date"), f"{name.upper()}_DISTRIBUTION_{index}_RECORD_DATE")
                ex_date = _date(event.get("ex_date"), f"{name.upper()}_DISTRIBUTION_{index}_EX_DATE")
                payment_date = _date(event.get("payment_date"), f"{name.upper()}_DISTRIBUTION_{index}_PAYMENT_DATE")
            except LocalInvestmentPilotError:
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_INVALID"
            if tax_amount < 0 or tax_amount >= gross_amount or abs((gross_amount - tax_amount) - amount) > Decimal("0.000001"):
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_GROSS_TAX_NET_MISMATCH"
            market = str((prepared.get("case") or {}).get("market") or "UNKNOWN").strip().upper()
            if market == "CN-A":
                # Mainland A-share practice: the record date precedes the ex-date;
                # a buyer entering after the cutoff must still be able to qualify
                # on the record date before the ex-date adjustment.
                dates_eligible = cutoff_date < record_date < ex_date <= payment_date <= terminal_date
            elif market == "HK":
                # Hong Kong T+2 practice: the ex-date is normally before the last
                # registration/record date (and can coincide with the second ex-date
                # under special book-close arrangements). Do not impose A-share order
                # on Hong Kong entitlements.
                dates_eligible = cutoff_date < ex_date <= record_date <= payment_date <= terminal_date
            else:
                # Unknown market or exceptional announced chronology needs review,
                # not an inferred cross-market convention.
                dates_eligible = False
            if not dates_eligible:
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_DATES_NOT_ELIGIBLE_FROM_CUTOFF"
            if event.get("eligible_if_entered_at_cutoff") is not True:
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_ENTRY_ELIGIBILITY_NOT_CONFIRMED"
            if not _is_identifiable_evidence_text(event.get("eligibility_basis")):
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_ELIGIBILITY_BASIS_NOT_IDENTIFIABLE"
            if not _is_identifiable_evidence_text(event.get("tax_basis")) or not _is_identifiable_evidence_text(event.get("tax_rationale")):
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_TAX_BASIS_NOT_IDENTIFIABLE"
            event_refs = _items(event.get("evidence_refs"))
            if not event_refs:
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_EVIDENCE_MISSING"
            for ref in event_refs:
                source = evidence_by_id.get(str(ref))
                if (
                    source is None or str(ref) in blocked_source_ids
                    or source.get("time_status") in bad_timing
                    or str(source.get("source_class") or "").upper() not in primary_classes
                ):
                    return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_EVIDENCE_NOT_CUTOFF_COMPATIBLE_PRIMARY"
                if source.get("cash_distribution_primary_domain_eligible") is not True:
                    return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_{index}_SOURCE_DOMAIN_CLASS_NOT_ACCEPTED"
            years = Decimal((payment_date - cutoff_date).days) / Decimal("365")
            event_total += amount
            normalized_events.append({
                "amount_per_share": str(amount),
                "gross_amount_per_share": str(gross_amount),
                "tax_amount_per_share": str(tax_amount),
                "tax_basis": str(event.get("tax_basis")),
                "tax_rationale": str(event.get("tax_rationale")),
                "record_date": record_date.isoformat(),
                "ex_date": ex_date.isoformat(),
                "payment_date": payment_date.isoformat(),
                "eligible_if_entered_at_cutoff": True,
                "eligibility_assumption": "CONDITIONAL_ON_HYPOTHETICAL_ENTRY_AT_INPUT_PRICE_ON_CUTOFF_DATE",
                "actual_execution_confirmed": False,
                "actual_dividend_entitlement_confirmed": False,
                "eligibility_basis": str(event.get("eligibility_basis")),
                "evidence_refs": event_refs,
                "year_fraction_from_entry": format(years, "f"),
            })
        if review_status == "NO_FUTURE_DISTRIBUTIONS_CONFIRMED":
            if distributions != 0 or normalized_events:
                return None, "CASH_DISTRIBUTION_REVIEW_CONTRADICTS_SCENARIO_INPUT"
        else:
            if not normalized_events or distributions <= 0:
                return None, f"{name.upper()}_CASH_DISTRIBUTION_TIMING_UNRESOLVED"
            if abs(event_total - distributions) > Decimal("0.000001"):
                return None, f"{name.upper()}_CASH_DISTRIBUTION_EVENT_TOTAL_MISMATCH"
        rows[name] = {
            "probability": str(row["probability"]),
            "terminal_value_per_share": str(row["terminal_value_per_share"]),
            "cash_distributions_per_share": str(row["cash_distributions_per_share"]),
            "cash_distribution_events": normalized_events,
            "probability_rationale": str(row["rationale"]),
        }

    # Preserve the prior scenario-total-wealth ordering contract. Timing and tax
    # metadata change return arithmetic, not the requirement Bear <= Base <= Bull.
    try:
        scenario_wealth = {
            name: _number(rows[name]["terminal_value_per_share"], f"SCENARIO_{name}_TERMINAL")
            + _number(rows[name]["cash_distributions_per_share"], f"SCENARIO_{name}_DISTRIBUTIONS")
            for name in SCENARIOS
        }
    except LocalInvestmentPilotError as exc:
        return None, f"SCENARIO_CALCULATION_INCOMPLETE:{exc}"
    if not (scenario_wealth["bear"] <= scenario_wealth["base"] <= scenario_wealth["bull"]):
        return None, "SCENARIO_WEALTH_ORDERING_INCONSISTENT"

    params = prepared["decision_parameters"]
    gate = {
        "entry_price": prepared["price_input"]["price"],
        "entry_value_reference": str(anchor),
        "horizon_years": str(params["horizon_years"]),
        "annualization_year_fraction": str(valuation_timing["annualization_year_fraction"]),
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
        # Keep the source-validated dated events for the published forecast JSON.
        # The shared return solver intentionally returns only arithmetic outputs,
        # not the full source/tax/entitlement metadata needed for audit display.
        if isinstance(prepared, dict):
            prepared["_validated_cash_distribution_events"] = {
                name: [dict(event) for event in rows[name]["cash_distribution_events"]]
                for name in SCENARIOS
            }
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
        if item.get("status") != "CALCULATED":
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
        not _is_identifiable_evidence_text(bear.get(field)) for field in required_bear_fields
    ):
        issues.append("BEAR_FAILURE_PATH_INCOMPLETE")

    required_stress_fields = ("failure_trigger", "operating_impact", "valuation_method", "rationale")
    if any(not _is_identifiable_evidence_text(stress.get(field)) for field in required_stress_fields):
        issues.append("THESIS_BREAK_STRESS_INPUTS_INCOMPLETE")

    stress_wealth: Decimal | None = None
    if stress.get("cash_distributions_per_share") in (None, ""):
        issues.append("THESIS_BREAK_STRESS_CASH_DISTRIBUTIONS_UNRESOLVED")
    else:
        try:
            terminal_raw = stress.get("terminal_value_per_share")
            if terminal_raw in (None, ""):
                raise LocalInvestmentPilotError("STRESS_TERMINAL_VALUE_MISSING")
            terminal = _number(terminal_raw, "THESIS_BREAK_STRESS_TERMINAL")
            distributions = _number(
                stress.get("cash_distributions_per_share"),
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
            if bear.get("cash_distributions_per_share") in (None, ""):
                issues.append("THESIS_BREAK_STRESS_BEAR_CASH_DISTRIBUTIONS_UNRESOLVED")
                raise LocalInvestmentPilotError("BEAR_CASH_DISTRIBUTIONS_UNRESOLVED")
            bear_terminal = _number(bear.get("terminal_value_per_share"), "BEAR_TERMINAL")
            bear_distributions = _number(
                bear.get("cash_distributions_per_share"),
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
        for status_issue in a[name].get("status_issues") or []:
            # Risk-item issue codes already carry the RISK_ITEM namespace. Avoid
            # turning them into confusing RISK_RISK_ITEM decision codes.
            issue = (
                status_issue
                if name == "risk" and status_issue.startswith("RISK_ITEM_")
                else f"{name.upper()}_{status_issue}"
            )
            if issue not in issues:
                issues.append(issue)
    if a["expectation_gap"]["direction"] != "POSITIVE":
        issues.append(f"EXPECTATION_GAP_DIRECTION_{a['expectation_gap']['direction']}")
    if not prepared["evidence_register"]:
        issues.append("EVIDENCE_REGISTER_EMPTY")
    if prepared["unresolved_evidence_references"]:
        issues.append("UNRESOLVED_EVIDENCE_REFERENCES")
    referenced_duplicate_ids = (
        set(prepared.get("referenced_evidence_ids") or [])
        & set(prepared.get("duplicate_evidence_ids") or [])
    )
    if referenced_duplicate_ids:
        issues.append("DUPLICATE_EVIDENCE_SOURCE_IDS")
    referenced_untraceable_ids = (
        set(prepared.get("referenced_evidence_ids") or [])
        & set(prepared.get("untraceable_evidence_ids") or [])
    )
    if referenced_untraceable_ids:
        issues.append("UNTRACEABLE_EVIDENCE_SOURCE_RECORDS")
    if prepared["after_cutoff_evidence_references"]:
        issues.append("REFERENCED_EVIDENCE_AFTER_CUTOFF")
    if prepared["uncertain_timing_evidence_references"]:
        issues.append("REFERENCED_EVIDENCE_TIMING_UNCERTAIN")
    if p["pit_time_status"] != "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY":
        issues.append("PRICE_NOT_PIT_QUALIFIED")
    if prepared.get("notes_price_conflicts"):
        issues.append("OPERATOR_NOTE_PRICE_CONFLICTS_WITH_PRICE_INPUT")
    model_consistency = prepared.get("valuation_model_consistency") or {}
    if model_consistency.get("primary_model_price_calculation_eligible") is not True:
        issues.append("PRIMARY_VALUATION_MODEL_NOT_DECISION_ELIGIBLE")
    valuation_timing = prepared.get("valuation_timing") or {}
    if valuation_timing.get("status") != "PASS":
        issues.append("VALUATION_TIMING_NOT_RESOLVED")
    if reason == "SCENARIO_WEALTH_ORDERING_INCONSISTENT":
        issues.append("SCENARIO_WEALTH_ORDERING_INCONSISTENT")
    if reason and reason.endswith("_SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED"):
        issues.append("SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED")
    if reason and (
        "CASH_DISTRIBUTION_REVIEW_SOURCE_DOMAIN_CLASS_NOT_ACCEPTED" in reason
        or ("_CASH_DISTRIBUTION_EVENT_" in reason and "SOURCE_DOMAIN_CLASS_NOT_ACCEPTED" in reason)
    ):
        issues.append("CASH_DISTRIBUTION_SOURCE_DOMAIN_CLASS_NOT_ACCEPTED")
    if stress_review:
        issues.extend(issue for issue in (stress_review.get("issues") or []) if issue not in issues)

    # Input/provenance faults are distinct from economic assessment states.
    validation_blockers = {
        "EVIDENCE_REGISTER_EMPTY",
        "UNRESOLVED_EVIDENCE_REFERENCES",
        "DUPLICATE_EVIDENCE_SOURCE_IDS",
        "UNTRACEABLE_EVIDENCE_SOURCE_RECORDS",
        "REFERENCED_EVIDENCE_AFTER_CUTOFF",
        "REFERENCED_EVIDENCE_TIMING_UNCERTAIN",
        "PRICE_NOT_PIT_QUALIFIED",
        "OPERATOR_NOTE_PRICE_CONFLICTS_WITH_PRICE_INPUT",
        "SCENARIO_WEALTH_ORDERING_INCONSISTENT",
        "SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED",
        "CASH_DISTRIBUTION_SOURCE_DOMAIN_CLASS_NOT_ACCEPTED",
        "BEAR_FAILURE_PATH_INCOMPLETE",
        "THESIS_BREAK_STRESS_INPUTS_INCOMPLETE",
        "THESIS_BREAK_STRESS_VALUE_INVALID",
        "THESIS_BREAK_STRESS_CASH_DISTRIBUTIONS_UNRESOLVED",
        "THESIS_BREAK_STRESS_BEAR_CASH_DISTRIBUTIONS_UNRESOLVED",
        "THESIS_BREAK_STRESS_BEAR_COMPARISON_UNAVAILABLE",
        "THESIS_BREAK_STRESS_NOT_MORE_SEVERE_THAN_BEAR",
        "THESIS_BREAK_STRESS_MISSING",
        "PRIMARY_VALUATION_MODEL_NOT_DECISION_ELIGIBLE",
        "VALUATION_TIMING_NOT_RESOLVED",
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
            row.get("status") == "PASS" for row in a["value_drivers"]
        ) else "UNKNOWN"
    )
    for row in a["value_drivers"]:
        for status_issue in row.get("status_issues") or []:
            issue = f"VALUE_DRIVER_{status_issue}"
            if issue not in issues:
                issues.append(issue)
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
    model_contract = analysis.get("valuation_model_consistency") or {}
    primary_model_eligible = model_contract.get("primary_model_price_calculation_eligible") is True
    model_anchor_label = (
        "主估值参考锚"
        if primary_model_eligible
        else "候选模型参考锚（主模型门禁未通过，仅供诊断）"
    )
    model_name_label = (
        "主估值计算模型"
        if primary_model_eligible
        else "候选模型（未获主模型门禁批准）"
    )
    model_rationale_label = (
        "主模型选择理由"
        if primary_model_eligible
        else "研究回答中的候选模型理由（未经主模型门禁认可）"
    )
    lines = [
        f"# IIOS 本地投资研究试运行：{c['company']}（{c['symbol']}）",
        "",
        f"- 运行等级：**{PILOT_STATUS}**",
        f"- 分析截止：{c.get('as_of_timestamp') or (c['as_of_date'] + ' 00:00:00+08:00（日期级截止）')}；当前价：{p['price']} {c['currency']}（观察日 {p['observation_date']}，价格可获得时点 {p['known_at']}）",
        f"- 入场价口径：假设在截止日以输入参考价 {p['price']} {c['currency']} 买入的反事实测算；实际成交：未确认，不保证能以该价格成交。",
        f"- 参考价时效：{(p.get('entry_assumption') or {}).get('price_observation_vs_cutoff', 'UNKNOWN')}；分红资格只表示该反事实入场下的条件判断，不代表实际成交或实际分红权益已确认。",
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
        f"- Trust：{_assessment_status_for_report(a['trust'])} — {a['trust'].get('summary') or '未知'}",
        f"- Reality：{_assessment_status_for_report(a['reality'])} — {a['reality'].get('summary') or '未知'}",
        f"- Quality：{_assessment_status_for_report(a['quality'])} — {a['quality'].get('summary') or '未知'}",
        "",
        "## 三、Thesis 与价值驱动因素",
        "",
        f"- Thesis 状态：{_assessment_status_for_report(a['thesis'])}",
        "",
        "### 核心论点",
        "",
    ]
    lines.extend(_format_text_block(a["thesis"].get("core_statement")))
    lines.extend(["", "### 价值驱动因素", ""])
    drivers = sorted(a["value_drivers"], key=lambda x: (x["rank"], x["driver"]))
    driver_issue_explanations = {
        "DRIVER_NAME_NOT_IDENTIFIABLE": "驱动因素名称为空或仅为占位文本。",
        "IMPACT_NOT_IDENTIFIABLE": "影响方向未知，不能作为已确认的价值驱动因素。",
        "RATIONALE_NOT_IDENTIFIABLE": "驱动机制/理由为空或仅为占位文本。",
        "HISTORICAL_EVIDENCE_NOT_IDENTIFIABLE": "没有给出可识别的历史经营依据，无法验证驱动的基线或变化起点。",
        "VALUATION_TRANSMISSION_NOT_IDENTIFIABLE": "没有说明驱动如何传导到收入、利润、现金流或每股价值。",
        "DRIVER_EVIDENCE_LINK_NOT_RESOLVED": "该价值驱动因素没有自己的可追溯截止时点证据，或其引用无法唯一解析/时点不兼容。",
        "RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED": "至少一个结构化风险项没有自己的可追溯截止时点证据，或其引用无法唯一解析/时点不兼容；整体风险状态不能视为 PASS。",

        "RANK_NOT_IDENTIFIABLE": "排名字段不是有效的正整数；为避免中断报告，按输入顺序临时展示，但该驱动因素不通过内容门禁。",
        "DUPLICATE_RANK_NOT_IDENTIFIABLE": "多个价值驱动因素使用相同排名，排序不唯一；相关条目均降为 UNKNOWN。",
    }
    if drivers:
        for display_rank, item in enumerate(drivers, start=1):
            lines.append(
                f"**价值驱动因素 {display_rank}：{item['driver']}**"
                f"（影响：{item['impact']}；内容门禁：{item.get('status', 'UNKNOWN')}）"
            )
            if item.get("driver_type"):
                lines.append(f"   类型：{item['driver_type']}")
            lines.append(f"   历史依据：{item.get('historical_evidence') or 'UNKNOWN'}")
            lines.append(f"   价值传导：{item.get('valuation_transmission') or 'UNKNOWN'}")
            unresolved_inputs = item.get("unresolved_inputs") if isinstance(item.get("unresolved_inputs"), list) else []
            if unresolved_inputs:
                lines.append("   尚待验证的经营输入：")
                lines.extend(f"   - {gap}" for gap in unresolved_inputs)
            if item.get("rationale") and item["rationale"] != item.get("valuation_transmission"):
                lines.append(f"   研究理由：{item['rationale']}")
            elif not item.get("rationale") and not item.get("valuation_transmission"):
                lines.append("   研究理由：UNKNOWN")
            if item.get("status_issues"):
                lines.append("   内容门禁问题：" + "；".join(
                    f"{issue}（{driver_issue_explanations.get(issue, issue)}）"
                    for issue in item["status_issues"]
                ))
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
        f"- {model_name_label}：{f['model']}",
        f"- {model_rationale_label}（清理状态 {f.get('model_rationale_status', 'UNKNOWN')}）：{f['model_rationale'] or '未提供'}",
        f"- 现金分配核查（模型输入声明，非正式证据准入）：{(f.get('cash_distribution_review') or {}).get('status', 'UNKNOWN')}；来源域名/类别核验：{(f.get('cash_distribution_review') or {}).get('source_validation_status', 'UNKNOWN')}；正式证据准入：未完成；{(f.get('cash_distribution_review') or {}).get('summary', '未提供') or '未提供'}；证据 {', '.join((f.get('cash_distribution_review') or {}).get('evidence_refs') or []) or 'UNKNOWN'}。",
        f"- {model_anchor_label}（不是 15% 回报门槛价格，也不是 MIE）：{f.get('entry_value_reference_per_share') or 'UNKNOWN'} {c['currency']}/股",
        f"- EPS_MULTIPLE 原始声明锚（仅供审计，不进入主计算）：{f.get('declared_entry_value_reference_before_eps_multiple_calculation', 'UNKNOWN')}",
        f"- 情景概率是否校准：{'是' if f['probabilities_calibrated'] else '否 / 未校准'}",
        "",
    ])
    model_contract = analysis.get("valuation_model_consistency") or {}
    timing_contract = analysis.get("valuation_timing") or {}
    lines.extend([
        "### 主估值模型一致性门禁",
        "",
        f"- 操作者选择的主模型类别：{model_contract.get('operator_selected_model_family', 'UNKNOWN')}",
        f"- 模型选择来源：{(analysis.get('operator_valuation_context') or {}).get('selection_source', 'LEGACY_OPERATOR_INPUT_UNVERIFIED')}；操作者是否明确确认：{(analysis.get('operator_valuation_context') or {}).get('selection_confirmed', False)}",
        f"- 当前情景实际计算模型类别：{model_contract.get('calculation_model_family', 'UNKNOWN')}（{model_contract.get('calculation_model_name', 'UNKNOWN')}）",
        f"- 根据模型名称解析出的类别：{model_contract.get('model_name_inferred_family', 'UNKNOWN')}；名称/类别交叉校验：{model_contract.get('model_family_name_crosscheck', 'UNKNOWN')}",
        f"- 一致性状态：**{model_contract.get('status', 'UNKNOWN')}**；可用于主模型价格计算：{model_contract.get('primary_model_price_calculation_eligible', False)}",
        f"- B5 传导状态：{model_contract.get('valuation_transmission_status', 'UNKNOWN')}；经营预测范围：{model_contract.get('operating_forecast_scope', 'UNKNOWN')}",
        f"- SOTP 适配器计算状态：{model_contract.get('sotp_calculation_status', 'UNKNOWN')}",
        f"- EPS_MULTIPLE 主估值适配器计算状态：{model_contract.get('eps_multiple_calculation_status', 'UNKNOWN')}",
        *(["- 门禁原因：" + "; ".join(model_contract.get("issues") or [])] if model_contract.get("issues") else []),
        *([] if model_contract.get("primary_model_price_calculation_eligible") is True else ["- 本报告保留的情景价值只作为替代模型/未确认模型研究输入，不进入预期回报、目标入场价或 B6 价格敏感性计算。"]),
        "",
        "### 估值终点与年化期限契约",
        "",
        f"- 预测期间：{timing_contract.get('forecast_period', 'UNKNOWN')}",
        f"- 显式估值终点日期：{timing_contract.get('valuation_terminal_date') or 'UNKNOWN'}",
        f"- 终点日期依据：{timing_contract.get('valuation_terminal_date_basis') or 'UNKNOWN'}",
        f"- 截止日到估值终点的日历天数：{timing_contract.get('elapsed_calendar_days') if timing_contract.get('elapsed_calendar_days') is not None else 'UNKNOWN'}",
        f"- 年化折算年数：{timing_contract.get('annualization_year_fraction') or 'UNKNOWN'}；日计数：{timing_contract.get('day_count_convention', 'UNKNOWN')}",
        f"- 期限门禁：**{timing_contract.get('status', 'UNKNOWN')}**；期间对齐：{timing_contract.get('period_alignment_status', 'UNKNOWN')}",
        f"- 年化公式：{timing_contract.get('annualized_return_formula', 'UNKNOWN')}",
        f"- 15% 回报门槛价格公式：{timing_contract.get('return_hurdle_entry_price_formula', 'UNKNOWN')}",
        *(["- 期限缺口：" + "; ".join(timing_contract.get("issues") or [])] if timing_contract.get("issues") else []),
        "- horizon_years 仍表示决策参考期限；年化回报与回报门槛价格使用截止日到显式估值终点的实际日历天数，不再把不同口径默认为相同的一年。",
        "",
    ])
    scenarios = f.get("scenarios") if isinstance(f.get("scenarios"), Mapping) else {}
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        lines.extend([
            f"### {label} 情景",
            "",
            f"- 情景概率：{('UNKNOWN' if row.get('probability') in (None, '') else row.get('probability'))}",
            f"- 期末每股价值：{('UNKNOWN' if row.get('terminal_value_per_share') in (None, '') else row.get('terminal_value_per_share'))} {c['currency']}",
            *([f"- EPS_MULTIPLE 原始声明终值（仅供审计，不进入主计算）：{row.get('declared_terminal_value_before_eps_multiple_calculation')} {c['currency']}" ] if row.get('eps_multiple_calculation_applied') is True else []),
            f"- 每股现金分配合计：{('UNKNOWN' if row.get('cash_distributions_per_share') in (None, '') else row.get('cash_distributions_per_share'))} {c['currency']}",
            *(
                [f"- 登记日 {event.get('record_date', 'UNKNOWN')}；除息日 {event.get('ex_date', 'UNKNOWN')}；支付日 {event.get('payment_date', 'UNKNOWN')}；税前 {event.get('gross_amount_per_share', 'UNKNOWN')}；税额 {event.get('tax_amount_per_share', 'UNKNOWN')}；计入每股税后现金流 {event.get('amount_per_share', 'UNKNOWN')}；税务口径 {event.get('tax_basis', 'UNKNOWN')}；假设截止日按输入参考价入场的分红资格 {event.get('eligible_if_entered_at_cutoff', 'UNKNOWN')}（条件性；实际成交/实际权益未确认；{event.get('eligibility_basis', 'UNKNOWN')}）；证据 {', '.join(event.get('evidence_refs') or []) or 'UNKNOWN'}"
                 for event in (row.get("cash_distribution_events") or []) if isinstance(event, Mapping)]
                if isinstance(row.get("cash_distribution_events"), list) else []
            ),
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
        f"- 压力情景结构/可比性校验：{stress_review.get('status', 'MISSING')}",
        "- 状态口径：PASS 仅表示压力输入可识别、数值可计算且压力总财富低于 Bear；不表示这一下跌幅度符合投资者损失容忍度，也不构成风险门槛通过。Bear 损失上限单独按 Bear 情景核验，独立压力测试用于反证，不纳入概率加权。",
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
    b4_report_source = analysis.get("operating_driver_forecast") or {}
    lines.extend(render_operating_driver_section(
        b4_report_source,
        f.get("scenarios") if isinstance(f.get("scenarios"), Mapping) else {},
        c["currency"],
        valuation_transmission=analysis.get("valuation_transmission") or {},
    ))
    assumption_links = b4_report_source.get("cross_node_assumption_links")
    if isinstance(assumption_links, list) and assumption_links:
        lines.extend(["", "#### B4 与估值假设的交叉引用", ""])
        for link in assumption_links:
            if not isinstance(link, Mapping):
                continue
            scenario_label = str(link.get("scenario") or "UNKNOWN").upper()
            status = str(link.get("status") or "UNKNOWN")
            if status == "ASSUMPTION_BASIS_NOT_IDENTIFIABLE_NOT_LINKED":
                lines.append(
                    f"- {scenario_label} 成本率：未复用估值假设 "
                    f"{link.get('source_assumption_id') or link.get('source_assumption_name') or '未命名假设'}；"
                    "原始依据为空或仅为 UNKNOWN/N/A/TBD 等占位文本，B4 不把该成本率用于计算。"
                )
            elif status == "LINKED_SAME_SCENARIO_ASSUMPTION":
                lines.append(
                    f"- {scenario_label} 成本率：已复用同情景估值假设 "
                    f"{link.get('source_assumption_id') or link.get('source_assumption_name') or '未命名假设'}；"
                    "该引用不构成独立证据或正式准入。"
                )
            else:
                lines.append(
                    f"- {scenario_label} 成本率：未完成交叉引用（{status}）；B4 不进行隐式补值。"
                )
        lines.append("")
    lines.extend(_render_eps_earnings_bridge_section(
        analysis.get("eps_earnings_bridge") or {},
        c["currency"],
    ))
    lines.extend(_render_primary_eps_multiple_section(
        analysis.get("eps_multiple_valuation") or {},
        c["currency"],
    ))
    lines.extend(render_sotp_valuation_section(
        analysis.get("sotp_valuation") or {},
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
        f"- 预期差：{_assessment_status_for_report(a['expectation_gap'])} / {a['expectation_gap']['direction']}{'（输入方向标签 ' + str(a['expectation_gap'].get('direction_input')) + '）' if a['expectation_gap'].get('direction_input') and str(a['expectation_gap'].get('direction_input')).upper() != str(a['expectation_gap']['direction']).upper() else ''} — {a['expectation_gap'].get('summary') or '未知'}",
        "- 若 MIE 无法识别或缺乏历史支持，不以内部估值代替市场隐含预期。",
        "",
        "## 六、风险与证据引用核对",
        "",
        f"- 风险状态：{_assessment_status_for_report(a['risk'])} — {a['risk'].get('summary') or '未知'}",
    ])
    risk_items = a["risk"].get("items") or []
    if risk_items:
        for item in risk_items:
            lines.append("- " + _humanize_item(item))
            if isinstance(item, Mapping) and item.get("status") is not None:
                gate_line = "  风险项门禁：" + str(item.get("status") or "UNKNOWN")
                if item.get("status_issues"):
                    gate_line += "；" + "；".join(item["status_issues"])
                lines.append(gate_line)
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
    duplicate_evidence_ids = sorted(set(analysis.get("duplicate_evidence_ids") or []))
    if duplicate_evidence_ids:
        lines.append(
            "- 来源登记表重复 ID："
            + "、".join(duplicate_evidence_ids)
            + "；这些 ID 无法唯一对应来源记录，凡被引用均按未解决处理。"
        )
    untraceable_evidence_ids = sorted(set(analysis.get("untraceable_evidence_ids") or []))
    untraceable_evidence_fields = (
        analysis.get("untraceable_evidence_fields")
        if isinstance(analysis.get("untraceable_evidence_fields"), Mapping) else {}
    )
    if untraceable_evidence_ids:
        lines.append(
            "- 来源登记关键内容缺失/为占位值的 ID："
            + "、".join(untraceable_evidence_ids)
            + "；若被引用，则按未解决证据处理。"
        )
    if referenced:
        for ref in referenced:
            if ref in duplicate_evidence_ids:
                lines.append(
                    f"- **{ref}**：**来源 ID 重复登记，引用无法唯一解析**；不得作为已解决证据支持结论。"
                )
            elif ref in untraceable_evidence_ids:
                fields = untraceable_evidence_fields.get(ref, [])
                field_labels = {
                    "title": "标题",
                    "source_ref": "来源位置",
                    "summary": "事实摘要",
                }
                missing_labels = "、".join(field_labels.get(field, field) for field in fields) or "来源描述"
                lines.append(
                    f"- **{ref}**：**引用无法完成来源定位**；不可识别字段：{missing_labels}；不得作为已解决证据支持结论。"
                )
            elif ref in evidence_by_id:
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
                f"  类型：{row['source_class']}；URL 主机名：{row.get('source_url_host') or 'UNKNOWN'}；域名/类别检查：{row.get('source_domain_class_status', 'UNKNOWN')}；published_at：{row.get('published_at') or 'UNKNOWN'}；known_at：{row['known_at'] or 'UNKNOWN'}；时间依据：{row.get('time_basis', 'UNKNOWN')}；时间精度：{'仅日期，原始标注具体时分未知' if row.get('known_at_precision') == 'DATE_ONLY_EXPLICIT_TIME_UNKNOWN' else '仅日期' if row.get('known_at_precision') == 'DATE_ONLY' else '时间戳' if row.get('known_at_precision') == 'TIMESTAMP_OR_OFFSET_DATETIME' else 'UNKNOWN'}；时间状态：{row['time_status']}。",
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
        "SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED": (
            "Bear/Base/Bull 至少一个情景未明确提供每股现金分配（包括明确为 0）；不能将缺失字段默认为零，因此回报、目标入场价和 B6 保持未知。"
        ),
        "CASH_DISTRIBUTION_SOURCE_DOMAIN_CLASS_NOT_ACCEPTED": (
            "分红/现金分配证据的 URL 主机名与声明来源类别不匹配、未在允许的交易所/监管域名清单内，或发行人域名无法独立确认；不得据此核算现金流，回报、目标入场价和 B6 保持未知。"
        ),
        "THESIS_BREAK_STRESS_CASH_DISTRIBUTIONS_UNRESOLVED": (
            "独立论点失效压力测试未明确提供每股现金分配；不能将缺失字段默认为零，压力总财富与风险准备状态未解决。"
        ),
        "THESIS_BREAK_STRESS_BEAR_CASH_DISTRIBUTIONS_UNRESOLVED": (
            "Bear 情景未明确提供每股现金分配；不能将缺失字段默认为零，独立压力情景与 Bear 的总财富比较未解决。"
        ),
        "THESIS_BREAK_STRESS_BEAR_COMPARISON_UNAVAILABLE": (
            "无法将独立压力情景与 Bear 情景的期末总财富进行比较。"
        ),
        "THESIS_BREAK_STRESS_NOT_MORE_SEVERE_THAN_BEAR": (
            "独立压力情景的期末总财富并不低于 Bear 情景，不能作为更严重的独立下行情景。"
        ),
        "RISK_ITEMS_NOT_IDENTIFIABLE": (
            "风险门禁原标为 PASS，但结构化风险清单为空，或至少一项风险只有 UNKNOWN/TBD 等占位文本；风险状态已降为 UNKNOWN。"
        ),
        "RISK_ITEMS_REQUIRE_STRUCTURED_MONITORING": (
            "当前风险清单仍有纯文本条目。文本会保留显示，但不能证明每项风险都有独立证据和可执行监控触发器，因此整体风险状态不能视为 PASS。"
        ),
        "RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED": (
            "至少一个结构化风险项没有自己的可追溯截止时点证据，或其引用无法唯一解析/时点不兼容；整体风险状态不能视为 PASS。"
        ),
        "RISK_ITEM_MONITORING_TRIGGER_NOT_IDENTIFIABLE": (
            "至少一个结构化风险项缺少明确且非占位的监控触发条件；整体风险状态已降为 UNKNOWN。"
        ),
        "RISK_ITEM_ID_NOT_IDENTIFIABLE": (
            "至少一个结构化风险项缺少稳定、非占位的 risk_id；后续监控与复核无法可靠定位该风险。"
        ),
        "RISK_ITEM_SEVERITY_NOT_IDENTIFIABLE": (
            "至少一个结构化风险项缺少受支持的严重程度分级；该风险排序与组合风险判断不能视为完整。"
        ),
        "RISK_ITEM_STATUS_NOT_PASS": (
            "至少一个结构化风险项的行级状态不是 PASS；整体风险状态不能继续标为 PASS，已降为 UNKNOWN。"
        ),
        "RISK_DUPLICATE_RISK_ID_NOT_IDENTIFIABLE": (
            "多个结构化风险项使用相同 risk_id；对应条目均降为 UNKNOWN，以免后续监控/复核无法唯一定位。"
        ),
        "THESIS_BREAK_CONDITIONS_NOT_IDENTIFIABLE": (
            "Thesis 原标为 INTACT，但失效条件列表为空或仅有 UNKNOWN/TBD 等占位文本；论点完整性降为 UNKNOWN。"
        ),
        "THESIS_REASSESSMENT_TRIGGERS_NOT_IDENTIFIABLE": (
            "Thesis 原标为 INTACT，但重新评估触发器为空或仅有 UNKNOWN/TBD 等占位文本；监控条件未能被识别。"
        ),
        "CORE_POLICY_VALUE_DRIVER_GATE_NOT_PASS": (
            "价值驱动因素名称、影响方向或驱动理由存在未知/占位内容；价值驱动门禁不能视为通过。"
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
    # Persist conditional entitlement metadata to the published scenario JSON
    # only after the return solver validated all dates, tax arithmetic, sources,
    # and hypothetical eligibility. Failed/unknown calculations never promote
    # an unverified dividend event to a normalized eligible cashflow.
    validated_distribution_events = prepared.pop("_validated_cash_distribution_events", None)
    if isinstance(metrics, Mapping) and isinstance(validated_distribution_events, Mapping):
        forecast = prepared.get("forecast_valuation")
        forecast = forecast if isinstance(forecast, dict) else None
        scenario_inputs = forecast.get("scenarios") if isinstance(forecast, dict) else None
        if isinstance(scenario_inputs, dict):
            for scenario_name in SCENARIOS:
                source_row = scenario_inputs.get(scenario_name)
                normalized_events = validated_distribution_events.get(scenario_name)
                if isinstance(source_row, dict) and isinstance(normalized_events, list):
                    source_row["cash_distribution_events"] = [
                        dict(event) for event in normalized_events if isinstance(event, Mapping)
                    ]
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
        "duplicate_evidence_ids": prepared["duplicate_evidence_ids"],
        "untraceable_evidence_ids": prepared["untraceable_evidence_ids"],
        "untraceable_evidence_fields": prepared["untraceable_evidence_fields"],
        "referenced_evidence_ids": prepared["referenced_evidence_ids"],
        "unresolved_evidence_references": prepared["unresolved_evidence_references"],
        "after_cutoff_evidence_references": prepared["after_cutoff_evidence_references"],
        "uncertain_timing_evidence_references": prepared["uncertain_timing_evidence_references"],
        "assessment": prepared["assessment"],
        "forecast_valuation": prepared["forecast_valuation"],
        "eps_multiple_valuation": prepared["eps_multiple_valuation"],
        "eps_earnings_bridge": prepared["eps_earnings_bridge"],
        "operating_driver_forecast": prepared["operating_driver_forecast"],
        "valuation_transmission": prepared["valuation_transmission"],
        "sotp_valuation": prepared["sotp_valuation"],
        "operator_valuation_context": prepared["operator_valuation_context"],
        "valuation_model_consistency": prepared["valuation_model_consistency"],
        "valuation_timing": prepared["valuation_timing"],
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
    input_path: Path,
    output_root: Path,
    *,
    replay_of: str | None = None,
    research_response_path: str | Path | None = None,
    expected_research_response_sha256: str | None = None,
    expected_research_response_byte_size: int | None = None,
) -> dict[str, Any]:
    try:
        input_text = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LocalInvestmentPilotError("PILOT_INPUT_FILE_UNREADABLE") from exc
    try:
        payload = json.loads(input_text)
    except json.JSONDecodeError as exc:
        raise LocalInvestmentPilotError("PILOT_INPUT_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise LocalInvestmentPilotError("PILOT_INPUT_JSON_OBJECT_REQUIRED")

    input_response_claim = payload.get("_local_research_response_provenance")
    previous_analysis: dict[str, Any] | None = None
    previous_receipt: dict[str, Any] | None = None
    previous_manifest: dict[str, Any] = {}
    prior_dir: Path | None = None
    response_bytes: bytes | None = None

    if replay_of:
        if research_response_path is not None:
            raise LocalInvestmentPilotError("REPLAY_RESEARCH_RESPONSE_MUST_INHERIT_FROM_VERIFIED_PARENT")
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

        if RAW_RESEARCH_RESPONSE_FILENAME in previous_manifest:
            response_path = prior_dir / RAW_RESEARCH_RESPONSE_FILENAME
            if response_path.is_symlink() or not response_path.is_file():
                raise LocalInvestmentPilotError("REPLAY_RESEARCH_RESPONSE_SOURCE_MISSING_OR_SYMLINK")
            try:
                response_bytes = response_path.read_bytes()
            except OSError as exc:
                raise LocalInvestmentPilotError("REPLAY_RESEARCH_RESPONSE_SOURCE_UNREADABLE") from exc
            response_fp = _fingerprint_bytes(response_bytes)
            if response_fp != previous_manifest[RAW_RESEARCH_RESPONSE_FILENAME]:
                raise LocalInvestmentPilotError("REPLAY_RESEARCH_RESPONSE_SOURCE_HASH_CHANGED")
            previous_response = previous_receipt.get("research_response_provenance")
            if not isinstance(previous_response, Mapping) or previous_response.get("status") not in _RESEARCH_RESPONSE_PRESENT_STATUSES:
                raise LocalInvestmentPilotError("REPLAY_RESEARCH_RESPONSE_PROVENANCE_INVALID")
            if (
                not isinstance(input_response_claim, Mapping)
                or input_response_claim.get("schema_version") != LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA
                or input_response_claim.get("status") != "CAPTURED_RAW_CHATGPT_RESPONSE"
                or input_response_claim.get("sha256") != response_fp["sha256"]
                or input_response_claim.get("byte_size") != response_fp["byte_size"]
            ):
                raise LocalInvestmentPilotError("REPLAY_INPUT_RESEARCH_RESPONSE_PROVENANCE_MISMATCH")
            response_provenance = {
                "schema_version": LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
                "status": "INHERITED_FROM_VERIFIED_PRIOR_RUN",
                "file": RAW_RESEARCH_RESPONSE_FILENAME,
                "sha256": response_fp["sha256"],
                "byte_size": response_fp["byte_size"],
                "origin_pilot_id": previous_response.get("origin_pilot_id") or previous_receipt.get("pilot_id"),
                "source_pilot_id": previous_receipt.get("pilot_id"),
                "capture_method": "BYTE_COPY_FROM_HASH_VERIFIED_PARENT_RUN",
                "raw_response_modified_by_runner": False,
                "note": "原始 ChatGPT 响应从哈希验证通过的父运行包逐字节复制；不在 Replay 阶段重新请求或生成研究回答。",
            }
        else:
            if isinstance(input_response_claim, Mapping):
                raise LocalInvestmentPilotError("REPLAY_INPUT_CLAIMS_RESEARCH_RESPONSE_NOT_PRESENT_IN_PARENT")
            response_provenance = {
                "schema_version": LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
                "status": "NOT_AVAILABLE_IN_LEGACY_PARENT_RUN",
                "file": None,
                "sha256": None,
                "byte_size": None,
                "origin_pilot_id": None,
                "source_pilot_id": previous_receipt.get("pilot_id"),
                "capture_method": "LEGACY_PARENT_HAS_NO_RAW_RESPONSE_CAPTURE",
                "raw_response_modified_by_runner": False,
            }
    elif research_response_path is not None:
        raw_path = Path(research_response_path).expanduser()
        if raw_path.is_symlink():
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_SOURCE_MUST_NOT_BE_SYMLINK")
        try:
            raw_path = raw_path.resolve(strict=True)
        except OSError as exc:
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_SOURCE_NOT_FOUND") from exc
        if not raw_path.is_file():
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_SOURCE_NOT_REGULAR_FILE")
        if (
            not isinstance(expected_research_response_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_research_response_sha256)
            or not isinstance(expected_research_response_byte_size, int)
            or isinstance(expected_research_response_byte_size, bool)
            or expected_research_response_byte_size < 1
        ):
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_EXPECTED_FINGERPRINT_REQUIRED")
        try:
            response_bytes = raw_path.read_bytes()
        except OSError as exc:
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_SOURCE_UNREADABLE") from exc
        response_fp = _fingerprint_bytes(response_bytes)
        if (
            response_fp["sha256"] != expected_research_response_sha256
            or response_fp["byte_size"] != expected_research_response_byte_size
        ):
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_CHANGED_AFTER_VALIDATION")
        try:
            raw_response_text = response_bytes.decode("utf-8")
            _extract_json_object(raw_response_text)
        except (UnicodeDecodeError, LocalInvestmentPilotError) as exc:
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_RAW_SNAPSHOT_NO_LONGER_VALID") from exc
        current_signature = _response_file_signature(raw_path)
        if (
            current_signature is None
            or current_signature[0] != expected_research_response_byte_size
            or current_signature[2] != expected_research_response_sha256
        ):
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_CHANGED_DURING_SNAPSHOT")
        if not isinstance(input_response_claim, Mapping):
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_INPUT_PROVENANCE_MISSING")
        if (
            input_response_claim.get("schema_version") != LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA
            or input_response_claim.get("status") != "CAPTURED_RAW_CHATGPT_RESPONSE"
            or not isinstance(input_response_claim.get("source_filename"), str)
            or not input_response_claim.get("source_filename")
            or Path(input_response_claim["source_filename"]).name != input_response_claim["source_filename"]
            or "/" in input_response_claim["source_filename"]
            or "\\" in input_response_claim["source_filename"]
            or input_response_claim.get("sha256") != response_fp["sha256"]
            or input_response_claim.get("byte_size") != response_fp["byte_size"]
        ):
            raise LocalInvestmentPilotError("CHATGPT_RESPONSE_INPUT_PROVENANCE_MISMATCH")
        response_provenance = {
            "schema_version": LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
            "status": "CAPTURED_RAW_CHATGPT_RESPONSE",
            "file": RAW_RESEARCH_RESPONSE_FILENAME,
            "source_filename": raw_path.name,
            "sha256": response_fp["sha256"],
            "byte_size": response_fp["byte_size"],
            "origin_pilot_id": None,
            "source_pilot_id": None,
            "capture_method": "BYTE_SNAPSHOT_OF_STABLE_VALIDATED_CHATGPT_RESPONSE",
            "response_validation_status": "RAW_JSON_OBJECT_PARSE_PASSED; NORMALIZED_INPUT_REQUIRED_FIELDS_PASSED_AFTER_OPERATOR_FIELD_RESTORATION",
            "local_operator_field_recovery": payload.get("_local_operator_controlled_field_recovery"),
            "raw_response_modified_by_runner": False,
        }
    else:
        if isinstance(input_response_claim, Mapping):
            raise LocalInvestmentPilotError("INPUT_CLAIMS_CHATGPT_RESPONSE_WITHOUT_VERIFIABLE_CAPTURE")
        response_provenance = {
            "schema_version": LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
            "status": "NOT_CAPTURED_DIRECT_OR_LEGACY_INPUT",
            "file": None,
            "sha256": None,
            "byte_size": None,
            "origin_pilot_id": None,
            "source_pilot_id": None,
            "capture_method": "NO_GUIDED_CHATGPT_RESPONSE_FILE_SUPPLIED",
            "raw_response_modified_by_runner": False,
        }

    # Provenance is hash-bound in input.json, but removed before analysis so it
    # cannot change analytical semantics or Replay equality.
    payload_for_analysis = dict(payload)
    payload_for_analysis.pop("_local_research_response_provenance", None)
    symbol = str((payload_for_analysis.get("case") or {}).get("symbol") or "candidate").replace(".", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"local-pilot-{symbol}-{stamp}"
    if response_provenance.get("status") == "CAPTURED_RAW_CHATGPT_RESPONSE":
        response_provenance["origin_pilot_id"] = run_id
        response_provenance["source_pilot_id"] = run_id

    analysis, report = _analyse(payload_for_analysis, run_id)
    if isinstance(input_response_claim, Mapping):
        # Keep a stable, analysis-level link to the byte-exact raw response. Do
        # not include a run-specific captured/inherited status here, otherwise
        # the same evidence would cause artificial first-run/Replay drift.
        # Record only the source basename in outputs; never expose its absolute private path.
        analysis["research_response_provenance"] = {
            "schema_version": LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
            "status": "RAW_CHATGPT_RESPONSE_HASH_BOUND",
            "file": RAW_RESEARCH_RESPONSE_FILENAME,
            "source_filename": input_response_claim.get("source_filename"),
            "sha256": input_response_claim.get("sha256"),
            "byte_size": input_response_claim.get("byte_size"),
            "capture_stage": input_response_claim.get("capture_stage"),
            "validation_status": input_response_claim.get("validation_status"),
            "local_operator_field_recovery": payload.get("_local_operator_controlled_field_recovery"),
            "formal_source_admission": False,
            "raw_response_modified_by_runner": False,
        }
        report = _render_report(analysis)
        report += (
            "\n\n## 原始 ChatGPT 响应来源链\n\n"
            f"- 原始响应文件：{RAW_RESEARCH_RESPONSE_FILENAME}（私有运行包内逐字节快照）\n"
            f"- 原始响应 SHA-256：{input_response_claim['sha256']}\n"
            f"- 原始响应字节数：{input_response_claim['byte_size']}\n"
            f"- 本地校验阶段：{input_response_claim.get('capture_stage', 'UNKNOWN')}；字段结构校验：{input_response_claim.get('validation_status', 'UNKNOWN')}\n"
            "- 本节只证明响应文本与本地输入之间的字节级关联，不证明响应中的事实/来源真实，也不构成正式 Evidence/PIT 准入。\n"
        )
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    _write_local(run_dir / "input.json", input_text)
    _write_local(run_dir / "analysis.json", json.dumps(_safe(analysis), ensure_ascii=False, indent=2, allow_nan=False))
    _write_local(run_dir / "report.md", report)
    if response_bytes is not None:
        raw_response_path = run_dir / RAW_RESEARCH_RESPONSE_FILENAME
        try:
            raw_response_path.write_bytes(response_bytes)
        except OSError as exc:
            raise LocalInvestmentPilotError("RUN_RESEARCH_RESPONSE_SNAPSHOT_WRITE_FAILED") from exc
        if os.name != "nt":
            raw_response_path.chmod(0o600)

    file_manifest = {name: _fingerprint_file(run_dir / name) for name in BUNDLE_FILENAMES}
    if response_bytes is not None:
        file_manifest[RAW_RESEARCH_RESPONSE_FILENAME] = _fingerprint_file(run_dir / RAW_RESEARCH_RESPONSE_FILENAME)
        if file_manifest[RAW_RESEARCH_RESPONSE_FILENAME] != _fingerprint_bytes(response_bytes):
            raise LocalInvestmentPilotError("RUN_RESEARCH_RESPONSE_SNAPSHOT_HASH_MISMATCH")
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
        "research_response_provenance": response_provenance,
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
        "research_response_provenance_status": response_provenance.get("status"),
        "run_dir": str(run_dir),
        "report_path": str(run_dir / "report.md"),
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "auto_execution": False,
    }


def run_local_investment_pilot(
    *,
    input_path: str | Path,
    output_root: str | Path,
    replay_of: str | None = None,
    research_response_path: str | Path | None = None,
    expected_research_response_sha256: str | None = None,
    expected_research_response_byte_size: int | None = None,
) -> dict[str, Any]:
    source = _outside_repo(input_path, "PILOT_INPUT_PATH", must_exist=True)
    root = _private_dir(output_root, "PILOT_OUTPUT_ROOT")
    return _write_run(
        source,
        root,
        replay_of=replay_of,
        research_response_path=research_response_path,
        expected_research_response_sha256=expected_research_response_sha256,
        expected_research_response_byte_size=expected_research_response_byte_size,
    )


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
            "model": "UNKNOWN", "model_family": "UNKNOWN", "model_rationale": "",
            "valuation_terminal_date": None, "valuation_terminal_date_basis": "",
            "entry_value_reference_per_share": None,
            "probabilities_calibrated": False, "assumptions": [],
            "cash_distribution_review": {"status": "UNKNOWN", "summary": "", "evidence_refs": []},
            "scenarios": {
                "bear": {
                    "probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": None,
                    "cash_distribution_events": [],
                    "rationale": "", "failure_trigger": "", "operating_impact": "", "valuation_mechanism": "",
                },
                "base": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": None, "cash_distribution_events": [], "rationale": ""},
                "bull": {"probability": None, "terminal_value_per_share": None, "cash_distributions_per_share": None, "cash_distribution_events": [], "rationale": ""},
            },
            "thesis_break_stress": {
                "failure_trigger": "", "operating_impact": "", "valuation_method": "",
                "terminal_value_per_share": None, "cash_distributions_per_share": "0",
                "rationale": "", "evidence_refs": [],
            },
        },
        "eps_multiple_valuation": {
            "schema_version": EPS_MULTIPLE_VALUATION_SCHEMA,
            "calculation_method": EPS_MULTIPLE_VALUATION_METHOD,
            "summary": "",
            "forecast_period": "UNKNOWN",
            "valuation_terminal_date": None,
            "scenarios": {
                "bear": {"rationale": "", "eps_per_share": {"value": None, "unit": f"{currency}/share", "data_class": "UNKNOWN", "basis": "", "assumption_derivation": "", "earnings_bridge": None, "evidence_refs": [], "note": ""}, "pe_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": ""}},
                "base": {"rationale": "", "eps_per_share": {"value": None, "unit": f"{currency}/share", "data_class": "UNKNOWN", "basis": "", "assumption_derivation": "", "earnings_bridge": None, "evidence_refs": [], "note": ""}, "pe_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": ""}},
                "bull": {"rationale": "", "eps_per_share": {"value": None, "unit": f"{currency}/share", "data_class": "UNKNOWN", "basis": "", "assumption_derivation": "", "earnings_bridge": None, "evidence_refs": [], "note": ""}, "pe_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": ""}}
            }
        },
        "sotp_valuation": {
            "schema_version": "IIOS-SOTP-VALUATION-0.1",
            "calculation_method": "SEGMENT_ATTRIBUTABLE_NET_PROFIT_X_SEGMENT_PE",
            "summary": "",
            "forecast_period": "UNKNOWN",
            "valuation_terminal_date": None,
            "scenarios": {
                "bear": {
                    "rationale": "", "segments": [],
                    "parent_level_adjustments": {
                        "central_cost_after_tax_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "母公司税后经常性成本；正数表示成本，显式为零也须说明依据"},
                        "central_cost_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "仅在母公司成本大于零时用于资本化"},
                        "net_cash_debt_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "有符号数；正数为净现金，负数为净负债"},
                        "other_adjustments_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "有符号数；其他明确、未重复计价的股权价值调整"}
                    },
                    "diluted_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "稀释后股数，单位为股而不是百万股"}
                },
                "base": {
                    "rationale": "", "segments": [],
                    "parent_level_adjustments": {
                        "central_cost_after_tax_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "母公司税后经常性成本；正数表示成本，显式为零也须说明依据"},
                        "central_cost_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "仅在母公司成本大于零时用于资本化"},
                        "net_cash_debt_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "有符号数；正数为净现金，负数为净负债"},
                        "other_adjustments_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "有符号数；其他明确、未重复计价的股权价值调整"}
                    },
                    "diluted_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "稀释后股数，单位为股而不是百万股"}
                },
                "bull": {
                    "rationale": "", "segments": [],
                    "parent_level_adjustments": {
                        "central_cost_after_tax_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "母公司税后经常性成本；正数表示成本，显式为零也须说明依据"},
                        "central_cost_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "仅在母公司成本大于零时用于资本化"},
                        "net_cash_debt_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "有符号数；正数为净现金，负数为净负债"},
                        "other_adjustments_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "有符号数；其他明确、未重复计价的股权价值调整"}
                    },
                    "diluted_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "稀释后股数，单位为股而不是百万股"}
                }
            }
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
        "估值与预期差、风险。schema_version、case、price_input、operator_valuation_context 和 decision_parameters 由本地可信模板保护并自动合并，不需要在回答里重复；最终输出格式见本提示末尾的“紧凑研究补丁 JSON 协议”。"
        "证据应给出可直接打开的来源 URL、标题、发布日期/已知时点与事实摘要；优先使用公司定期报告、公告、交易所与监管文件。"
        "不得为了填满字段编造事实、URL、财务数字或所谓市场一致预期。对于 MIE，不具备可核实的一致预期/市场定价证据时，明确使用 NOT_IDENTIFIABLE 并解释原因。"
        "请用可解释的显式假设建立 Bear/Base/Bull 数值情景；情景是估算而非已披露事实，说明盈利/利润率/销量等驱动及估值倍数来源。"
        "概率之和必须为 1；期末总财富次序必须 Bear ≤ Base ≤ Bull。若无法有根据地估算某情景，请明确报告其不可识别及缺少什么依据，不要捏造。"
        "Bear 必须明确写 failure_trigger、operating_impact 和 valuation_mechanism；若论点依赖盈利恢复，Bear 必须检验恢复失败。"
        "独立 thesis_break_stress 必须另行量化失效后的每股期末价值和现金分配，并明确估值方法、触发条件、经营影响与理由；不参与概率加权，且须比 Bear 更悲观。"
        "不要在 notes 中重述与 price_input.price 不同的现价；当前股价只取结构化 price_input。不能将人工价格标为已验证。"
        "未知事实用 UNKNOWN，并解释缺口；研究结论可以是 REVIEW_REQUIRED，但不可以把整个结构留空。只返回一个完整 JSON 对象，不要输出代码围栏或额外说明。"
    )
    investment_thesis_chain_instructions = (
        "\\n\\n核心投资判断链：必须逐项回答以下六个问题，并把答案落到现有 JSON 字段中；不得新增顶层字段，也不得用空泛口号代替因果解释。"
        "1. 公司究竟靠什么赚钱：识别关键产品/服务、客户与应用、销量/价格/产品组合、单位经济、利润率、资本占用和现金来源；区分经常性经营与一次性/周期性收益。写入 assessment.thesis.core_statement、assessment.thesis.drivers 和 assessment.value_drivers。"
        "2. 未来最重要的变化是什么：按价值重要性排序，不要罗列宏观热点；指出未来 1 年（如有明确理由再用 2–3 年）最可能改变收入、单位利润、现金流或每股价值的变量，说明起点、预期变化、时间和可观测指标。写入 assessment.value_drivers 与 operating_driver_forecast。"
        "3. 为什么相信变化会发生：把每个关键变化连接到截止时点前已公开的具体证据、证据日期、业务机制和反证；区分领先指标/结果指标、公司指引/分析师假设/历史事实，不得把管理层目标当成已实现结果。写入 evidence_register、assessment.value_drivers.historical_evidence 与 rationale。"
        "4. 变化如何进入每股价值：明确写出“销量/价格/组合/利用率 → 收入 → 单位毛利与费用 → EBIT/净利润 → 资本开支/营运资金/FCF → 稀释股数与每股盈利 → 估值”的可验证传导链；说明关键假设、量纲、期间、约束、潜在蚕食与稀释，避免重复计价。使用 operating_driver_forecast、valuation_transmission 和 forecast_valuation.scenarios；无法闭合的环节保留 UNKNOWN/NOT_LINKED。"
        "5. 当前价格已反映多少：price_input.price 是本次唯一现价，不得覆盖。分清外部可验证的市场隐含预期（MIE）、市场可比估值和内部估值；只有存在独立、截止时点兼容的定价/一致预期证据时才量化 MIE。缺少证据就将 assessment.market_implied_expectation 标为 NOT_IDENTIFIABLE，并具体解释哪些隐含增长、利润率、资本回报或估值倍数无法反推；绝不能把自己的 Base 估值伪装成市场预期。assessment.expectation_gap 必须说明市场预期与独立经营推演在方向、规模、时间或概率上有何差异；无法量化时明确方向也不可识别。"
        "6. 哪些事实要求改变看法：写出会证伪核心论点或使情景切换的可观察指标、阈值/方向、验证时间和对应经营/估值影响；区分暂时波动与结构性恶化。落入 assessment.thesis.break_conditions、assessment.thesis.reassessment_triggers、assessment.risk.items 的监控触发项以及 Bear.failure_trigger / operating_impact / valuation_mechanism。"
        "每个排名靠前的 value driver 都应尽量填写 driver_type、historical_evidence、valuation_transmission、impact、rationale 和其自身的 evidence_refs；证据只证明事实，不自动证明因果，因果需另给机制。Bear/Base/Bull 应由经营驱动假设产生有意义的差异，而不是只改终值或概率；说明情景间销量、净售价、单位成本、利润率、现金转化、资本开支和估值倍数发生哪些变化以及依据。"
        "最终要判断的是“按输入价格是否值得承担风险”，而不是只判断公司是否优秀或值得研究。请提供足以让本地决策引擎复算的输入，不要另造顶层 action/target-price 字段，也不要在研究回答中声称已发出 BUY/ADD/交易指令；15% 年化门槛、共同约束入场价与暂定动作由本地既有计算器独立计算。"
    )
    eps_multiple_instructions = (
        "\n\nEPS_MULTIPLE 主估值计算契约（IIOS-EPS-MULTIPLE-VALUATION-0.1 / B27 EPS earnings bridge）："
        "必须保留 eps_multiple_valuation 节点；forecast_period 与 operating_driver_forecast.forecast_period 一致，valuation_terminal_date 与 forecast_valuation.valuation_terminal_date 一致。"
        "Bear/Base/Bull 每个情景都填 rationale、eps_per_share 与 pe_multiple_x。每个 measure 至少使用 {value,unit,data_class,basis,evidence_refs,note}；eps_per_share 还要填 assumption_derivation 与 earnings_bridge（不可计算时可为 null，但不得因此把 ISSUER_FORECAST 冒充成可复算）。"
        "eps_per_share 单位为个股币种/share（CNY/share 或 HKD/share），必须为同一期间的正 EPS；P/E 的 unit 为 x。数据类别只允许 ISSUER_FORECAST 或 ANALYST_ASSUMPTION。发行人 EPS 必须提供 cutoff 前 evidence_refs，且来源类别须为 EXCHANGE_PRIMARY/REGULATOR_PRIMARY 并与官方域名状态匹配；域名匹配不是内容核实或正式 Evidence/PIT 准入。"
        "凡声明 ISSUER_FORECAST 的 EPS，都必须提供 earnings_bridge 对象，schema_version=IIOS-EPS-EARNINGS-BRIDGE-0.1、calculation_method=B4_NET_PROFIT_PROXY_MINUS_NCI_PLUS_ADJUSTMENTS_DIVIDED_BY_DILUTED_SHARES、forecast_period 与估值终点一致、scope=COMPANY_WIDE。不可拿 PROJECT_INCREMENTAL/PRODUCT_LINE EBIT、EBITDA 或项目增量利润代替整家公司净利润。"
        "earnings_bridge 必须包含 project_profit_treatment（INCLUDED_IN_COMPANY_WIDE_BASELINE / EXCLUDED_FROM_COMPANY_WIDE_BASELINE / NO_PROJECT_INCREMENTAL_ADJUSTMENT 之一）、non_controlling_interests_after_tax、other_after_tax_attribution_adjustment、diluted_shares；每个数值对象均须包含 value、unit、measure、data_class、basis、evidence_refs、forecast_period、note。非控股股东损益必须非负，其他税后归属调整可正可负，diluted_shares 必须是同一期间加权平均稀释股数的实际 shares 数量，而非百万股。CNY 桥接使用 CNY；本地 B4 未提供 HKD 换算合同，不能把 CNY 利润直接除以 HKD 股数，HKD 只能保留有明确推导说明的 ANALYST_ASSUMPTION 路径。"
        "本地桥接先取 B4 scope=COMPANY_WIDE 且可用的 net_profit_cny 代理，再减非控股股东税后损益、加其他税后归属调整，除以 weighted average diluted shares，得到计算 EPS，并与申报 EPS 比较；每股绝对差异需不超过 0.005 才视为匹配。差异超出容差时报告 EPS_MISMATCH，不得静默覆写任一数值，必须阻断主估值、回报、目标入场价与 B6。"
        "项目利润不得重复计价：若基线已含项目须得到操作者显式确认且 B5 不得再次加入；若基线不含项目，则需操作者显式确认并由 B5 已传导；未知处理方式一律阻断。发行人桥中净利润调整与稀释股数须有可识别口径与同期间依据，发行人预测证据引用必须时点兼容且类别/域名一致。"
        "纯 ANALYST_ASSUMPTION 在未提供完整桥接时，须给出清楚、可审计的 assumption_derivation，且保持 ASSUMPTION_ONLY；不得声称它已由公司净利润/稀释股数证实。桥接对象一旦提供但口径/期间/来源/分母不匹配，就失败关闭，不得退化为假设路径。亏损 EPS 或不可识别值保留 UNKNOWN/null，不用负 EPS 乘正 P/E 伪造价值。"
        "本地程序使用 EPS×P/E 复算每股终值和 Base 主估值锚；forecast_valuation 中模型填写的终值/锚仅作未信任诊断。任一输入、EPS 桥、P/E 或情景次序不合格时，回报、目标入场价、B6 均须 UNKNOWN。此处算术和来源类别校验不等于验证预测真实性、倍数公允性或正式估值准入。"
    )
    b5_transmission_instructions = (
        "\n\nB5 估值传导要求（IIOS-VALUATION-TRANSMISSION-0.1）："
        "必须保留 valuation_transmission 节点和 Bear/Base/Bull 三个情景。valuation_model_name 必须逐字匹配 forecast_valuation.model；model_family 必须准确分类为 EPS_MULTIPLE、FCF_DCF、DDM、SOTP、RNPV、OTHER 或 UNKNOWN；earnings_period 必须与 operating_driver_forecast.forecast_period 完全一致。"
        "forecast_valuation.model_family 必须明确填写实际生成 Bear/Base/Bull 终值和入场参考锚的估值模型类别（仅允许 EPS_MULTIPLE、FCF_DCF、DDM、SOTP、RNPV、OTHER、UNKNOWN），不得把操作者选定模型抄成实际计算模型。forecast_valuation.model 的人类可读名称还必须带有可识别的模型族标记，例如 EPS_MULTIPLE/EPS×P/E、FCF_DCF/DCF、DDM、SOTP、RNPV 或 OTHER；代码会从名称解析模型族并与 model_family 交叉核对，无法识别或不一致时阻断价格计算。此交叉核对是防止字段自相矛盾的一致性检查，不代表系统已独立证明所有情景数值确实由该公式计算。操作者选择与计算模型不同将阻断回报/目标入场价计算，不能悄悄覆盖；未支持模型只能标为替代情景。"
        "forecast_valuation.valuation_terminal_date 必须填写终值真正对应的 ISO 日期 YYYY-MM-DD；valuation_terminal_date_basis 说明该日期对应的报告期间/财年终点依据。不得仅因默认 horizon=1Y 就把 2027FY 终值当成一年后价值。日期缺失、早于/等于 cutoff 或与 forecast_period 年份明显不兼容时，年化回报和目标入场价必须保持 UNKNOWN。年化使用 ACT/365F 的实际日历天数；decision_parameters.horizon_years 仍单独保留为决策参考期限。经营预测范围 scope 必须明确；B5 未传导时，除明确 COMPANY_WIDE 的整家公司估值外，UNKNOWN/PRODUCT_LINE/PROJECT_INCREMENTAL 不得流入主价格计算，除非 B5 已成功传导或已明确确认基线包含项目。"
        "operator_valuation_context 是操作者拥有的字段，必须原样保留模板中的 UNKNOWN/null，不得替操作者选择估值模型或判断原估值是否已包含项目；操作者稍后会在本地独立确认。"
        "本批只有 EPS_MULTIPLE 适配器可传导。每个情景必须提供 ownership_ratio、displaced_existing_after_tax_profit_cny、basic_shares、convertible_bond_incremental_shares、other_dilution_shares、pe_multiple_x，均用 {value,unit,data_class,basis,evidence_refs,note} 结构。"
        "ownership_ratio 是 0–1 的比例；被替代存量业务税后归属利润为非负 CNY；股数单位 shares，填写实际普通股数量而非百万股；可转债潜在新增股数和其他稀释股数可明确为 0，但须说明依据。P/E 倍数单位 x。"
        "事实/发行人预测必须有可解析且截止时间兼容的 evidence_refs；分析假设须标为 ANALYST_ASSUMPTION 并解释依据，不能伪装成事实。缺少项目税后净利润、所有权比例、存量业务蚕食、股数/可转债稀释、期间或模型一致性时保持 NOT_LINKED。"
        "仅当操作者明确确认现有 Bear/Base/Bull 每股终值及入场价值锚均不含该项目时，方可将稀释口径增量加到三个情景，并以 Base 增量同步调整入场价值锚；如已经包含则只显示敏感性、不重复相加；如不确定则不修改原估值。论点失效压力测试不自动加回项目价值。"
    )
    sotp_instructions = (
        "\\n\\nSOTP 主估值计算契约（IIOS-SOTP-VALUATION-0.1）："
        "操作者尚未确认模型时，也请把 sotp_valuation 作为独立候选计算节点：若公司分部口径与数据足以支持，应提供清楚标记为事实/发行人预测/分析假设的输入；不要替操作者选择主模型。最终只有操作者本地选定 SOTP 时，本节点才进入主估值计算，否则保持诊断性备用输入。"
        "若主估值模型采用 SOTP，必须填写可复算的 sotp_valuation 节点；本版本只支持 SEGMENT_ATTRIBUTABLE_NET_PROFIT_X_SEGMENT_PE。"
        "注意：SOTP v0.1 金额字段全部为 CNY，尚无 HKD/CNY 汇率转换合同；个股币种非 CNY 时不得提交可用于主估值的 SOTP，不得把 CNY 输入或 CNY/股结果标成 HKD，系统将阻断该路径。"
        "Bear/Base/Bull 必须使用完全相同的 segment_id 与 segment_name 集合，每个分部填写 attributable_net_profit_cny 与 pe_multiple_x，均用 {value,unit,data_class,basis,evidence_refs,note} 结构。"
        "归属净利润必须是分部层面归属于上市公司股东的预测净利润，单位 CNY；P/E 单位 x。两项只允许 ISSUER_FORECAST 或 ANALYST_ASSUMPTION；发行人预测必须有可解析、截止时点兼容的 evidence_refs，分析假设必须写明可识别的推理依据。分部亏损业务当前不支持直接套用正 P/E，不得把负利润乘正倍数当作合理价值；应明确保留 UNKNOWN 并说明需要另建模型。"
        "每个分部归属净利润必须是已扣除该分部非控股股东损益、归属于上市公司股东的预测净利润（单位 CNY），并且不含尚未分摊的母公司中央税后费用。已按上市公司股东口径计算的分部利润，不得再扣除同一业务的少数股东权益，否则会重复扣减；如果只有未扣非控股股东损益的合并口径利润，本方法不能直接用于计算。"
        "计算公式必须是 Σ（已归属于上市公司股东的分部净利润 × 分部 P/E）−（母公司税后成本 × 母公司成本倍数）+ 不重复计价的净现金/净负债 + 其他显式调整，再除以稀释后股数；结果生成 Bear/Base/Bull 终值，Base 每股值作为主估值参考锚。每个分部利润应与上市公司股东权益口径一致，不能再次扣同一分部的少数股东权益。所有分部、期间、股数、现金/债务及母公司成本须避免重复计价。"
        "sotp_valuation.forecast_period 必须与 operating_driver_forecast.forecast_period 一致，valuation_terminal_date 必须与 forecast_valuation.valuation_terminal_date 一致。数值、证据、期间、分部集合或 Bear≤Base≤Bull 任一项不成立时，不要在 forecast_valuation 中用手填每股终值冒充已计算 SOTP；保留缺口，系统会阻断回报、目标入场价与 B6。"
        "此 SOTP 算术仍为 PILOT_NON_CANONICAL，并不代表正式证据或估值准入。B5 的 EPS_MULTIPLE 增量适配器不能用于 SOTP。"
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
    prompt += investment_thesis_chain_instructions
    prompt += driver_instructions
    prompt += eps_multiple_instructions
    prompt += b5_transmission_instructions
    prompt += sotp_instructions
    _write_local(prompt_path, prompt + "\n")
    return {
        "status": "PILOT_TEMPLATE_CREATED", "input_template": str(input_path),
        "analysis_prompt": str(prompt_path), "private_local_storage": True,
        "formal_decision_created": False,
    }



def _expand_research_patch_with_template(
    template_path: str | Path, response: Mapping[str, Any]
) -> tuple[dict[str, Any], str, list[str]]:
    """Merge the compact AI research patch onto the trusted local template.

    Legacy full-object responses remain accepted. Patch responses are deliberately
    sparse: omitted fields inherit the template's UNKNOWN/null/default structure.
    Operator-owned roots can never be supplied inside a patch.
    """
    if response.get("response_mode") != "IIOS-RESEARCH-PATCH-0.1":
        return dict(response), "FULL_OBJECT", []

    if set(response) != {"response_mode", "research"}:
        raise LocalInvestmentPilotError(
            "CHATGPT_RESEARCH_PATCH_ENVELOPE_INVALID: compact response must contain only "
            "response_mode and research."
        )
    research = response.get("research")
    if not isinstance(research, Mapping) or not research:
        raise LocalInvestmentPilotError(
            "CHATGPT_RESEARCH_PATCH_BODY_REQUIRED: research must be a non-empty JSON object."
        )

    path = Path(template_path).expanduser()
    try:
        template = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalInvestmentPilotError(
            "TRUSTED_PILOT_TEMPLATE_UNREADABLE_FOR_PATCH_MERGE"
        ) from exc
    if not isinstance(template, dict) or template.get("schema_version") != PILOT_SCHEMA:
        raise LocalInvestmentPilotError(
            "TRUSTED_PILOT_TEMPLATE_SCHEMA_INVALID_FOR_PATCH_MERGE"
        )

    protected_roots = {
        "schema_version",
        "case",
        "price_input",
        "operator_valuation_context",
        "decision_parameters",
    }
    forbidden = sorted(set(research) & protected_roots)
    if forbidden:
        raise LocalInvestmentPilotError(
            "CHATGPT_RESEARCH_PATCH_CONTAINS_OPERATOR_OWNED_FIELDS:"
            + ",".join(forbidden)
        )
    allowed_roots = set(template) - protected_roots
    unknown = sorted(set(research) - allowed_roots)
    if unknown:
        raise LocalInvestmentPilotError(
            "CHATGPT_RESEARCH_PATCH_UNKNOWN_TOP_LEVEL_FIELDS:" + ",".join(unknown)
        )

    def merge(base: Any, overlay: Any) -> Any:
        if isinstance(base, Mapping) and isinstance(overlay, Mapping):
            result: dict[str, Any] = {}
            for key, value in base.items():
                result[key] = merge(value, overlay[key]) if key in overlay else value
            for key, value in overlay.items():
                if key not in base:
                    result[key] = value
            return result
        # Arrays are intentionally replaced atomically to prevent silently
        # mixing old evidence/events/scenario rows with newly generated rows.
        return overlay

    expanded = merge(template, research)
    return expanded, "COMPACT_PATCH_MERGED_WITH_TRUSTED_TEMPLATE", sorted(research)


def _remove_json_trailing_commas(text: str) -> str:
    """Remove commas directly before JSON container closers, never inside strings."""
    output: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue

        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead] in " \t\r\n":
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue

        output.append(char)
        index += 1
    return "".join(output)


def _extract_json_object(text: str) -> dict[str, Any]:
    """Accept one JSON object, optionally fenced, and reject every non-whitespace suffix."""
    raw = str(text or "").strip()
    if not raw:
        raise LocalInvestmentPilotError("CHATGPT_JSON_EMPTY")
    has_leading_fence = bool(re.match(r"^\s*```(?:json)?\s*", raw, flags=re.IGNORECASE))
    if has_leading_fence:
        raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, count=1, flags=re.IGNORECASE)
    start = raw.find("{")
    if start < 0:
        raise LocalInvestmentPilotError("CHATGPT_JSON_OBJECT_NOT_FOUND")
    candidate = raw[start:]
    fence_opened_before_object = has_leading_fence or bool(
        re.search(r"```(?:json)?\s*$", raw[:start], flags=re.IGNORECASE)
    )
    if fence_opened_before_object:
        closing_fence = re.search(r"\s*```[ \t\r\n]*$", candidate)
        if closing_fence is None:
            raise LocalInvestmentPilotError(
                "CHATGPT_JSON_INVALID_CODE_FENCE_NOT_CLOSED: 请复制完整代码围栏内的 JSON，包含结束的三个反引号。"
            )
        candidate = candidate[:closing_fence.start()]
    parsed_candidate = candidate
    decoder = json.JSONDecoder()
    parse_error: json.JSONDecodeError | None = None
    parsed_end: int | None = None

    # Attempt strict parsing first. If it fails, apply only deterministic,
    # syntax-preserving repairs for two known copy artifacts:
    # (1) backslashes accidentally inserted before URL punctuation;
    # (2) trailing commas immediately before '}' or ']' outside JSON strings.
    # The raw response file is never rewritten. Incomplete strings/objects,
    # non-trailing malformed commas, and any non-whitespace suffix still fail.
    url_normalized = re.sub(r"(?i)\b(https?)\\://", r"\1://", candidate)
    url_normalized = re.sub(r"(?i)\bwww\\\.", "www.", url_normalized)
    candidates = [candidate]
    if url_normalized != candidate:
        candidates.append(url_normalized)
    for base_candidate in list(candidates):
        comma_repaired = _remove_json_trailing_commas(base_candidate)
        if comma_repaired != base_candidate:
            candidates.append(comma_repaired)

    seen_candidates: set[str] = set()
    for candidate_variant in candidates:
        if candidate_variant in seen_candidates:
            continue
        seen_candidates.add(candidate_variant)
        try:
            value, parsed_end = decoder.raw_decode(candidate_variant)
        except json.JSONDecodeError as exc:
            parse_error = exc
            continue
        parsed_candidate = candidate_variant
        parse_error = None
        break

    if parse_error is not None:
        detail = (
            f"{parse_error.msg}（第 {parse_error.lineno} 行，第 "
            f"{parse_error.colno} 列）"
        )
        raise LocalInvestmentPilotError(
            "CHATGPT_JSON_INVALID_COPY_THE_COMPLETE_JSON_OBJECT: "
            f"{detail}。程序已尝试修复明确的 URL 转义与对象/数组闭合前的尾随逗号；"
            "如果仍失败，请检查响应是否被截断；其余 JSON 语法错误不会自动改写。"
        ) from parse_error

    if parsed_end is None:
        raise LocalInvestmentPilotError("CHATGPT_JSON_INVALID_NO_COMPLETE_OBJECT")
    trailing = parsed_candidate[parsed_end:]
    if trailing.strip():
        # Previously raw_decode's end offset was ignored, meaning valid JSON
        # followed by a second object or prose could be silently accepted.
        # Only optional leading prose and one optional surrounding code fence
        # are tolerated; nothing may follow the first complete JSON object.
        raise LocalInvestmentPilotError(
            "CHATGPT_JSON_TRAILING_CONTENT_AFTER_OBJECT: "
            "检测到完整 JSON 对象后仍有额外内容。请只保留一个完整 JSON 对象；"
            "删除第二个对象、尾随解释文字或未闭合的 Markdown 代码围栏后再保存。"
        )
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


def _response_file_diagnostic(path: str | Path) -> str:
    """Report metadata about the watched path without exposing response contents."""
    response_path = Path(path).expanduser()
    try:
        resolved = response_path.resolve()
    except OSError:
        resolved = response_path
    try:
        stat = response_path.stat()
    except FileNotFoundError:
        return f"目标路径：{resolved}；文件不存在。请在文件选择窗口中选取实际保存的 JSON。"
    except OSError as exc:
        return (
            f"目标路径：{resolved}；文件状态无法读取："
            f"{type(exc).__name__}: {exc}。请在文件选择窗口中选取实际保存的 JSON。"
        )
    try:
        content = response_path.read_bytes()
    except OSError as exc:
        return (
            f"目标路径：{resolved}；磁盘记录大小={stat.st_size} 字节，但当前无法读取："
            f"{type(exc).__name__}: {exc}。请检查文件是否被锁定，或选择另一个已保存文件。"
        )
    modified = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
    if not content:
        return (
            f"目标路径：{resolved}；文件存在但当前读取为 0 字节；"
            f"磁盘记录大小={stat.st_size} 字节；最后修改={modified}。"
        )
    return (
        f"目标路径：{resolved}；当前可读取 {len(content)} 字节；"
        f"最后修改={modified}。系统正在等待文件内容变更或接受手动重检。"
    )


def _choose_saved_response_file(target_path: str | Path) -> bool:
    """Let the operator import an already-saved response if TextEdit wrote elsewhere."""
    if sys.platform != "darwin":
        print("当前平台不支持 macOS 文件选择窗口；请确认响应内容写入上方指定路径。", flush=True)
        return False

    script = (
        'POSIX path of (choose file with prompt '
        '"请选择已经保存的 ChatGPT 完整 JSON 文件；原文件不会被删除")'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
    except subprocess.CalledProcessError:
        print("已取消文件选择；程序继续等待指定结果文件更新。", flush=True)
        return False
    except (OSError, subprocess.SubprocessError) as exc:
        print(
            f"无法打开 macOS 文件选择窗口：{type(exc).__name__}: {exc}。"
            "程序继续等待；也可以重新按回车尝试。",
            flush=True,
        )
        return False

    selected_text = result.stdout.strip()
    if not selected_text:
        print("文件选择窗口没有返回路径；程序继续等待。", flush=True)
        return False

    selected_path = Path(selected_text).expanduser()
    target = Path(target_path).expanduser()
    try:
        selected_resolved = selected_path.resolve(strict=True)
        target_resolved = target.resolve()
        content = selected_path.read_bytes()
    except OSError as exc:
        print(
            f"无法读取所选文件：{type(exc).__name__}: {exc}；"
            "原结果文件未改动，程序继续等待。",
            flush=True,
        )
        return False

    if not content.strip():
        print("所选文件当前为空；原结果文件未改动。请选择已保存且包含完整 JSON 的文件。", flush=True)
        return False
    if selected_resolved == target_resolved:
        print("所选文件就是指定结果文件，但当前内容仍为空或不可读；原结果文件未改动。", flush=True)
        return False

    temporary = target.with_name(target.name + f".import-{os.getpid()}.tmp")
    try:
        temporary.write_bytes(content)
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, target)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        print(
            f"无法导入所选文件到指定结果路径：{type(exc).__name__}: {exc}；"
            "所选原文件未改动，程序继续等待。",
            flush=True,
        )
        return False

    print(
        f"已将所选文件的 {len(content)} 字节复制到指定响应路径；"
        "所选原文件保留不变。系统将自动读取并校验。",
        flush=True,
    )
    return True


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
                if latest is None or latest[0] == 0:
                    print("按回车触发了文件检查，但指定结果路径当前没有可读取的非空内容。", flush=True)
                    print(_response_file_diagnostic(response_path), flush=True)
                    print(
                        "现在打开文件选择窗口，可选择你实际保存的 JSON；"
                        "导入时会保留原文件，不需要重新研究或重新填写标的。",
                        flush=True,
                    )
                    _choose_saved_response_file(response_path)
                elif latest == previous_signature:
                    # Explicit Enter means the operator requests a fresh validation
                    # even when file metadata/content did not change since the prior read.
                    print(
                        "指定结果文件当前非空，但内容签名与上次读取相同；"
                        "按回车请求重新校验当前文件。",
                        flush=True,
                    )
                    return latest
        else:
            _time.sleep(poll_interval)



def _restore_operator_controlled_fields_from_template(
    template_path: str | Path, payload: dict[str, Any]
) -> list[str]:
    """Discard AI rewrites of operator-owned values and restore them from the local template.

    The original ChatGPT response file is not edited. The caller records the
    restored field paths in the private completed-input copy before validation.
    """
    path = Path(template_path).expanduser()
    try:
        template = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LocalInvestmentPilotError("OPERATOR_INPUT_TEMPLATE_NOT_FOUND") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalInvestmentPilotError("OPERATOR_INPUT_TEMPLATE_UNREADABLE") from exc
    if not isinstance(template, Mapping):
        raise LocalInvestmentPilotError("OPERATOR_INPUT_TEMPLATE_UNREADABLE")

    restored: list[str] = []
    # These entire sections are controlled by the operator/generated local
    # template, not by the research model. Missing sections are restored too.
    for field in ("case", "price_input", "operator_valuation_context"):
        if field not in template:
            raise LocalInvestmentPilotError(f"OPERATOR_INPUT_TEMPLATE_FIELD_MISSING:{field}")
        if payload.get(field) != template[field]:
            payload[field] = copy.deepcopy(template[field])
            restored.append(field)

    template_parameters = template.get("decision_parameters")
    if not isinstance(template_parameters, Mapping):
        raise LocalInvestmentPilotError("OPERATOR_INPUT_TEMPLATE_DECISION_PARAMETERS_INVALID")
    response_parameters = payload.get("decision_parameters")
    if not isinstance(response_parameters, dict):
        response_parameters = {}
        payload["decision_parameters"] = response_parameters
    for field in ("max_loss_pct", "required_return_annualized"):
        if field not in template_parameters:
            raise LocalInvestmentPilotError(f"OPERATOR_INPUT_TEMPLATE_POLICY_FIELD_MISSING:{field}")
        if response_parameters.get(field) != template_parameters[field]:
            response_parameters[field] = copy.deepcopy(template_parameters[field])
            restored.append(f"decision_parameters.{field}")
    return restored


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
    template_parameters = template.get("decision_parameters")
    template_parameters = template_parameters if isinstance(template_parameters, Mapping) else {}
    response_parameters = payload.get("decision_parameters")
    response_parameters = response_parameters if isinstance(response_parameters, Mapping) else {}
    # These operator-owned policy parameters directly shape return/risk gates and
    # B6 entry-price ceilings. The LLM may explain the case, but must not silently
    # lower the required-return hurdle or loosen/tighten the Bear-loss cap.
    # The operator may intentionally edit either value in the private template first.
    for policy_field in ("max_loss_pct", "required_return_annualized"):
        if response_parameters.get(policy_field) != template_parameters.get(policy_field):
            mismatched_sections.append(f"decision_parameters.{policy_field}")
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
    model_family = str(valuation.get("model_family") or "").strip().upper()
    if model_family not in PRIMARY_MODEL_FAMILIES:
        missing.append("实际计算主估值模型类别（model_family）")
    terminal_date_raw = valuation.get("valuation_terminal_date")
    terminal_date_ok = False
    if isinstance(terminal_date_raw, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", terminal_date_raw):
        try:
            _date(terminal_date_raw, "VALUATION_TERMINAL_DATE")
            terminal_date_ok = True
        except LocalInvestmentPilotError:
            terminal_date_ok = False
    if not terminal_date_ok:
        missing.append("明确的估值终点日期（valuation_terminal_date，YYYY-MM-DD）")
    if not str(valuation.get("valuation_terminal_date_basis") or "").strip():
        missing.append("估值终点日期对应预测期间的依据（valuation_terminal_date_basis）")
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

    sotp = payload.get("sotp_valuation")
    if not isinstance(sotp, Mapping) or sotp.get("schema_version") != "IIOS-SOTP-VALUATION-0.1":
        missing.append("SOTP sotp_valuation schema_version")
    elif not isinstance(sotp.get("scenarios"), Mapping) or any(not isinstance(sotp["scenarios"].get(name), Mapping) for name in ("bear", "base", "bull")):
        missing.append("SOTP Bear/Base/Bull 情景结构")

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
    """Build a short repair request; do not retransmit the huge template and prior answer."""
    return (
        "上一条完整研究提示和你的上一份回答已在当前对话中，无需重新复制模板，也不要再次输出数百行完整输入文件。"
        "\n\n【本地校验反馈】\n" + validation_error
        + "\n\n请重新检查上一份回答，输出一个简短、完整、严格可解析的 JSON 对象，使用本轮研究提示末尾定义的 "
        "IIOS-RESEARCH-PATCH-0.1 紧凑研究补丁协议。对象只能含 response_mode 与 research 两个顶层键。"
        "只输出需要修改/补充的研究字段；不要返回 schema_version、case、price_input、operator_valuation_context 或 decision_parameters。"
        "本地程序会把补丁合并进受信任的原始模板，并继续执行既有完整性、证据与估值校验。"
        "不要补造未知事实、来源、财务数字或市场一致预期。不要把截断回答强行闭合；请完整输出新的补丁对象。"
        "\n\n不要让用户手工编辑 JSON；只返回一个 JSON 对象，不要代码围栏或额外说明。"
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
    confirmed = family != "UNKNOWN"
    print(
        f"已记录主估值模型选择：{family}；操作者明确确认：{'是' if confirmed else '否'}",
        flush=True,
    )
    return {
        "selected_model_family": family,
        "baseline_includes_project": baseline_includes_project,
        "input_owner": "OPERATOR",
        "selection_source": "INTERACTIVE_OPERATOR_PROMPT",
        "selection_confirmed": confirmed,
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
        + "请填写 entry_value_reference_per_share，以及三种情景各自 probability、terminal_value_per_share、cash_distributions_per_share、cash_distribution_events、rationale；概率合计为 1。"
        + "cash_distribution_review.status 必须是 KNOWN_FUTURE_DISTRIBUTIONS 或 NO_FUTURE_DISTRIBUTIONS_CONFIRMED，并给出 summary 和 cutoff-compatible evidence_refs。"
        + "核查截至截止时点已公告的股利/现金分配，优先使用公司、交易所或监管机构的实施公告；每个 cash_distribution_events 项必须填写 gross_amount_per_share（公告税前金额）、tax_amount_per_share、amount_per_share（扣税后的计算金额）、tax_basis、tax_rationale、record_date、ex_date、payment_date、eligible_if_entered_at_cutoff、eligibility_basis、evidence_refs。"
        + "注意：price_input 是观测/参考价，不是成交回报。程序的收益与目标入场价是反事实测算，假设在分析截止日以该输入价格买入；程序不会声称该价位实际可成交，也不会声称实际分红权益已产生。eligible_if_entered_at_cutoff 只回答“若在截止日按输入参考价假设成交，日期与市场规则是否支持资格”，不能表示成交保证或已取得权益。"
        + "只有税前、税额、税后净额满足 gross_amount_per_share - tax_amount_per_share = amount_per_share，税务口径/持有期限假设具体可追责，并明确该反事实入场是否可符合分红资格（eligible_if_entered_at_cutoff=true）时，才可以把分红计入条件性回报。日期顺序必须按标的市场核验，不可把 A 股与港股规则混用：CN-A 通常为 cutoff < record_date < ex_date；HK 通常为 cutoff < ex_date <= record_date（考虑 T+2 与除净安排）；所有市场支付日须处在除净/登记及估值终点的合理顺序内。若公告的特殊安排不符合该市场通常顺序，或条件性买入资格无法证实，保留 UNKNOWN 并阻断回报/目标入场价，不要猜测修正日期。不得把公告税前金额直接当税后收益，也不得将不符合资格的分红计入新买入的收益。"
        + "每情景 cash_distributions_per_share 必须等于这些日期明确、税后金额明确、买入资格确认的现金流金额合计。若已核实未来期间无分配，填 0、空事件列表并用截止日前官方证据说明；若未能确定，不得填 0 冒充无分配，保持 UNKNOWN。日期化现金流使用实际支付日期，不能一律假设在终值日支付。"
        + "请填写 thesis_break_stress 的 failure_trigger、operating_impact、valuation_method、terminal_value_per_share、cash_distributions_per_share、rationale，且其期末总财富必须低于 Bear。"
        + "不要只原样返回模板，不允许把核心研究字段全部留空。若无法识别必须具体解释原因和证据缺口；数字估值可以建立透明、可追责的假设，但不得把假设伪装为披露事实。"
        + "严格保留 schema_version、case、price_input 原样不变，尤其不得更改人工股价、观察日期、known_at 或 price assurance 标签。"
        + """【紧凑研究补丁 JSON 协议（最高优先级，覆盖前文“返回完整对象”的旧措辞）】
不要重复输出上面的整份 600+ 行模板。只返回一个紧凑 JSON 对象。最外层只能有 response_mode 与 research 两个键，形状如下（仅示意，research 内容必须来自本次真实研究，不能照抄示例值）：
{
  "response_mode": "IIOS-RESEARCH-PATCH-0.1",
  "research": {
    "assessment": {
      "trust": {
        "summary": "填写由本轮证据支持的结论和缺口"
      }
    }
  }
}
research 是需要覆盖到可信模板上的稀疏补丁，只放本轮有证据或明确分析假设需要更新的字段；不要输出空数组、空对象或默认占位字段来凑结构。 omitted fields will be inherited from the local trusted template. 对象字段按字段递归合并；数组如 evidence_register、drivers、risk.items、cash_distribution_events 和 product_lines 则整体替换，必须把该数组中需要保留的条目一次性写全。
不要把 schema_version、case、price_input、operator_valuation_context、decision_parameters 放进 research；这些由本地可信模板提供并锁定。研究和假设仍须遵守前文所有证据、估值、分红、期间、币种及情景约束。不得通过省略必须研究的事实来隐藏问题：关键结论、Bear/Base/Bull、独立 thesis_break_stress、经营驱动因素树、EPS_MULTIPLE、SOTP 候选输入和 B5 结构仍需尽力提供；确实未知的关键字段应在相应 summary/rationale 中说明缺口。
旧版完整 IIOS JSON 对象仍可接收；但本次优先使用紧凑补丁协议，以避免回答过长被截断。只返回一个符合该协议的 JSON 对象，不要 Markdown 代码围栏或 JSON 以外的文字。"""
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
        print("\n已打开 ChatGPT 和 JSON 结果文件；研究提示与完整基准模板已复制到剪贴板。ChatGPT 只需返回紧凑研究补丁，本地会自动合并模板，不需要复制整份大 JSON。")
    else:
        print("\n研究提示（已包含本次完整 JSON 模板）：\n" + prompt)

    print(f"\nChatGPT 完整回答的保存位置：\n{response_path}")
    print("操作步骤（只需在 ChatGPT 与这个结果文件之间复制一次）：")
    print("  1. 在已打开的 ChatGPT 对话中粘贴剪贴板中的完整研究提示并发送；提示里已经包含本次 JSON 模板，不用上传模板或另找公告。")
    print("  2. 复制 ChatGPT 返回的紧凑研究补丁 JSON，覆盖上面已打开的结果文件并保存；本地将补齐模板默认结构并锁定人工控制字段。")
    print("  3. 保存后等待程序自动检测；通常无需按回车。不要把 JSON 粘贴到终端，也不要手工填写 JSON 字段。")
    if sys.platform == "darwin":
        print("  提示：JSON 文件已用 TextEdit 打开；粘贴后按 Command+S 保存。若按回车检查时目标文件仍为空，程序会打开文件选择窗口供你选择实际保存的 JSON。")

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
            response_object = _read_json_response_file(response_path)
            payload, response_format, merged_top_level_fields = _expand_research_patch_with_template(
                template_path, response_object
            )
            if _response_file_signature(response_path) != response_signature:
                raise LocalInvestmentPilotError("CHATGPT_RESPONSE_CHANGED_DURING_VALIDATION")
            # Never trust AI-authored copies of operator controls. Restore only
            # these fields from the trusted local template; leave the raw response
            # file untouched and record the exact paths in the completed input.
            payload.pop("_local_operator_controlled_field_recovery", None)
            payload.pop("_local_research_response_provenance", None)
            restored_fields = _restore_operator_controlled_fields_from_template(template_path, payload)
            if restored_fields:
                payload["_local_operator_controlled_field_recovery"] = {
                    "status": "RESTORED_BEFORE_VALIDATION",
                    "fields": restored_fields,
                    "source_template": Path(template_path).name,
                    "method": "LOCAL_TEMPLATE_OVERRIDES_AI_RESPONSE",
                    "raw_response_file_modified": False,
                }
                print(
                    "[WARN] 已丢弃 ChatGPT 对人工控制字段的改写，并从本地模板恢复："
                    + ", ".join(restored_fields)
                    + "。原始 ChatGPT 响应文件未修改；恢复清单将随本次私有输入保存。",
                    flush=True,
                )
            _assert_response_preserves_operator_inputs(template_path, payload)
            _prepare_input(payload)
            _validate_guided_research_response(payload)
            payload["_local_research_response_provenance"] = {
                "schema_version": LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
                "status": "CAPTURED_RAW_CHATGPT_RESPONSE",
                "source_filename": response_path.name,
                "sha256": response_signature[2],
                "byte_size": response_signature[0],
                "capture_stage": "RAW_RESPONSE_HASHED_ON_STABLE_SAVE_BEFORE_LOCAL_TEMPLATE_MERGE_AND_OPERATOR_FIELD_RECOVERY",
                "validation_status": "JSON_OBJECT_PARSE_PASSED; RESPONSE_FORMAT=" + response_format + "; MERGED_FIELDS=" + ",".join(merged_top_level_fields) + "; COMPLETED_INPUT_REQUIRED_FIELDS_PASSED_AFTER_LOCAL_OPERATOR_FIELD_RECOVERY",
                "raw_response_file_modified_by_runner": False,
            }
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
    result = run_local_investment_pilot(
        input_path=completed,
        output_root=output_root,
        research_response_path=response_path,
        expected_research_response_sha256=response_signature[2],
        expected_research_response_byte_size=response_signature[0],
    )
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
