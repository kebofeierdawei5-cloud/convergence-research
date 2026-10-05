from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def capture(url: str, destination: Path) -> tuple[int, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "IIOS-public-source-capture/0.1",
            "Accept": "*/*",
        },
        method="GET",
    )
    sha = hashlib.sha256()
    total = 0
    with urlopen(request, timeout=90) as response, destination.open("wb") as handle:
        status = getattr(response, "status", 200)
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            sha.update(chunk)
            total += len(chunk)
    return status, sha.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    receipt = {
        "schema_version": "IIOS-PUBLIC-SOURCE-CAPTURE-RECEIPT-0.1",
        "case_id": manifest["case_id"],
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sources": [],
    }

    with tempfile.TemporaryDirectory(prefix="iios-core04b-") as tmp:
        tmpdir = Path(tmp)
        for source in manifest["sources"]:
            filename = source["source_id"] + ".bin"
            path = tmpdir / filename
            started = datetime.now(timezone.utc).isoformat()
            status, sha256 = capture(source["url"], path)
            content_type = None
            receipt["sources"].append(
                {
                    "source_id": source["source_id"],
                    "role": source["role"],
                    "observation_date": source["observation_date"],
                    "known_at": source.get("known_at"),
                    "source_url": source["url"],
                    "retrieved_at": started,
                    "http_status": status,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256,
                    "exact_bytes_captured": True,
                    "admission_status": "NOT_ADMITTED",
                    "admission_reason": "Capture receipt proves bytes fetched in this run; it is not a PIT evidence admission by itself.",
                }
            )

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
