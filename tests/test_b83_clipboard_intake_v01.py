from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from iios_mvp.local_investment_pilot_v01 import (
    _capture_clipboard_response_once,
    _response_file_signature,
    _wait_for_response_file_change,
)


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



def test_clipboard_capture_replaces_only_the_exact_prior_response_during_repair(tmp_path, monkeypatch):
    target = tmp_path / "response.json"
    target.write_bytes(b'{"invalid":')
    expected = _response_file_signature(target)
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.platform", "darwin")
    with patch(
        "iios_mvp.local_investment_pilot_v01.subprocess.run",
        return_value=SimpleNamespace(stdout=b'{"corrected":true}'),
    ) as run:
        assert _capture_clipboard_response_once(
            target,
            expected_existing_signature=expected,
        ) is True
    run.assert_called_once()
    assert target.read_bytes() == b'{"corrected":true}'
    assert target.stat().st_mode & 0o777 == 0o600


def test_clipboard_repair_refuses_to_overwrite_if_target_changed_since_observation(tmp_path, monkeypatch):
    target = tmp_path / "response.json"
    target.write_bytes(b'{"user_saved_newer_version":true}')
    observed = (len(target.read_bytes()), target.stat().st_mtime_ns, "0" * 64)
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.platform", "darwin")
    with patch("iios_mvp.local_investment_pilot_v01.subprocess.run") as run:
        assert _capture_clipboard_response_once(
            target,
            expected_existing_signature=observed,
        ) is False
    run.assert_not_called()
    assert target.read_bytes() == b'{"user_saved_newer_version":true}'


def test_enter_during_repair_wait_captures_corrected_clipboard_once(tmp_path, monkeypatch):
    class FakeStdin:
        def isatty(self):
            return True

        def readline(self):
            return "\n"

    target = tmp_path / "response.json"
    target.write_bytes(b'{"invalid":')
    previous = _response_file_signature(target)
    fake_stdin = FakeStdin()
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.platform", "darwin")
    monkeypatch.setattr("iios_mvp.local_investment_pilot_v01.sys.stdin", fake_stdin)
    monkeypatch.setattr(
        "iios_mvp.local_investment_pilot_v01.select.select",
        lambda *_args, **_kwargs: ([fake_stdin], [], []),
    )
    with patch(
        "iios_mvp.local_investment_pilot_v01.subprocess.run",
        return_value=SimpleNamespace(stdout=b'{"corrected":true}'),
    ) as run:
        corrected_signature = _wait_for_response_file_change(
            target,
            previous_signature=previous,
            poll_interval=0,
            stable_seconds=0,
        )
    run.assert_called_once()
    assert target.read_bytes() == b'{"corrected":true}'
    assert corrected_signature == _response_file_signature(target)
    assert corrected_signature != previous
