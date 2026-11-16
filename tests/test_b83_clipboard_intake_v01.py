from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from iios_mvp.local_investment_pilot_v01 import _capture_clipboard_response_once


def test_clipboard_capture_is_one_shot_and_writes_private_response(tmp_path, monkeypatch):
    target = tmp_path / "response.json"
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.platform", "darwin")
    with patch("iios_mvp.local_investment_pilot_v01.subprocess.run",
               return_value=SimpleNamespace(stdout=b'{"status":"ok"}')) as run:
        assert _capture_clipboard_response_once(target) is True
    run.assert_called_once()
    assert run.call_args.args[0] == ["pbpaste"]
    assert target.read_bytes() == b'{"status":"ok"}'
    assert target.stat().st_mode & 0o777 == 0o600


def test_clipboard_capture_does_not_overwrite_existing_response(tmp_path, monkeypatch):
    target = tmp_path / "response.json"
    target.write_text('{"original":true}', encoding="utf-8")
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.platform", "darwin")
    with patch("iios_mvp.local_investment_pilot_v01.subprocess.run") as run:
        assert _capture_clipboard_response_once(target) is True
    run.assert_not_called()
    assert target.read_text(encoding="utf-8") == '{"original":true}'


def test_clipboard_capture_rejects_empty_content(tmp_path, monkeypatch):
    target = tmp_path / "response.json"
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.platform", "darwin")
    with patch("iios_mvp.local_investment_pilot_v01.subprocess.run",
               return_value=SimpleNamespace(stdout=b"  \n")):
        assert _capture_clipboard_response_once(target) is False
    assert not target.exists()


def test_clipboard_capture_rejects_oversized_content(tmp_path, monkeypatch):
    target = tmp_path / "response.json"
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.platform", "darwin")
    with patch("iios_mvp.local_investment_pilot_v01.subprocess.run",
               return_value=SimpleNamespace(stdout=b"x" * (2 * 1024 * 1024 + 1))):
        assert _capture_clipboard_response_once(target) is False
    assert not target.exists()
