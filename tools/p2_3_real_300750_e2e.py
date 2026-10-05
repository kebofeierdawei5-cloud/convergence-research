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
    bridge = {
        "E011": ("market_price", "CNY/share", "2026-09-30 official SZSE EOD close", "2026-09-30", "2026-09-30T00:00:00+08:00"),
        "E008": ("shares_outstanding", "shares", "existing CORE-03 current share-count bridge", "2026-09-29", "2026-09-29T00:00:00+08:00"),
        "E005": ("net_debt", "CNY", "2026-06-30 cash less short-term and long-term borrowings", "2026-06-30", "2026-07-24T00:00:00+08:00"),
    }
    existing = {item.evidence_id for item in output}
    for evidence_id, (variable, unit, basis, obs, known) in bridge.items():
        if evidence_id in existing:
            continue
        output.append(
            MarketObservableEvidence(
                evidence_id=evidence_id,
                variable=variable,
                unit=unit,
                basis=basis,
                observation_date=date.fromisoformat(obs),
                known_at=_dt(known),
                source="RC-CN-A-300750-20261004 admitted bridge",
                range_low=Decimal("0"),
                range_high=Decimal("0"),
            )
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
        records.append(
            P4FProvenanceRecord(
                evidence_id=str(row["evidence_id"]),
                variable=str(row["variable"]),
                unit=str(row["unit"]),
                basis=str(row["basis"]),
                observation_date=date.fromisoformat(str(row["observation_date"])),
                known_at=_dt(str(row["known_at"])),
                source=str(row["source"]),
                source_location=f"admitted://{row['evidence_id']}",
                content_sha256=str(
                    metadata.get("source_sha256")
                    or metadata.get("content_sha256")
                    or "0" * 64
                ),
                captured_at=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
                value=_d(row["value"]),
            )
        )
    return tuple(records)


def run_real_case(input_path: Path, out_path: Path) -> dict[str, Any]:
    data = _load_json(input_path)
    if data.get("case_id") != CASE_ID:
        raise ValueError("real P2.3 input case_id mismatch")
    receipt = data.get("source_receipt") or {}
    if receipt.get("status") != "ADMITTED":
        raise ValueError("CORE-04-C receipt is not admitted")
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

    if evaluation.fit.status.value == "FEASIBLE":
        raise AssertionError("unexpected feasible EV/EBITDA model in real 300750 slice")
    if ident.feasible_model_ids:
        raise AssertionError("real 300750 case unexpectedly identified a feasible model")

    p4b_reason = (
        "P4-B cannot materialize an EV/EBITDA MIE because P3-A "
        "has no feasible model."
    )
    model_eval = MIEModelEvaluation.no_feasible_solution(
        model_id=MODEL_ID,
        evidence_ids=tuple(sorted(set(evaluation.fit.evidence_ids))),
        rationale=(
            "Real P3-A evaluation found current implied EV/EBITDA "
            "outside the admitted historical multiple range."
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
            "feasible_model_ids": list(ident.feasible_model_ids),
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
