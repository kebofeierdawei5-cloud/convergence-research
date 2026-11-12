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


## I1 — pilot adapter and B76/B83 source integration (2026-11-12)

**Code integration: COMPLETE on candidate branch. Exact-head validation: RUNNING.**

- Integrated B76's full research/calculation/report pilot implementation as the base and ported B83's guided market/cutoff/price parsing, one-shot clipboard intake, current-company entry-zone prompt, compact guided wizard and `--resume-task` CLI.
- Added B83 durable task workspace/session/resume, operator profile, quick-start modules, launcher and their four dedicated test files.
- Ported the B76 net changed file set (115 paths excluding the four overlapping files handled separately), including B42–B81 research modules, schemas, examples, docs and regression suites.
- Reconciled the overlapping Local Pilot test file: retained B76 tests, added 13 B83-only tests, and used B83 versions of the three overlapping guided-entry tests. The combined file contains 298 uniquely named test functions after duplicate-definition cleanup.
- Reconciled the Local Pilot workflow: retains B76 Ubuntu + macOS 15 jobs and adds B83 module/test path triggers, launcher syntax and B83 test files.
- Reconciled `docs/PROJECT_STATE_INDEX.md`: canonical authority marker and canonical snapshot date are preserved; release integration is explicitly recorded as non-canonical proposal state.
- Set `IIOS.command` Git mode to `100755` using the Git tree API; verified exact candidate tree mode.

### First exact-head validation and corrections

The initial PR #589 head `1cd8d7734afda16e578b861dfbe97fe703d2a073` exposed four integration defects:
1. State index canonical marker/date were overwritten, failing C0, State Hygiene and Investment Core authority checks.
2. Test merge left a pytest parametrization decorator detached from its intended function, causing collection failure.
3. The Contents API stored `IIOS.command` as mode `100644`, failing the hosted macOS executable check.
4. Local Pilot Ubuntu/macOS suites stopped at test collection / launcher validation, so no investment-suite pass was obtained on that head.

Corrections were applied:
- Canonical state header restored, with release branch recorded separately as non-canonical.
- Combined test file rebuilt from the two source versions with decorators preserved.
- `IIOS.command` changed to mode `100755`.
- Corrected exact candidate head: `d8f9dbcf3161e8524c046358a32bd37b60a1f635`.

At the corrected head, the PR-triggered workflow matrix was observed as 35 workflows: 1 completed success, 0 failures, 34 queued/in progress at the last check. This is a live intermediate snapshot, not final validation.

### Still open

- Exact-head 307-test combined Local Pilot suite + dedicated task/clipboard tests on Ubuntu and macOS 15.
- Full 35-workflow matrix and red-team completion.
- Real EPS_MULTIPLE run / Replay, SOTP if source data allows.
- Operator's own Mac Finder / clipboard / interruption / resume acceptance.
- Formal Evidence/PIT and Forecast admission remain unavailable while production signer registry is empty.


## I1 — integrated exact-head acceptance (2026-11-12)

<status>PASS — hosted CI / operator Mac still open</status>

- Exact code-tested integration HEAD: `f62d9beeeac01d5661244ac256c36233fab17c88`.
- **35/35** PR-triggered GitHub Actions workflows succeeded on that exact code-tested HEAD; zero failures, zero cancellations.
- Local Investment Pilot + B76 arithmetic / Xinhecheng readiness / Replay + B83 task/clipboard/quick-start suite: **538 passed on Ubuntu** (5.57s) and **538 passed on hosted macOS 15** (19.78s).
- The same exact-head matrix includes Investment Core CI, C0 Governance Hygiene, State Hygiene, Signed Evidence Admission Gate, TR-03 Replay, Post-B04 Independent Red-team, B2-F fresh independent red-team, and the B76/B83 Local Investment Pilot workflow.
- Hosted macOS validates the CI runner and launcher syntax/mode; it does not substitute for the user's own Finder launch, clipboard handoff, interruption/relaunch and private bundle Replay.
- The tested code head was followed only by this worklog documentation update; no code or workflow changes were made after `f62d9be`.

### I1 exit status

- B76 research/calculation/report source and B83 durable local task workflow are integrated in one tree.
- Ubuntu + hosted macOS Local Pilot suites are green on the same exact code head.
- Full triggered workflow and red-team matrix is green on the same exact code head.
- I1 code integration and hosted validation: **CLOSED**.
- I4 real operator Mac acceptance: **OPEN**.
- Real EPS_MULTIPLE user-run E2E and deterministic Replay: **OPEN**.
- Real-company SOTP E2E: **UNVERIFIED / conditional on complete segment data**.
- Formal Evidence/PIT and Forecast Admission: **NOT AVAILABLE** while production signer registry is empty.
- Release merge: **NOT AUTHORIZED** until operator acceptance and final PR diff/base review.
