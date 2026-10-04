from __future__ import annotations

import argparse, hashlib, json, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

OFFICIAL_000906 = "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000906cons.xls"
EXPECTED_000906_SIZE = 169984
EXPECTED_000906_SHA256 = "f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984"
ORIGINS = ["2023Q3","2023Q4","2024Q1","2024Q2","2024Q3","2024Q4","2025Q1","2025Q2","2025Q3","2025Q4","2026Q1"]
Q_END = {
  "2023Q3":"20230930","2023Q4":"20231231","2024Q1":"20240331","2024Q2":"20240630","2024Q3":"20240930","2024Q4":"20241231",
  "2025Q1":"20250331","2025Q2":"20250630","2025Q3":"20250930","2025Q4":"20251231","2026Q1":"20260331",
}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def post_tushare(token: str, api_name: str, params: dict, fields: str, out: Path, timeout: int = 60) -> dict:
    payload = {"api_name": api_name, "token": token, "params": params, "fields": fields}
    started = datetime.now(timezone.utc).isoformat()
    resp = requests.post("https://api.tushare.pro", json=payload, timeout=timeout)
    raw = resp.content
    digest = sha256_bytes(raw)
    out.write_bytes(raw)
    parsed = resp.json()
    result = {"api_name": api_name, "params": params, "fields": fields, "requested_at": started, "retrieved_at": datetime.now(timezone.utc).isoformat(), "http_status": resp.status_code, "response_sha256": digest, "response_bytes": len(raw), "tushare_code": parsed.get("code"), "tushare_msg": parsed.get("msg")}
    return result

def choose_origin_trading_dates(token: str, root: Path) -> dict[str, str]:
    # One raw query covering the full period; selection is deterministic and does not mutate response bytes.
    meta = post_tushare(token, "trade_cal", {"exchange":"SSE","start_date":"20230101","end_date":"20260331","is_open":"1"}, "exchange,cal_date,is_open,pretrade_date", root/"trade_cal_SSE_20230101_20260331.json")
    raw = json.loads((root/"trade_cal_SSE_20230101_20260331.json").read_text(encoding="utf-8"))
    if raw.get("code") != 0: raise RuntimeError(f"trade_cal failed: {raw.get('msg')}")
    fields = raw["data"]["fields"]; rows = raw["data"]["items"]; idx={r[fields.index('cal_date')]:r for r in rows}
    open_dates=sorted(idx)
    result={}
    for origin,end in Q_END.items():
        candidates=[d for d in open_dates if d<=end]
        if not candidates: raise RuntimeError(f"no trading date for {origin}")
        result[origin]=candidates[-1]
    (root/"origin_trading_dates.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (root/"trade_cal_SSE_20230101_20260331.meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--out",required=True); ap.add_argument("--tushare-token",default="")
    args=ap.parse_args(); root=Path(args.out).resolve(); root.mkdir(parents=True,exist_ok=True)
    receipt={"schema_version":"IIOS-A02-RAW-MATERIALIZATION-0.1","retrieved_at":datetime.now(timezone.utc).isoformat(),"A":{},"B":{},"status":"BLOCKED"}
    try:
        r=requests.get(OFFICIAL_000906,timeout=90,headers={"User-Agent":"Mozilla/5.0"},allow_redirects=True)
        raw=r.content; digest=sha256_bytes(raw)
        target=root/"A_CSI800_RAW"/"official_000906_000906cons.xls"; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
        ar={"requested_url":OFFICIAL_000906,"final_url":r.url,"retrieved_at":datetime.now(timezone.utc).isoformat(),"http_status":r.status_code,"size_bytes":len(raw),"sha256":digest,"expected_size_bytes":EXPECTED_000906_SIZE,"expected_sha256":EXPECTED_000906_SHA256,"size_match":len(raw)==EXPECTED_000906_SIZE,"sha256_match":digest==EXPECTED_000906_SHA256,"exact_bytes":True}
        (target.parent/"official_000906_000906cons.xls.meta.json").write_text(json.dumps(ar,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        receipt["A"]={"status":"PASS" if ar["size_match"] and ar["sha256_match"] else "BLOCKED","terminal":ar}
    except Exception as exc:
        receipt["A"]={"status":"BLOCKED","reason":f"DOWNLOAD_ERROR:{exc}"}
    if args.tushare_token:
        try:
            b=root/"B_PIT_SECURITY_MASTER_RAW"; b.mkdir(parents=True,exist_ok=True)
            all_meta=[]
            for status in ["L","D","P"]:
                p=post_tushare(args.tushare_token,"stock_basic",{"exchange":"","list_status":status},"ts_code,symbol,name,area,industry,market,exchange,curr_type,list_status,list_date,delist_date,is_hs",b/f"stock_basic_{status}.json"); all_meta.append(p)
            dates=choose_origin_trading_dates(args.tushare_token,b); receipt["B"]["origin_trading_dates"]=dates
            for origin,trade_date in dates.items():
                all_meta.append(post_tushare(args.tushare_token,"stock_st",{"trade_date":trade_date},"ts_code,name,trade_date,type,type_name",b/f"stock_st_{origin}_{trade_date}.json"))
            all_meta.append(post_tushare(args.tushare_token,"index_classify",{"level":"L1","src":"SW2021"},"index_code,industry_name,parent_code,level,is_pub",b/"sw_index_classify_L1.json"))
            raw_cls=json.loads((b/"sw_index_classify_L1.json").read_text(encoding="utf-8")); fields=raw_cls.get("data",{}).get("fields",[]); rows=raw_cls.get("data",{}).get("items",[]); code_i=fields.index("index_code") if "index_code" in fields else -1
            l1codes=sorted({row[code_i] for row in rows if code_i>=0})
            for code in l1codes:
                safe=code.replace(".","_")
                all_meta.append(post_tushare(args.tushare_token,"index_member_all",{"l1_code":code,"is_new":"N"},"l1_code,l1_name,l2_code,l2_name,l3_code,l3_name,ts_code,name,in_date,out_date,is_new",b/f"sw_member_all_{safe}_old.json"))
                all_meta.append(post_tushare(args.tushare_token,"index_member_all",{"l1_code":code,"is_new":"Y"},"l1_code,l1_name,l2_code,l2_name,l3_code,l3_name,ts_code,name,in_date,out_date,is_new",b/f"sw_member_all_{safe}_current.json"))
            for item in all_meta: item["provenance_class"]="VENDOR_PIT_QUERY" if item["api_name"]=="stock_st" or item["api_name"]=="index_member_all" else "UNKNOWN"
            (b/"TUSHARE_QUERY_RECEIPTS.json").write_text(json.dumps(all_meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            receipt["B"]["status"]="CONDITIONAL_RAW_ONLY"
            receipt["B"]["pit_admission"]="BLOCKED_PROVENANCE"
            receipt["B"]["block_reason"]="stock_basic static listing snapshot lacks historical known_at; index_member_all exposes effective dates but not source publication/known_at; stock_st is historical daily PIT-query capable and updated 09:20, but does not by itself close the full security-master provenance chain."
        except Exception as exc:
            receipt["B"]={"status":"BLOCKED","reason":f"TUSHARE_COLLECTION_ERROR:{exc}"}
    else:
        receipt["B"]={"status":"BLOCKED","reason":"TUSHARE_TOKEN_UNAVAILABLE"}
    receipt["status"]="PASS" if receipt["A"].get("status")=="PASS" and receipt["B"].get("pit_admission")=="PASS" else "BLOCKED"
    (root/"A02_RAW_MATERIALIZATION_RECEIPT.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return 0 if receipt["status"]=="PASS" else 4

if __name__=="__main__": raise SystemExit(main())