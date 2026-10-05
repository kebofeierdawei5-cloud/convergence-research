# DR-02 Acceptance — Persistence + CLI Integration

Date: 2026-10-05
State classification: **CANONICAL**

## Acceptance decision

**DR-02 = MERGED / IMPLEMENTATION COMPLETE**

Canonical merge:
- PR #87;
- merge commit: a4e493cc0c7f45647a02dd587f89fb7d98ee22e2.

## Accepted production lifecycle

    run
      ↓
    immutable snapshot
      ↓
    canonical Decision Revision
      ↓
    Human Approval artifact
      ↓
    Current Projection
      ↓
    Lifecycle Replay / Audit

Accepted invariants:
- revision artifact is immutable and bound to the exact snapshot hash;
- revision index is centrally advanced by the persistence layer;
- approval artifact is immutable and bound to exact revision + snapshot;
- rejected or older approvals do not replace current;
- approved revisions advance current monotonically;
- current projection is hash-protected;
- lifecycle replay checks every revision against its persisted snapshot;
- CLI supports lifecycle-replay;
- auto execution remains impossible through this lifecycle layer.

## CI / verification evidence

The dedicated workflow exists at .github/workflows/iios_dr_02.yml.
The available GitHub workflow connector did not expose a runtime result for PR #87 or merge commit a4e493cc0c7f45647a02dd587f89fb7d98ee22e2.
Therefore:
- canonical implementation = MERGED;
- post-merge structural verification = PASS;
- workflow telemetry = UNOBSERVED.

No claim is made that an unobserved workflow run passed.

## Boundary

DR-02 does not alter Decision Precedence, valuation, forecast, Risk / Portfolio semantics, P3/P4/MIE, or Trigger/Monitoring semantics.

Next product boundary:
**Trigger / Monitoring / Validation Productization**.