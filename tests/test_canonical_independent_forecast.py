from __future__ import annotations

from datetime import date
from pathlib import Path
from decimal import Decimal
import json

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.canonical_independent_forecast import (
    CanonicalIndependentForecastReference,
    FileSystemCanonicalIndependentForecastRegistry,
    InMemoryCanonicalIndependentForecastRegistry,
)


CUTOFF = date(2026, 10, 4)


def forecast(**overrides):
    value = {
        "case_id": "P1-3-CASE",
        "market": "CN-A",
        "symbol": "300750",
        "cutoff_date": "2026-10-04",
        "forecast_id": "forecast-p1-3",
        "forecast_version": "TEST-FORECAST-0.1",
        "model_version": "TEST-MODEL-0.1",
        "variable_id": "forward_eps",
        "value": "12",
        "unit": "CNY/share",
        "basis": "2026A_to_2028E",
        "horizon_years": "2",
        "forecast_origin": "2026-10-04T12:00:00+00:00",
        "known_at": "2026-10-04T15:00:00+00:00",
        "prepared_without_current_price": True,
        "evidence_ids": ["EV-F1"],
    }
    value.update(overrides)
    return value


def test_inmemory_admission_round_trip():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    ref = registry.admit_independent_forecast(forecast())
    record = registry.resolve_independent_forecast(
        ref.to_dict(),
        case_id="P1-3-CASE",
        market="CN-A",
        symbol="300750",
        cutoff_date=CUTOFF,
    )
    assert record["value"] == "12"
    assert record["variable_id"] == "forward_eps"
    assert record["evidence_ids"] == ["EV-F1"]


def test_unknown_forecast_is_fail_closed():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    with pytest.raises(ValueError, match="unknown"):
        registry.resolve_independent_forecast(
            {"forecast_id": "never-admitted", "admission_record_hash": "a" * 64},
            case_id="P1-3-CASE",
            market="CN-A",
            symbol="300750",
            cutoff_date=CUTOFF,
        )


def test_wrong_admission_hash_is_rejected():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    registry.admit_independent_forecast(forecast())
    with pytest.raises(ValueError, match="admission hash mismatch"):
        registry.resolve_independent_forecast(
            {"forecast_id": "forecast-p1-3", "admission_record_hash": "0" * 64},
            case_id="P1-3-CASE",
            market="CN-A",
            symbol="300750",
            cutoff_date=CUTOFF,
        )


def test_cross_instrument_reuse_is_rejected():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    ref = registry.admit_independent_forecast(forecast())
    with pytest.raises(ValueError, match="instrument identity mismatch"):
        registry.resolve_independent_forecast(
            ref.to_dict(),
            case_id="P1-3-CASE",
            market="CN-A",
            symbol="000001",
            cutoff_date=CUTOFF,
        )


def test_signed_forecast_value_is_admissible():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    ref = registry.admit_independent_forecast(
        forecast(value="-3", forecast_id="signed-forecast")
    )
    record = registry.resolve_independent_forecast(
        ref.to_dict(),
        case_id="P1-3-CASE",
        market="CN-A",
        symbol="300750",
        cutoff_date=CUTOFF,
    )
    assert record["value"] == "-3"


def test_forecast_must_be_independent_of_current_price():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    with pytest.raises(ValueError, match="without current price"):
        registry.admit_independent_forecast(
            forecast(prepared_without_current_price=False)
        )


def test_future_forecast_origin_or_known_at_is_rejected():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    with pytest.raises(ValueError, match="origin is after cutoff"):
        registry.admit_independent_forecast(
            forecast(forecast_origin="2026-10-05T00:00:00+00:00")
        )
    with pytest.raises(ValueError, match="known_at is after cutoff"):
        registry.admit_independent_forecast(
            forecast(known_at="2026-10-05T00:00:00+00:00", forecast_id="future-known")
        )


def test_filesystem_tampering_is_fail_closed(tmp_path):
    registry = FileSystemCanonicalIndependentForecastRegistry(tmp_path)
    ref = registry.admit_independent_forecast(forecast())
    path = registry._path("forecast-p1-3")
    record = json.loads(path.read_text(encoding="utf-8"))
    record["value"] = "999"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="admission record hash mismatch"):
        registry.resolve_independent_forecast(
            ref.to_dict(),
            case_id="P1-3-CASE",
            market="CN-A",
            symbol="300750",
            cutoff_date=CUTOFF,
        )


def test_same_forecast_id_with_different_bytes_is_rejected():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    registry.admit_independent_forecast(forecast())
    with pytest.raises(ValueError, match="already exists with different bytes"):
        registry.admit_independent_forecast(
            forecast(value="999")
        )


def test_reference_rejects_extra_fields():
    with pytest.raises(ValueError, match="unsupported fields"):
        CanonicalIndependentForecastReference.from_mapping(
            {
                "forecast_id": "forecast-p1-3",
                "admission_record_hash": "a" * 64,
                "value": "999",
            }
        )


def test_schema_accepts_only_forecast_reference():
    schema = json.loads(
        Path("schemas/canonical_independent_forecast_reference_v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    ref = {
        "forecast_id": "forecast-p1-3",
        "admission_record_hash": "a" * 64,
    }
    Draft202012Validator(schema).validate(ref)
    with pytest.raises(Exception):
        Draft202012Validator(schema).validate({**ref, "value": "999"})
