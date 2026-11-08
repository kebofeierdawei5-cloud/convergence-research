# B83-1 — Durable Task Workspace Foundation

**Date:** 2026-11-08  
**Baseline:** canonical `main@2fd009b10bd4b13467ebdd8b2692eab62a772878`  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Scope:** B83-1 persistence primitives plus B83-2 guided workflow integration; source implementation is complete on this feature branch, validation remains pending.

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
## B83-2 — End-to-end guided workflow wiring (source complete; validation pending)

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