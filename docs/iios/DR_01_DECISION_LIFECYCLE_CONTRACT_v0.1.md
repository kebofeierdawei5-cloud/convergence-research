# DR-01 — Decision Revision / Human Approval Lifecycle Contract v0.1

Date: 2026-10-05
Status: ACCEPTED / CANONICAL

## Objective

Freeze the canonical lifecycle semantics for AI decision revisions, human approval binding, and current projection before integrating them into persistence.

## Core rules

1. Every decision revision is immutable and identified by decision_series_id + revision.
2. The revision binds the exact snapshot hash and AI action.
3. Human approval binds the exact decision revision hash and snapshot hash.
4. An approval for one revision cannot authorize another revision.
5. Current projection is monotonic by revision number.
6. Rejected or older revisions cannot replace the current approved projection.
7. Human approval never changes the AI action itself.
8. auto_execution is always false.
9. A revision lifecycle contract has no Decision Precedence or valuation semantics.

## Boundary

This batch is the lifecycle contract only. Storage/CLI integration is intentionally the next batch so that immutable semantics are frozen before persistence behavior is changed.

## Acceptance

DR-01 acceptance evidence:
- independent execution of the exact canonical module/test logic: 8 passed;
- compileall: PASS;
- revision schema JSON validation: PASS;
- approval and current-projection schema definitions are covered by regression tests;
- conflicting same-revision approval is rejected;
- rejected/older revisions cannot replace current projection.

GitHub Actions workflow: .github/workflows/iios_dr_01.yml.
The available GitHub workflow connector did not expose a run for the relevant PR/merge commits during this session, so runtime telemetry is recorded as UNOBSERVED, not misrepresented as PASS.

Canonical acceptance decision: DR-01 = PASS / MERGED, with CI telemetry limitation explicitly recorded.