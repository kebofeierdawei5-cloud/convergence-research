# DR-02 — Persistence + CLI Integration v0.1

Date: 2026-10-05
Status: ACCEPTED / CANONICAL

## Objective

Integrate the canonical DR-01 lifecycle contract into the persistent run store and CLI.

Production flow:

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

## Store boundary

store.py becomes the canonical persistence adapter for:
- Decision Revision;
- Human Approval;
- Current Projection;
- revision index.

The older v0.1.1 artifacts are not the authority for canonical v0.3 lifecycle state.

## Invariants

- revision files are immutable;
- revision index advances only through write_decision_revision;
- revision allocation is contiguous and fail-closed;
- approval is bound to exact decision revision and snapshot;
- rejected approvals never replace current;
- approved revisions advance current monotonically;
- current projection is validated and hash-protected;
- lifecycle replay reconstructs current from revision history + approvals;
- snapshot replay remains separately hash-verified;
- CLI never enables auto-execution.

## CLI

The canonical CLI lifecycle is:
- run: persist snapshot + revision;
- approve: persist human approval + update current when approved;
- replay: replay the frozen snapshot;
- lifecycle-replay: reconstruct and audit the decision lifecycle.

## Out of scope

- Decision Precedence changes;
- new risk/portfolio models;
- Trigger/Monitoring semantics beyond existing persisted artifacts;
- Machine Publication;
- Human Report;
- P3/P4/MIE.

## Acceptance

Canonical implementation is merged in PR #87, merge commit a4e493cc0c7f45647a02dd587f89fb7d98ee22e2.

Accepted production behavior:
- store.py delegates revision / approval / current projection semantics to DR-01 canonical contract;
- revision index is advanced by write_decision_revision, not by CLI;
- immutable canonical revision artifacts are persisted;
- approval artifacts are immutable and exact-snapshot/revision bound;
- rejected or older approvals do not replace current;
- current projection is hash-protected and monotonic;
- lifecycle replay verifies every historical revision against its snapshot;
- CLI exposes lifecycle-replay.

The available GitHub workflow connector did not expose a runtime result for PR #87 or the merge commit. Therefore CI telemetry is recorded as UNOBSERVED rather than claimed as PASS.

Static canonical-main verification after merge confirmed all DR-02 production surfaces are present and the scope contains no Decision Precedence, valuation, forecast, P3/P4 or MIE change.

**Canonical acceptance decision: DR-02 = MERGED / IMPLEMENTATION COMPLETE; CI telemetry = UNOBSERVED.**
