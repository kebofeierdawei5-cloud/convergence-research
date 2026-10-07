from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json

import pytest

from iios_mvp.canonical_investment_admission_v01 import (
    build_canonical_investment_admission,
)
from iios_mvp.canonical_independent_forecast import (
    InMemoryCanonicalIndependentForecastRegistry,
)
from iios_mvp.engine import decide, replay, run_case
from iios_mvp.forecast_valuation_return_lineage_v01 import (
    InMemoryCanonicalValuationOutputResolver,
    build_canonical_valuation_output,
)
from iios_mvp.investment_core_contract_v03 import validate_case_v03
from tests.test_investment_core_v03 import (
    CURRENT_PRICE_REGISTRY,
    EVIDENCE_ROOT_REGISTRY,
    INDEPENDENT_FORECAST_REGISTRY,
    UPSTREAM_AUTHORITY_REGISTRY,
    VALUATION_ADMISSION_REGISTRY,
    VALUATION_OUTPUT_RESOLVER,
    case,
)


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _full_validate(c: dict, *, forecast_registry=None, valuation_resolver=None):
    return validate_case_v03(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=forecast_registry or INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
        valuation_output_resolver=valuation_resolver or VALUATION_OUTPUT_RESOLVER,
    )


def _alternate_forecast_ref(c: dict) -> dict:
    original_ref = c["return_gate"]["canonical_forecast_ref"]
    original = INDEPENDENT_FORECAST_REGISTRY.resolve_independent_forecast(
        original_ref,
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        cutoff_date=date.fromisoformat(c["cutoff_date"]),
    )
    payload = {
        key: original[key]
        for key in (
            "case_id",
            "market",
            "symbol",
            "cutoff_date",
            "forecast_id",
            "forecast_version",
            "model_version",
            "variable_id",
            "value",
            "unit",
            "basis",
            "horizon_years",
            "forecast_origin",
            "known_at",
            "prepared_without_current_price",
            "evidence_ids",
        )
    }
    payload["forecast_id"] = "POST-B04-ALT-FORECAST-001"
    payload["forecast_version"] = "POST-B04-AUDIT-FORECAST-ALT-0.1"
    payload["value"] = "999"
    return INDEPENDENT_FORECAST_REGISTRY.admit_independent_forecast(payload).to_dict()


def _alternate_valuation_ref(c: dict, forecast_ref: dict):
    gate = c["return_gate"]
    canonical_output = VALUATION_OUTPUT_RESOLVER.resolve_valuation_output(
        c["return_gate"]["canonical_valuation_ref"],
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        company=c["company"],
        cutoff_date=date.fromisoformat(c["cutoff_date"]),
    )
    output = build_canonical_valuation_output(
        {
            "valuation_id": "POST-B04-ALT-VALUATION-001",
            "valuation_version": "POST-B04-AUDIT-VALUATION-ALT-0.1",
            "case_id": c["case_id"],
            "market": c["market"],
            "symbol": c["symbol"],
            "company": c["company"],
            "cutoff_date": c["cutoff_date"],
            "forecast_ref": forecast_ref,
            "horizon_years": str(gate["horizon_years"]),
            "reference_value_per_share": "999",
            "scenarios": {
                "bear": {
                    "probability": "0.20",
                    "value_per_share": "800",
                    "cash_distributions_per_share": "0",
                },
                "base": {
                    "probability": "0.50",
                    "value_per_share": "999",
                    "cash_distributions_per_share": "0",
                },
                "bull": {
                    "probability": "0.30",
                    "value_per_share": "1200",
                    "cash_distributions_per_share": "0",
                },
            },
            "evidence_ids": ["POST-B04-ALT-VALUATION-EVIDENCE"],
        }
    )
    admission = build_canonical_investment_admission(
        admission_id=output["valuation_id"] + "-ADMISSION",
        domain="VALUATION",
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        company=c["company"],
        cutoff_date=c["cutoff_date"],
        domain_status="PASS",
        source_record_id=output["valuation_id"],
        source_record_hash=_sha({"valuation": output}),
        output_hash=output["output_hash"],
        producer_version="POST-B04-AUDIT-VALUATION-PRODUCER-0.1",
        evidence_ids=["POST-B04-ALT-VALUATION-EVIDENCE"],
        admitted_at="2026-10-07T02:00:00+00:00",
    )
    ref = VALUATION_ADMISSION_REGISTRY.admit(admission).to_dict()
    VALUATION_OUTPUT_RESOLVER.register_output(
        valuation_reference=ref,
        valuation_output=output,
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        company=c["company"],
        cutoff_date=date.fromisoformat(c["cutoff_date"]),
    )
    return ref, canonical_output


def test_baseline_decision_still_passes_with_all_canonical_resolvers():
    result = decide(
        case(),
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
    )
    assert result["validation"]["status"] == "PASS"
    assert result["decision"]["auto_execution"] is False


def test_valid_alternate_forecast_cannot_be_substituted_under_an_admitted_valuation():
    c = case()
    alternate = _alternate_forecast_ref(c)
    c["return_gate"]["canonical_forecast_ref"] = alternate

    result = _full_validate(c)
    assert result["status"] == "BLOCKED"
    assert any(
        error["code"] == "V03-RETURN-LINEAGE-CANONICAL"
        and "valuation.forecast_ref" in error["message"]
        for error in result["errors"]
    )


def test_valid_alternate_valuation_cannot_be_substituted_without_matching_return_economics():
    c = case()
    original_forecast = c["return_gate"]["canonical_forecast_ref"]
    alternate_ref, _ = _alternate_valuation_ref(c, original_forecast)
    c["return_gate"]["canonical_valuation_ref"] = alternate_ref

    result = _full_validate(c)
    assert result["status"] == "BLOCKED"
    assert any(
        error["code"] == "V03-RETURN-LINEAGE-CANONICAL"
        and "entry_value_reference" in error["message"]
        for error in result["errors"]
    )


def test_valid_canonical_upstream_ref_cannot_cross_domain_slots():
    c = case()
    refs = c["decision_upstream_admission"]["canonical_admission_refs"]
    swapped = deepcopy(refs)
    swapped["VALUATION"] = refs["REALITY"]
    c["decision_upstream_admission"]["canonical_admission_refs"] = swapped

    result = _full_validate(c)
    assert result["status"] == "BLOCKED"
    assert any(
        error["code"] == "V03-UPSTREAM-ADMISSION"
        and "domain mismatch" in error["message"]
        for error in result["errors"]
    )


def test_engine_runtime_cannot_revalidate_v03_without_valuation_resolver():
    c = case()
    with pytest.raises((TypeError, ValueError)):
        decide(
            c,
            evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
            current_price_resolver=CURRENT_PRICE_REGISTRY,
            independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
            upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
        )


def test_replay_cannot_reconstruct_a_v03_decision_without_valuation_resolver():
    c = case()
    snapshot, _ = run_case(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
    )
    result = replay(
        snapshot,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert result["replay_status"] == "FAIL"
    assert result["same_decision"] is False
    assert result["integrity_status"] == "FAIL"


def test_forecast_registry_remains_immutable_on_conflicting_same_id_bytes():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    first = {
        "case_id": "POST-B04-AUDIT",
        "market": "CN-A",
        "symbol": "TEST",
        "cutoff_date": "2026-10-07",
        "forecast_id": "POST-B04-IMMUTABLE-001",
        "forecast_version": "0.1",
        "model_version": "0.1",
        "variable_id": "forward_eps",
        "value": "10",
        "unit": "CNY/share",
        "basis": "audit",
        "horizon_years": "1",
        "forecast_origin": "2026-10-07T10:00:00+00:00",
        "known_at": "2026-10-07T11:00:00+00:00",
        "prepared_without_current_price": True,
        "evidence_ids": ["audit-ev-1"],
    }
    registry.admit_independent_forecast(first)
    conflicting = dict(first)
    conflicting["value"] = "20"
    with pytest.raises(ValueError, match="different bytes"):
        registry.admit_independent_forecast(conflicting)
