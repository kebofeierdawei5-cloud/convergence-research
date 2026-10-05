from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.public_source_capture import capture


def test_capture_hashes_exact_local_http_bytes(monkeypatch, tmp_path: Path):
    body = b"iios-exact-bytes\x00\x01"

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _size):
            nonlocal body
            chunk, body = body, b""
            return chunk

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://example.invalid/raw"
        assert timeout == 90
        return FakeResponse()

    monkeypatch.setattr("tools.public_source_capture.urlopen", fake_urlopen)
    destination = tmp_path / "raw.bin"
    status, sha = capture("https://example.invalid/raw", destination)

    assert status == 200
    assert destination.read_bytes() == b"iios-exact-bytes\x00\x01"
    assert sha == hashlib.sha256(destination.read_bytes()).hexdigest()
