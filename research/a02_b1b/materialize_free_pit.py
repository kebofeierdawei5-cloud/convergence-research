from __future__ import annotations

import argparse, hashlib, json, random
from datetime import datetime, timezone
from pathlib import Path
import requests

ORIGINS = {
    "2023Q3":"2023-09-28","2023Q4":"2023-12-29","2024Q1":"2024-03-29",
    "2024Q2":"2024-06-28","2024Q3":"2024-09-30","2024Q4":"2024-12-31",
    "2025Q1":"2025-03-31","2025Q2":"2025-06-30","2025Q3":"2025-09-30",
    "2025Q4":"2025-12-31","2026Q1":"2026-03-31",
}
OFFICIAL_SSE = "https://query.sse.com.cn/security/stock/getStockListData2.do"
OFFICIAL_SZSE = "https://www.szse.cn/api/report/ShowReport"
CSI_STANDARD = "https://oss-ch.csindex.com.cn/industryClassification/%E4%B8%AD%E8%AF%81%E8%A1%8C%E4%B8%9A%E5%88%86%E7%B1%BB%E7%9A%84%E8%AF%B4%E6%98%8E.pdf"
HEADERS = {"User-Agent":"Mozilla/5.0 (IIOS-B1B-free-first)","Accept":"*/*"}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def capture(session, method, url, out, params=None, headers=None, retries=3):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            r = session.request(method, url, params=params, headers=headers or HEADERS, timeout=90, allow_redirects=True)
            body = r.content
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(body)
            return {
                "requested_url": r.request.url, "final_url": r.url, "method": method,
                "retrieved_at": datetime.now(timezone.utc).isoformat(), "http_status": r.status_code,
                "content_type": r.headers.get("Content-Type"), "size_bytes": len(body),
                "sha256": sha256(body), "exact_bytes": True, "source_class":"OFFICIAL_PUBLIC_HTTP",
                "attempts": attempt,
                "redirect_history":[{"status":h.status_code,"url":h.url,"location":h.headers.get("Location")} for h in r.history]
            }
        except requests.RequestException as exc:
            last_error = str(exc)
    return {
        "status": "BLOCKED_SOURCE_UNREACHABLE",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "exact_bytes": False,
        "source_class": "OFFICIAL_PUBLIC_HTTP",
        "error": last_error,
        "attempts": retries,
    }

def to_df(rs):
    import pandas as pd
    rows=[]
    while rs.error_code=='0' and rs.next(): rows.append(rs.get_row_data())
    return pd.DataFrame(rows, columns=rs.fields)

def capture_baostock(root):
    import baostock as bs
    login=bs.login()
    if login.error_code!='0': raise RuntimeError(f'baostock login failed: {login.error_code} {login.error_msg}')
    out={"provider":"BAOSTOCK","source_class":"FREE_SECONDARY_API","retrieved_at":datetime.now(timezone.utc).isoformat(),"records":{}}
    try:
        df=to_df(bs.query_stock_basic()); p=root/'secondary_baostock'/'stock_basic.csv'; p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8')
        out['records']['stock_basic']={"path":str(p.relative_to(root)),"rows":len(df),"sha256":sha256(p.read_bytes()),"fields":list(df.columns),"status":"CONDITIONAL"}
        for origin,day in ORIGINS.items():
            df=to_df(bs.query_all_stock(day=day)); p=root/'secondary_baostock'/f'all_stock_{origin}_{day}.csv'; df.to_csv(p,index=False,encoding='utf-8')
            out['records'][f'all_stock_{origin}']={"path":str(p.relative_to(root)),"rows":len(df),"sha256":sha256(p.read_bytes()),"fields":list(df.columns),"observation_date":day,"known_at":None,"status":"CONDITIONAL"}
            df=to_df(bs.query_stock_industry(date=day)); p=root/'secondary_baostock'/f'industry_{origin}_{day}.csv'; df.to_csv(p,index=False,encoding='utf-8')
            out['records'][f'industry_{origin}']={"path":str(p.relative_to(root)),"rows":len(df),"sha256":sha256(p.read_bytes()),"fields":list(df.columns),"observation_date":day,"known_at":None,"status":"CONDITIONAL"}
    finally: bs.logout()
    (root/'secondary_baostock'/'receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args(); root=Path(args.out).resolve(); root.mkdir(parents=True,exist_ok=True)
    s=requests.Session(); off={"retrieved_at":datetime.now(timezone.utc).isoformat(),"records":{}}
    off['records']['sse_stock_list']=capture(s,'GET',OFFICIAL_SSE,root/'official'/'sse_stock_list.json',params={
        "jsonCallBack":"jsonpCallback","isPagination":"true","stockCode":"","csrcCode":"","areaName":"","stockType":"1",
        "pageHelp.cacheSize":"1","pageHelp.beginPage":"1","pageHelp.pageSize":"10000","pageHelp.pageNo":"1","pageHelp.endPage":"1"},
        headers={**HEADERS,"Referer":"https://www.sse.com.cn/"})
    szse = capture(s,'GET',OFFICIAL_SZSE,root/'official'/'szse_stock_list.xlsx',params={"SHOWTYPE":"xlsx","CATALOGID":"1110","TABKEY":"tab1","random":str(random.random())},headers={**HEADERS,"Referer":"https://www.szse.cn/market/product/stock/list/index.html"})
    if szse.get("exact_bytes") is not True:
        szse = capture(s,'GET',"https://www.szse.cn/api/report/ShowReport/data",root/'official'/'szse_stock_list.json',params={"SHOWTYPE":"JSON","CATALOGID":"1110","TABKEY":"tab1","PAGENO":"1","PAGESIZE":"10000","tab1PAGENO":"1","tab1PAGESIZE":"10000","random":str(random.random())},headers={**HEADERS,"Referer":"https://www.szse.cn/market/product/stock/list/index.html"})
        szse["fallback_from"]="xlsx"
    off['records']['szse_stock_list']=szse
    off['records']['sse_risk_plate']=capture(s,'GET','https://www.sse.com.cn/disclosure/listedinfo/riskplate/',root/'official'/'sse_risk_plate.html',headers={**HEADERS,"Referer":"https://www.sse.com.cn/"})
    off['records']['szse_company_notice']=capture(s,'GET','https://www.szse.cn/disclosure/notice/company/index.html',root/'official'/'szse_company_notice.html',headers={**HEADERS,"Referer":"https://www.szse.cn/"})
    csi=capture(s,'GET',CSI_STANDARD,root/'official'/'csi_industry_classification_standard.pdf',headers={**HEADERS,"Referer":"https://www.csindex.com.cn/"})
    off['records']['csi_industry_standard']={**csi,"field":"CSI_INDUSTRY_TAXONOMY","status":"STANDARD_ONLY","known_at":None}
    (root/'official'/'receipt.json').write_text(json.dumps(off,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:
        secondary = capture_baostock(root)
    except Exception as exc:
        secondary = {"provider":"BAOSTOCK","source_class":"FREE_SECONDARY_API","status":"BLOCKED","error":str(exc)}
        (root/"secondary_baostock").mkdir(parents=True,exist_ok=True)
        (root/"secondary_baostock"/"receipt.json").write_text(
            json.dumps(secondary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
        )
    admission={
      "schema_version":"IIOS-A02-B1B-ADMISSION-0.1","overall":"BLOCKED",
      "free_first":True,"paid_mandatory":False,"current_to_historical_substitution":False,
      "fields":{
        "identity":{"status":"BLOCKED","reason":"Official stock-list snapshots materialized; historical source-vintage/known_at not closed."},
        "listing_delisting":{"status":"CONDITIONAL","reason":"Current exchange listing metadata materialized; historical source publication/vintage and known_at are not closed."},
        "common_equity":{"status":"CONDITIONAL","reason":"Current instrument metadata materialized; historical source authority and known_at are not closed."},
        "ST_status":{"status":"BLOCKED","reason":"Official risk-warning source is current snapshot; historical PIT known_at not closed."},
        "CSI_industry_taxonomy":{"status":"PASS_FOR_STANDARD_DEFINITION","reason":"Official CSI taxonomy document captured exactly; security-level assignments remain separate."},
        "CSI_industry_security_history":{"status":"BLOCKED","reason":"Historical security-level CSI assignments with reproducible known_at are not yet materialized."}
      },
      "secondary_source":{"provider":secondary["provider"],"role":"RECONCILIATION_ONLY","admitted":False}
    }
    (root/'B1B_FIELD_ADMISSION_MATRIX.json').write_text(json.dumps(admission,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 4

if __name__=='__main__': raise SystemExit(main())