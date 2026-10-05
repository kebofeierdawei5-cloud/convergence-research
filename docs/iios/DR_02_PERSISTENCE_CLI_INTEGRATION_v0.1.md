# DR-02 — Persistence + CLI Integration v0.1

Date: 2026-10-05
Status: IMPLEMENTATION TARGET

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

DR-02 is accepted only when dedicated persistence/CLI regressions and replay tests pass, canonical v0.3 behavior remains intact, and no historical lifecycle artifact becomes current authority.
