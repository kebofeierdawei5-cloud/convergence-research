from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from pypdf import PdfWriter
import pytest

from tools import route_a_605016_official_https_b2_adjudicate as MODULE


def _pdf_bytes() -> bytes:
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=612, height=792)
    import io
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _ledger(pdf_raw: bytes) -> dict:
    return {
        "schema_version": "IIOS-605016-DIVIDEND-IMPLEMENTATION-ADJUDICATION-0.1",
        "record_class": "OFFICIAL_SOURCE_FACT_ADJUDICATION",
        "case_id": MODULE.CASE_ID,
        "cutoff_date": MODULE.CUTOFF_DATE,
        "source": {
            "source_id": "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION",
            "listing_sha256": MODULE.EXPECTED_DIVIDEND_LISTING_SHA256,
            "listing_size_bytes": MODULE.EXPECTED_DIVIDEND_LISTING_SIZE,
            "listing_row": {
                "ADDDATE": "2026-09-21 16:44:10",
                "SSEDATE": "2026-09-22",
                "SECURITY_CODE": "605016",
                "SECURITY_NAME": "百龙创园",
                "TITLE": "2026年半年度权益分派实施公告",
                "URL": "/disclosure/listedinfo/announcement/c/new/2026-09-22/605016_20260922_1YLT.pdf",
            },
            "pdf_url": MODULE.EXPECTED_DIVIDEND_PDF_URL,
            "pdf_size_bytes": len(pdf_raw),
            "pdf_sha256": hashlib.sha256(pdf_raw).hexdigest(),
            "pdf_page_count": 3,
        },
        "reuse": {"status": "RESTRICTED_NO_REDISTRIBUTION"},
        "evidence_record": {
            "evidence_id": "605016-H1-DIVIDEND-IMPLEMENTED-202609",
            "subject_id": MODULE.CASE_ID,
            "field_id": "capital_structure.dividend_implementation_2026H1",
            "claim_type": "OBSERVED_FACT",
            "value": {"announcement_no": "2026-043"},
            "unit": "CNY_per_share_and_total_CNY",
            "observation_date": "2026-09-29",
            "known_at": "2026-09-22",
            "published_at": "2026-09-22",
            "known_at_basis": "Official prior adjudication; date precision only.",
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
            "license_status": "RESTRICTED_NO_REDISTRIBUTION",
            "content_sha256": hashlib.sha256(pdf_raw).hexdigest(),
            "source_locator": "Prior source adjudication record",
        },
    }


def _setup(tmp_path: Path, monkeypatch, pdf_raw: bytes) -> Path:
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    ledger_path = repo / MODULE.DIVIDEND_LEDGER_RELATIVE
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(_ledger(pdf_raw), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(MODULE, "__file__", str(repo / "tools" / "route_a_605016_official_https_b2_adjudicate.py"))
    monkeypatch.setattr(MODULE, "EXPECTED_DIVIDEND_PDF_SHA256", hashlib.sha256(pdf_raw).hexdigest())
    monkeypatch.setattr(MODULE, "EXPECTED_DIVIDEND_PDF_SIZE", len(pdf_raw))
    return repo


def test_reuses_prior_listing_decision_but_refetches_and_rehashes_exact_pdf(tmp_path: Path, monkeypatch) -> None:
    pdf_raw = _pdf_bytes()
    _setup(tmp_path, monkeypatch, pdf_raw)
    monkeypatch.setattr(MODULE, "fetch_https", lambda *_args, **_kwargs: {
        "status": "CAPTURED",
        "url": MODULE.EXPECTED_DIVIDEND_PDF_URL,
        "final_url": MODULE.EXPECTED_DIVIDEND_PDF_URL,
        "http_status": 200,
        "content_type": "application/pdf",
        "body": pdf_raw,
    })

    output = tmp_path / "followup"
    dividend, ledger = MODULE._recover_dividend_from_prior_canonical_adjudication(output)

    persisted_pdf = output / "raw" / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf"
    assert persisted_pdf.read_bytes() == pdf_raw
    assert hashlib.sha256(persisted_pdf.read_bytes()).hexdigest() == MODULE.EXPECTED_DIVIDEND_PDF_SHA256
    assert dividend["status"] == "RAW_PDF_CAPTURED_NOT_ADMITTED"
    assert dividend["prior_adjudication"]["listing_bytes_reverified_in_current_run"] is False
    assert ledger["case_id"] == MODULE.CASE_ID
    capture_report = json.loads((output / "FOLLOWUP_SOURCE_CAPTURE_REPORT.json").read_text(encoding="utf-8"))
    assert capture_report["prior_listing_bytes_reverified_in_current_run"] is False



def test_official_static_https_candidate_is_used_only_after_primary_transport_block(
    tmp_path: Path, monkeypatch
) -> None:
    pdf_raw = _pdf_bytes()
    _setup(tmp_path, monkeypatch, pdf_raw)
    calls: list[str] = []
    fallback_url = MODULE.DIVIDEND_PDF_HTTPS_URLS[1]

    def fake_fetch(url: str, **_kwargs):
        calls.append(url)
        if url == MODULE.DIVIDEND_PDF_HTTPS_URLS[0]:
            return {"status": "BLOCKED", "url": url, "error": "NETWORK_UNREACHABLE"}
        if url == fallback_url:
            return {
                "status": "CAPTURED",
                "url": url,
                "final_url": url,
                "http_status": 200,
                "content_type": "application/pdf",
                "body": pdf_raw,
            }
        raise AssertionError("later candidates must not be tried after a successful response")

    monkeypatch.setattr(MODULE, "fetch_https", fake_fetch)
    output = tmp_path / "followup"
    dividend, _ledger_obj = MODULE._recover_dividend_from_prior_canonical_adjudication(output)

    assert calls == list(MODULE.DIVIDEND_PDF_HTTPS_URLS[:2])
    assert dividend["pdf_capture"]["requested_url"] == fallback_url
    assert dividend["pdf_capture"]["final_url"] == fallback_url
    persisted_pdf = output / "raw" / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf"
    assert persisted_pdf.read_bytes() == pdf_raw
    assert hashlib.sha256(persisted_pdf.read_bytes()).hexdigest() == MODULE.EXPECTED_DIVIDEND_PDF_SHA256


def test_curl_transport_fallback_uses_same_official_pdf_exact_byte_gate(
    tmp_path: Path, monkeypatch
) -> None:
    pdf_raw = _pdf_bytes()
    _setup(tmp_path, monkeypatch, pdf_raw)
    python_calls: list[str] = []
    curl_calls: list[str] = []

    def blocked_python(url: str, **_kwargs):
        python_calls.append(url)
        return {"status": "BLOCKED", "url": url, "error": "NETWORK_UNREACHABLE"}

    def captured_curl(url: str, **_kwargs):
        curl_calls.append(url)
        return {
            "status": "CAPTURED",
            "url": url,
            "final_url": url,
            "http_status": 200,
            "content_type": "application/pdf",
            "body": pdf_raw,
        }

    monkeypatch.setattr(MODULE, "fetch_https", blocked_python)
    monkeypatch.setattr(MODULE, "_fetch_official_pdf_via_curl", captured_curl)
    output = tmp_path / "curl-followup"
    dividend, _ledger_obj = MODULE._recover_dividend_from_prior_canonical_adjudication(output)

    assert python_calls == list(MODULE.DIVIDEND_PDF_HTTPS_URLS)
    assert curl_calls == [MODULE.DIVIDEND_PDF_HTTPS_URLS[0]]
    assert dividend["pdf_capture"]["requested_url"] == MODULE.EXPECTED_DIVIDEND_PDF_URL
    persisted_pdf = output / "raw" / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf"
    assert persisted_pdf.read_bytes() == pdf_raw
    assert hashlib.sha256(persisted_pdf.read_bytes()).hexdigest() == MODULE.EXPECTED_DIVIDEND_PDF_SHA256


def test_curl_helper_keeps_tls_verification_and_https_redirect_only(
    tmp_path: Path, monkeypatch
) -> None:
    pdf_raw = _pdf_bytes()
    _setup(tmp_path, monkeypatch, pdf_raw)
    monkeypatch.setattr(MODULE.shutil, "which", lambda name: "/usr/bin/curl" if name == "curl" else None)

    def fake_run(command, **kwargs):
        output_path = Path(command[command.index("--output") + 1])
        output_path.write_bytes(pdf_raw)
        url = command[-1]
        assert command[command.index("--proto") + 1] == "=https"
        assert command[command.index("--proto-redir") + 1] == "=https"
        assert kwargs["timeout"] == 10
        return type("Completed", (), {
            "returncode": 0,
            "stdout": f"200\n{url}\napplication/pdf\n".encode("utf-8"),
        })()

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    response = MODULE._fetch_official_pdf_via_curl(
        MODULE.EXPECTED_DIVIDEND_PDF_URL,
        referer="https://www.sse.com.cn/disclosure/listedinfo/announcement/index.shtml",
    )

    assert response["status"] == "CAPTURED"
    assert response["final_url"] == MODULE.EXPECTED_DIVIDEND_PDF_URL
    assert response["body"] == pdf_raw


def test_recovery_condition_requires_exact_live_notice_identity_when_listing_was_captured() -> None:
    matching = {
        "status": "BLOCKED_NO_VERIFIED_PDF_BYTES",
        "listing_request": {"status": "CAPTURED"},
        "listing_row": dict(MODULE.EXPECTED_DIVIDEND_LISTING_ROW),
    }
    assert MODULE._can_recover_dividend_from_prior(matching)

    wrong_title = dict(matching)
    wrong_title["listing_row"] = {**MODULE.EXPECTED_DIVIDEND_LISTING_ROW, "TITLE": "其他公告"}
    assert not MODULE._can_recover_dividend_from_prior(wrong_title)

    missing_row = dict(matching)
    missing_row.pop("listing_row")
    assert not MODULE._can_recover_dividend_from_prior(missing_row)

    # Preserve the original listing-transport-blocked recovery route.
    assert MODULE._can_recover_dividend_from_prior({
        "status": "BLOCKED", "listing_request": {"status": "BLOCKED"}
    })


def test_all_blocked_pdf_fetch_diagnostics_are_safe_and_specific() -> None:
    blocked = MODULE.OfficialDividendPdfFetchBlocked([
        {"endpoint": "BIG5", "transport": "PYTHON_HTTPS", "outcome": "DNS_FAILURE"},
        {"endpoint": "BIG5", "transport": "CURL_HTTPS", "outcome": "TIMEOUT"},
    ])
    assert str(blocked) == "OFFICIAL_DIVIDEND_PDF_DIRECT_HTTPS_FETCH_BLOCKED"
    assert blocked.safe_diagnostics == [
        {"endpoint": "BIG5", "transport": "PYTHON_HTTPS", "outcome": "DNS_FAILURE"},
        {"endpoint": "BIG5", "transport": "CURL_HTTPS", "outcome": "TIMEOUT"},
    ]


def test_cli_writes_sanitized_blocked_report_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    diagnostics = [
        {"endpoint": "BIG5", "transport": "PYTHON_HTTPS", "outcome": "DNS_FAILURE"},
        {"endpoint": "STATIC", "transport": "CURL_HTTPS", "outcome": "TLS_CERTIFICATE_FAILURE"},
    ]
    attempt_root = tmp_path / "attempt10"
    attempt_root.mkdir()
    output_root = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "route_a_605016_official_https_b2_adjudicate.py",
        "--attempt10-root", str(attempt_root),
        "--out-dir", str(output_root),
    ])
    monkeypatch.setattr(
        MODULE, "adjudicate",
        lambda *_args: (_ for _ in ()).throw(MODULE.OfficialDividendPdfFetchBlocked(diagnostics)),
    )

    assert MODULE.main() == 0
    report = json.loads((output_root / "OFFICIAL_HTTPS_B2_ADJUDICATION_REPORT.json").read_text(encoding="utf-8"))
    console = json.loads(capsys.readouterr().out)
    assert report["overall_status"] == "BLOCKED_SOURCE_FETCH"
    assert report["candidate_manifest_status"] == "NOT_CREATED"
    assert report["source_fetch_diagnostics"] == diagnostics
    assert report["raw_source_bytes_uploaded"] is False
    assert console["status"] == "BLOCKED"
    assert "sse.com.cn" not in json.dumps(report).lower()


def test_successful_but_wrong_pdf_bytes_block_without_trying_another_host(
    tmp_path: Path, monkeypatch
) -> None:
    expected_pdf = _pdf_bytes()
    wrong_pdf = b"%PDF-1.7\\nnot-the-adjudicated-document"
    _setup(tmp_path, monkeypatch, expected_pdf)
    calls: list[str] = []

    def fake_fetch(url: str, **_kwargs):
        calls.append(url)
        return {
            "status": "CAPTURED",
            "url": url,
            "final_url": url,
            "http_status": 200,
            "content_type": "application/pdf",
            "body": wrong_pdf,
        }

    monkeypatch.setattr(MODULE, "fetch_https", fake_fetch)
    output = tmp_path / "followup"
    with pytest.raises(ValueError, match="OFFICIAL_DIVIDEND_PDF_EXACT_BYTES_MISMATCH"):
        MODULE._recover_dividend_from_prior_canonical_adjudication(output)

    assert calls == [MODULE.DIVIDEND_PDF_HTTPS_URLS[0]]
    assert not (output / "raw" / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf").exists()


def test_direct_pdf_fetch_failure_blocks_without_creating_passing_capture(tmp_path: Path, monkeypatch) -> None:
    pdf_raw = _pdf_bytes()
    _setup(tmp_path, monkeypatch, pdf_raw)
    monkeypatch.setattr(MODULE, "fetch_https", lambda url, **_kwargs: {
        "status": "BLOCKED",
        "url": url,
        "error": "NETWORK_UNREACHABLE",
    })
    monkeypatch.setattr(MODULE, "_fetch_official_pdf_via_curl", lambda url, **_kwargs: {
        "status": "BLOCKED", "url": url, "error": "CURL_EXIT_6",
    })

    output = tmp_path / "followup"
    with pytest.raises(ValueError, match="OFFICIAL_DIVIDEND_PDF_DIRECT_HTTPS_FETCH_BLOCKED"):
        MODULE._recover_dividend_from_prior_canonical_adjudication(output)

    assert not (output / "raw" / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf").exists()


def test_wrong_pdf_hash_is_rejected_before_a_passing_capture_is_returned(tmp_path: Path, monkeypatch) -> None:
    pdf_raw = _pdf_bytes()
    _setup(tmp_path, monkeypatch, pdf_raw)
    monkeypatch.setattr(MODULE, "EXPECTED_DIVIDEND_PDF_SHA256", "0" * 64)
    monkeypatch.setattr(MODULE, "fetch_https", lambda *_args, **_kwargs: {
        "status": "CAPTURED",
        "url": MODULE.EXPECTED_DIVIDEND_PDF_URL,
        "final_url": MODULE.EXPECTED_DIVIDEND_PDF_URL,
        "http_status": 200,
        "content_type": "application/pdf",
        "body": pdf_raw,
    })

    with pytest.raises(ValueError, match="CANONICAL_DIVIDEND_SOURCE_PIN_MISMATCH"):
        MODULE._recover_dividend_from_prior_canonical_adjudication(tmp_path / "followup")
