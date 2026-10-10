from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "workflows"
    / "iios_one_click_case_readiness.yml"
)


def _job_block(workflow: str, job_name: str) -> list[str]:
    lines = workflow.splitlines()
    start = lines.index(f"  {job_name}:")
    for end in range(start + 1, len(lines)):
        if re.match(r"^  [A-Za-z0-9_-]+:$", lines[end]):
            return lines[start:end]
    return lines[start:]


def test_contract_tests_are_not_skipped_on_manual_dispatch() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "workflow_dispatch:" in workflow

    contract_tests = _job_block(workflow, "contract-tests")
    # No job-level if: means this job runs for both declared workflow events.
    # Keep this explicit so GitHub does not show a misleading 0s skipped job
    # after a manual dispatch.
    assert not any(re.match(r"^    if:", line) for line in contract_tests)


def test_readiness_still_requires_explicit_manual_authorization() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    readiness = _job_block(workflow, "readiness")
    assert (
        "    if: ${{ github.event_name == 'workflow_dispatch' && inputs.authorize_read_only_preflight }}"
        in readiness
    )
    assert 'default: false' in workflow
    assert 'required: true' in workflow
