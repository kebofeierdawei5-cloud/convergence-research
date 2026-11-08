# B83-1 — Durable Task Workspace Foundation

**Date:** 2026-11-08  
**Baseline:** canonical `main@2fd009b10bd4b13467ebdd8b2692eab62a772878`  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Scope:** persistence primitives only; not yet an end-to-end resume claim.

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

This slice does **not** yet wire the task workspace into `run_guided_wizard`, persist Round A/B artifacts from the live workflow, or provide a user-facing `--resume-task` CLI continuation. Those are required before B83 can be called complete. A stale lock recovery policy also remains to be specified; do not delete a lock automatically based only on a PID.

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

## B83-2 — Guided phase persistence adapter (partial)

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

B83-2 is **not yet end-to-end wired** into run_guided_wizard or _main. There is no --resume-task user entry point yet, and the current wizard still runs its Round A/B loops in one process. The adapter is a persistence contract and test seam, not a claim that the existing CLI can resume today.

The next slice must wire each adapter call into the real wizard at the exact successful phase boundary, then implement --resume-task TASK_ID as a true branch into the pending phase. It must preserve the current prompt bytes, response file path, frozen Round A payload and validation behavior. It must also handle the existing response-repair loop without overwriting raw captured attempts. Only after that wiring and interruption tests can the feature be described as end-to-end resumable.

### Validation status update

- B83-1 persistence primitive: source authored.
- B83-2 guided phase adapter: source authored.
- B83-2 targeted tests: authored, not run.
- Existing run_guided_wizard integration: not done.
- --resume-task: not implemented.
- Python / pytest / hosted CI / real-company run / macOS acceptance: not run.