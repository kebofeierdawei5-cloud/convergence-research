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
