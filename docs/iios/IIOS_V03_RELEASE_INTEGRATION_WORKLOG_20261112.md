# IIOS v0.3 Release Integration Worklog — 2026-11-12

## Branch baseline

- Integration branch: `release/v03-integration-20261112`
- Created from canonical `main` at `2fd009b10bd4b13467ebdd8b2692eab62a772878`.
- B83 source: `feat/b83-durable-task-resume-20261108` (PR #588, Draft; latest audited branch compare 141 ahead / 0 behind, 21 paths).
- Deep-research source: `feat/b76-core-integrated-20261101` (PR #587, Draft validation-only, base is B73 proposal branch; compare to main 515 ahead / 0 behind, about 110 paths).
- Neither source branch is to be merged wholesale. Their historical commits and draft PRs remain intact.

## Verified source facts

1. B76/B80 Linux Local Pilot regression suite recorded 466 passed. The B80 combined workflow was cancelled due to its macOS job cancellation; it is not a macOS pass.
2. B81 exact code commit `7fb679835a71e25572dc6db701e24e6dddb59bdf` has 35/35 associated workflow runs successful, including hosted macOS 15 arm64 and 466 tests. This closes the hosted-runner image retirement issue, not operator Mac acceptance.
3. B79 production signer registry remains `NO_TRUSTED_SIGNERS_REGISTERED`. Real formal Evidence/PIT and Forecast admission are unavailable; keep this product explicitly `PILOT_NON_CANONICAL`.
4. Xinhecheng real-case gaps (physical tonnes/ASP/unit variable cost, Q4 assumptions, annual diluted shares, operator price) remain UNKNOWN/data dependencies. Do not weaken gates or invent inputs.
5. Real-company SOTP acceptance remains unproven; only claim code-tested / real-case-unverified unless a data-sufficient real case is actually completed.

## Integration seam

- B76's `local_investment_pilot_v01.py` contains the B42–B81 calculation/report path (about 9,728 lines).
- B83's version contains durable task integration and compact entry (about 6,367 lines), but omits B76-specific calculation/report functions.
- B83's `guided_task_resume_v01.run_guided_task()` deliberately delegates investment analysis to `local_investment_pilot_v01`. This is the intended seam: task persistence/orchestration must not duplicate calculation logic.
- B83 resume-driver pilot API references are largely present in B76 pilot; B76 lacks the B83-specific `_ask_operator_entry_zone` helper. B83 compact market/cutoff/price parsing and one-shot clipboard capture helpers are absent from B76.
- Both branches modify the pilot, Local Pilot workflow, Local Pilot tests and project state index. A blind file copy would lose functionality.

## Ordered execution

### I1 — Merge the pilot adapter
Use B76's research/calculation/report implementation as the calculation source of truth. Port B83's durable task imports, compact entry, one-shot clipboard path, resume CLI mode and operator profile hooks into it. Resolve the missing operator-entry-zone helper explicitly. Preserve Round A/B stage semantics and B76 report projections.

### I2 — Integrate task modules and launcher
Port B83 task workspace/session/resume/profile/quick-start modules and launcher only after I1's adapter contract is satisfied. Keep all private files outside Git.

### I3 — Reconcile workflow and tests
Combine B76 B42–B81 regression coverage with B83 durable-resume/clipboard/quick-start tests. CI must test the integrated tree, not separate branch heads. Include Ubuntu and hosted macOS 15, Replay and independent red-team.

### I4 — Release acceptance
Run one real EPS_MULTIPLE task end-to-end with Round A/B, interruption/Finder relaunch, raw response provenance, bundle integrity and Replay MATCH. SOTP is real-case accepted only if data suffices; otherwise document its real-case limitation. User's local Mac acceptance remains a required external gate.

## Current status

- I0 clean integration branch: CREATED.
- I1 pilot adapter merge: NOT STARTED.
- I2 task modules/launcher: NOT STARTED.
- I3 integrated validation: NOT STARTED.
- I4 operator Mac acceptance: NOT VERIFIED.

No changes have been made to canonical main. No PR has been merged.
