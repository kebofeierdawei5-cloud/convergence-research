from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from core04c_catl_ev_ebitda import (
    parse_annual_ebitda,
    parse_balance_sheet,
    parse_exact_h1_share_capital,
    parse_szse_market_snapshot,
    build_observation,
    sha256,
)
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    TemporalProvenance,
    VerifiedMarketEvidence,
    admit_market_valuation_observation,
)


def download(url: str, path: Path) -> None:
    cmd = [
        "curl", "--location", "--fail", "--silent", "--show-error",
        "--retry", "4", "--retry-delay", "1", "--retry-all-errors",
        "--connect-timeout", "20", "--max-time", "120",
        "--user-agent", "IIOS-core04c/0.3",
        "--output", str(path), url,
    ]
    p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"curl rc={p.returncode}")


def _evidence(
    evidence_id: str,
    *,
    variable: str,
    unit: str,
    basis: str,
    observation_date: str,
    known_at: str,
    source: str,
    source_location: str,
    content_sha256: str,
    value: Decimal,
) -> VerifiedMarketEvidence:
    return VerifiedMarketEvidence(
        evidence_id=evidence_id,
        variable=variable,
        unit=unit,
        basis=basis,
        observation_date=datetime.fromisoformat(observation_date).date(),
        known_at=datetime.fromisoformat(known_at),
        source=source,
        source_location=source_location,
        content_sha256=content_sha256,
        exact_bytes=True,
        status=AdmissionStatus.ADMITTED,
        temporal_provenance=TemporalProvenance.SOURCE_VINTAGE,
        value=value,
    )


def _admit(
    *,
    case_id: str,
    market_date: str,
    market_file: str,
    market_url: str,
    market_data: dict[str, str],
    market_hash: str,
    financial_file: str,
    financial_url: str,
    financial_hash: str,
    financial_data: dict[str, object],
    financial_known_at: str,
    ebitda_file: str,
    ebitda_url: str,
    ebitda_hash: str,
    ebitda_data: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    market_known_at = f"{market_date}T23:59:59+08:00"

    share_ev = _evidence(
        f"{case_id}:{market_date}:shares",
        variable="shares_outstanding",
        unit="shares",
        basis="reported_total_share_capital",
        observation_date=market_date,
        known_at=financial_known_at,
        source="CNINFO",
        source_location=financial_url,
        content_sha256=financial_hash,
        value=Decimal(str(financial_data["share_count"])),
    )
    net_debt_ev = _evidence(
        f"{case_id}:{market_date}:net_debt",
        variable="net_debt",
        unit="CNY",
        basis="interest_bearing_debt_less_cash_using_latest_known_balance_sheet",
        observation_date=market_date,
        known_at=financial_known_at,
        source="CNINFO",
        source_location=financial_url,
        content_sha256=financial_hash,
        value=Decimal(str(financial_data["net_debt_cny"])),
    )
    ebitda_ev = _evidence(
        f"{case_id}:{market_date}:ebitda",
        variable="ebitda",
        unit="CNY",
        basis=f"FY{ebitda_data['fiscal_year']} completed_fiscal_year_EBITDA",
        observation_date=market_date,
        known_at=str(ebitda_data["known_at"]),
        source="CNINFO",
        source_location=ebitda_url,
        content_sha256=ebitda_hash,
        value=Decimal(str(ebitda_data["ebitda_cny"])),
    )
    price_ev = _evidence(
        f"{case_id}:{market_date}:price",
        variable="market_price",
        unit="CNY/share",
        basis="SZSE_EOD_CLOSE",
        observation_date=market_date,
        known_at=market_known_at,
        source="SZSE:MARKET_DATA",
        source_location=market_url,
        content_sha256=market_hash,
        value=Decimal(str(market_data["close_cny"])),
    )

    admission = admit_market_valuation_observation(
        cutoff_date=datetime.fromisoformat("2026-10-04T23:59:59+08:00").date(),
        observation_id=f"CATL-EVEBITDA-{market_date}",
        price_evidence=price_ev,
        shares_evidence=share_ev,
        economic_evidence=ebitda_ev,
        net_debt_evidence=net_debt_ev,
    )
    if admission.status is not AdmissionStatus.ADMITTED or admission.observation is None:
        raise RuntimeError(
            f"{market_date}: CORE-04-A admission failed: "
            + "; ".join(admission.blockers)
        )

    typed = admission.observation
    typed.validate(datetime.fromisoformat("2026-10-04T23:59:59+08:00").date())
    observation = {
        "observation_id": typed.observation_id,
        "observation_date": typed.observation_date.isoformat(),
        "known_at": typed.known_at.isoformat(),
        "market_price_cny_per_share": format(typed.price, "f"),
        "shares_outstanding": format(typed.shares_outstanding, "f"),
        "net_debt_cny": format(typed.net_debt, "f"),
        "ebitda_cny": format(typed.economic_value, "f"),
        "market_cap_cny": format(typed.price * typed.shares_outstanding, "f"),
        "enterprise_value_cny": format(
            typed.price * typed.shares_outstanding + typed.net_debt, "f"
        ),
        "ev_ebitda": format(
            (typed.price * typed.shares_outstanding + typed.net_debt)
            / typed.economic_value,
            "f",
        ),
        "basis": (
            "historical_market_date / latest_known_financial_vintage / "
            "latest_known_completed_fiscal_year_EBITDA"
        ),
        "economic_variable": typed.economic_variable,
        "economic_unit": typed.unit,
        "economic_basis": typed.basis,
        "evidence_ids": list(typed.evidence_ids),
        "admission_status": admission.status.value,
        "admission_blockers": list(admission.blockers),
        "source_hashes": {
            market_file: market_hash,
            financial_file: financial_hash,
            ebitda_file: ebitda_hash,
        },
        "source_locations": {
            market_file: market_url,
            financial_file: financial_url,
            ebitda_file: ebitda_url,
        },
        "market_source_row": {
            "symbol": market_data["symbol"],
            "company": market_data["company"],
            "close_cny": market_data["close_cny"],
        },
        "prior_market_capture_status": "NOT_EVALUATED_IN_ADMISSION",
        "share_count_basis": "reported_total_share_capital",
        "net_debt_basis": "interest_bearing_debt_less_cash",
    }
    evidence_records = {
        "price": price_ev,
        "shares": share_ev,
        "net_debt": net_debt_ev,
        "ebitda": ebitda_ev,
    }
    return observation, {
        name: {
            "evidence_id": ev.evidence_id,
            "variable": ev.variable,
            "unit": ev.unit,
            "basis": ev.basis,
            "observation_date": ev.observation_date.isoformat(),
            "known_at": ev.known_at.isoformat(),
            "source": ev.source,
            "source_location": ev.source_location,
            "content_sha256": ev.content_sha256,
            "exact_bytes": ev.exact_bytes,
            "status": ev.status.value,
            "temporal_provenance": ev.temporal_provenance.value,
            "value": format(ev.value, "f"),
        }
        for name, ev in evidence_records.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    m = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    source_by_name = {s["filename"]: s for s in m["sources"]}
    raw_hashes = {}

    for source in m["sources"]:
        path = out / source["filename"]
        download(source["url"], path)
        raw_hashes[source["filename"]] = sha256(path)

    configs = [
        (
            "2025-10-22",
            "SZSE-MKT-2025-10-22.xlsx",
            "CNINFO-Q3-2025.pdf",
            (),
            "2025-10-21T23:59:59+08:00",
            "CNINFO-FY2024-2025-03-15.pdf",
            (),
            (),
            2024,
            "2025-03-15T23:59:59+08:00",
        ),
        (
            "2026-04-17",
            "SZSE-MKT-2026-04-17.xlsx",
            "CNINFO-Q1-2026.pdf",
            (),
            "2026-04-16T23:59:59+08:00",
            "CNINFO-FY2025-2026-03-10.pdf",
            (),
            (),
            2025,
            "2026-03-10T23:59:59+08:00",
        ),
        (
            "2026-07-27",
            "SZSE-MKT-2026-07-27.xlsx",
            "CNINFO-H1-2026.pdf",
            (),
            "2026-07-24T23:59:59+08:00",
            "CNINFO-FY2025-2026-03-10.pdf",
            (),
            (),
            2025,
            "2026-03-10T23:59:59+08:00",
        ),
    ]

    observations = []
    evidence_by_observation = {}
    for (
        market_date,
        market_file,
        financial_file,
        financial_pages,
        financial_known_at,
        ebitda_file,
        ebitda_income_pages,
        ebitda_cashflow_pages,
        year,
        ebitda_known_at,
    ) in configs:
        mp = out / market_file
        fp = out / financial_file
        ep = out / ebitda_file
        market_source = source_by_name[market_file]
        financial_source = source_by_name[financial_file]
        ebitda_source = source_by_name[ebitda_file]

        market = parse_szse_market_snapshot(mp, expected_date=market_date)
        fin = parse_balance_sheet(
            fp,
            pages_1based=financial_pages,
            market_date=market_date,
            known_at=financial_known_at,
        )
        if market_date == "2026-07-27":
            fin["share_count"] = parse_exact_h1_share_capital(fp)

        ebitda = parse_annual_ebitda(
            ep,
            pages_income=ebitda_income_pages,
            pages_cashflow=ebitda_cashflow_pages,
            fiscal_year=year,
            known_at=ebitda_known_at,
        )

        observation, evidence = _admit(
            case_id=m["case_id"],
            market_date=market_date,
            market_file=market_file,
            market_url=market_source["url"],
            market_data=market,
            market_hash=raw_hashes[market_file],
            financial_file=financial_file,
            financial_url=financial_source["url"],
            financial_hash=raw_hashes[financial_file],
            financial_data=fin,
            financial_known_at=financial_known_at,
            ebitda_file=ebitda_file,
            ebitda_url=ebitda_source["url"],
            ebitda_hash=raw_hashes[ebitda_file],
            ebitda_data=ebitda,
        )
        observations.append(observation)
        evidence_by_observation[observation["observation_id"]] = evidence

    out_file = out / "core04c_catl_ev_ebitda_observations.json"
    out_file.write_text(
        json.dumps(
            {
                "schema_version": "IIOS-CORE04C-CATL-EVEBITDA-0.2",
                "case_id": m["case_id"],
                "status": "PASS / HISTORICAL OBSERVATIONS ADMITTED",
                "admission_engine": "CORE-04-A",
                "observation_count": len(observations),
                "observations": observations,
                "evidence": evidence_by_observation,
                "ev_formula": "market_price * reported_total_share_capital + (interest_bearing_debt - cash)",
                "ev_ebitda_formula": "enterprise_value / latest_known_completed_fiscal_year_EBITDA",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
