from __future__ import annotations

import argparse
import json
from pathlib import Path

from .company_evidence import validate_company_evidence_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a B2 supplementary evidence manifest against a private raw evidence vault."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--raw-root", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = validate_company_evidence_manifest(
        manifest,
        raw_root=args.raw_root,
        require_raw_verification=True,
    )
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, ensure_ascii=False, indent=2))
        return 2

    print(
        json.dumps(
            {
                "status": "PASS",
                "case_id": manifest["case_id"],
                "evidence_ids": [x["evidence_id"] for x in manifest["evidence"]],
                "raw_root": str(args.raw_root),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
