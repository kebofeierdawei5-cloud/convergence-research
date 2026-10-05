from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research.a02.a02_exact_admission import (
    EXPECTED_000906_SHA256,
    EXPECTED_000906_SIZE,
    build_attempt,
    verify_exact_file,
)


class A02AdmissionTests(unittest.TestCase):
    def test_missing_terminal_bytes_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = build_attempt(Path(directory))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["selection_permission"], False)
        self.assertEqual(result["object_A_terminal_000906"]["reason"], "EXACT_000906_BYTES_MISSING")

    def test_wrong_hash_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "000906cons.xls"
            path.write_bytes(b"wrong-test-only")
            result = verify_exact_file(path, EXPECTED_000906_SIZE, EXPECTED_000906_SHA256)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["sha256_match"])

    def test_generic_exact_file_verifier_can_pass_on_test_fixture_only(self):
        payload = b"synthetic-test-fixture-do-not-use-as-A02-data"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.bin"
            path.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            result = verify_exact_file(path, len(payload), digest)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["exact_bytes"])

    def test_cli_emits_blocked_result_without_raw_bytes(self):
        with tempfile.TemporaryDirectory() as input_dir, tempfile.TemporaryDirectory() as output_dir:
            completed = subprocess.run(
                [sys.executable, "-m", "research.a02.a02_exact_admission", "--input-dir", input_dir, "--out", output_dir],
                check=True, capture_output=True, text=True,
            )
            result = json.loads(Path(output_dir, "A02_EXACT_ADMISSION_RESULT.json").read_text(encoding="utf-8"))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["selection_permission"])


if __name__ == "__main__":
    unittest.main()