from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_000906_SIZE = 169984
EXPECTED_000906_SHA256 = "f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984"
REQUIRED_ORIGINS = (
    "2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4",
    "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_exact_file(path: Path, expected_size: int, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "BLOCKED", "reason": "EXACT_BYTES_MISSING", "path": str(path), "size_bytes": None, "sha256": None, "exact_bytes": False}
    size = path.stat().st_size
    digest = sha256_file(path)
    size_ok = size == expected_size
    sha_ok = digest == expected_sha256
    return {
        "status": "PASS" if size_ok and sha_ok else "BLOCKED",
        "reason": "EXACT_BYTES_VERIFIED" if size_ok and sha_ok else "EXACT_BYTES_MISMATCH",
        "path": str(path),
        "size_bytes": size,
        "sha256": digest,
        "expected_size_bytes": expected_size,
        "expected_sha256": expected_sha256,
        "size_match": size_ok,
        "sha256_match": sha_ok,
        "exact_bytes": True,
    }


def find_terminal_xls(root: Path) -> Path | None:
    direct = root / "000906cons.xls"
    if direct.is_file():
        return direct
    matches = sorted(root.rglob("000906cons.xls")) if root.exists() else []
    return matches[0] if matches else None


def inspect_security_master(root: Path) -> dict[str, Any]:
    manifest_path = root / "pit_security_master_manifest.json"
    if not manifest_path.is_file():
        return {"status": "BLOCKED", "reason": "PIT_SECURITY_MASTER_MANIFEST_MISSING", "covered_origins": [], "verified_artifacts": []}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED", "reason": f"PIT_SECURITY_MASTER_MANIFEST_INVALID:{exc}", "covered_origins": [], "verified_artifacts": []}
    origins = list(manifest.get("covered_origins") or [])
    if sorted(origins) != sorted(REQUIRED_ORIGINS):
        return {"status": "BLOCKED", "reason": "PIT_SECURITY_MASTER_ORIGIN_COVERAGE_INCOMPLETE", "covered_origins": origins, "verified_artifacts": []}
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return {"status": "BLOCKED", "reason": "PIT_SECURITY_MASTER_ARTIFACTS_MISSING", "covered_origins": origins, "verified_artifacts": []}
    verified: list[dict[str, Any]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            return {"status": "BLOCKED", "reason": "PIT_SECURITY_MASTER_ARTIFACT_ENTRY_INVALID", "covered_origins": origins, "verified_artifacts": verified}
        path_raw = item.get("path")
        expected_sha = item.get("sha256")
        expected_size = item.get("size_bytes")
        known_evidence = item.get("known_at_evidence")
        if not path_raw or not expected_sha or not isinstance(expected_size, int) or not known_evidence:
            return {"status": "BLOCKED", "reason": "PIT_SECURITY_MASTER_ARTIFACT_PROVENANCE_INCOMPLETE", "covered_origins": origins, "verified_artifacts": verified}
        path = root / path_raw
        result = verify_exact_file(path, expected_size, expected_sha)
        verified.append(result)
        if result["status"] != "PASS":
            return {"status": "BLOCKED", "reason": "PIT_SECURITY_MASTER_EXACT_ARTIFACT_FAILED", "covered_origins": origins, "verified_artifacts": verified}
    return {"status": "PASS", "reason": "PIT_SECURITY_MASTER_EXACT_ARTIFACTS_VERIFIED", "covered_origins": origins, "verified_artifacts": verified}


def build_attempt(input_dir: Path) -> dict[str, Any]:
    terminal = find_terminal_xls(input_dir)
    object_a_exact = verify_exact_file(terminal, EXPECTED_000906_SIZE, EXPECTED_000906_SHA256) if terminal else {
        "status": "BLOCKED", "reason": "EXACT_000906_BYTES_MISSING", "path": None, "size_bytes": None, "sha256": None, "exact_bytes": False
    }
    historical_manifest = input_dir / "historical_membership_manifest.json"
    if not historical_manifest.is_file():
        historical = {"status": "BLOCKED", "reason": "HISTORICAL_MEMBERSHIP_MANIFEST_MISSING", "covered_origins": []}
    else:
        try:
            hm = json.loads(historical_manifest.read_text(encoding="utf-8"))
            covered = list(hm.get("covered_origins") or [])
            historical = {
                "status": "PASS" if sorted(covered) == sorted(REQUIRED_ORIGINS) else "BLOCKED",
                "reason": "HISTORICAL_MEMBERSHIP_COVERAGE_DECLARED" if sorted(covered) == sorted(REQUIRED_ORIGINS) else "HISTORICAL_MEMBERSHIP_ORIGIN_COVERAGE_INCOMPLETE",
                "covered_origins": covered,
            }
        except (OSError, json.JSONDecodeError) as exc:
            historical = {"status": "BLOCKED", "reason": f"HISTORICAL_MEMBERSHIP_MANIFEST_INVALID:{exc}", "covered_origins": []}
    security_master = inspect_security_master(input_dir)
    overall = object_a_exact["status"] == "PASS" and historical["status"] == "PASS" and security_master["status"] == "PASS"
    return {
        "schema_version": "IIOS-B2-A02-EXACT-ADMISSION-0.1",
        "universe_id": "OU-M12-A02-CSI800-NONFIN-PIT-001",
        "epoch_id": "RE-M12-A02-CSI800-NONFIN-PIT-20261001",
        "input_dir": str(input_dir),
        "status": "PASS" if overall else "BLOCKED",
        "selection_permission": overall,
        "object_A_terminal_000906": object_a_exact,
        "object_A_historical_membership": historical,
        "object_B_pit_security_master": security_master,
        "required_origins": list(REQUIRED_ORIGINS),
        "prohibited_actions": [
            "DO_NOT_TREAT_DECLARED_SHA256_AS_LOCAL_BYTE_VERIFICATION",
            "DO_NOT_USE_CURRENT_CSI800_AS_HISTORICAL_PIT",
            "DO_NOT_USE_EFFECTIVE_DATES_AS_KNOWN_AT_WITHOUT_VINTAGE_PROOF",
            "DO_NOT_PARAMETERIZE_FM02_ACROSS_SECURITIES",
            "DO_NOT_PARAMETERIZE_FM03_ACROSS_SECURITIES",
            "DO_NOT_RUN_A02_MODEL_SELECTION",
        ],
        "next_transition": "A02_ADMISSION_PASS" if overall else "SUPPLY_EXACT_RAW_BYTES_AND_PROVENANCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = build_attempt(Path(args.input_dir).resolve())
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "A02_EXACT_ADMISSION_RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())