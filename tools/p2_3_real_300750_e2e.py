from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
from typing import Any

from iios_mvp.market_model_domain import (
    CandidateMarketModel,
    MarketModelFamily,
    MarketObservableEvidence,
)
from iios_mvp.market_model_identification import (
    MarketModelIdentificationInput,
    MarketValuationObservation,
    identify_market_models,
)
from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
)
from iios_mvp.multi_model_market_implied_expectation_set import (
    MIEModelEvaluation,
    build_multi_model_market_implied_expectation_set,
)
from iios_mvp.p4f_mie_snapshot import (
    P4FProvenanceRecord,
    build_p4f_snapshot,
    replay_p4f_snapshot,
)
from iios_mvp.canonical_entry_evaluation import build_canonical_entry_evaluation


P23_VERSION = "IIOS-P2.3-REAL-300750-E2E-0.1"
CASE_ID = "RC-CN-A-300750-20261004"
CUTOFF = date(2026, 10, 4)
MODEL_ID = "real-ev-ebitda-300750"
RECEIPT_PATH = Path("research/core04c_catl_ev_ebitda_receipt_v0.2.json")


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("known_at must be timezone-aware")
    return parsed


def _d(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("numeric value must be finite")
    return result


def _ev_ebitda(row: dict[str, Any]) -> Decimal:
    price = _d(row["price"])
    shares = _d(row["shares_outstanding"])
    net_debt = _d(row["net_debt"])
    ebitda = _d(row["economic_value"])
    if ebitda <= 0:
        raise ValueError("EBITDA must be > 0 for EV/EBITDA calculation")
    with localcontext() as ctx:
        ctx.prec = 60
        return (price * shares + net_debt) / ebitda


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _evidence_rows(data: dict[str, Any]) -> tuple[MarketObservableEvidence, ...]:
    output: list[MarketObservableEvidence] = []
    for row in data["evidence"]:
        output.append(
            MarketObservableEvidence(
                evidence_id=str(row["evidence_id"]),
                variable=str(row["variable"]),
                unit=str(row["unit"]),
                basis=str(row["basis"]),
                observation_date=date.fromisoformat(str(row["observation_date"])),
                known_at=_dt(str(row["known_at"])),
                source=str(row["source"]),
                value=_d(row["value"]),
                metadata={
                    str(k): str(v)
                    for k, v in (row.get("metadata") or {}).items()
                },
            )
        )
    required_bridge_ids = {"E011", "E008", "E005"}
    supplied_ids = {item.evidence_id for item in output}
    missing = sorted(required_bridge_ids - supplied_ids)
    if missing:
        raise ValueError(
            "P2.3 refuses to synthesize bridge evidence; missing admitted evidence: "
            + ", ".join(missing)
        )
    return tuple(output)


def _observations(data: dict[str, Any]) -> tuple[MarketValuationObservation, ...]:
    return tuple(
        MarketValuationObservation(
            observation_id=str(row["observation_id"]),
            observation_date=date.fromisoformat(str(row["observation_date"])),
            known_at=_dt(str(row["known_at"])),
            price=_d(row["price"]),
            shares_outstanding=_d(row["shares_outstanding"]),
            economic_variable=str(row["economic_variable"]),
            economic_value=_d(row["economic_value"]),
            unit=str(row["unit"]),
            basis=str(row["basis"]),
            evidence_ids=tuple(str(x) for x in row["evidence_ids"]),
            source=str(row["source"]),
            net_debt=_d(row["net_debt"]),
        )
        for row in data["observations"]
    )


def _provenance(data: dict[str, Any]) -> tuple[P4FProvenanceRecord, ...]:
    records: list[P4FProvenanceRecord] = []
    for row in sorted(data["evidence"], key=lambda x: str(x["evidence_id"])):
        metadata = row.get("metadata") or {}
        content_sha = str(
            metadata.get("source_sha256")
            or metadata.get("content_sha256")
            or ""
        ).lower()
        if len(content_sha) != 64 or any(ch not in "0123456789abcdef" for ch in content_sha):
            raise ValueError(
                f"{row['evidence_id']}: admitted source/content SHA-256 is required"
            )
        source = str(row.get("source") or "").strip()
        if not source:
            raise ValueError(f"{row['evidence_id']}: admitted source is required")
        records.append(
            P4FProvenanceRecord(
                evidence_id=str(row["evidence_id"]),
                variable=str(row["variable"]),
                unit=str(row["unit"]),
                basis=str(row["basis"]),
                observation_date=date.fromisoformat(str(row["observation_date"])),
                known_at=_dt(str(row["known_at"])),
                source=source,
                source_location=f"admitted://{row['evidence_id']}",
                content_sha256=content_sha,
                captured_at=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
                value=_d(row["value"]),
            )
        )
    return tuple(records)


def _load_and_validate_canonical_receipt(
    input_receipt: dict[str, Any],
) -> dict[str, Any]:
    receipt = _load_json(RECEIPT_PATH)

    expected = {
        "schema_version": "IIOS-CORE04C-CATL-EVEBITDA-RECEIPT-0.2",
        "case_id": CASE_ID,
        "status": "ADMITTED",
        "admission_engine": "CORE-04-A",
        "cutoff_date": CUTOFF.isoformat(),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError(
                f"canonical CORE-04-C receipt mismatch for {key}: "
                f"expected {value!r}, got {receipt.get(key)!r}"
            )

    ci = receipt.get("ci")
    if not isinstance(ci, dict):
        raise ValueError("canonical CORE-04-C receipt missing ci object")
    expected_ci = {
        "workflow": "real-ev-ebitda",
        "run_id": 37261197564,
        "artifact_id": 11324731141,
        "result": "SUCCESS",
        "artifact_sha256": "51e9e8c19404ef241383c99e0f9ed98bf3088fbe2b4a47778e9f5d79a26ee6c4",
    }
    for key, value in expected_ci.items():
        if ci.get(key) != value:
            raise ValueError(
                f"canonical CORE-04-C CI receipt mismatch for {key}: "
                f"expected {value!r}, got {ci.get(key)!r}"
            )

    if input_receipt.get("status") != "ADMITTED":
        raise ValueError("P2.3 input does not carry ADMITTED CORE-04-C linkage")
    if input_receipt.get("path") != str(RECEIPT_PATH):
        raise ValueError(
            "P2.3 input source_receipt.path is not the canonical CORE-04-C receipt path"
        )
    if input_receipt.get("ci_run_id") != ci["run_id"]:
        raise ValueError("P2.3 input ci_run_id does not match canonical receipt")
    if input_receipt.get("artifact_sha256") != ci["artifact_sha256"]:
        raise ValueError("P2.3 input artifact_sha256 does not match canonical receipt")

    canonical_by_id = {
        str(row["observation_id"]): row
        for row in receipt.get("observations", [])
    }
    if len(canonical_by_id) != 3:
        raise ValueError("canonical CORE-04-C receipt must contain exactly three observations")

    return receipt


def _validate_evidence_source_hash_binding(
    data: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    evidence_by_id = {
        str(row["evidence_id"]): row
        for row in data.get("evidence", [])
    }
    receipt_by_id = {
        str(row["observation_id"]): row
        for row in receipt.get("observations", [])
    }
    for observation_id, canonical in receipt_by_id.items():
        # CORE-04-C records one canonical EBITDA source for each admitted
        # observation. The consumer must carry the same byte fingerprint.
        candidates = [
            row for row in evidence_by_id.values()
            if str(row.get("observation_date")) == str(canonical["observation_date"])
            and str(row.get("variable")) == "ebitda"
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"expected exactly one admitted EBITDA evidence row for {observation_id}"
            )
        evidence = candidates[0]
        metadata = evidence.get("metadata") or {}
        actual_sha = str(
            metadata.get("source_sha256")
            or metadata.get("content_sha256")
            or ""
        ).lower()
        expected_sha = str(
            (canonical.get("source_hashes") or {}).get(canonical["ebitda_source"])
            or ""
        ).lower()
        if actual_sha != expected_sha or len(actual_sha) != 64:
            raise ValueError(
                f"CORE-04-C EBITDA source SHA drift for {observation_id}"
            )
        if _d(evidence["value"]) != _d(canonical["ebitda_cny"]):
            raise ValueError(
                f"CORE-04-C EBITDA evidence value drift for {observation_id}"
            )


def _validate_historical_observation_binding(
    data: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    rows = {
        str(row["observation_id"]): row
        for row in data.get("observations", [])
    }
    canonical_rows = {
        str(row["observation_id"]): row
        for row in receipt.get("observations", [])
    }

    missing = sorted(set(canonical_rows) - set(rows))
    unexpected = sorted(set(rows) & set(canonical_rows) - set(canonical_rows))
    if missing:
        raise ValueError(
            "P2.3 real input is missing canonical CORE-04-C observations: "
            + ", ".join(missing)
        )

    for observation_id, canonical in canonical_rows.items():
        row = rows[observation_id]
        checks = {
            "observation_date": str(row["observation_date"]) == str(canonical["observation_date"]),
            "price": _d(row["price"]) == _d(canonical["price_cny_per_share"]),
            "shares_outstanding": _d(row["shares_outstanding"]) == _d(canonical["shares_outstanding"]),
            "net_debt": _d(row["net_debt"]) == _d(canonical["net_debt_cny"]),
            "economic_value": _d(row["economic_value"]) == _d(canonical["ebitda_cny"]),
            "basis": str(row["basis"]) == str(canonical["ebitda_basis"]),
        }
        if not all(checks.values()):
            failed = [key for key, ok in checks.items() if not ok]
            raise ValueError(
                f"canonical CORE-04-C observation binding drift for "
                f"{observation_id}: {failed}"
            )

        computed = _ev_ebitda(row)
        canonical_multiple = _d(canonical["ev_ebitda"])
        if computed != canonical_multiple:
            raise ValueError(
                f"canonical CORE-04-C EV/EBITDA arithmetic mismatch for "
                f"{observation_id}: computed {computed}, receipt {canonical_multiple}"
            )


def _validate_current_bridge_binding(data: dict[str, Any]) -> None:
    evidence_by_id = {
        str(row["evidence_id"]): row
        for row in data.get("evidence", [])
    }
    rows = {
        str(row["observation_id"]): row
        for row in data.get("observations", [])
    }
    current = rows.get("CATL-EVEBITDA-CURRENT-2026-09-30")
    if current is None:
        raise ValueError("P2.3 missing canonical 2026-09-30 current observation")

    required = {
        "E011": ("price", "291.11"),
        "E008": ("shares_outstanding", "4380630342"),
        "E005": ("net_debt", "-276904623000"),
        "CORE03-CURRENT-EBITDA-FY2025": ("economic_value", "119197217000"),
    }
    for evidence_id, (field, expected) in required.items():
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            raise ValueError(
                f"P2.3 missing admitted current-bridge evidence: {evidence_id}"
            )
        if _d(evidence["value"]) != _d(expected):
            raise ValueError(
                f"P2.3 current bridge evidence value drift: {evidence_id}"
            )
        if _d(current[field]) != _d(evidence["value"]):
            raise ValueError(
                f"P2.3 current observation is not bound to {evidence_id}"
            )

    if str(current["observation_date"]) != "2026-09-30":
        raise ValueError("P2.3 current observation date drift")
    if _dt(str(current["known_at"])).date() > CUTOFF:
        raise ValueError("P2.3 current observation violates PIT cutoff")


def run_real_case(input_path: Path, out_path: Path) -> dict[str, Any]:
    data = _load_json(input_path)
    if data.get("case_id") != CASE_ID:
        raise ValueError("real P2.3 input case_id mismatch")
    input_receipt = data.get("source_receipt") or {}
    receipt = _load_and_validate_canonical_receipt(input_receipt)
    _validate_evidence_source_hash_binding(data, receipt)
    _validate_historical_observation_binding(data, receipt)
    _validate_current_bridge_binding(data)

    if data.get("status") != "EXECUTABLE_REAL_SLICE":
        raise ValueError("unexpected P3A real-slice input status")

    observations = _observations(data)
    evidence = _evidence_rows(data)
    candidate = CandidateMarketModel(
        model_id=MODEL_ID,
        family=MarketModelFamily.EV_EBITDA,
        required_economic_variables=("ebitda", "enterprise_value"),
        required_observable_variables=("ebitda", "enterprise_value"),
        evidence_ids=tuple(str(x) for x in data["candidate"]["evidence_ids"]),
        admission_basis=str(data["candidate"]["admission_basis"]),
        inverse_solvable=True,
    )
    coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState.SUFFICIENT,
        scope_basis=str(data["candidate_coverage"]["scope_basis"]),
        candidate_model_ids=(MODEL_ID,),
        evidence_ids=tuple(sorted(set(str(x) for x in data["candidate_coverage"]["evidence_ids"]))),
        rationale=str(data["candidate_coverage"]["rationale"]),
    )
    sufficiency = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState.SUFFICIENT,
        rationale=str(data["evidence_sufficiency"]["rationale"]),
        evidence_ids=tuple(sorted(set(str(x) for x in data["evidence_sufficiency"]["evidence_ids"]))),
    )

    current_id = "CATL-EVEBITDA-CURRENT-2026-09-30"
    identification_input = MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id=current_id,
        candidates=(candidate,),
        observations=observations,
        evidence=evidence,
        stability_min_historical_points=3,
    )
    identification = identify_market_models(identification_input)
    ident = identification["identifiability"]
    stability = identification["stability"]
    evaluation = identification["evaluations"][0]

    if evaluation.fit.status.value != "FEASIBLE":
        raise AssertionError("real 300750 EV/EBITDA model should remain mathematically feasible")
    if ident.feasible_model_ids != (MODEL_ID,):
        raise AssertionError("real 300750 EV/EBITDA model should remain uniquely identifiable")

    p4b_reason = (
        "P4-B cannot materialize a decision-grade EV/EBITDA MIE because "
        "the identified model is outside the admitted historical support range."
    )
    model_eval = MIEModelEvaluation.outside_historical_support(
        model_id=MODEL_ID,
        evidence_ids=tuple(sorted(set(evaluation.fit.evidence_ids))),
        rationale=(
            "Real P3-A evaluation found a mathematically feasible and uniquely "
            "identifiable EV/EBITDA model whose current observation is outside "
            "the historical support range; this does not prove model failure."
        ),
    )
    mie_set = build_multi_model_market_implied_expectation_set(
        set_id=f"MIESET-{CASE_ID}-P2.3",
        candidate_coverage=coverage,
        evidence_sufficiency=sufficiency,
        model_evaluations=(model_eval,),
        qualification_rationale=p4b_reason,
        evidence_ids=tuple(
            sorted(
                set(coverage.evidence_ids)
                | set(sufficiency.evidence_ids)
                | set(model_eval.evidence_ids)
            )
        ),
    )
    snapshot = build_p4f_snapshot(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        created_at=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
        mie_set=mie_set,
        provenance_records=_provenance(data),
    )
    p4f_replay = replay_p4f_snapshot(snapshot)

    current_row = next(
        row for row in data["observations"] if row["observation_id"] == current_id
    )
    current_price = _d(current_row["price"])
    current_shares = _d(current_row["shares_outstanding"])
    current_net_debt = _d(current_row["net_debt"])
    current_ebitda = _d(current_row["economic_value"])
    with localcontext() as ctx:
        ctx.prec = 60
        current_ev = current_price * current_shares + current_net_debt
        current_multiple = current_ev / current_ebitda
    entry_evaluation = build_canonical_entry_evaluation(
        current_price=current_price,
        return_target_entry_price=current_price,
        price_response=None,
        price_response_source="P2.1_CANONICAL",
        entry_reference_source="EXPECTATION_GAP",
        market_expectation_id=None,
        independent_forecast_ref=None,
    )

    result = {
        "schema_version": P23_VERSION,
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF.isoformat(),
        "core04c_receipt": receipt,
        "core04c_receipt_path": str(RECEIPT_PATH),
        "core04c_input_link": input_receipt,
        "current_bridge_binding": {
            "E011": "price",
            "E008": "shares_outstanding",
            "E005": "net_debt",
            "CORE03-CURRENT-EBITDA-FY2025": "economic_value",
        },
        "real_current_observation": {
            "observation_id": current_id,
            "price": str(current_price),
            "shares_outstanding": str(current_shares),
            "net_debt": str(current_net_debt),
            "ebitda": str(current_ebitda),
            "enterprise_value": format(current_ev, "f"),
            "ev_ebitda": format(current_multiple, "f"),
        },
        "p3a": {
            "status": identification["status"],
            "method": identification["method"],
            "identifiability": ident.state.value,
            "stability": stability.state.value,
            "stability_scope": stability.assessment_scope,
            "feasible_model_ids": list(ident.feasible_model_ids),
            "historical_support": evaluation.fit.historical_support.value,
            "regime_interpretation": evaluation.fit.regime_interpretation.value,
            "evaluation_status": evaluation.fit.status.value,
            "historical_range": {
                "low": format(
                    min(
                        _ev_ebitda(row)
                        for row in data["observations"]
                        if row["observation_id"] != current_id
                    ),
                    "f",
                ),
                "high": format(
                    max(
                        _ev_ebitda(row)
                        for row in data["observations"]
                        if row["observation_id"] != current_id
                    ),
                    "f",
                ),
            },
        },
        "p4b": {
            "status": "BLOCKED",
            "reason": p4b_reason,
            "mie_materialized": False,
        },
        "p4f": {
            "status": "BLOCKED",
            "qualification": snapshot["mie_set"]["qualification"],
            "resolution_state": snapshot["mie_set"]["resolution_state"],
            "snapshot_hash": snapshot["snapshot_hash"],
            "replay_status": p4f_replay["replay_status"],
        },
        "p2_1": {
            "status": "BLOCKED",
            "reason": (
                "No DECISION_GRADE MIE was materialized by P4-B; "
                "P2.1 must not invent a market expectation."
            ),
        },
        "p2_2": {
            "canonical_entry_evaluation": entry_evaluation,
            "decision_admission_status": "NOT_APPLICABLE",
            "reason": (
                "No capital-increase action is admissible because "
                "the upstream real MIE chain is blocked."
            ),
        },
        "final_state": "REVIEW_REQUIRED",
        "capital_admitted": False,
        "non_claims": [
            "EV/EBITDA is not established as the true market model.",
            "No Market Implied Expectation is materialized.",
            "No Expectation Gap is calculated.",
            "No BUY/ADD decision is issued.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = run_real_case(Path(args.input), Path(args.out))
    print(
        json.dumps(
            {
                "case_id": result["case_id"],
                "final_state": result["final_state"],
                "p3a": result["p3a"],
                "p4b": result["p4b"],
                "p4f": result["p4f"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
