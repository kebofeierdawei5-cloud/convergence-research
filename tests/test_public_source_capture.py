from __future__ import annotations

import hashlib
from pathlib import Path

from tools.public_source_capture import capture


def test_capture_hashes_exact_local_fixture_bytes(monkeypatch, tmp_path: Path):
    body = b"iios-exact-bytes\x00\x01"

    def fake_run(command, check, capture_output, text):
        output_index = command.index("--output") + 1
        Path(command[output_index]).write_bytes(body)

        class Result:
            returncode = 0
            stdout = "200"
            stderr = ""

        return Result()

    monkeypatch.setattr("tools.public_source_capture.subprocess.run", fake_run)
    destination = tmp_path / "raw.bin"
    status, sha = capture("https://example.invalid/raw", destination)

    assert status == 200
    assert destination.read_bytes() == body
    assert sha == hashlib.sha256(body).hexdigest()
