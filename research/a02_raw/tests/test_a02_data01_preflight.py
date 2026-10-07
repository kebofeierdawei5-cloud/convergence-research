import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from a02_evidence_delivery import (
    EXPECTED_000906_SHA256,
    EXPECTED_000906_SIZE,
    run,
)


class A02Data01PreflightTests(unittest.TestCase):
    def test_empty_delivery_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "DELIVERY_MANIFEST.json").write_text(
                json.dumps({
                    "a_membership_states": [],
                    "b_domain_records": [],
                }),
                encoding="utf-8",
            )
            self.assertEqual(run(root, strict=True), 4)
            result = json.loads((root / "A02_DATA01_INDEPENDENT_RAW_PREFLIGHT.json").read_text())
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["admission_status"], "NOT_ADMISSION")

    def test_wrong_terminal_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "A_CSI800_RAW" / "official"
            d.mkdir(parents=True)
            (root / "DELIVERY_MANIFEST.json").write_text(
                json.dumps({"a_membership_states": [], "b_domain_records": []}),
                encoding="utf-8",
            )
            (d / "000906cons.xls").write_bytes(b"not-the-target")
            self.assertEqual(run(root, strict=True), 4)
            result = json.loads((root / "A02_DATA01_INDEPENDENT_RAW_PREFLIGHT.json").read_text())
            self.assertEqual(result["terminal_a"]["status"], "BLOCKED")
            self.assertNotEqual(result["terminal_a"]["candidates"][0]["sha256"], EXPECTED_000906_SHA256)

    def test_target_constants_are_frozen(self):
        self.assertEqual(EXPECTED_000906_SIZE, 169984)
        self.assertEqual(
            EXPECTED_000906_SHA256,
            "f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984",
        )


if __name__ == "__main__":
    unittest.main()
