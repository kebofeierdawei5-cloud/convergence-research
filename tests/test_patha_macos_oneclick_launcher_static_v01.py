from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "IIOS_PathA_Scenario_OneClick" / "双击运行_IIOS情景分析.command"


def test_macos_patha_launcher_has_valid_bash_syntax() -> None:
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_macos_patha_launcher_keeps_private_output_root_fail_closed() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'OUTPUT_ROOT="$PRIVATE_BASE/scenario-analysis"' in text
    assert 'mkdir -m 700 -p "$OUTPUT_ROOT"' in text
    assert 'buttons {"取消并停止", "收紧权限"}' in text
    assert '[[ "$permission_choice" == "收紧权限" ]]' in text
    assert 'chmod 700 "$OUTPUT_ROOT"' in text
    # Initialization plus braced expansion avoids an unbound code? parameter.
    assert 'code=0' in text
    assert '"${code}"' in text
    assert "${code?}" not in text


def test_macos_patha_launcher_pins_and_verifies_module_blobs() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'PINNED_COMMIT="4ccb8cf89084d7299dfa8d0774cce97009eb5b54"' in text
    assert 'SCENARIO_BLOB_SHA="0bcc38ad953dc0a8ff60fcef6abd008a5507595c"' in text
    assert 'PRICE_BLOB_SHA="b3aa8afaa6e6b753dc9192f736f9ddec58e52672"' in text
    assert 'actual="$(blob_sha1 "$temp")"' in text
    assert '[[ "$actual" != "$expected" ]]' in text
