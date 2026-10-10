from __future__ import annotations

import hashlib
import json
import re
import sys
import time as _clock
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CASE_ID = "RC-CN-A-605016-20261009"
ORIGINAL_DATE_ONLY_CUTOFF = "2026-10-09"
REQUIRED_PRICE_DATE = "2026-10-08"
USER_AGENT = "IIOS-free-first-source-adjudication/0.1"
SOCKET_TIMEOUT_SECONDS = 6
TOTAL_FETCH_DEADLINE_SECONDS = 10
MAX_BYTES = 10 * 1024 * 1024
KLINE_ENDPOINTS = [
    {
        "url": "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=sh605016,day,,,100",
        "adjustment": "UNADJUSTED_KLINE_ENDPOINT_CANDIDATE",
    },
    {
        "url": "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh605016,day,,,100,qfq",
        "adjustment": "QFQ_ADJUSTED_CANDIDATE_NOT_EQUAL_TO_RAW_CLOSE",
    },
    {
        "url": "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh605016,day,,,100,hfq",
        "adjustment": "HFQ_ADJUSTED_CANDIDATE_NOT_EQUAL_TO_RAW_CLOSE",
    },
]
TARGET_STOCK_PAGE = "https://gu.qq.com/sh605016/gp"
KNOWN_TERMS_PAGES = [
    "https://www.tencent.com/zh-cn/service-agreement.html",
    "https://www.tencent.com/zh-cn/legal.html",
    "https://www.tencent.com/zh-cn/terms.html",
]


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fetch(url: str, referer: str) -> dict[str, Any]:
    request = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Connection": "close",
        "Referer": referer,
    })
    deadline = _clock.monotonic() + TOTAL_FETCH_DEADLINE_SECONDS
    try:
        with urlopen(request, timeout=SOCKET_TIMEOUT_SECONDS) as response:
            status = int(getattr(response, "status", 0))
            content_type = str(response.headers.get("Content-Type", ""))
            chunks: list[bytes] = []
            total = 0
            reader = getattr(response, "read1", None)
            while True:
                if _clock.monotonic() >= deadline:
                    return {"url": url, "status": "BLOCKED", "error": "TOTAL_DEADLINE_EXCEEDED"}
                block = (reader if callable(reader) else response.read)(
                    min(64 * 1024, MAX_BYTES + 1 - total)
                )
                if _clock.monotonic() >= deadline:
                    return {"url": url, "status": "BLOCKED", "error": "TOTAL_DEADLINE_EXCEEDED"}
                if not block:
                    break
                total += len(block)
                if total > MAX_BYTES:
                    return {"url": url, "status": "BLOCKED", "error": "SOURCE_EXCEEDS_MAX_BYTES"}
                chunks.append(block)
            raw = b"".join(chunks)
            return {
                "url": url, "http_status": status, "content_type": content_type,
                "status": "CAPTURED" if 200 <= status < 300 else "BLOCKED",
                "size_bytes": len(raw), "sha256": sha256(raw), "bytes": raw,
            }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {"url": url, "status": "BLOCKED", "error": f"{type(exc).__name__}:{str(exc)[:240]}"}


def save(root: Path, rel: str, raw: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def parse_json_or_jsonp(raw: bytes) -> Any:
    text = raw.decode("utf-8-sig", errors="strict").strip()
    if text.startswith("{") or text.startswith("["):
        return json.loads(text)
    left, right = text.find("("), text.rfind(")")
    if left >= 0 and right > left:
        return json.loads(text[left + 1:right])
    raise ValueError("RESPONSE_NOT_JSON_OR_JSONP")


def find_date_rows(node: Any, path: str = "$") -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, list):
                for i, row in enumerate(value):
                    if isinstance(row, list) and row and str(row[0]).replace("-", "") == "20261008":
                        found.append({
                            "json_path": f"{path}.{key}[{i}]",
                            "raw_row": row,
                            "date": str(row[0]),
                            "open": row[1] if len(row) > 1 else None,
                            "close": row[2] if len(row) > 2 else None,
                            "high": row[3] if len(row) > 3 else None,
                            "low": row[4] if len(row) > 4 else None,
                            "volume": row[5] if len(row) > 5 else None,
                            "amount": row[6] if len(row) > 6 else None,
                            "unverified_field_order_assumption": "date,open,close,high,low,volume,amount",
                        })
                    found.extend(find_date_rows(row, f"{path}.{key}[{i}]"))
            else:
                found.extend(find_date_rows(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(find_date_rows(value, f"{path}[{i}]"))
    return found


def capture_terms(root: Path) -> dict[str, Any]:
    homepage = fetch("https://www.tencent.com/zh-cn/", "https://www.tencent.com/")
    record: dict[str, Any] = {
        "source_id": "TENCENT-PUBLIC-TERMS-CANDIDATES",
        "status": "TERMS_NOT_ADJUDICATED",
        "homepage": {k:v for k,v in homepage.items() if k != "bytes"},
        "known_terms_pages": [],
        "important_limit": "A web page or terms excerpt is not a licence grant; reuse stays UNKNOWN unless explicitly supported by captured terms.",
    }
    if homepage.get("status") == "CAPTURED":
        raw = homepage["bytes"]
        save(root, "raw/TENCENT-COMPANY-HOMEPAGE.html", raw)
        html = raw.decode("utf-8", errors="replace")
        anchors = re.findall(r"<a\b[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", html, flags=re.I | re.S)
        candidates: list[tuple[str, str]] = []
        for href, label in anchors:
            title = re.sub(r"<[^>]+>", " ", label)
            title = re.sub(r"\s+", " ", title).strip()
            if re.search(r"法律|条款|协议|版权|免责声明|数据|服务", title, flags=re.I):
                u = urljoin("https://www.tencent.com/zh-cn/", href.strip())
                if u.startswith("https://") and all(u != old[0] for old in candidates):
                    candidates.append((u, title))
        record["discovered_links"] = [{"url":u,"label":label} for u,label in candidates[:12]]
    else:
        candidates=[]
    all_urls=[]
    for u,label in candidates[:5]:
        if u not in all_urls: all_urls.append(u)
    for u in KNOWN_TERMS_PAGES:
        if u not in all_urls: all_urls.append(u)
    for i,u in enumerate(all_urls[:6]):
        page=fetch(u,"https://www.tencent.com/zh-cn/")
        item={"url":u,"capture":{k:v for k,v in page.items() if k!="bytes"}}
        if page.get("status")=="CAPTURED":
            raw=page["bytes"]
            rel=f"raw/TENCENT-TERMS-{i+1}.bin"
            save(root,rel,raw)
            text=raw.decode("utf-8",errors="replace")
            plain=re.sub(r"<[^>]+>"," ",text)
            plain=re.sub(r"\s+"," ",plain)
            excerpts=[]
            for m in re.finditer(r"未经授权|书面许可|商业使用|转载|复制|传播|行情|数据|版权|许可|使用权|非商业",plain,flags=re.I):
                excerpt=plain[max(0,m.start()-110):min(len(plain),m.end()+180)]
                if excerpt not in excerpts: excerpts.append(excerpt)
                if len(excerpts)>=8: break
            item.update({"saved_path":rel,"size_bytes":len(raw),"sha256":sha256(raw),"terms_excerpts":excerpts})
        record["known_terms_pages"].append(item)
    record["status"]="TERMS_CAPTURED_NEEDS_REVIEW" if any(x.get("saved_path") for x in record["known_terms_pages"]) else "TERMS_NOT_CAPTURED"
    return record


def main() -> int:
    out=Path(sys.argv[1] if len(sys.argv)>1 else "/tmp/605016-https-provider")
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()): raise SystemExit("OUTPUT_DIRECTORY_MUST_BE_EMPTY")
    report:dict[str,Any]={
        "schema_version":"IIOS-605016-HTTPS-PRICE-PROVIDER-CANDIDATE-0.1",
        "case_id":CASE_ID,
        "original_cutoff_date_only":ORIGINAL_DATE_ONLY_CUTOFF,
        "required_price_observation_date":REQUIRED_PRICE_DATE,
        "captured_at":datetime.now(timezone.utc).isoformat(),
        "sources":[],
        "overall_status":"BLOCKED_UNTIL_SOURCE_AUTHORITY_REUSE_AND_PIT_ADMITTED",
        "non_claims":[
            "A provider API response, correct date or cross-provider price match does not prove source licensing, reuse rights or first-known time.",
            "The 2026-10-09 close cannot be used for the date-only 2026-10-09 cutoff; this capture seeks 2026-10-08 only.",
            "No captured price becomes an ADMITTED Evidence Record in this acquisition workflow.",
            "Raw payloads are captured in temporary Actions artifacts only; do not commit raw quote bytes to Git."
        ]
    }
    price_record: dict[str, Any] = {
        "source_id":"PRICE-TENCENT-KLINE-605016-2026-10-08",
        "source_class":"PUBLIC_SECONDARY_MARKET_DATA_CANDIDATE",
        "expected_date":REQUIRED_PRICE_DATE,
        "terms_reuse_status":"UNKNOWN_UNTIL_TERMS_REVIEW",
        "admission_status":"NOT_ADMITTED",
        "endpoint_attempts":[],
        "matching_rows":[],
    }
    for index, endpoint in enumerate(KLINE_ENDPOINTS):
        kline=fetch(endpoint["url"],TARGET_STOCK_PAGE)
        attempt={"url":endpoint["url"],"adjustment":endpoint["adjustment"],"capture":{k:v for k,v in kline.items() if k!="bytes"}}
        if kline.get("status")=="CAPTURED":
            raw=kline["bytes"]
            rel=f"raw/TENCENT-KLINE-CANDIDATE-{index+1}.bin"
            save(out,rel,raw)
            attempt.update({"raw_path":rel,"sha256":sha256(raw),"size_bytes":len(raw)})
            try:
                payload=parse_json_or_jsonp(raw)
                matches=find_date_rows(payload)
                attempt["matched_2026_10_08_rows"]=matches
                attempt["payload_sha256"]=sha256(raw)
                price_record["matching_rows"].extend(
                    [{"endpoint_index":index+1,"adjustment":endpoint["adjustment"],**row} for row in matches]
                )
            except (ValueError,UnicodeDecodeError,json.JSONDecodeError) as exc:
                attempt["parse_error"]=str(exc)
                attempt["payload_prefix"]=raw[:1000].decode("utf-8",errors="replace")
        price_record["endpoint_attempts"].append(attempt)
    unadjusted_matches=[item for item in price_record["matching_rows"] if item.get("adjustment")=="UNADJUSTED_KLINE_ENDPOINT_CANDIDATE"]
    price_record["candidate_status"] = "UNADJUSTED_ROW_CAPTURED_NOT_ADMITTED" if len(unadjusted_matches)==1 else "BLOCKED_UNADJUSTED_ROW_NOT_FOUND"
    price_record["source_reuse_status"]="UNKNOWN_UNTIL_TERMS_REVIEW"
    price_record["field_order_note"]="Tencent response schema has not yet been independently accepted; do not interpret adjusted qfq/hfq values as raw closing price."
    report["sources"].append(price_record)
    page=fetch(TARGET_STOCK_PAGE,"https://gu.qq.com/")
    page_record={"source_id":"TENCENT-STOCK-PAGE-605016","capture":{k:v for k,v in page.items() if k!="bytes"}}
    if page.get("status")=="CAPTURED":
        raw=page["bytes"]
        save(out,"raw/TENCENT-STOCK-PAGE.html",raw)
        page_record.update({"raw_path":"raw/TENCENT-STOCK-PAGE.html","sha256":sha256(raw),"size_bytes":len(raw)})
    report["sources"].append(page_record)
    report["sources"].append(capture_terms(out))
    report["raw_files"]=[]
    rawdir=out/"raw"
    if rawdir.exists():
        for p in sorted(rawdir.iterdir()):
            if p.is_file():
                b=p.read_bytes()
                report["raw_files"].append({"path":str(p.relative_to(out)),"size_bytes":len(b),"sha256":sha256(b)})
    (out/"HTTPS_PRICE_PROVIDER_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "overall_status":report["overall_status"],
        "price_candidate_status":price_record.get("candidate_status"),
        "price_rows":price_record.get("matching_rows"),
        "terms_status":report["sources"][-1].get("status"),
        "raw_file_count":len(report["raw_files"])
    },ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
