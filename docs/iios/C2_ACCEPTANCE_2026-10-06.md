# C2 Acceptance — Human Report + Report Quality Gate

Date: 2026-10-06
Status: CANDIDATE — PENDING ACCEPTANCE

## Acceptance target

C2 must establish a one-way projection:

Machine Publication → Human-readable Investment Report → Deterministic Report Quality Gate

The report must never become an alternate decision source.

## Implemented candidate

- Human Report renderer bound to exact Machine Publication.
- Immutable JSON report metadata.
- Immutable Markdown report artifact.
- Deterministic Report QA receipt.
- Publication binding by publication ID/hash.
- Decision identity binding by Decision Revision / case / cutoff.
- Deterministic render replay check.
- Required-section and decision-fidelity checks.
- Explicit Human Decision Boundary and non-authority language.
- CLI report command.
- JSON Schemas for report and Report QA.

## Red-team target

C2 must fail closed on:
- invalid/tampered Machine Publication;
- publication/report identity mismatch;
- report hash tampering;
- rendered content drift;
- canonical action/reason drift;
- missing Human Approval boundary;
- report language that implies decision or execution authority.

## Explicit boundary

C2 does not:
- change Decision Kernel semantics;
- change Trust / Quality / Valuation / Forecast / MIE / Risk / Portfolio;
- create a second decision source;
- mutate Decision Revision;
- mutate Monitoring / Validation;
- create scheduler/alerts/automatic execution;
- enter C3/C4/C5.

## Pending evidence

Dedicated C2 CI must pass before canonical acceptance.
