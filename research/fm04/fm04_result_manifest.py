from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("GIT_REVISION_UNAVAILABLE")
    return proc.stdout.strip()


def git_blob_sha(path: Path) -> str:
    proc = subprocess.run(
        ["git", "hash-object", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"GIT_BLOB_SHA_UNAVAILABLE:{path}")
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result_path = Path(args.result)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "IIOS-FM04-RESULT-MANIFEST-0.1",
        "result_schema_version": result["schema_version"],
        "result_sha256": sha256_file(result_path),
        "code_commit_sha": git_revision(),
        "workflow_run_id": __import__("os").environ.get("GITHUB_RUN_ID"),
        "workflow_name": __import__("os").environ.get("GITHUB_WORKFLOW"),
        "repository": __import__("os").environ.get("GITHUB_REPOSITORY"),
        "ref": __import__("os").environ.get("GITHUB_REF"),
        "python_version": platform.python_version(),
        "input_bindings": result["input_bindings"],
    }
    output = Path(args.output)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
