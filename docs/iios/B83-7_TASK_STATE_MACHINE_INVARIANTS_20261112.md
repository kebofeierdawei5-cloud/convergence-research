# B83-7 — Durable task state-machine consistency

**Date:** 2026-11-12  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Status:** IMPLEMENTED / 418 TARGETED TESTS PASS / 6 OF 6 TRIGGERED WORKFLOWS PASS / MAC ACCEPTANCE OPEN

## Finding

The durable journal previously verified record hashes, sequence numbers and hash-chain linkage, but did not replay the stage-transition contract when reopening a task. The low-level record API also allowed terminal task statuses to be paired with non-terminal stages (and vice versa). Such records could leave the task status, current stage and resume action inconsistent.

## Change

- Introduce one explicit stage/status compatibility check:
  - `BLOCKED` stage iff `BLOCKED` task status;
  - `COMPLETED` stage iff `COMPLETED` task status;
  - non-terminal stages accept only `ACTIVE` or `INTERRUPTED`.
- Reject malformed stage/status types with controlled task-workspace errors.
- Replay and validate every journal transition on open, not only the hash chain:
  - first event must be `TASK_CREATED / ACTIVE`;
  - every event must carry one stable, syntactically valid Task ID;
  - only the next legal stage, a same-stage checkpoint/retry, or an explicit transition to `BLOCKED` is accepted;
  - no event may follow `BLOCKED` or `COMPLETED`.
- Check that the journal Task ID matches the directory's Task ID before deriving or repairing the manifest.
- Apply the same stage/status rule before writing new records, preventing invalid artifacts or journal events from being created through the low-level API.

## Regression tests added

- Reject mismatched `TASK_CREATED / COMPLETED`, non-terminal / `BLOCKED`, `COMPLETED / ACTIVE`, and `BLOCKED / ACTIVE` combinations.
- Verify a rejected write leaves the journal revision unchanged.
- Recompute a modified event's hash after introducing an illegal forward transition, then verify journal replay still rejects the semantic transition. This proves the new guard is independent of ordinary hash-mismatch detection.

## Boundaries

- No research prompt, evidence admission, PIT, earnings forecast, valuation arithmetic, 15% return hurdle, risk gate, canonical decision, or execution authority is changed.
- The hash chain remains tamper-evident, not a cryptographic signature against an attacker with write access to the local files.
- Exact PR-head CI: Local Investment Pilot workflow #718 passed **418 tests**; all **6/6 triggered workflows** completed successfully (Local Investment Pilot, Investment Core CI, State Hygiene, C0 Governance, Post-B04 Independent Red-team, and M1.2 FM01 Source Admission). The CI checkout asserted the exact PR head. This is Ubuntu CI, not macOS acceptance.
- macOS Finder, clipboard, real-company interruption/resume and report-hash acceptance remain unverified. Do not merge on the basis of this code change alone.
