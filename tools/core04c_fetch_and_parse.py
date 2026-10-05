from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from core04c_catl_ev_ebitda import (
    parse_annual_ebitda,
    parse_balance_sheet,
    parse_exact_h1_share_capital,
    parse_szse_market_snapshot,
    build_observation,
    sha256,
)


def download(url: str, path: Path) -> None:
    cmd = ["curl","--location","--fail","--silent","--show-error","--retry","4","--retry-delay","1","--retry-all-errors","--connect-timeout","20","--max-time","120","--user-agent","IIOS-core04c/0.2","--output",str(path),url]
    p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"curl rc={p.returncode}")


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    m=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out=Path(args.out)
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)

    by_name={}
    for s in m["sources"]:
        p=out/s["filename"]
        download(s["url"],p)
        by_name[s["filename"]]=sha256(p)

    configs=[
      ("2025-10-22","SZSE-MKT-2025-10-22.xlsx","CNINFO-Q3-2025.pdf",(6,7,8),"2025-10-21T23:59:59+08:00","CNINFO-FY2024-2025-03-15.pdf",(119,),(201,),2024,"2025-03-15T23:59:59+08:00"),
      ("2026-04-17","SZSE-MKT-2026-04-17.xlsx","CNINFO-Q1-2026.pdf",(5,6,7),"2026-04-16T23:59:59+08:00","CNINFO-FY2025-2026-03-10.pdf",(116,),(200,),2025,"2026-03-10T23:59:59+08:00"),
      ("2026-07-27","SZSE-MKT-2026-07-27.xlsx","CNINFO-H1-2026.pdf",(73,74,75),"2026-07-24T23:59:59+08:00","CNINFO-FY2025-2026-03-10.pdf",(116,),(200,),2025,"2026-03-10T23:59:59+08:00"),
    ]
    observations=[]
    prior={
      "SZSE-MKT-2025-10-22.xlsx":"dfe49f5fade60087e5118f17446bbf55161c4cd7d765dd81155edb10ccdd6ba9",
      "SZSE-MKT-2026-04-17.xlsx":"bd5875b4294e3acdcca6aeddf42dd65d8284a15e5a29d6290308c65973b49a0d",
      "SZSE-MKT-2026-07-27.xlsx":"ab420679237525a7e6846ffa49a3ef8115e4d64d6bc97f63319f5ee9c333e568",
    }
    for md,mf,ff,fp,fknown,ef,eip,ecp,year,eknown in configs:
      mp=out/mf; fpath=out/ff; ep=out/ef
      market=parse_szse_market_snapshot(mp,expected_date=md)
      fin=parse_balance_sheet(fpath,pages_1based=fp,market_date=md,known_at=fknown)
      if md=="2026-07-27":
          fin["share_count"]=parse_exact_h1_share_capital(fpath)
      ebitda=parse_annual_ebitda(ep,pages_income=eip,pages_cashflow=ecp,fiscal_year=year,known_at=eknown)
      observations.append(build_observation(
        observation_id=f"CATL-EVEBITDA-{md}",
        market_path=mp,market_data=market,market_known_at=md+"T23:59:59+08:00",
        financial_path=fpath,financial_data=fin,financial_known_at=fknown,
        ebitda_path=ep,ebitda_data=ebitda,ebitda_known_at=eknown,
        source_hashes={mf:by_name[mf],ff:by_name[ff],ef:by_name[ef]},
        market_prior_hash=prior[mf]))
    out_file=out/"core04c_catl_ev_ebitda_observations.json"
    out_file.write_text(json.dumps({"schema_version":"IIOS-CORE04C-CATL-EVEBITDA-0.1","case_id":m["case_id"],"status":"PASS / HISTORICAL OBSERVATIONS ADMITTED","observations":observations,"ev_formula":"market_price * reported_total_share_capital + (interest_bearing_debt - cash)","ev_ebitda_formula":"enterprise_value / latest_known_completed_fiscal_year_EBITDA"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
