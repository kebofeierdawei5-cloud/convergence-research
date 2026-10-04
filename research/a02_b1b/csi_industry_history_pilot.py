from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

CSI_SECURITY_INDUSTRY_SEARCH = (
    "https://www.csindex.com.cn/csindex-home/indexInfo/security-industry-search"
)
CSI_SECURITY_INDUSTRY_EXPORT = (
    "https://www.csindex.com.cn/csindex-home/exportExcel/"
    "security-industry-search-excel/CH"
)

ORIGINS = {
    "2023Q3": "2023-09-28",
    "2023Q4": "2023-12-29",
    "2024Q1": "2024-03-29",
    "2024Q2": "2024-06-28",
    "2024Q3": "2024-09-30",
    "2024Q4": "2024-12-31",
    "2025Q1": "2025-03-31",
    "2025Q2": "2025-06-30",
    "2025Q3": "2025-09-30",
    "2025Q4": "2025-12-31",
    "2026Q1": "2026-03-31",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (IIOS-B1B2-CSI-Industry-History-Pilot)",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.csindex.com.cn",
    "Referer": "https://www.csindex.com.cn/#/dataService/industryClassification",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def capture_response(
    response: requests.Response,
    out: Path,
    *,
    request_body: dict[str, Any] | None = None,
    source_class: str,
) -> dict[str, Any]:
    body = response.content
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    request_body_bytes = (
        json.dumps(request_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if request_body is not None
        else b""
    )
    return {
        "requested_url": response.request.url,
        "final_url": response.url,
        "method": response.request.method,
        "retrieved_at": utc_now(),
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "size_bytes": len(body),
        "sha256": sha256(body),
        "request_body_sha256": sha256(request_body_bytes) if request_body is not None else None,
        "exact_bytes": True,
        "source_class": source_class,
        "redirect_history": [
            {
                "status": h.status_code,
                "url": h.url,
                "location": h.headers.get("Location"),
            }
            for h in response.history
        ],
    }


def post_json(
    session: requests.Session,
    url: str,
    payload: dict[str, Any],
    out: Path,
    *,
    source_class: str,
) -> dict[str, Any]:
    response = session.post(
        url,
        json=payload,
        headers=HEADERS,
        timeout=15,
        allow_redirects=True,
    )
    meta = capture_response(
        response,
        out,
        request_body=payload,
        source_class=source_class,
    )
    meta["payload"] = payload
    return meta


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    data = payload.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ("data", "records", "rows", "list"):
            nested = data.get(key)
            if isinstance(nested, list):
                return [x for x in nested if isinstance(x, dict)]

    for key in ("records", "rows", "list"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return [x for x in candidate if isinstance(x, dict)]

    return []


def canonical_row(row: dict[str, Any]) -> dict[str, Any]:
    preferred = (
        "securityCode",
        "securityName",
        "cics1stCode",
        "cics1stName",
        "cics2ndCode",
        "cics2ndName",
        "cics3rdCode",
        "cics3rdName",
        "cics4thCode",
        "cics4thName",
    )
    result = {key: row.get(key) for key in preferred if key in row}
    if "securityCode" not in result:
        for candidate in ("code", "stockCode", "security_code"):
            if row.get(candidate) not in (None, ""):
                result["securityCode"] = row[candidate]
                break
    return result


def parse_page(raw_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = extract_rows(payload)
    codes = [
        str(row.get("securityCode", "")).strip()
        for row in rows
        if str(row.get("securityCode", "")).strip()
    ]
    return [canonical_row(row) for row in rows], {
        "row_count": len(rows),
        "security_code_count": len(codes),
        "unique_security_code_count": len(set(codes)),
        "duplicate_security_codes": sorted(
            {code for code in codes if codes.count(code) > 1}
        ),
        "payload_top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
    }


def materialize_current_table(
    session: requests.Session,
    root: Path,
    *,
    page_size: int,
    max_pages: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    raw_dir = root / "current_search_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "schema_version": "IIOS-A02-B1B2-CSI-INDUSTRY-CURRENT-PILOT-0.1",
        "provider": "CSI",
        "provider_role": "OFFICIAL_PUBLIC_CURRENT_ONLY",
        "retrieved_at": utc_now(),
        "endpoint": CSI_SECURITY_INDUSTRY_SEARCH,
        "page_size_requested": page_size,
        "pages": [],
        "status": "BLOCKED",
        "reason": None,
    }

    all_rows: list[dict[str, Any]] = []
    page = 1
    while page <= max_pages:
        payload = {
            "searchInput": "",
            "pageNum": page,
            "pageSize": page_size,
            "sortField": None,
            "sortOrder": None,
        }
        raw_path = raw_dir / f"page_{page:04d}.json"
        meta = post_json(
            session,
            CSI_SECURITY_INDUSTRY_SEARCH,
            payload,
            raw_path,
            source_class="OFFICIAL_PUBLIC_HTTP",
        )
        entry: dict[str, Any] = {"page": page, "raw": meta}

        if meta["http_status"] != 200:
            entry["status"] = "BLOCKED_HTTP"
            receipt["pages"].append(entry)
            break

        try:
            rows, stats = parse_page(raw_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            entry["status"] = "BLOCKED_PARSE"
            entry["error"] = str(exc)
            receipt["pages"].append(entry)
            break

        entry.update(stats)
        entry["status"] = "OK"
        receipt["pages"].append(entry)
        all_rows.extend(rows)

        if not rows or len(rows) < page_size:
            break
        page += 1
        if sleep_seconds:
            time.sleep(sleep_seconds)

    code_set = [
        str(row.get("securityCode", "")).strip()
        for row in all_rows
        if str(row.get("securityCode", "")).strip()
    ]
    duplicates = sorted({code for code in code_set if code_set.count(code) > 1})
    unique_codes = sorted(set(code_set))

    receipt["aggregate"] = {
        "rows": len(all_rows),
        "security_codes": len(code_set),
        "unique_security_codes": len(unique_codes),
        "duplicate_security_codes": duplicates,
        "sample_codes": unique_codes[:20],
        "required_columns_observed": sorted(
            {
                key
                for row in all_rows
                for key in row.keys()
            }
        ),
    }

    normalized_path = root / "current_search_normalized.json"
    normalized_path.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    receipt["normalized"] = {
        "path": str(normalized_path.relative_to(root)),
        "sha256": sha256(normalized_path.read_bytes()),
        "exact_bytes": True,
    }

    if receipt["pages"] and all(p.get("status") == "OK" for p in receipt["pages"]):
        receipt["status"] = "PASS_CURRENT_ONLY"
        receipt["reason"] = (
            "Current security-level CSI industry assignment is reproducibly "
            "retrievable; no historical/PIT semantics are implied."
        )
    else:
        receipt["status"] = "BLOCKED"
        receipt["reason"] = "Current security-level retrieval was incomplete."

    return receipt


def materialize_export(
    session: requests.Session,
    root: Path,
) -> dict[str, Any]:
    raw_path = root / "current_export.xlsx"
    payload = {
        "searchInput": "",
        "pageNum": 1,
        "pageSize": 10000,
        "sortField": None,
        "sortOrder": None,
    }
    meta = post_json(
        session,
        CSI_SECURITY_INDUSTRY_EXPORT,
        payload,
        raw_path,
        source_class="OFFICIAL_PUBLIC_HTTP",
    )
    meta["role"] = "CURRENT_TABLE_EXPORT_ONLY"
    return meta


def probe_historical_parameters(
    session: requests.Session,
    root: Path,
    *,
    page_size: int,
) -> dict[str, Any]:
    probe_dir = root / "historical_parameter_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)

    base_payload = {
        "searchInput": "",
        "pageNum": 1,
        "pageSize": page_size,
        "sortField": None,
        "sortOrder": None,
    }
    base_path = probe_dir / "baseline.json"
    baseline_meta = post_json(
        session,
        CSI_SECURITY_INDUSTRY_SEARCH,
        base_payload,
        base_path,
        source_class="OFFICIAL_PUBLIC_HTTP",
    )

    result: dict[str, Any] = {
        "schema_version": "IIOS-A02-B1B2-CSI-HISTORICAL-PARAM-PROBE-0.2",
        "provider": "CSI",
        "endpoint": CSI_SECURITY_INDUSTRY_SEARCH,
        "retrieved_at": utc_now(),
        "baseline": baseline_meta,
        "discovery_origin": "2026Q1",
        "candidate_parameters": ["date", "effectiveDate", "asOfDate", "queryDate"],
        "probes": [],
        "interpretation": {
            "historical_semantics_verified": False,
            "status": "BLOCKED",
        },
    }

    discovery_origin = "2026Q1"
    discovery_date = ORIGINS[discovery_origin]
    sensitive_parameters: list[str] = []

    for parameter in result["candidate_parameters"]:
        payload = dict(base_payload)
        payload[parameter] = discovery_date
        raw_path = probe_dir / f"{discovery_origin}_{parameter}.json"
        meta = post_json(
            session,
            CSI_SECURITY_INDUSTRY_SEARCH,
            payload,
            raw_path,
            source_class="OFFICIAL_PUBLIC_HTTP",
        )
        probe: dict[str, Any] = {
            "origin": discovery_origin,
            "requested_date": discovery_date,
            "parameter": parameter,
            "raw": meta,
            "same_response_sha256_as_baseline": (
                meta["sha256"] == baseline_meta["sha256"]
            ),
        }
        try:
            probe["rows"], probe["stats"] = parse_page(raw_path)
            baseline_rows, baseline_stats = parse_page(base_path)
            probe["same_normalized_rows_as_baseline"] = (
                probe["rows"] == baseline_rows
            )
            probe["baseline_row_count"] = baseline_stats["row_count"]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            probe["parse_error"] = str(exc)

        if (
            meta["sha256"] != baseline_meta["sha256"]
            or probe.get("same_normalized_rows_as_baseline") is False
        ):
            probe["status"] = "DATE_SENSITIVITY_DETECTED_UNVERIFIED"
            sensitive_parameters.append(parameter)
        else:
            probe["status"] = "NO_DATE_SENSITIVITY_OBSERVED"
        result["probes"].append(probe)

    for parameter in sensitive_parameters:
        for origin, date_value in ORIGINS.items():
            if origin == discovery_origin:
                continue
            payload = dict(base_payload)
            payload[parameter] = date_value
            raw_path = probe_dir / f"{origin}_{parameter}.json"
            meta = post_json(
                session,
                CSI_SECURITY_INDUSTRY_SEARCH,
                payload,
                raw_path,
                source_class="OFFICIAL_PUBLIC_HTTP",
            )
            probe = {
                "origin": origin,
                "requested_date": date_value,
                "parameter": parameter,
                "raw": meta,
                "same_response_sha256_as_baseline": (
                    meta["sha256"] == baseline_meta["sha256"]
                ),
            }
            try:
                probe["rows"], probe["stats"] = parse_page(raw_path)
                baseline_rows, baseline_stats = parse_page(base_path)
                probe["same_normalized_rows_as_baseline"] = (
                    probe["rows"] == baseline_rows
                )
                probe["baseline_row_count"] = baseline_stats["row_count"]
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                probe["parse_error"] = str(exc)
            if (
                meta["sha256"] != baseline_meta["sha256"]
                or probe.get("same_normalized_rows_as_baseline") is False
            ):
                probe["status"] = "DATE_SENSITIVITY_DETECTED_UNVERIFIED"
            else:
                probe["status"] = "NO_DATE_SENSITIVITY_OBSERVED"
            result["probes"].append(probe)

    if not sensitive_parameters:
        result["interpretation"]["status"] = "BLOCKED_DATE_PARAMETER_NOT_EVIDENCED"
        result["interpretation"]["reason"] = (
            "Candidate date parameters did not change the current endpoint response "
            "for the discovery origin. The public route cannot be admitted as "
            "historical PIT evidence."
        )
    else:
        result["interpretation"]["status"] = (
            "BLOCKED_DATE_PARAMETER_SENSITIVITY_UNVERIFIED"
        )
        result["interpretation"]["reason"] = (
            "At least one exploratory date parameter changed the response. "
            "The change is not sufficient to establish historical semantics or "
            "source-side known_at without an official source contract."
        )
        result["interpretation"]["sensitive_parameters"] = sensitive_parameters

    return result

def build_admission(current: dict[str, Any], export: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    current_ok = current.get("status") == "PASS_CURRENT_ONLY"
    export_ok = export.get("http_status") == 200 and export.get("exact_bytes") is True
    historical_ok = probe.get("interpretation", {}).get("historical_semantics_verified") is True
    return {
        "schema_version": "IIOS-A02-B1B2-CSI-INDUSTRY-ADMISSION-0.1",
        "overall": "BLOCKED",
        "field": "CSI_industry_security_history",
        "current_security_level_route": {
            "status": "CONDITIONAL" if current_ok else "BLOCKED",
            "reason": (
                "Current CSI security-level industry assignments are reproducibly "
                "materializable, but are a current snapshot only."
            ),
        },
        "current_export_route": {
            "status": "CONDITIONAL" if export_ok else "BLOCKED",
            "reason": (
                "Official public export bytes are captured for current-table "
                "reconciliation; historical vintage is not established."
            ),
        },
        "historical_security_level_assignment": {
            "status": "PASS" if historical_ok else "BLOCKED",
            "reason": (
                "Historical PIT route is not admitted without source-vintage or "
                "official date semantics."
            ),
        },
        "known_at": {
            "status": "BLOCKED",
            "reason": (
                "The current public endpoint does not expose source-side known_at "
                "for historical assignments."
            ),
        },
        "provenance_boundary": {
            "current_route": "OFFICIAL_PUBLIC_CURRENT_ONLY",
            "historical_route": "UNKNOWN",
            "secondary_crosscheck_allowed": True,
            "current_to_historical_substitution": False,
        },
        "transition": (
            "KEEP_BLOCKED_AND_SEARCH_OFFICIAL_ARCHIVED_CLASSIFICATION_ARTIFACTS"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    args = parser.parse_args()

    root = Path(args.out).resolve()
    root.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    current = materialize_current_table(
        session,
        root,
        page_size=args.page_size,
        max_pages=args.max_pages,
        sleep_seconds=args.sleep_seconds,
    )
    export = materialize_export(session, root)
    probe = probe_historical_parameters(
        session,
        root,
        page_size=min(args.page_size, 100),
    )

    admission = build_admission(current, export, probe)

    (root / "CSI_INDUSTRY_PILOT_RECEIPT.json").write_text(
        json.dumps(
            {
                "schema_version": "IIOS-A02-B1B2-CSI-INDUSTRY-PILOT-BUNDLE-0.1",
                "retrieved_at": utc_now(),
                "current": current,
                "export": export,
                "historical_probe": probe,
                "admission": admission,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "CSI_INDUSTRY_FIELD_ADMISSION.json").write_text(
        json.dumps(admission, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "current_status": current["status"],
                "current_unique_security_codes": current.get("aggregate", {}).get(
                    "unique_security_codes"
                ),
                "export_http_status": export.get("http_status"),
                "historical_status": probe["interpretation"]["status"],
                "admission": admission["overall"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
