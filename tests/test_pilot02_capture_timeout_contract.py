from pathlib import Path


def test_pilot02_external_source_capture_is_time_bounded_and_fail_closed():
    repo_root = Path(__file__).resolve().parents[1]
    workflow = (repo_root / ".github" / "workflows" / "iios_pilot02_xinhecheng.yml").read_text(
        encoding="utf-8"
    )
    marker = "- name: Capture exact primary evidence and latest tradable price"
    assert marker in workflow
    capture_step = workflow.split(marker, 1)[1].split("\n      - name:", 1)[0]
    assert "timeout-minutes: 4" in capture_step
    assert "set -euo pipefail" in capture_step

    curl_lines = [line.strip() for line in capture_step.splitlines() if "curl -L --fail" in line]
    assert len(curl_lines) == 3, "expected bounded curl for H1 PDF, historical price, and trading calendar"
    for line in curl_lines:
        assert "--connect-timeout 8" in line
        assert "--max-time 25" in line
        assert "--retry 1" in line
        assert "--retry-delay 2" in line
