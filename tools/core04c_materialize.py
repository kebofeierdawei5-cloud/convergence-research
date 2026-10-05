from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def fetch(url: str, destination: Path) -> None:
    command = [
        "curl",
        "--location",
        "--fail",
        "--silent",
        "--show-error",
        "--retry", "4",
        "--retry-delay", "1",
        "--retry-all-errors",
        "--connect-timeout", "20",
        "--max-time", "120",
        "--user-agent", "IIOS-core04c/0.1",
        "--header", "Accept: */*",
        "--output", str(destination),
        url,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"curl failed rc={completed.returncode}: {completed.stderr.strip()}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    receipt = {"schema_version": "IIOS-CORE04C-MATERIALIZATION-RECEIPT-0.1", "case_id": manifest["case_id"], "sources": []}
    for source in manifest["sources"]:
        path = out / source["filename"]
        fetch(source["url"], path)
        actual_size = path.stat().st_size
        actual_sha256 = sha256(path)
        if actual_size != source["expected_size_bytes"]:
            raise RuntimeError(
                f'{source["source_id"]}: size mismatch {actual_size} != {source["expected_size_bytes"]}'
            )
        if actual_sha256 != source["expected_sha256"]:
            raise RuntimeError(
                f'{source["source_id"]}: sha256 mismatch {actual_sha256} != {source["expected_sha256"]}'
            )
        receipt["sources"].append({
            "source_id": source["source_id"],
            "filename": source["filename"],
            "size_bytes": actual_size,
            "sha256": actual_sha256,
            "status": "EXACT_MATCH",
        })
    (out / "materialization_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
