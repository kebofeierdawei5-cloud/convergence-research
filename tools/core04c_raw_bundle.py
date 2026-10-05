from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def fetch(url: str, destination: Path) -> tuple[bool, str | None]:
    cmd = [
        "curl", "--location", "--fail", "--silent", "--show-error",
        "--retry", "4", "--retry-delay", "1", "--retry-all-errors",
        "--connect-timeout", "20", "--max-time", "120",
        "--user-agent", "IIOS-core04c-diagnostic/0.1",
        "--header", "Accept: */*",
        "--output", str(destination), url,
    ]
    p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if p.returncode != 0:
        return False, p.stderr.strip() or f"curl rc={p.returncode}"
    return True, None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    receipt = {
        "schema_version": "IIOS-CORE04C-RAW-BUNDLE-DIAGNOSTIC-0.1",
        "case_id": manifest["case_id"],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sources": [],
    }

    for s in manifest["sources"]:
        path = out / s["filename"]
        ok, err = fetch(s["url"], path)
        row = {
            "source_id": s["source_id"],
            "filename": s["filename"],
            "expected_size_bytes": s["expected_size_bytes"],
            "expected_sha256": s["expected_sha256"],
            "retrieval_ok": ok,
        }
        if not ok:
            row.update({
                "status": "FETCH_FAILED",
                "actual_size_bytes": path.stat().st_size if path.exists() else 0,
                "actual_sha256": None,
                "error": err,
            })
        else:
            actual_size = path.stat().st_size
            actual_sha = sha256(path)
            row.update({
                "status": "EXACT_MATCH" if (
                    actual_size == s["expected_size_bytes"] and
                    actual_sha == s["expected_sha256"]
                ) else "CURRENT_BYTES_DIFFER",
                "actual_size_bytes": actual_size,
                "actual_sha256": actual_sha,
                "size_matches": actual_size == s["expected_size_bytes"],
                "sha256_matches": actual_sha == s["expected_sha256"],
            })
        receipt["sources"].append(row)

    (out / "diagnostic_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
