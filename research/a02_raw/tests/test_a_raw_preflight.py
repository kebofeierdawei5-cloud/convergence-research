import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from a_raw_preflight import run

EXPECTED_SHA = "f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984"

def manifest(states):
    return {
        "schema_version": "IIOS-A02-DATA-01-DELIVERY-MANIFEST-0.1",
        "universe_id": "OU-M12-A02-CSI800-NONFIN-PIT-001",
        "required_membership_states": [
            "2023-06", "2023-12", "2024-06", "2024-12",
            "2025-06", "2025-12", "2026-06"
        ],
        "a_membership_states": states,
    }

class A02ARawPreflightTests(unittest.TestCase):
    def test_manifest_only_never_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "A_CSI800_RAW").mkdir()
            (root / "DELIVERY_MANIFEST.json").write_text(json.dumps(manifest([])), encoding="utf-8")
            rc = run(root, strict=True)
            self.assertEqual(rc, 4)
            report = json.loads((root / "A02_DATA01_A_INDEPENDENT_RAW_PREFLIGHT.json").read_text())
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("A terminal 000906cons.xls bytes are absent", report["findings"])

    def test_wrong_terminal_bytes_block(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = root / "A_CSI800_RAW" / "official" / "000906cons.xls"
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b"not-the-real-file")
            (root / "DELIVERY_MANIFEST.json").write_text(json.dumps(manifest([])), encoding="utf-8")
            self.assertEqual(run(root, strict=True), 4)

    def test_state_without_raw_bytes_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "A_CSI800_RAW").mkdir()
            states = [{
                "state_id": "2023-06",
                "raw_path": "A_CSI800_RAW/rebalance/2023-06.xls",
                "raw_sha256": EXPECTED_SHA,
                "source_ref": "TEST",
                "publication_basis": "TEST",
                "effective_date": "2023-06-01",
                "known_at_basis": "TEST",
            }]
            (root / "DELIVERY_MANIFEST.json").write_text(json.dumps(manifest(states)), encoding="utf-8")
            self.assertEqual(run(root, strict=True), 4)

if __name__ == "__main__":
    unittest.main()
