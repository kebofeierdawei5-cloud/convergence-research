# B83-1 — Durable Task Workspace Foundation

**Date:** 2026-11-08  
**Baseline:** canonical `main@2fd009b10bd4b13467ebdd8b2692eab62a772878`  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Scope:** B83-1 persistence primitives plus B83-2 guided workflow integration; GitHub CI passed on code head `f55b1e90efdc8aad08fcec65b18e8b0660920e21`; macOS real-user acceptance remains open.

## Why this slice exists

The current guided Pilot has durable Round A/B response files and run receipts, but its process-local control flow cannot reopen an interrupted task. Before wiring the wizard, the task persistence contract must be independently deterministic and tamper-evident.

## Implemented foundation

- Stable task IDs under the existing private local-pilot root.
- A per-task directory with a machine-readable manifest and append-only JSONL transition journal.
- The journal is authoritative; the manifest is a derived snapshot checked for exact agreement.
- Hash-chained transition records detect modification, reordering and deletion.
- Accepted artifacts are immutable and recorded with SHA-256 plus byte size.
- Artifact paths reject traversal and symlinks; task directories reject symlinks.
- Atomic manifest snapshot replacement; journal append is flushed and fsynced before snapshot update.
- Exclusive per-task resume lock; an existing lock fails closed rather than being silently removed.
- Explicit stage/status contract and a deterministic next-stage hint.
- Formal Decision, execution and auto-execution flags remain false.

## Deliberate limitations of B83-1

Historical B83-1 status at the time this section was first written: the workflow was not yet wired. This was superseded by the B83-2 integration section below. POSIX/macOS stale-lock handling was subsequently replaced with a kernel advisory lock that is released on process exit; see B83-2.

## Required next implementation slice

1. Integrate task creation immediately after the operator confirms case/price/cutoff.
2. Persist exact prompt and response bytes at each phase boundary; only accepted/validated artifacts advance the stage.
3. Persist the frozen Round A payload and validated Round B payload before moving forward.
4. Persist operator-only portfolio/model inputs and the final completed input before running calculations.
5. Persist run ID and output artifact hashes after successful bundle creation.
6. Implement `--resume-task TASK_ID` as actual continuation, not status display:
   - Round A prompt ready / response pending: reopen the same prompt and response file, wait and validate.
   - Round A validated / Round B pending: load the frozen Round A payload and continue directly at Round B.
   - Round B response captured but not accepted: revalidate the immutable captured response; allow a new named attempt if the source changed.
   - Round B validated / operator context pending: skip both Web rounds and collect only missing operator-owned inputs.
   - Run created: verify receipt and hashes; do not rerun analysis unless explicit Replay is requested.
7. Add interruption tests at every boundary and end-to-end acceptance before claiming full recovery.

## Validation status

- Source implementation added.
- Targeted tests authored but not yet executed.
- No Python test suite, hosted CI, real-company workflow or user Mac acceptance has been run in this slice.
- This does not close B34 or B89.

## Safety invariants

- Raw responses and accepted artifacts are never overwritten in place.
- An invalid response never advances the stage.
- Recovery verifies the journal chain, manifest agreement and every indexed artifact hash before continuing.
- An interrupted/ambiguous/corrupt task blocks and asks for review; it never guesses a resume point.
- Research output remains `PILOT_NON_CANONICAL`.

## B83-2 — Guided phase persistence adapter (historical intermediate milestone; superseded below)

A separate guided_task_session_v01.py adapter now maps the existing guided workflow's semantic boundaries onto the durable workspace without importing or invoking investment calculations.

Implemented adapter operations:

- Persist exact Round A / Round B prompt bytes and the operator-facing response filename.
- Capture raw response bytes as separately named immutable attempts. A corrected response is a new attempt; the prior invalid response remains available for audit.
- Persist accepted Round A and Round B payloads only after the caller reports validation success.
- Persist operator-owned context separately from AI-authored research.
- Persist a run receipt only when its pilot_id matches the supplied run ID.
- Mark a task complete only after the caller supplies PILOT_BUNDLE_HASH_CHECK_PASS.
- Reopen verifies journal and artifact hashes, then returns an explicit resume_action plus the required artifacts. It never executes a continuation automatically.

Targeted adapter tests have been authored for interruption after Round A prompt, response attempts, Round A freeze, Round B response, operator context, run receipt, and artifact tampering. They have **not** been executed.

### Important non-completion boundary

At this intermediate commit the adapter was not yet wired into the live wizard. The following end-to-end integration section supersedes this status.

The next slice must wire each adapter call into the real wizard at the exact successful phase boundary, then implement --resume-task TASK_ID as a true branch into the pending phase. It must preserve the current prompt bytes, response file path, frozen Round A payload and validation behavior. It must also handle the existing response-repair loop without overwriting raw captured attempts. Only after that wiring and interruption tests can the feature be described as end-to-end resumable.

### Validation status update

- B83-1 persistence primitive: source authored.
- B83-2 guided phase adapter: source authored.
- B83-2 targeted tests: authored, not run.
- Existing run_guided_wizard integration: subsequently implemented in the next B83-2 milestone below.
- --resume-task: subsequently implemented in the next B83-2 milestone below.
- Python / pytest / hosted CI / real-company run / macOS acceptance: not run.
## B83-2 — End-to-end guided workflow wiring (historical pre-CI milestone; current validation follows below)

The durable runner is now wired into the existing local_investment_pilot_v01 entry point:

- A new task is created only after the operator confirms the company, symbol, cutoff, position and manually attested price.
- The task context freezes the original template payload and analysis prompt. Resume reconstructs task-local snapshots rather than trusting mutable files at their original paths.
- The existing guided workflow delegates Round A/B, operator-owned context, run creation and final bundle verification to guided_task_resume_v01.py.
- --resume-task TASK_ID reopens the task under the same --template-root and continues from the journal-derived resume_action.
- Round A accepted payload is persisted before Round B prompt generation. A resumed Round B therefore does not rerun Round A or regenerate its accepted result.
- Each stable raw response is captured as an immutable attempt. A correction saved while the process is offline is detected on resume and captured as a new attempt; prior attempts remain intact.
- The final Round B response is copied from its immutable accepted attempt into a task-local stable snapshot before run creation. The run input provenance and raw response hash are bound to that exact snapshot.
- Run IDs are deterministic per task. If the process exits after a complete run bundle is written but before the task journal records RUN_CREATED, resume verifies the existing bundle and reuses it only when input and raw-response bytes match. A partial or conflicting bundle fails closed.
- On POSIX/macOS, task exclusivity uses an advisory OS lock released automatically when a process exits or crashes. The lock marker file may remain; it is not itself a stale lock. Windows retains a conservative exclusive-create fallback.

### Operator usage

Start normally with the existing launcher / --wizard. The task ID is printed after confirmation. If the terminal closes or the process stops, rerun the same module with:

    python -m iios_mvp.local_investment_pilot_v01 --resume-task TASK_ID

If the original task used a non-default --template-root, supply that same root when resuming. The persisted output root is used unless an explicit non-default --output-root is supplied.

### Remaining validation boundary

- Source integration and resume entry point: implemented on this feature branch.
- Unit tests: authored in the B83-1/B83-2 test files but **not run**.
- No GitHub Actions result is claimed.
- No real company Round A/B interruption-resume run has been performed.
- No macOS launcher / clipboard / TextEdit acceptance has been performed.
- A process crash during a partially written run bundle intentionally blocks with a partial-bundle error; it does not delete or overwrite ambiguous output. This requires explicit operator review.
- This remains PILOT_NON_CANONICAL; it does not create a formal investment decision or authorize execution.
## Current B83-2 status — authoritative update (2026-11-08)

The historical intermediate status blocks above are retained as an audit trail. This section is the current status and supersedes earlier statements that integration or CI validation was pending.

### Implemented and integrated on this branch

- The normal --wizard path creates a task only after operator confirmation and delegates research phases to the durable runner.
- --resume-task TASK_ID reopens a task and resumes from the hash-verified journal-derived stage.
- Round A and Round B prompts, prompt projections, raw response attempts and accepted payloads are persisted independently.
- Round A is frozen before Round B; a restarted Round B reuses the accepted Round A payload and the exact persisted Round B prompt.
- Offline response corrections are captured as new immutable attempts rather than overwriting prior responses.
- The two operator-controlled input substeps (portfolio constraints and valuation-model context) are now journaled separately. An interruption after one input is captured can resume without asking for that input again.
- A completed run bundle is hash-verified and reused before calling analysis if the process stopped before journaling RUN_CREATED. Partial or conflicting run bundles fail closed.
- POSIX/macOS task locks are kernel advisory locks released after a process exits or crashes.

### Automated validation

- GitHub Actions commit: f55b1e90efdc8aad08fcec65b18e8b0660920e21.
- B83 Pilot workflow: **374 passed**; compileall, bash syntax checks and git diff --check passed.
- All 8 check runs attached to that PR head completed successfully.
- The added cross-instance tests exercise restart during Round A response wait, restart after Round A freeze while Round B is pending, and restart between operator portfolio and valuation input capture.
- CI runs on Ubuntu / Python 3.12. It does not replace macOS GUI/clipboard/TextEdit acceptance or a real-company user acceptance.

### Still open

- Real macOS `.command` launcher, `pbcopy`, ChatGPT browser and TextEdit save/reopen acceptance: **OPEN / NOT VERIFIED**.
- Full real-company task interrupted at each phase and resumed manually end to end: **NOT YET PERFORMED**.
- Canonical main integration: **NOT MERGED**. PR #588 remains Draft.
- B34 macOS acceptance and B89 full acceptance remain open.

### Operator recovery command

Use the same private template root used when the task was created:

    python -m iios_mvp.local_investment_pilot_v01 --resume-task TASK_ID

The task ID is printed after the initial operator confirmation. The research output remains PILOT_NON_CANONICAL; no formal decision or order execution is created.

## B83-3 — low-friction explicit clipboard intake

**Implementation commit:** `a1da61ede5d39a7962e222aee22b62e980f81047`

The guided response wait now supports a one-shot macOS clipboard capture. The operator copies the complete ChatGPT answer and presses Enter in the waiting IIOS terminal. Only then does IIOS invoke `pbpaste` once and write the captured UTF-8 bytes to the existing task response file. The existing response parser, validation, immutable attempt capture and durable resume flow remain the authority.

Security constraints:
- No clipboard polling, daemon, background monitor, browser integration or Accessibility permission.
- Clipboard content is never printed or logged.
- Capture is capped at 2 MiB and requires valid UTF-8.
- A non-empty response file is never overwritten; symlink targets are rejected.
- A private temporary file is created with mode 0600, flushed and fsynced before atomic replacement.
- If clipboard capture fails, the existing file-based workflow remains available.

This removes TextEdit and manual response-file saving from the normal macOS path, but does not remove the user's explicit copy action or manual ChatGPT send action.

### Validation boundary

This source change is committed to the B83 feature branch. It is not yet evidence of successful macOS acceptance. The capture helper still requires automated tests and a real Mac run covering clipboard permission behavior, empty/oversized/non-UTF-8 content, pre-existing response files, interruption and subsequent task resume. B34 macOS acceptance remains open.



## B83-4 — low-friction local quick start (2026-11-08)

**Implementation:** `iios_mvp/quick_start_v01.py`, `IIOS.command`, and the TextEdit-free explicit clipboard handoff.

- A single unfinished task resumes automatically; multiple unfinished tasks require one numbered choice; no unfinished task starts the existing new-research wizard.
- Corrupt, blocked, symlinked or unverifiable tasks fail closed. No task ID is exposed to normal usage.
- Normal macOS prompt handoff now opens ChatGPT without launching TextEdit. The copied answer is captured only after the user presses Enter once; no clipboard polling or browser automation.
- A local report is opened only after run-bundle hash verification and after its resolved path is confirmed under the private output root.
- Launcher does not request sudo, install dependencies, run a network updater or alter browser sessions.
- The GitHub contents API does not set the executable bit on `IIOS.command`; a one-time `chmod +x IIOS.command` is required after checkout.

## B83-5 — opt-in local operator profile (2026-11-09)

**Implementation:** `iios_mvp/operator_profile_v01.py`, integrated into the guided post-Round-B operator-input phase.

The profile exists only to reduce repeated manual entry. Its final schema is `IIOS-LOCAL-OPERATOR-PROFILE-0.2`.

### What is reusable

- Cross-company portfolio guardrails: constraint status, add-risk permission, risk budget and initial/target/maximum position percentages.
- The last selected primary valuation-model family, used only as the default suggestion in the next company's model-selection prompt.

### What deliberately remains company-specific

- Entry-price band: re-entered for every company, even when the general portfolio guardrails are reused.
- For EPS_MULTIPLE, whether the project/expansion value is already included in the baseline: re-confirmed for every company.
- The prior model-family choice is a preselection only; the operator confirms or changes it for every company.

### Storage and safety

- Local path: `~/.iios-private/local-pilot/profile/operator-defaults.json`.
- Profile save/update requires explicit opt-in; the save prompt defaults to no. Updating an existing profile also defaults to no.
- Private directories use POSIX mode 0700; profile/lock files use 0600. Writes are validated, size-limited, symlink-resistant, atomic and protected by a local process lock.
- Unknown fields, malformed schema, corrupted JSON, unsafe paths and invalid numeric ranges fail closed. The profile is not silently reset.
- Permissions are not encryption. The file is not committed to Git or sent by IIOS, but whole-home backup/synchronization may copy it. FileVault and backup/sync settings remain the user's responsibility.

### Current automated validation

- Latest code validation commit: `313c18fb2866754108fb5d8df05aa04d68536a5a`.
- Local Investment Pilot workflow: **394 passed**; compileall, launcher syntax, and diff checks passed.
- All 7 GitHub Actions workflow runs associated with that code commit completed successfully.
- CI is Ubuntu / Python 3.12. It does not constitute macOS Finder, actual clipboard-permission or end-to-end user acceptance.

### Remaining acceptance and repository state

- Real macOS double-click launcher, one-time executable permission, actual clipboard capture, ChatGPT handoff and task interruption/resume remain **OPEN / NOT VERIFIED**.
- Full real-company interruption/resume acceptance remains **NOT YET PERFORMED**.
- PR #588 remains Draft and unmerged; canonical `main` is unchanged.
- B34 macOS acceptance and B89 full acceptance remain open.
- B83-4/B83-5 change only local operator interaction and persistence. Research prompts, evidence admission, valuation calculations, return hurdle, decision gates and order-execution authority are unchanged.


## B83-6 — compact new-research entry and launcher checks (2026-11-09)

**Implementation commits:** `090d53371263c810440b54c887dfcdbd57ca1b4a`, `ded4750c30a323020bf142636de278eec031683c`, `ab49e2e6904f079bedc94c57c4caf6e6fc6dfb6a`, `ea9e090e91fc437e3041e75504bbc2c60d63f666`; launcher: `185caccc10ac52e1425d193001afd1920b65a516`.

### User input reduction

The new-research wizard now removes the separate market selector, cutoff-mode choice, price-observation-date question and price-time-mode question.

- Market is inferred from explicit A/H suffix/prefix or unambiguous code length. Invalid/ambiguous input fails with instructions instead of silently selecting a market.
- Blank cutoff uses the latest weekday close that is not in the future, based on Asia/Shanghai. A plain date means 15:30 Shanghai time; an exact ISO timestamp with timezone supports intraday or strict date-level cutoff.
- One price field accepts `19.74`, `19.74@YYYY-MM-DD`, or `19.74@YYYY-MM-DDTHH:MM:SS+08:00`.
- The default price observation date is chosen relative to the cutoff clock. If cutoff is before 15:00, the same-day close is not used.
- Price remains operator-attested and unverified against an exchange/market-data source; holiday calendars are not fetched.

### Launcher

- `umask 077`; checks project entry file; uses the project `.venv` if present or existing Python 3 otherwise.
- Requires Python 3.10+, isolates user-site packages with `PYTHONNOUSERSITE=1` and uses explicit project `PYTHONPATH`.
- A broken existing project venv fails with a clear message; no silent fallback to a different Python and no automatic package/network installation.

### Validation status

- First B83-6 local-pilot CI run at `185caccc10ac52e1425d193001afd1920b65a516`: **409 passed / 2 failed**. One was bare five-digit HK market inference; one acceptance fixture used the pre-B83-6 prompt order.
- Both issues were corrected in subsequent commits and new tests were added for Shanghai cutoff defaults, intraday price handling and launcher environment checks.
- No fresh CI result has yet been observed for the latest post-fix branch head. Therefore B83-6 is **implemented, but final CI verification is pending / not claimed**.
- CI runs Ubuntu/Python 3.12 and does not replace macOS Finder or actual clipboard acceptance.

B34 macOS acceptance and B89 full acceptance remain open. PR #588 remains Draft/unmerged; canonical `main` is unchanged.
