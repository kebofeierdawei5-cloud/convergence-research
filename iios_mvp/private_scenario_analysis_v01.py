from __future__ import annotations

"""Deterministic private scenario valuation for Path A operator-attested prices.

This is intentionally not a canonical Investment Core / Evidence-PIT / Decision
path. It consumes a private normalized Path A record, binds it to a versioned
scenario profile, writes a private immutable analysis bundle, and supports
deterministic replay. No network, LLM, provider, or paid data source is used.
"""

import argparse
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Any, Mapping

from .operator_attested_price_input_v01 import (
    ANALYSIS_ONLY_STATUS,
    OPERATOR_PRICE_RECORD_SCHEMA,
    resolve_scenario_price,
)

SCENARIO_ANALYSIS_SCHEMA = "IIOS-PRIVATE-SCENARIO-ANALYSIS-0.1"
SCENARIO_RECEIPT_SCHEMA = "IIOS-PRIVATE-SCENARIO-RECEIPT-0.1"
SCENARIO_RUNNER_VERSION = "IIOS-PRIVATE-SCENARIO-RUNNER-0.1"
SCENARIO_PROFILE_SET_VERSION = "IIOS-PATH-A-SCENARIO-PROFILES-0.1"
SCENARIO_ONLY_STATUS = "PRIVATE_SCENARIO_ANALYSIS_ONLY"
SHANGHAI = timezone(timedelta(hours=8))
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CODE_RE = re.compile(r"^\d{6}$")
_FALSE_ONLY_FLAGS = (
    "source_origin_verified",
    "source_vintage_verified",
    "source_use_rights_verified",
    "canonical_price_admission",
    "formal_evidence_pit_admission",
    "decision_authority",
)

# Values below are intentionally explicit and version-bound. They reproduce
# the existing scenario assumptions; they are NOT admitted Forecast objects.
# To change them, make a new profile version rather than silently editing a run.
_SCENARIO_PROFILES: dict[str, dict[str, Any]] = {
    "RC-CN-A-002001-20261009": {
        "profile_id": "XINHECHENG-PILOT02-NORMALIZED-EARNINGS-1Y-0.1",
        "symbol": "002001",
        "company": "浙江新和成股份有限公司",
        "economic_profile": "CYCLICAL_70_GROWTH_30",
        "model": "NORMALIZED_EPS_X_PE",
        "assumptions_as_of_date": "2026-10-07",
        "assumption_class": "EXISTING_PILOT02_MODEL_ASSUMPTIONS_NOT_MARKET_CONSENSUS",
        "assumptions_reference": "docs/iios/PILOT-02_XINHECHENG_20261007.md",
        "probabilities_calibrated": False,
        "horizon_years": 1,
        "target_annualized_return_fraction": "0.15",
        "maximum_bear_loss_fraction": "0.25",
        "loss_limit_class": "EXISTING_PILOT02_DECLARED_MAX_LOSS_BOUNDARY",
        "cash_distributions_included": False,
        "scenarios": {
            "bear": {
                "eps_cny": "2.10",
                "multiple": "9.5",
                "probability": "0.30",
                "cash_distributions_per_share_cny": "0",
                "rationale": "周期较快均值回归，盈利中枢下行；为既有 PILOT-02 明确模型假设。",
            },
            "base": {
                "eps_cny": "2.80",
                "multiple": "11.5",
                "probability": "0.50",
                "cash_distributions_per_share_cny": "0",
                "rationale": "周期正常化，产品结构与成长项目部分托住盈利；为既有模型假设。",
            },
            "bull": {
                "eps_cny": "3.50",
                "multiple": "13.0",
                "probability": "0.20",
                "cash_distributions_per_share_cny": "0",
                "rationale": "核心产品周期更强、成长项目提升盈利中枢；为既有模型假设。",
            },
        },
        "limitations": [
            "情景 EPS、估值倍数与概率是既有 PILOT-02 模型假设，不是市场一致预期，也未声称经过概率校准。",
            "基础业务假设沿用 2026-10-07 PILOT-02；价格 overlay 不等于全套公司事实已更新到 2026-10-10。",
        ],
    },
    "RC-CN-A-605016-20261009": {
        "profile_id": "BAILONG-PRIOR-ANALYST-SCENARIO-UNCALIBRATED-1Y-0.1",
        "symbol": "605016",
        "company": "山东百龙创园生物科技股份有限公司",
        "economic_profile": "CAPACITY_GROWTH_B2B",
        "model": "EPS_X_PE_ANALYST_SCENARIO_ONLY",
        "assumptions_as_of_date": "2026-10-10",
        "assumption_class": "PRIOR_ANALYST_SCENARIO_ONLY_UNCALIBRATED",
        "assumptions_reference": "IIOS price-updated scenario analysis 2026-10-10; not a canonical Forecast",
        "probabilities_calibrated": False,
        "horizon_years": 1,
        "target_annualized_return_fraction": "0.15",
        "maximum_bear_loss_fraction": "0.25",
        "loss_limit_class": "PROVISIONAL_ANALYSIS_ONLY_MAX_LOSS_STRESS",
        "cash_distributions_included": False,
        "scenarios": {
            "bear": {
                "eps_cny": "0.80",
                "multiple": "17",
                "probability": "0.25",
                "cash_distributions_per_share_cny": "0",
                "rationale": "较弱盈利与倍数收缩压力情景；并非已准入预测。",
            },
            "base": {
                "eps_cny": "1.10",
                "multiple": "22",
                "probability": "0.50",
                "cash_distributions_per_share_cny": "0",
                "rationale": "先前分析采用的基准 EPS / P-E 假设；未经正式盈利预测准入。",
            },
            "bull": {
                "eps_cny": "1.30",
                "multiple": "25",
                "probability": "0.25",
                "cash_distributions_per_share_cny": "0",
                "rationale": "较强盈利与估值维持情景；并非已准入预测。",
            },
        },
        "limitations": [
            "此情景复现先前分析所用的 EPS / P-E 假设，不是 canonical Independent Forecast。",
            "概率未经校准；基准 EPS 和 22 倍 P-E 需要独立验证，不能单凭本模型成为可信目标价。",
            "25% 最大损失仅是临时情景压力边界，不是经过正式 Risk / Portfolio Admission 的限制。",
        ],
    },
}


class PrivateScenarioAnalysisError(ValueError):
    """Raised when a private scenario input or output violates its contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise PrivateScenarioAnalysisError("NON_FINITE_JSON_NUMBER")


def _unique_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PrivateScenarioAnalysisError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _load_json_bytes(raw: bytes, *, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, PrivateScenarioAnalysisError):
            raise
        raise PrivateScenarioAnalysisError(reason) from exc
    if not isinstance(value, dict):
        raise PrivateScenarioAnalysisError("JSON_ROOT_MUST_BE_OBJECT")
    return value


def _outside_repository(path: Path, field: str) -> Path:
    if path.is_symlink():
        raise PrivateScenarioAnalysisError(f"{field}_MUST_NOT_BE_SYMLINK")
    resolved = path.expanduser().resolve(strict=False)
    repo = REPOSITORY_ROOT.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY")
    return resolved


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool):
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_FINITE_DECIMAL")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_FINITE_DECIMAL") from exc
    if not result.is_finite():
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_FINITE_DECIMAL")
    return result


def _positive(value: Any, field: str) -> Decimal:
    result = _decimal(value, field)
    if result <= 0:
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_POSITIVE")
    return result


def _format_decimal(value: Decimal, places: int = 8) -> str:
    quantum = Decimal(1).scaleb(-places)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    return format(rounded, "f")


def _format_percent(fraction: Decimal) -> str:
    return _format_decimal(fraction * Decimal("100"), 4)


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_ISO_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_ISO_DATE") from exc


def _timezone_aware_shanghai(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_TIMEZONE_AWARE")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_TIMEZONE_AWARE") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise PrivateScenarioAnalysisError(f"{field}_MUST_BE_TIMEZONE_AWARE")
    return result.astimezone(SHANGHAI)


def _validate_normalized_price_record(normalized: Mapping[str, Any]) -> list[dict[str, Any]]:
    if normalized.get("record_schema") != OPERATOR_PRICE_RECORD_SCHEMA:
        raise PrivateScenarioAnalysisError("PRICE_RECORD_SCHEMA_MISMATCH")
    if normalized.get("record_class") != "OPERATOR_ATTESTED_PRICE_ANALYSIS_ONLY":
        raise PrivateScenarioAnalysisError("PRICE_RECORD_CLASS_NOT_ANALYSIS_ONLY")
    if normalized.get("status") != ANALYSIS_ONLY_STATUS:
        raise PrivateScenarioAnalysisError("PRICE_RECORD_STATUS_NOT_ANALYSIS_ONLY")
    if normalized.get("date_cutoff_semantics") != "START_OF_DAY_ASIA_SHANGHAI":
        raise PrivateScenarioAnalysisError("PRICE_CUTOFF_SEMANTICS_INVALID")
    batch_id = normalized.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise PrivateScenarioAnalysisError("PRICE_BATCH_ID_REQUIRED")
    cutoff = _date(normalized.get("analysis_cutoff_date"), "ANALYSIS_CUTOFF_DATE")

    scope = normalized.get("scope_controls")
    if not isinstance(scope, Mapping):
        raise PrivateScenarioAnalysisError("PRICE_SCOPE_CONTROLS_REQUIRED")
    if scope.get("may_feed_scenario_valuation") is not True:
        raise PrivateScenarioAnalysisError("SCENARIO_VALUATION_SCOPE_NOT_GRANTED")
    for key in (
        "may_feed_canonical_current_price_resolver",
        "canonical_price_admission",
        "formal_evidence_pit_admission",
        "source_origin_verified",
        "source_vintage_verified",
        "source_use_rights_verified",
        "decision_authority",
        "frozen_base_case_mutated",
    ):
        if scope.get(key) is not False:
            raise PrivateScenarioAnalysisError(f"FORBIDDEN_SCOPE_FLAG_NOT_FALSE:{key}")

    records = normalized.get("records")
    if not isinstance(records, list) or not records:
        raise PrivateScenarioAnalysisError("PRICE_RECORDS_REQUIRED")

    seen: set[tuple[str, str, str]] = set()
    normalized_rows: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, Mapping):
            raise PrivateScenarioAnalysisError("PRICE_ROW_MUST_BE_OBJECT")
        base_case_id = row.get("base_case_id")
        symbol = row.get("symbol")
        if not isinstance(base_case_id, str) or not base_case_id.strip():
            raise PrivateScenarioAnalysisError("BASE_CASE_ID_REQUIRED")
        if not isinstance(symbol, str) or not _CODE_RE.fullmatch(symbol):
            raise PrivateScenarioAnalysisError("SYMBOL_INVALID")
        profile = _SCENARIO_PROFILES.get(base_case_id)
        if profile is None or profile.get("symbol") != symbol:
            raise PrivateScenarioAnalysisError("UNSUPPORTED_SCENARIO_PROFILE_FOR_CASE")
        if row.get("record_schema") != OPERATOR_PRICE_RECORD_SCHEMA:
            raise PrivateScenarioAnalysisError("PRICE_ROW_SCHEMA_MISMATCH")
        if row.get("record_class") != "OPERATOR_ATTESTED_MARKET_DATA":
            raise PrivateScenarioAnalysisError("PRICE_ROW_CLASS_NOT_OPERATOR_ATTESTED")
        if row.get("analysis_only_status") != ANALYSIS_ONLY_STATUS:
            raise PrivateScenarioAnalysisError("PRICE_ROW_STATUS_NOT_ANALYSIS_ONLY")
        if row.get("market") != "CN-A":
            raise PrivateScenarioAnalysisError("MARKET_UNSUPPORTED")
        expected_exchange = "SSE" if symbol.startswith(("60", "68", "90")) else "SZSE"
        if row.get("exchange") != expected_exchange:
            raise PrivateScenarioAnalysisError("EXCHANGE_SYMBOL_MISMATCH")
        if row.get("currency") != "CNY" or row.get("unit") != "CNY/share":
            raise PrivateScenarioAnalysisError("PRICE_CURRENCY_OR_UNIT_INVALID")
        if row.get("adjustment_semantics") != "UNADJUSTED_CLOSE":
            raise PrivateScenarioAnalysisError("PRICE_ADJUSTMENT_SEMANTICS_INVALID")
        price = _positive(row.get("price"), "CURRENT_PRICE")
        observation = _date(row.get("observation_date"), "OBSERVATION_DATE")
        known_at = _timezone_aware_shanghai(row.get("operator_attested_known_at"), "OPERATOR_ATTESTED_KNOWN_AT")
        cutoff_start = datetime.combine(cutoff, time.min, tzinfo=SHANGHAI)
        if observation > cutoff:
            raise PrivateScenarioAnalysisError("OBSERVATION_DATE_AFTER_ANALYSIS_CUTOFF")
        if observation != known_at.date():
            raise PrivateScenarioAnalysisError("KNOWN_AT_DATE_MUST_MATCH_OBSERVATION_DATE")
        if known_at >= cutoff_start:
            raise PrivateScenarioAnalysisError("PRICE_KNOWN_AT_NOT_BEFORE_CUTOFF_START")
        sources = row.get("sources_claimed")
        if not isinstance(sources, list) or not sources or any(not isinstance(v, str) or not v.strip() for v in sources):
            raise PrivateScenarioAnalysisError("SOURCE_CLAIMS_INVALID")
        for flag in _FALSE_ONLY_FLAGS:
            if row.get(flag) is not False:
                raise PrivateScenarioAnalysisError(f"FORBIDDEN_PRICE_AUTHORITY_FLAG_NOT_FALSE:{flag}")
        key = (base_case_id, symbol, observation.isoformat())
        if key in seen:
            raise PrivateScenarioAnalysisError("DUPLICATE_CASE_SYMBOL_OBSERVATION")
        seen.add(key)
        # Delegate scope resolution to the existing Path A resolver and recheck
        # its returned flags rather than trusting a caller-supplied price object.
        price_ref = resolve_scenario_price(normalized, base_case_id=base_case_id, symbol=symbol)
        if (
            price_ref.get("status") != "OPERATOR_ATTESTED_SCENARIO_INPUT_ONLY"
            or price_ref.get("current_price") != format(price, "f")
            or price_ref.get("may_feed_canonical_current_price_resolver") is not False
            or price_ref.get("may_create_formal_decision") is not False
        ):
            raise PrivateScenarioAnalysisError("PATH_A_SCENARIO_PRICE_RESOLUTION_FAILED")
        normalized_rows.append(dict(row))
    return normalized_rows


def _profile_digest(profiles: list[dict[str, Any]]) -> str:
    return _sha256(_canonical({"profile_set_version": SCENARIO_PROFILE_SET_VERSION, "profiles": profiles}))


def _validate_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    scenarios = profile.get("scenarios")
    if not isinstance(scenarios, Mapping) or set(scenarios) != {"bear", "base", "bull"}:
        raise PrivateScenarioAnalysisError("SCENARIO_PROFILE_MUST_HAVE_BEAR_BASE_BULL")
    horizon = profile.get("horizon_years")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon not in (1, 2, 3):
        raise PrivateScenarioAnalysisError("HORIZON_YEARS_MUST_BE_1_TO_3")
    target = _decimal(profile.get("target_annualized_return_fraction"), "TARGET_RETURN")
    loss = _decimal(profile.get("maximum_bear_loss_fraction"), "MAXIMUM_BEAR_LOSS")
    if target <= Decimal("-1") or target > Decimal("2"):
        raise PrivateScenarioAnalysisError("TARGET_RETURN_OUT_OF_RANGE")
    if loss <= 0 or loss >= 1:
        raise PrivateScenarioAnalysisError("MAXIMUM_BEAR_LOSS_OUT_OF_RANGE")
    probability_sum = Decimal("0")
    clean: dict[str, dict[str, Any]] = {}
    for name in ("bear", "base", "bull"):
        row = scenarios[name]
        if not isinstance(row, Mapping):
            raise PrivateScenarioAnalysisError(f"SCENARIO_NOT_OBJECT:{name}")
        eps = _positive(row.get("eps_cny"), f"{name.upper()}_EPS")
        multiple = _positive(row.get("multiple"), f"{name.upper()}_MULTIPLE")
        probability = _decimal(row.get("probability"), f"{name.upper()}_PROBABILITY")
        cash_distribution = _decimal(
            row.get("cash_distributions_per_share_cny", "0"),
            f"{name.upper()}_CASH_DISTRIBUTION",
        )
        if probability < 0 or probability > 1:
            raise PrivateScenarioAnalysisError(f"SCENARIO_PROBABILITY_OUT_OF_RANGE:{name}")
        if cash_distribution < 0:
            raise PrivateScenarioAnalysisError(f"SCENARIO_CASH_DISTRIBUTION_NEGATIVE:{name}")
        probability_sum += probability
        clean[name] = {
            "eps": eps,
            "multiple": multiple,
            "probability": probability,
            "cash_distribution": cash_distribution,
            "value": eps * multiple,
            "rationale": str(row.get("rationale", "")),
        }
    if probability_sum != Decimal("1"):
        raise PrivateScenarioAnalysisError("SCENARIO_PROBABILITIES_MUST_SUM_TO_ONE")
    return {
        "scenario_rows": clean,
        "horizon_years": horizon,
        "target_return": target,
        "maximum_bear_loss": loss,
    }


def _scenario_analysis_for_row(
    row: Mapping[str, Any],
    *,
    input_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_id = str(row["base_case_id"])
    symbol = str(row["symbol"])
    profile = _SCENARIO_PROFILES[case_id]
    validated = _validate_profile(profile)
    price_ref_value = _decimal(row.get("price"), "CURRENT_PRICE")
    price_ref = {
        "status": "OPERATOR_ATTESTED_SCENARIO_INPUT_ONLY",
        "base_case_id": case_id,
        "symbol": symbol,
        "current_price": format(price_ref_value, "f"),
        "observation_date": row["observation_date"],
        "operator_attested_known_at": row["operator_attested_known_at"],
        "source_class": "OPERATOR_ATTESTED_MARKET_DATA",
        "source_origin_verified": False,
        "source_vintage_verified": False,
        "source_use_rights_verified": False,
        "canonical_price_admission": False,
        "formal_evidence_pit_admission": False,
        "may_feed_canonical_current_price_resolver": False,
        "may_create_formal_decision": False,
        "decision_authority": False,
    }
    # Call the existing Path A resolver through a small source-bound envelope
    # assembled only from the validated normalized input by the caller.
    current_price = _positive(price_ref_value, "CURRENT_PRICE")
    horizon = validated["horizon_years"]
    target = validated["target_return"]
    max_loss = validated["maximum_bear_loss"]
    scenario_results: dict[str, dict[str, str]] = {}
    expected_wealth = Decimal("0")
    bear_wealth: Decimal | None = None
    for name in ("bear", "base", "bull"):
        scenario = validated["scenario_rows"][name]
        value = scenario["value"]
        distribution = scenario["cash_distribution"]
        terminal_wealth = value + distribution
        contribution = scenario["probability"] * terminal_wealth
        expected_wealth += contribution
        if name == "bear":
            bear_wealth = terminal_wealth
        scenario_results[name] = {
            "eps_cny": _format_decimal(scenario["eps"]),
            "multiple": _format_decimal(scenario["multiple"]),
            "value_per_share_cny": _format_decimal(value),
            "probability": _format_decimal(scenario["probability"]),
            "cash_distributions_per_share_cny": _format_decimal(distribution),
            "terminal_wealth_per_share_cny": _format_decimal(terminal_wealth),
            "probability_weighted_wealth_contribution_cny": _format_decimal(contribution),
            "rationale": scenario["rationale"],
        }
    if bear_wealth is None:
        raise PrivateScenarioAnalysisError("BEAR_SCENARIO_REQUIRED")
    with localcontext() as ctx:
        ctx.prec = 28
        target_denominator = (Decimal("1") + target) ** horizon
        expected_total_return = expected_wealth / current_price - Decimal("1")
        expected_annualized_return = (
            (expected_wealth / current_price) ** (Decimal("1") / Decimal(horizon))
            - Decimal("1")
        )
        entry_ceiling_return = expected_wealth / target_denominator
        entry_ceiling_bear = bear_wealth / (Decimal("1") - max_loss)
        binding_ceiling = min(entry_ceiling_return, entry_ceiling_bear)
        bear_return_at_current_price = bear_wealth / current_price - Decimal("1")
    headroom = binding_ceiling - current_price
    profile_summary = {
        "profile_id": profile["profile_id"],
        "profile_version": SCENARIO_PROFILE_SET_VERSION,
        "model": profile["model"],
        "economic_profile": profile["economic_profile"],
        "assumptions_as_of_date": profile["assumptions_as_of_date"],
        "assumption_class": profile["assumption_class"],
        "assumptions_reference": profile["assumptions_reference"],
        "probabilities_calibrated": profile["probabilities_calibrated"],
        "horizon_years": horizon,
        "target_annualized_return_pct": _format_percent(target),
        "maximum_bear_loss_pct": _format_percent(max_loss),
        "loss_limit_class": profile["loss_limit_class"],
        "cash_distributions_included": profile["cash_distributions_included"],
        "scenarios": scenario_results,
        "limitations": list(profile["limitations"]),
    }
    analysis = {
        "schema_version": SCENARIO_ANALYSIS_SCHEMA,
        "runner_version": SCENARIO_RUNNER_VERSION,
        "scenario_profile_set_version": SCENARIO_PROFILE_SET_VERSION,
        "analysis_id": "",
        "status": SCENARIO_ONLY_STATUS,
        "analysis_only": True,
        "case": {
            "case_id": case_id,
            "market": row["market"],
            "symbol": symbol,
            "exchange": row["exchange"],
            "company": profile["company"],
            "base_case_cutoff_date": "2026-10-09",
            "price_observation_date": row["observation_date"],
            "analysis_overlay_cutoff_date": None,
            "current_price_cny": _format_decimal(current_price),
            "price_adjustment_semantics": row["adjustment_semantics"],
            "price_record_class": "OPERATOR_ATTESTED_MARKET_DATA",
            "operator_attested_known_at": row["operator_attested_known_at"],
        },
        "scenario_profile": profile_summary,
        "return_and_entry_evaluation": {
            "expected_terminal_wealth_per_share_cny": _format_decimal(expected_wealth),
            "expected_total_return_pct": _format_percent(expected_total_return),
            "expected_annualized_return_pct": _format_percent(expected_annualized_return),
            "return_hurdle_entry_price_ceiling_cny": _format_decimal(entry_ceiling_return),
            "bear_terminal_wealth_per_share_cny": _format_decimal(bear_wealth),
            "bear_return_at_current_price_pct": _format_percent(bear_return_at_current_price),
            "entry_price_ceiling_from_max_bear_loss_cny": _format_decimal(entry_ceiling_bear),
            "binding_conditional_entry_price_ceiling_cny": _format_decimal(binding_ceiling),
            "headroom_to_binding_ceiling_cny": _format_decimal(headroom),
            "conditional_price_screen": (
                "PRICE_AT_OR_BELOW_CONDITIONAL_ENTRY_CEILING"
                if current_price <= binding_ceiling
                else "PRICE_ABOVE_CONDITIONAL_ENTRY_CEILING"
            ),
            "cash_distributions_included": False,
            "formulae": {
                "expected_terminal_wealth": "sum(probability * (scenario_value_per_share + scenario_cash_distributions_per_share))",
                "expected_total_return": "expected_terminal_wealth / current_price - 1",
                "expected_annualized_return": "(expected_terminal_wealth / current_price) ** (1 / horizon_years) - 1",
                "return_hurdle_entry_price_ceiling": "expected_terminal_wealth / (1 + target_annualized_return) ** horizon_years",
                "bear_loss_price_ceiling": "bear_terminal_wealth / (1 - maximum_bear_loss_fraction)",
                "binding_conditional_entry_ceiling": "min(return_hurdle_entry_price_ceiling, bear_loss_price_ceiling)",
            },
        },
        "input_binding": {
            "private_input_sha256": input_sha256,
            "profile_sha256": "",
            "frozen_base_case_mutated": False,
            "company_evidence_revalidated_to_overlay_cutoff": False,
            "source_origin_verified": False,
            "source_vintage_verified": False,
            "source_use_rights_verified": False,
        },
        "governance": {
            "decision_authority": False,
            "canonical_price_admission": False,
            "formal_evidence_pit_admission": False,
            "formal_forecast_created": False,
            "formal_valuation_admission": False,
            "formal_decision_created": False,
            "machine_publication_created": False,
            "run_receipt_created": False,
            "execution_authorized": False,
            "auto_execution": False,
        },
    }
    return analysis, price_ref


def _render_report(analyses: list[dict[str, Any]], *, analysis_id: str) -> str:
    lines = [
        "# IIOS 本地私有情景分析",
        "",
        f"- 分析 ID：`{analysis_id}`",
        f"- Runner：`{SCENARIO_RUNNER_VERSION}`",
        f"- Profile 集：`{SCENARIO_PROFILE_SET_VERSION}`",
        "- 性质：**PRIVATE_SCENARIO_ANALYSIS_ONLY / NON-CANONICAL**",
        "",
        "> **重要边界：** 价格来自人工确认的未复权收盘价。行情来源原始字节、精确首次公开时间及使用权没有通过正式准入。本价格更新只进行情景分析，不表示同一截止时点的全部公司证据已重做 PIT 验证；不创建正式 Forecast、Valuation Admission、Decision、Publication、完整 Run Receipt 或交易授权。",
        "",
    ]
    for analysis in analyses:
        case = analysis["case"]
        profile = analysis["scenario_profile"]
        returns = analysis["return_and_entry_evaluation"]
        lines.extend([
            "---",
            "",
            f"## {case['company']}（{case['symbol']}.{case['exchange']}）",
            "",
            f"- 基础 Case：`{case['case_id']}`",
            f"- 行情日期：{case['price_observation_date']}；人工输入价格：**¥{case['current_price_cny']}** / 股",
            f"- 分析截止：{case['analysis_overlay_cutoff_date']}（仅价格 overlay，不是新 Case PIT）",
            f"- 估值模型：{profile['model']}；假设版本：`{profile['profile_id']}`",
            f"- 假设性质：{profile['assumption_class']}",
            f"- 概率是否校准：{'是' if profile['probabilities_calibrated'] else '否'}",
            "",
            "| 情景 | EPS（元） | 倍数 | 情景价值（元/股） | 概率 | 分析说明 |",
            "|---|---:|---:|---:|---:|---|",
        ])
        for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
            scenario = profile["scenarios"][name]
            lines.append(
                f"| {label} | {scenario['eps_cny']} | {scenario['multiple']}x | "
                f"{scenario['value_per_share_cny']} | {scenario['probability']} | {scenario['rationale']} |"
            )
        lines.extend([
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| 概率加权终值（含本模型现金分配假设） | ¥{returns['expected_terminal_wealth_per_share_cny']} |",
            f"| 预期总回报 | {returns['expected_total_return_pct']}% |",
            f"| 预期年化回报（H={profile['horizon_years']}Y） | {returns['expected_annualized_return_pct']}% |",
            f"| 满足 15% 年化门槛的入场价上限 | ¥{returns['return_hurdle_entry_price_ceiling_cny']} |",
            f"| Bear 情景在当前价的价格回报 | {returns['bear_return_at_current_price_pct']}% |",
            f"| Bear 损失上限约束下的价格上限 | ¥{returns['entry_price_ceiling_from_max_bear_loss_cny']} |",
            f"| **两项约束共同决定的条件性入场价上限** | **¥{returns['binding_conditional_entry_price_ceiling_cny']}** |",
            f"| 当前价格相对该上限的差额 | ¥{returns['headroom_to_binding_ceiling_cny']} |",
            "",
            f"**价格情景筛选：** `{returns['conditional_price_screen']}`。这是基于本组假设的计算标签，不是 IIOS BUY/ADD/NO-BUY/Decision。",
            "",
            "**本情景假设的限制：**",
        ])
        for limitation in profile["limitations"]:
            lines.append(f"- {limitation}")
        lines.append("")
    lines.extend([
        "---",
        "",
        "## 治理和证据限制",
        "",
        "- `OPERATOR_ATTESTED_MARKET_DATA` 只可进入本地情景计算，不进入 canonical current-price resolver。",
        "- 情景概率、EPS 与估值倍数均为版本化模型假设，不是证据事实；模型本身不会把它们升级为正式 Forecast。",
        "- 本报告不修改原始 Case，不将人工价格变成 source-vintage verified，不创建正式投资 Decision。",
        "- 输出与输入保存在本机私有目录，文件权限要求为目录 0700、文件 0600；不会提交 GitHub 或工作流 artifact。",
        "",
    ])
    return "\n".join(lines)


def _analysis_body_without_hashes(analyses: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCENARIO_ANALYSIS_SCHEMA,
        "runner_version": SCENARIO_RUNNER_VERSION,
        "scenario_profile_set_version": SCENARIO_PROFILE_SET_VERSION,
        "status": SCENARIO_ONLY_STATUS,
        "analysis_only": True,
        "company_analyses": analyses,
        "governance": {
            "source_origin_verified": False,
            "source_vintage_verified": False,
            "source_use_rights_verified": False,
            "canonical_price_admission": False,
            "formal_evidence_pit_admission": False,
            "formal_forecast_created": False,
            "formal_valuation_admission": False,
            "formal_decision_created": False,
            "machine_publication_created": False,
            "run_receipt_created": False,
            "decision_authority": False,
            "execution_authorized": False,
            "auto_execution": False,
        },
    }


def _build_artifacts(input_raw: bytes) -> tuple[str, bytes, bytes, bytes, bytes, dict[str, Any]]:
    normalized = _load_json_bytes(input_raw, reason="PRICE_RECORD_JSON_INVALID")
    rows = _validate_normalized_price_record(normalized)
    rows = sorted(rows, key=lambda row: (row["base_case_id"], row["symbol"], row["observation_date"]))
    selected_profiles = [_SCENARIO_PROFILES[row["base_case_id"]] for row in rows]
    profile_sha = _profile_digest(selected_profiles)
    input_sha = _sha256(input_raw)
    identity = _sha256(_canonical({
        "runner_version": SCENARIO_RUNNER_VERSION,
        "profile_set_version": SCENARIO_PROFILE_SET_VERSION,
        "input_sha256": input_sha,
        "profile_sha256": profile_sha,
    }))
    analysis_id = "patha-scenario-" + identity[:24]
    analyses: list[dict[str, Any]] = []
    for row in rows:
        analysis, _price_ref = _scenario_analysis_for_row(row, input_sha256=input_sha)
        analysis["case"]["analysis_overlay_cutoff_date"] = normalized["analysis_cutoff_date"]
        analysis["input_binding"]["profile_sha256"] = profile_sha
        analysis["analysis_id"] = analysis_id
        analyses.append(analysis)

    body = _analysis_body_without_hashes(analyses)
    body["analysis_id"] = analysis_id
    body["input_sha256"] = input_sha
    body["profile_sha256"] = profile_sha
    body_hash = _sha256(_canonical(body))
    machine = dict(body)
    machine["analysis_content_sha256"] = body_hash
    machine_raw = _canonical(machine) + b"\n"
    report_raw = _render_report(analyses, analysis_id=analysis_id).encode("utf-8")
    receipt = {
        "receipt_schema": SCENARIO_RECEIPT_SCHEMA,
        "status": SCENARIO_ONLY_STATUS,
        "analysis_id": analysis_id,
        "runner_version": SCENARIO_RUNNER_VERSION,
        "scenario_profile_set_version": SCENARIO_PROFILE_SET_VERSION,
        "input_sha256": input_sha,
        "profile_sha256": profile_sha,
        "analysis_file_sha256": _sha256(machine_raw),
        "report_file_sha256": _sha256(report_raw),
        "input_file_name": "input.json",
        "analysis_file_name": "analysis.json",
        "report_file_name": "report.md",
        "integrity_scope": "EXACT_PRIVATE_FILE_BYTES_ONLY_NOT_EXTERNAL_SOURCE_AUTHENTICATION",
        "quote_values_redacted": True,
        "private_source_labels_redacted": True,
        "private_input_copy_included": True,
        "public_upload_allowed": False,
        "source_origin_verified": False,
        "source_vintage_verified": False,
        "source_use_rights_verified": False,
        "canonical_price_admission": False,
        "formal_evidence_pit_admission": False,
        "formal_forecast_created": False,
        "formal_valuation_admission": False,
        "formal_decision_created": False,
        "machine_publication_created": False,
        "run_receipt_created": False,
        "decision_authority": False,
        "execution_authorized": False,
        "auto_execution": False,
    }
    receipt_raw = _canonical(receipt) + b"\n"
    return analysis_id, input_raw, machine_raw, report_raw, receipt_raw, receipt


def _read_regular_child(path: Path, filename: str) -> bytes:
    child = path / filename
    if child.is_symlink() or not child.is_file():
        raise PrivateScenarioAnalysisError(f"BUNDLE_FILE_MISSING_OR_SYMLINK:{filename}")
    return child.read_bytes()


def _assert_private_bundle_permissions(path: Path) -> None:
    if os.name == "nt":
        return
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise PrivateScenarioAnalysisError("BUNDLE_DIRECTORY_PERMISSIONS_TOO_OPEN")
    for filename in ("input.json", "analysis.json", "report.md", "receipt.json"):
        mode = stat.S_IMODE((path / filename).stat().st_mode)
        if mode & 0o077:
            raise PrivateScenarioAnalysisError(f"BUNDLE_FILE_PERMISSIONS_TOO_OPEN:{filename}")


def verify_private_scenario_bundle(run_dir: str | Path) -> dict[str, Any]:
    """Recompute analysis/report/receipt from the private preserved input copy."""
    bundle_path = Path(run_dir).expanduser()
    if bundle_path.is_symlink() or not bundle_path.is_dir():
        raise PrivateScenarioAnalysisError("BUNDLE_MUST_BE_DIRECTORY_NOT_SYMLINK")
    root = _outside_repository(bundle_path, "BUNDLE_PATH")
    input_raw = _read_regular_child(root, "input.json")
    stored_analysis = _read_regular_child(root, "analysis.json")
    stored_report = _read_regular_child(root, "report.md")
    stored_receipt = _read_regular_child(root, "receipt.json")
    analysis_id, expected_input, expected_analysis, expected_report, expected_receipt, receipt = _build_artifacts(input_raw)
    if _sha256(input_raw) != receipt["input_sha256"]:
        raise PrivateScenarioAnalysisError("BUNDLE_INPUT_HASH_MISMATCH")
    if stored_analysis != expected_analysis:
        raise PrivateScenarioAnalysisError("BUNDLE_ANALYSIS_REPLAY_MISMATCH")
    if stored_report != expected_report:
        raise PrivateScenarioAnalysisError("BUNDLE_REPORT_REPLAY_MISMATCH")
    if stored_receipt != expected_receipt:
        raise PrivateScenarioAnalysisError("BUNDLE_RECEIPT_BINDING_MISMATCH")
    _assert_private_bundle_permissions(root)
    return {
        "status": "REPLAY_PASS",
        "analysis_id": analysis_id,
        "analysis_file_sha256": _sha256(stored_analysis),
        "report_file_sha256": _sha256(stored_report),
        "receipt_file_sha256": _sha256(stored_receipt),
        "company_count": len(_load_json_bytes(stored_analysis, reason="ANALYSIS_JSON_INVALID")["company_analyses"]),
        "analysis_only": True,
        "quote_values_redacted": True,
        "decision_authority": False,
        "formal_decision_created": False,
    }


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
        raise PrivateScenarioAnalysisError("OUTPUT_FILE_PERMISSIONS_TOO_OPEN")


def _prepare_output_root(path: str | Path) -> Path:
    raw = Path(path).expanduser()
    if raw.is_symlink():
        raise PrivateScenarioAnalysisError("OUTPUT_ROOT_MUST_NOT_BE_SYMLINK")
    resolved = _outside_repository(raw, "OUTPUT_ROOT")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    if resolved.is_symlink() or not resolved.is_dir():
        raise PrivateScenarioAnalysisError("OUTPUT_ROOT_MUST_BE_DIRECTORY")
    if hasattr(os, "getuid") and resolved.stat().st_uid != os.getuid():
        raise PrivateScenarioAnalysisError("OUTPUT_ROOT_OWNER_MISMATCH")
    if os.name != "nt" and stat.S_IMODE(resolved.stat().st_mode) & 0o077:
        # Fail safely; do not chmod or otherwise mutate an existing operator directory.
        raise PrivateScenarioAnalysisError("OUTPUT_ROOT_PERMISSIONS_TOO_OPEN")
    return resolved


def run_private_scenario_analysis(
    *,
    input_path: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    """Create a deterministic private analysis bundle or reuse an identical one."""
    incoming = Path(input_path).expanduser()
    if incoming.is_symlink() or not incoming.is_file():
        raise PrivateScenarioAnalysisError("INPUT_MUST_BE_REGULAR_FILE_NOT_SYMLINK")
    input_resolved = _outside_repository(incoming, "INPUT_PATH").resolve(strict=True)
    input_raw = input_resolved.read_bytes()
    analysis_id, preserved_input, machine_raw, report_raw, receipt_raw, _receipt = _build_artifacts(input_raw)
    root = _prepare_output_root(output_root)
    run_dir = root / analysis_id

    if run_dir.exists() or run_dir.is_symlink():
        replay = verify_private_scenario_bundle(run_dir)
        return {
            "status": "SCENARIO_ANALYSIS_REUSED_IDENTICAL",
            "run_dir": str(run_dir),
            **replay,
        }

    temp_dir = Path(tempfile.mkdtemp(prefix=".scenario-tmp-", dir=str(root)))
    if os.name != "nt":
        os.chmod(temp_dir, 0o700)
    try:
        _write_private_file(temp_dir / "input.json", preserved_input)
        _write_private_file(temp_dir / "analysis.json", machine_raw)
        _write_private_file(temp_dir / "report.md", report_raw)
        _write_private_file(temp_dir / "receipt.json", receipt_raw)
        if run_dir.exists() or run_dir.is_symlink():
            raise PrivateScenarioAnalysisError("OUTPUT_RUN_ALREADY_EXISTS_RACE")
        os.rename(temp_dir, run_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    replay = verify_private_scenario_bundle(run_dir)
    return {
        "status": "SCENARIO_ANALYSIS_CREATED",
        "run_dir": str(run_dir),
        **replay,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run/replay private Path A scenario valuation without formal Decision authority."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prices", help="Path to the existing normalized private Path A JSON record.")
    group.add_argument("--replay-run", help="Verify a previous private scenario bundle directory.")
    parser.add_argument(
        "--output-root",
        default=str(Path.home() / ".iios-private" / "scenario-analysis"),
        help="Private output directory outside the repository (default: ~/.iios-private/scenario-analysis).",
    )
    args = parser.parse_args(argv)
    try:
        if args.replay_run:
            result = verify_private_scenario_bundle(args.replay_run)
            result["run_dir"] = str(Path(args.replay_run).expanduser().resolve())
        else:
            result = run_private_scenario_analysis(input_path=args.prices, output_root=args.output_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (PrivateScenarioAnalysisError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
