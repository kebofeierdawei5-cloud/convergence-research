# IIOS C7 — Full Lifecycle E2E v0.1

Date: 2026-10-06
Status: IMPLEMENTATION CANDIDATE — pending dedicated CI and canonical acceptance

## Objective

C7 proves the complete canonical operating loop using the existing production components. It adds no new investment rule.

Canonical lifecycle:

Decision Revision
→ Human Approval
→ Execution Receipt
→ Active Trigger
→ Trigger Event
→ Monitoring State
→ Evaluation Receipt
→ Validation
→ Replay
→ New Run
→ New Decision Revision
→ Machine Publication
→ Human Report

## Acceptance semantics

C7 must prove:

- historical Decision Revisions are append-only;
- Human Approval is bound to an exact Revision;
- Execution Receipt is bound to the exact approved Revision and remains downstream-only;
- Trigger Contract and Trigger Event remain bound to the Revision hash;
- Monitoring State changes do not mutate Decision Revision;
- Validation independently recomputes from persisted source artifacts;
- lifecycle replay reproduces persisted state;
- a changed Decision requires a new Run and a new Revision;
- Machine Publication and Human Report are projections, not authorities;
- the complete path can cross from r001 BUY to r002 REDUCE without overwriting r001.

## Boundary

C7 is orchestration / evidence-integrity validation only.

It does not:

- add new valuation or forecasting logic;
- add a new Decision precedence rule;
- add new MIE models;
- alter Trust / Quality semantics;
- modify Monitoring semantics;
- authorize execution;
- introduce scheduler / alerts;
- introduce automatic execution;
- produce portfolio optimization.

## Acceptance target

Dedicated C7 CI must prove the complete loop, the three key isolation boundaries, deterministic validation/replay, and projection-only Publication / Report behavior.

The separately tracked broader Investment Core / Risk Portfolio regressions remain independent and are not used as C7 acceptance evidence.
