from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def capture(url: str, destination: Path) -> tuple[int, str]:
    command = [
        "curl",
        "--location",
        "--fail",
        "--silent",
        "--show-error",
        "--retry",
        "4",
        "--retry-delay",
        "1",
        "--retry-all-errors",
        "--connect-timeout",
        "20",
        "--max-time",
        "120",
        "--user-agent",
        "IIOS-public-source-capture/0.1",
        "--header",
        "Accept: */*",
        "--output",
        str(destination),
        "--write-out",
        "%{http_code}",
        url,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"curl failed rc={completed.returncode}: "
            f"{completed.stderr.strip() or 'no stderr'}"
        )
    status_text = completed.stdout.strip()
    status = int(status_text) if status_text.isdigit() else 0
    if status < 200 or status >= 300:
        raise RuntimeError(f"unexpected HTTP status {status}")
    sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
    return status, sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    receipt = {
        "schema_version": "IIOS-PUBLIC-SOURCE-CAPTURE-RECEIPT-0.2",
        "case_id": manifest["case_id"],
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sources": [],
    }
    failed = False

    with tempfile.TemporaryDirectory(prefix="iios-core04b-") as tmp:
        tmpdir = Path(tmp)
        for source in manifest["sources"]:
            filename = source["source_id"] + ".bin"
            path = tmpdir / filename
            retrieved_at = datetime.now(timezone.utc).isoformat()
            record = {
                "source_id": source["source_id"],
                "role": source["role"],
                "observation_date": source["observation_date"],
                "known_at": source.get("known_at"),
                "source_url": source["url"],
                "retrieved_at": retrieved_at,
                "admission_status": "NOT_ADMITTED",
            }
            try:
                status, sha256 = capture(source["url"], path)
                record.update(
                    {
                        "http_status": status,
                        "size_bytes": path.stat().st_size,
                        "sha256": sha256,
                        "exact_bytes_captured": True,
                        "capture_status": "SUCCESS",
                        "admission_reason": (
                            "Capture receipt proves bytes fetched in this run; "
                            "it is not a PIT evidence admission by itself."
                        ),
                    }
                )
            except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                failed = True
                record.update(
                    {
                        "http_status": None,
                        "size_bytes": path.stat().st_size if path.exists() else 0,
                        "sha256": None,
                        "exact_bytes_captured": False,
                        "capture_status": "FAILED",
                        "error": str(exc),
                        "admission_reason": (
                            "Source capture failed; no evidence admission is possible."
                        ),
                    }
                )
            receipt["sources"].append(record)

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
