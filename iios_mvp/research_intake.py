from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any

CONTRACT_VERSION = "IIOS-RESEARCH-CASE-0.1"
GENERATOR_VERSION = "CORE-01-0.1"
MARKETS = {"CN-A", "HK"}

def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc

def _normalize_market(value: Any) -> str:
    raw = str(value or "").strip().upper().replace("A股", "CN-A").replace("A-SHARE", "CN-A")
    if raw in {"A", "CN"}:
        raw = "CN-A"
    if raw in {"HKEX", "HKS"}:
        raw = "HK"
    if raw not in MARKETS:
        raise ValueError(f"market must be one of {sorted(MARKETS)}")
    return raw

def _normalize_symbol(value: Any, market: str) -> str:
    raw = str(value or "").strip().upper().replace(" ", "")
    if not raw:
        raise ValueError("symbol is required")
    if market == "CN-A":
        if re.fullmatch(r"\d{6}", raw):
            return raw
        if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", raw):
            return raw
        raise ValueError("CN-A symbol must be six digits or six digits with .SH/.SZ/.BJ")
    if re.fullmatch(r"\d{4,5}", raw):
        return raw
    if re.fullmatch(r"\d{4,5}\.HK", raw):
        return raw
    raise ValueError("HK symbol must be 4-5 digits or digits with .HK")

def _venue_hint(symbol: str, market: str) -> str | None:
    if market == "HK":
        return "HKEX"
    bare = symbol.split(".")[0]
    if re.fullmatch(r"(000|001|002|003|300)\d{3}", bare):
        return "SZSE"
    if re.fullmatch(r"(600|601|603|605|688)\d{3}", bare):
        return "SSE"
    if re.fullmatch(r"(43|83|87|92)\d{4}", bare):
        return "BSE"
    return None

def _position(value: Any) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("current_position_pct must be numeric") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > 100:
        raise ValueError("current_position_pct must be within [0,100]")
    return format(parsed, "f")

EVIDENCE_PLAN = (
    ("security_identity", "Authoritatively resolve issuer identity, venue and security status.", "P0", ("OFFICIAL_EXCHANGE", "ISSUER_PRIMARY")),
    ("market_price", "Bind decision price to the requested as-of/cutoff observation.", "P0", ("OFFICIAL_EXCHANGE", "REPRODUCIBLE_PUBLIC_DATA")),
    ("corporate_disclosures", "Capture material filings, announcements and disclosure chronology.", "P0", ("ISSUER_PRIMARY", "OFFICIAL_EXCHANGE", "REGULATOR_PRIMARY")),
    ("business_reality", "Establish business mix, products, customers and material operating facts.", "P0", ("ISSUER_PRIMARY", "OFFICIAL_DATABASE")),
    ("financial_reality", "Establish PIT financial reality and key operating/economic observations.", "P0", ("ISSUER_PRIMARY", "OFFICIAL_DATABASE")),
    ("capital_structure", "Establish shares, ownership, dilution and other capital-structure facts.", "P1", ("ISSUER_PRIMARY", "OFFICIAL_EXCHANGE")),
    ("trust_governance_events", "Check material governance, integrity, litigation and shareholder-risk evidence.", "P0", ("REGULATOR_PRIMARY", "OFFICIAL_EXCHANGE", "ISSUER_PRIMARY")),
)

def build_research_case(symbol: Any, as_of_date: Any, current_position_pct: Any, market: Any = "CN-A", generated_at: Any | None = None) -> dict[str, Any]:
    normalized_market = _normalize_market(market)
    normalized_symbol = _normalize_symbol(symbol, normalized_market)
    cutoff = _date(as_of_date, "as_of_date")
    today = date.today()
    if cutoff > today:
        raise ValueError("as_of_date cannot be in the future")
    position = _position(current_position_pct)
    user_input = {
        "market": normalized_market,
        "symbol": normalized_symbol,
        "as_of_date": cutoff.isoformat(),
        "current_position_pct": position,
    }
    case_id = f"RC-{normalized_market}-{normalized_symbol.replace('.', '-')}-{cutoff.strftime('%Y%m%d')}"
    mode = "CURRENT" if cutoff == today else "HISTORICAL"
    plan = [
        {
            "field_group": group,
            "purpose": purpose,
            "priority": priority,
            "source_classes": list(source_classes),
            "required_for_admission": True,
            "pit_rule": "known_at <= cutoff",
            "status": "PENDING",
        }
        for group, purpose, priority, source_classes in EVIDENCE_PLAN
    ]
    generated_dt = datetime.now(timezone.utc) if generated_at is None else datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    if generated_dt.tzinfo is None:
        raise ValueError("generated_at must include an explicit timezone")
    return {
        "contract_version": CONTRACT_VERSION,
        "case_id": case_id,
        "generator_version": GENERATOR_VERSION,
        "request": user_input,
        "security_identity": {
            "status": "UNRESOLVED",
            "market": normalized_market,
            "symbol": normalized_symbol,
            "venue_hint": _venue_hint(normalized_symbol, normalized_market),
            "venue_hint_is_evidence": False,
            "resolution_basis_required": "PRIMARY_OFFICIAL",
        },
        "temporal_scope": {
            "as_of_date": cutoff.isoformat(),
            "cutoff_date": cutoff.isoformat(),
            "mode": mode,
            "pit_required": True,
            "pit_rule": "known_at <= cutoff",
            "current_state_substitution": "FORBIDDEN",
        },
        "decision_context": {
            "current_position_pct": position,
            "position_basis": "CURRENT_PORTFOLIO_STATE",
        },
        "evidence_plan": plan,
        "evidence": [],
        "admission": {
            "status": "EVIDENCE_PENDING",
            "decision_ready": False,
            "blockers": [
                "SECURITY_IDENTITY_EVIDENCE_REQUIRED",
                "MARKET_PRICE_EVIDENCE_REQUIRED",
                "MANDATORY_COMPANY_EVIDENCE_PENDING",
            ],
        },
        "audit": {
            "input_sha256": _sha(user_input),
            "evidence_plan_sha256": _sha(plan),
            "generated_at": generated_dt.astimezone(timezone.utc).isoformat(),
        },
    }

def validate_research_case(case: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(case, dict):
        return ["CASE_TYPE:must be an object"]
    for field in ("contract_version","case_id","generator_version","request","security_identity","temporal_scope","decision_context","evidence_plan","evidence","admission","audit"):
        if field not in case:
            errors.append(f"MISSING:{field}")
    if errors:
        return errors
    if case.get("contract_version") != CONTRACT_VERSION:
        errors.append("CASE_VERSION:unsupported contract version")
    request = case["request"]
    try:
        market = _normalize_market(request.get("market"))
        symbol = _normalize_symbol(request.get("symbol"), market)
        cutoff = _date(request.get("as_of_date"), "request.as_of_date")
        position = _position(request.get("current_position_pct"))
    except ValueError as exc:
        errors.append(f"REQUEST_INVALID:{exc}")
        return errors
    expected_id = f"RC-{market}-{symbol.replace('.', '-')}-{cutoff.strftime('%Y%m%d')}"
    if case["case_id"] != expected_id:
        errors.append("CASE_ID_NOT_DETERMINISTIC")
    temporal = case["temporal_scope"]
    if temporal.get("as_of_date") != cutoff.isoformat() or temporal.get("cutoff_date") != cutoff.isoformat():
        errors.append("TEMPORAL_SCOPE_MISMATCH")
    if temporal.get("pit_required") is not True or temporal.get("pit_rule") != "known_at <= cutoff":
        errors.append("PIT_RULE_INVALID")
    if temporal.get("current_state_substitution") != "FORBIDDEN":
        errors.append("CURRENT_STATE_SUBSTITUTION_NOT_FORBIDDEN")
    if case["decision_context"].get("current_position_pct") != position:
        errors.append("POSITION_CONTEXT_MISMATCH")
    identity = case["security_identity"]
    if identity.get("market") != market or identity.get("symbol") != symbol:
        errors.append("IDENTITY_REQUEST_MISMATCH")
    if identity.get("venue_hint_is_evidence") is not False:
        errors.append("VENUE_HINT_MUST_NOT_BE_EVIDENCE")
    if not isinstance(case["evidence"], list):
        errors.append("EVIDENCE_TYPE:must be a list")
    if not isinstance(case["evidence_plan"], list) or len(case["evidence_plan"]) != len(EVIDENCE_PLAN):
        errors.append("EVIDENCE_PLAN_INCOMPLETE")
    else:
        for item in case["evidence_plan"]:
            if item.get("pit_rule") != "known_at <= cutoff" or item.get("required_for_admission") is not True:
                errors.append("EVIDENCE_PLAN_PIT_OR_REQUIRED_FLAG_INVALID")
                break
    return errors

def is_decision_ready(case: dict[str, Any]) -> bool:
    return not validate_research_case(case) and case.get("admission", {}).get("status") == "ADMITTED"

__all__ = ["CONTRACT_VERSION","GENERATOR_VERSION","build_research_case","validate_research_case","is_decision_ready"]
