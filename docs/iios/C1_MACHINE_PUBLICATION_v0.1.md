# C1 — Machine Publication v0.1

Date: 2026-10-06
Status: ACCEPTED / CANONICAL
Scope: read-only machine publication of a canonical Decision Revision

## Objective

Create a stable machine-readable projection of a persisted IIOS Decision Revision that can be consumed without parsing Markdown or depending on internal storage layout.

## Product boundary

Canonical decision state remains authoritative.

The publication layer is a projection:

```
Snapshot + Decision Revision
        +
Human Approval (when present)
        +
Current Projection
        +
bound Trigger / Monitoring / Validation references
        ↓
Machine Publication
```

Publication does not:
- create or amend a Decision;
- approve or reject a Decision;
- change Decision Precedence;
- trigger Monitoring;
- validate or reinterpret investment economics;
- place orders or execute capital.

## Publication identity and immutability

Each publication is content-addressed.

The publication hash covers:
- publication version;
- publication timestamp;
- Decision Revision reference;
- case metadata;
- AI decision payload;
- human approval state;
- current projection state;
- lifecycle references;
- integrity hashes.

The publication identifier is derived from the publication hash.

The persisted filename is the full publication hash:

`<publication_hash>.publication.json`

Re-publishing identical content is idempotent. Any content change creates a different immutable publication. Existing publication bytes are never overwritten.

## Decision / Human separation

The publication exposes:
- `ai_decision`: the Decision result produced by the canonical engine;
- `human_approval`: explicit approval/rejection/pending status bound to the exact Decision Revision and Snapshot;
- `current_projection`: whether the published revision is current, superseded, not current, or has no current projection.

Human approval is therefore evidence about the human decision boundary, not a mutation of the AI proposal.

## Lifecycle references

The publication may reference:
- Trigger Contracts bound to the exact Decision Revision;
- Monitoring State bound to those Trigger Contracts;
- the latest persisted Validation Record for each Trigger.

References are derived from persisted records and validated before inclusion. Missing lifecycle records are represented by empty lists, not fabricated placeholders.

## Provenance / integrity

The publication records:
- Snapshot hash;
- Decision Revision hash;
- Approval hash when present;
- Trigger hashes;
- Monitoring State hashes;
- Validation hashes;
- engine and contract versions.

This allows an external consumer to identify exactly which canonical Decision Revision was published without gaining write authority over that state.

## Fail-closed rules

Publication must fail when:
- the Decision Revision is missing or malformed;
- the bound Snapshot fails its integrity check;
- the Decision Revision hash or snapshot binding is invalid;
- an existing Human Approval fails its lifecycle validation;
- a persisted Trigger / Monitoring / Validation record included in the projection is invalid;
- source records are internally inconsistent.

Publication does not synthesize a missing approval or lifecycle record.

## CLI

```bash
python -m iios_mvp.cli publish <decision-id>   --published-at <ISO-8601-timestamp>   --out runs
```

The command emits the publication path, publication identity, decision revision and currentness. It does not mutate the Decision Revision.

## Acceptance

C1 PASS requires:
1. dedicated C1 CI passes;
2. schema validates the publication object;
3. pending and human-approved revisions are represented correctly;
4. Trigger / Monitoring / Validation references are correctly bound;
5. publication is content-addressed and immutable;
6. source tampering fails closed;
7. publication remains a read-only projection;
8. CLI exposes the machine publication command;
9. no Decision Kernel / Trust / Quality / Valuation / Forecast / MIE / Risk / Portfolio semantics change.

## Explicitly out of scope

- Human-readable investor report;
- Report Quality Gate;
- scheduler;
- alerts/notifications;
- automatic execution/order placement;
- new P3/P4 market-model families;
- Expectation Gap decision integration;
- Positioning / Sizing policy.
