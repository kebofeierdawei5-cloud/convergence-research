from __future__ import annotations

import argparse, hashlib, json, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

OFFICIAL_000906 = "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000906cons.xls"
LEGACY_000906_URLS = [
    "https://www.csindex.com.cn/csindex-home/uploads/file/autofile/cons/000906cons.xls",
    "http://www.csindex.com.cn/csindex-home/uploads/file/autofile/cons/000906cons.xls",
    "https://www.csindex.com.cn/csindex-home/uploads/file/autofile/cons/000906cons.xls?download=1",
]
EXPECTED_000906_SIZE = 169984
EXPECTED_000906_SHA256 = "f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984"
ORIGINS = ["2023Q3","2023Q4","2024Q1","2024Q2","2024Q3","2024Q4","2025Q1","2025Q2","2025Q3","2025Q4","2026Q1"]
Q_END = {
  "2023Q3":"20230930","2023Q4":"20231231","2024Q1":"20240331","2024Q2":"20240630","2024Q3":"20240930","2024Q4":"20241231",
  "2025Q1":"20250331","2025Q2":"20250630","2025Q3":"20250930","2025Q4":"20251231","2026Q1":"20260331",
}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_attempt(attempts, source, **kw):
    item = {"archive_provider": source}
    item.update(kw)
    attempts.append(item)


def fetch_archive_pt_target(urls: list[str], attempts: list[dict]) -> dict:
    """Search Arquivo.pt CDX and accept only exact frozen target bytes."""
    import urllib.parse
    for source_url in urls:
        params = {
            "url": source_url,
            "from": "2026",
            "to": "2026",
            "output": "json",
            "fields": "url,timestamp,status,digest,length",
            "limit": 100,
        }
        cdx_url = "https://arquivo.pt/wayback/cdx?" + urllib.parse.urlencode(params)
        try:
            cdx = requests.get(cdx_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            cdx.raise_for_status()
            rows = cdx.json()
            _record_attempt(attempts, "ARQUIVO_PT_CDX", source_url=source_url, cdx_status="OK", capture_count=len(rows) if isinstance(rows, list) else 0)
        except Exception as exc:
            _record_attempt(attempts, "ARQUIVO_PT_CDX", source_url=source_url, cdx_status="ERROR", cdx_error=str(exc))
            continue
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            timestamp = str(row.get("timestamp", ""))
            original = row.get("url") or source_url
            try:
                length = int(row.get("length", 0))
            except (TypeError, ValueError):
                length = 0
            if length != EXPECTED_000906_SIZE:
                continue
            archive_url = f"https://arquivo.pt/noFrame/replay/{timestamp}id_/{original}"
            try:
                resp = requests.get(archive_url, timeout=90, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
                data = resp.content
                got = sha256_bytes(data)
                _record_attempt(attempts, "ARQUIVO_PT", source_url=source_url, timestamp=timestamp, archive_url=archive_url, http_status=resp.status_code, size_bytes=len(data), sha256=got, expected_match=(got == EXPECTED_000906_SHA256))
                if len(data) == EXPECTED_000906_SIZE and got == EXPECTED_000906_SHA256:
                    return {"status": "PASS", "timestamp": timestamp, "archive_url": archive_url, "size_bytes": len(data), "sha256": got, "bytes": data}
            except Exception as exc:
                _record_attempt(attempts, "ARQUIVO_PT", source_url=source_url, timestamp=timestamp, archive_url=archive_url, error=str(exc))
    return {"status": "BLOCKED"}


def fetch_wayback_target() -> dict:
    """Try multiple web archives; accept only exact frozen bytes."""
    import urllib.parse
    urls = [OFFICIAL_000906, *LEGACY_000906_URLS]
    attempts = []
    # Internet Archive / Wayback.
    for source_url in urls:
        params = {
            "url": source_url,
            "from": "2026",
            "to": "2026",
            "output": "json",
            "filter": "statuscode:200",
            "fl": "timestamp,original,digest,length",
            "collapse": "digest",
        }
        cdx_url = "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(params)
        try:
            cdx = requests.get(cdx_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            cdx.raise_for_status()
            rows = cdx.json()
            if rows and isinstance(rows[0], list) and rows[0] and str(rows[0][0]).lower() == "timestamp":
                rows = rows[1:]
            _record_attempt(attempts, "WAYBACK_CDX", source_url=source_url, cdx_status="OK", capture_count=len(rows) if isinstance(rows, list) else 0)
        except Exception as exc:
            _record_attempt(attempts, "WAYBACK_CDX", source_url=source_url, cdx_status="ERROR", cdx_error=str(exc))
            continue
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, list) or len(row) < 4:
                continue
            timestamp, original, digest, length = row[:4]
            if str(length) != str(EXPECTED_000906_SIZE):
                continue
            archive_url = f"https://web.archive.org/web/{timestamp}id_/{original}"
            try:
                resp = requests.get(archive_url, timeout=90, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
                data = resp.content
                got = sha256_bytes(data)
                _record_attempt(attempts, "WAYBACK", source_url=source_url, timestamp=timestamp, archive_url=archive_url, http_status=resp.status_code, size_bytes=len(data), sha256=got, expected_match=(got == EXPECTED_000906_SHA256))
                if len(data) == EXPECTED_000906_SIZE and got == EXPECTED_000906_SHA256:
                    return {"status": "PASS", "timestamp": timestamp, "archive_url": archive_url, "size_bytes": len(data), "sha256": got, "bytes": data, "attempts": attempts}
            except Exception as exc:
                _record_attempt(attempts, "WAYBACK", source_url=source_url, timestamp=timestamp, archive_url=archive_url, error=str(exc))
    # Independent archive discovery: Internet Archive Availability API, Memento aggregator, then Arquivo.pt.
    availability = fetch_availability_api(urls, attempts)
    if availability.get("status") == "PASS":
        availability["attempts"] = attempts
        return availability
    memento = fetch_memento_target(urls, attempts)
    if memento.get("status") == "PASS":
        memento["attempts"] = attempts
        return memento
    # Arquivo.pt.
    arquivo = fetch_archive_pt_target(urls, attempts)
    if arquivo.get("status") == "PASS":
        arquivo["attempts"] = attempts
        return arquivo
    # Common Crawl: discover recent 2026 collections and pull only indexed exact-URL records.
    try:
        info = requests.get("https://index.commoncrawl.org/collinfo.json", timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        info.raise_for_status()
        target_start = "20260601"
        target_end = "20260731"
        collections = []
        for c in info.json():
            cid = str(c.get("id", ""))
            if not cid.startswith("CC-MAIN-2026-"):
                continue
            c_from = str(c.get("from", "")).replace("-", "")
            c_to = str(c.get("to", "")).replace("-", "")
            if (not c_from or c_from <= target_end) and (not c_to or c_to >= target_start):
                collections.append(c)
        collections = sorted(collections, key=lambda c: str(c.get("id")), reverse=True)
        _record_attempt(attempts, "COMMONCRAWL_INDEX", status="OK", collection_count=len(collections))
    except Exception as exc:
        _record_attempt(attempts, "COMMONCRAWL_INDEX", status="ERROR", error=str(exc))
        collections = []
    for collection in collections:
        index_id = str(collection.get("id"))
        index_url = str(collection.get("cdx-api"))
        if not index_url:
            continue
        for source_url in urls:
            try:
                params = {"url": source_url, "output": "json", "filter": "status:200", "collapse": "digest"}
                cdx_resp = requests.get(index_url, params=params, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
                if cdx_resp.status_code != 200:
                    _record_attempt(attempts, "COMMONCRAWL_CDX", collection=index_id, source_url=source_url, http_status=cdx_resp.status_code)
                    continue
                rows = [json.loads(line) for line in cdx_resp.text.splitlines() if line.strip()]
                _record_attempt(attempts, "COMMONCRAWL_CDX", collection=index_id, source_url=source_url, http_status=cdx_resp.status_code, capture_count=len(rows))
            except Exception as exc:
                _record_attempt(attempts, "COMMONCRAWL_CDX", collection=index_id, source_url=source_url, error=str(exc))
                continue
            for row in rows:
                try:
                    length = int(row.get("length", 0))
                    offset = int(row.get("offset", 0))
                    filename = row["filename"]
                    original = row.get("url", source_url)
                    timestamp = row.get("timestamp")
                except (KeyError, TypeError, ValueError):
                    continue
                if length < 1:
                    continue
                warc_url = "https://data.commoncrawl.org/" + filename
                try:
                    resp = requests.get(warc_url, headers={"Range": f"bytes={offset}-{offset+length-1}", "User-Agent": "Mozilla/5.0"}, timeout=120)
                    if resp.status_code not in (200, 206):
                        _record_attempt(attempts, "COMMONCRAWL_RECORD", collection=index_id, original=original, timestamp=timestamp, http_status=resp.status_code)
                        continue
                    blob = resp.content
                    try:
                        import gzip
                        blob = gzip.decompress(blob)
                    except (OSError, EOFError):
                        pass
                    h1 = blob.find(b"\r\n\r\n")
                    http_payload = blob[h1+4:] if h1 >= 0 else blob
                    h2 = http_payload.find(b"\r\n\r\n")
                    payload = http_payload[h2+4:] if h2 >= 0 else http_payload
                    got = sha256_bytes(payload)
                    _record_attempt(attempts, "COMMONCRAWL_RECORD", collection=index_id, original=original, timestamp=timestamp, http_status=resp.status_code, size_bytes=len(payload), sha256=got, expected_match=(got == EXPECTED_000906_SHA256))
                    if len(payload) == EXPECTED_000906_SIZE and got == EXPECTED_000906_SHA256:
                        return {"status": "PASS", "timestamp": timestamp, "archive_url": warc_url, "size_bytes": len(payload), "sha256": got, "bytes": payload, "attempts": attempts}
                except Exception as exc:
                    _record_attempt(attempts, "COMMONCRAWL_RECORD", collection=index_id, original=original, timestamp=timestamp, archive_url=warc_url, error=str(exc))
    return {"status": "BLOCKED", "attempts": attempts}

def _try_archived_bytes(archive_url: str, source_label: str, source_url: str, attempts: list[dict]) -> dict:
    try:
        resp = requests.get(archive_url, timeout=120, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        data = resp.content
        got = sha256_bytes(data)
        _record_attempt(attempts, source_label, source_url=source_url, archive_url=archive_url, http_status=resp.status_code, size_bytes=len(data), sha256=got, expected_match=(len(data) == EXPECTED_000906_SIZE and got == EXPECTED_000906_SHA256))
        if len(data) == EXPECTED_000906_SIZE and got == EXPECTED_000906_SHA256:
            return {"status":"PASS","archive_url":archive_url,"size_bytes":len(data),"sha256":got,"bytes":data}
    except Exception as exc:
        _record_attempt(attempts, source_label, source_url=source_url, archive_url=archive_url, error=str(exc))
    return {"status":"BLOCKED"}

def fetch_memento_target(source_urls: list[str], attempts: list[dict]) -> dict:
    import urllib.parse
    timestamps = ["20260930","20261001","20261002","20261003","20261004","20261005"]
    for source_url in source_urls:
        for target_dt in timestamps:
            api_url = "https://timetravel.mementoweb.org/api/json/" + target_dt + "/" + source_url
            try:
                resp = requests.get(api_url, timeout=60, headers={"User-Agent":"Mozilla/5.0"}, allow_redirects=True)
                if resp.status_code != 200:
                    _record_attempt(attempts, "MEMENTO_API", source_url=source_url, target_datetime=target_dt, http_status=resp.status_code)
                    continue
                payload = resp.json()
                memento = payload.get("memento") or {}
                uri = memento.get("uri") or payload.get("uri") or payload.get("url")
                _record_attempt(attempts, "MEMENTO_API", source_url=source_url, target_datetime=target_dt, http_status=resp.status_code, memento_uri=uri, memento_datetime=memento.get("datetime") or payload.get("datetime"))
                if not uri:
                    continue
                result = _try_archived_bytes(uri, "MEMENTO_MEMENTO", source_url, attempts)
                if result.get("status") == "PASS":
                    return result
            except Exception as exc:
                _record_attempt(attempts, "MEMENTO_API", source_url=source_url, target_datetime=target_dt, error=str(exc))
    return {"status":"BLOCKED"}

def fetch_availability_api(source_urls: list[str], attempts: list[dict]) -> dict:
    import urllib.parse
    timestamps = ["20260930000000","20261001000000","20261002000000","20261003000000","20261004000000"]
    for source_url in source_urls:
        for target_dt in timestamps:
            api_url = "https://archive.org/wayback/available?" + urllib.parse.urlencode({"url":source_url,"timestamp":target_dt})
            try:
                resp = requests.get(api_url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
                resp.raise_for_status()
                payload = resp.json()
                closest = payload.get("archived_snapshots", {}).get("closest")
                _record_attempt(attempts, "WAYBACK_AVAILABILITY", source_url=source_url, target_datetime=target_dt, http_status=resp.status_code, available=bool(closest), snapshot=closest)
                if not closest or not closest.get("url"):
                    continue
                result = _try_archived_bytes(closest["url"], "WAYBACK_AVAILABILITY_REPLAY", source_url, attempts)
                if result.get("status") == "PASS":
                    result["timestamp"] = closest.get("timestamp")
                    return result
            except Exception as exc:
                _record_attempt(attempts, "WAYBACK_AVAILABILITY", source_url=source_url, target_datetime=target_dt, error=str(exc))
    return {"status":"BLOCKED"}
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
        current=root/"A_CSI800_RAW"/"official_000906_current_20261004_000906cons.xls"; current.parent.mkdir(parents=True,exist_ok=True); current.write_bytes(raw)
        ar={"requested_url":OFFICIAL_000906,"final_url":r.url,"retrieved_at":datetime.now(timezone.utc).isoformat(),"http_status":r.status_code,"size_bytes":len(raw),"sha256":digest,"expected_size_bytes":EXPECTED_000906_SIZE,"expected_sha256":EXPECTED_000906_SHA256,"size_match":len(raw)==EXPECTED_000906_SIZE,"sha256_match":digest==EXPECTED_000906_SHA256,"exact_bytes":True,"role":"CURRENT_SNAPSHOT_NOT_HISTORICAL_TARGET"}
        (current.parent/"official_000906_current_20261004_000906cons.xls.meta.json").write_text(json.dumps(ar,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        receipt["A"]={"status":"PASS" if ar["size_match"] and ar["sha256_match"] else "BLOCKED","terminal_current_snapshot":ar}
        if receipt["A"]["status"] != "PASS":
            historical=fetch_wayback_target()
            receipt["A"]["wayback_attempt"]={k:v for k,v in historical.items() if k!="bytes"}
            if historical.get("status")=="PASS":
                hist=root/"A_CSI800_RAW"/"official_000906_historical_target_000906cons.xls"
                hist.write_bytes(historical["bytes"])
                hmeta={k:v for k,v in historical.items() if k!="bytes"}
                (hist.parent/"official_000906_historical_target_000906cons.xls.meta.json").write_text(json.dumps(hmeta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                receipt["A"]["status"]="PASS"
                receipt["A"]["terminal_historical_target"]=hmeta
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
        receipt["B"]={
            "status":"BLOCKED",
            "pit_admission":"BLOCKED_FREE_FIRST_ROUTE_NOT_MATERIALIZED",
            "optional_vendor":{"provider":"TUSHARE","credential":"TUSHARE_TOKEN","status":"NOT_CONFIGURED"},
            "reason":"No mandatory paid/vendor credential is available. B remains blocked only because the free-first PIT evidence bundle has not yet been materialized and admitted."
        }
    receipt["status"]="PASS" if receipt["A"].get("status")=="PASS" and receipt["B"].get("pit_admission")=="PASS" else "BLOCKED"
    (root/"A02_RAW_MATERIALIZATION_RECEIPT.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return 0 if receipt["status"]=="PASS" else 4

if __name__=="__main__": raise SystemExit(main())