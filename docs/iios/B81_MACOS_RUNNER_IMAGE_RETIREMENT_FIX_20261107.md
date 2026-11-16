# B81 — macOS hosted-runner image retirement and Local Pilot acceptance repair

Date: 2026-11-07  
Branch: `feat/b76-core-integrated-20261101`  
State: IMPLEMENTED AND CI-VERIFIED on the Draft proposal branch; not canonical main.

## Root cause

The Local Investment Pilot workflow used `runs-on: macos-14`. GitHub's 2026-10-01 retirement notice states that the macOS 14 runner image, including the `macos-14` label, would be retired on **2026-11-02**. It directs users to move Apple Silicon workflows to `macos-15` or `macos-latest`.

The original Local Investment Pilot workflow run #637 showed the corresponding pre-runner failure signature:

- Attempt 1 job `macos-acceptance`: created 2026-11-07 14:22:16Z, cancelled 14:22:19Z.
- Attempt 2 after explicit rerun: created 2026-11-07 14:37:41Z, cancelled 14:37:42Z.
- Both attempts had `runner_id=0`, empty `runner_name`, and `steps=[]`.
- The paired Ubuntu `local-pilot` job passed in both attempts.
- The workflow had no `concurrency` block or `cancel-in-progress` rule.

This is a runner-image lifecycle/configuration defect, not a failure in the IIOS Python code, local GUI handoff, or Replay calculation. The job never reached checkout or application execution.

## Change

Commit: `7fb679835a71e25572dc6db701e24e6dddb59bdf`

In `.github/workflows/iios_local_investment_pilot_v01.yml`:

1. Changed only the macOS job runner from retired `macos-14` to supported `macos-15`, preserving the Apple Silicon arm64 runner family.
2. Added an explicit environment diagnostic step recording `sw_vers`, `uname -m`, and `hw.optional.arm64` before Python setup. Future failures can be classified by actual OS and architecture rather than inferred from the label.

No investment calculation, local acceptance, source admission, Forecast, Valuation, Decision, or execution code changed.

## Exact-head verification

**PR workflow run #643**, exact code commit `7fb679835a71e25572dc6db701e24e6dddb59bdf`:

- Local Investment Pilot macOS job: **success**.
  - Actual runner: **macOS 15.8.2**
  - Architecture: **arm64**
  - `arm64_capable=1`
  - Double-click launcher executable checks passed.
  - Launcher and updater shell syntax checks passed.
  - Python package compilation passed.
  - B76 arithmetic / real-case readiness / Local Pilot / Replay suite: **466 passed in 6.72s**.
  - `git diff --check` passed.
- Local Investment Pilot Linux job: **success**, **466 passed in 2.89s**.
- All related PR workflows: **35/35 success, 0 failure, 0 cancelled**.

This closes the recurring GitHub-hosted macOS CI cancellation. It does not close the separate operator-desktop acceptance: GitHub's macOS runner is headless and does not prove the user's own Finder double-click, browser/TextEdit interaction, clipboard behavior, saved live research response, or a real operator-run two-round Replay. That remains **OPEN / NOT VERIFIED** until performed on the user's Mac.

## Governance boundary

- PR #587 remains Open + Draft + Unmerged, targeting the B73 proposal branch.
- No changes were merged to canonical `main`.
- No test fixture or hosted-runner pass creates formal Evidence/PIT, Forecast, Valuation, Decision, or execution authority.
- Local IIOS remains `PILOT_NON_CANONICAL`; the Replay acceptance remains a reproducibility check, not an investment-thesis approval.
