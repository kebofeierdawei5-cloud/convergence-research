# C2 — Human Report + Report Quality Gate v0.1

Date: 2026-10-06
Status: ACCEPTED / CANONICAL

## Objective

Turn an accepted IIOS Machine Publication into a human-readable investment report that remains a deterministic projection of canonical decision state.

Pipeline:

```
Machine Publication
        ↓
Human-readable Investment Report
        ↓
Deterministic Report Quality Gate
```

## Product boundary

The report is a projection only.

It MUST NOT:
- create or amend a Decision;
- approve or reject a Decision;
- change Decision Precedence;
- change Trust, Quality, Thesis, Valuation, Forecast, MIE, Risk or Portfolio semantics;
- mutate Monitoring or Validation state;
- place orders or enable automatic execution.

## Report content

The report MUST expose enough context for human audit of the decision:
- case identity and cutoff;
- action, decision status, investability status and primary reason;
- core gate outcomes relevant to the Decision;
- return metrics when present;
- Trust / PIT / provenance boundary;
- current/target entry fields when present;
- risk and thesis-falsifier context;
- monitoring references;
- explicit Human Decision Boundary;
- Machine Publication identity and integrity hashes.

The report renderer does not independently recalculate company economics. It reproduces the canonical Decision payload and identifies its provenance.

## Human-readable artifact

A successful publication produces:
- immutable JSON report metadata;
- immutable Markdown report;
- immutable Report QA receipt.

The report hash covers the report metadata plus exact Markdown bytes. A changed source Publication or generated timestamp produces a distinct report hash.

## Report Quality Gate

The deterministic QA MUST check:
1. Machine Publication integrity;
2. exact Publication binding;
3. Report integrity/hash;
4. deterministic render replay;
5. required report sections;
6. action/reason fidelity;
7. Human approval boundary;
8. explicit non-authority language.

Overall QA is PASS only when all checks are PASS. Otherwise report publication fails closed.

## CLI

```bash
python -m iios_mvp.cli report <publication.json>   --generated-at <ISO-8601-timestamp>   --out runs
```

The command produces the Markdown report, metadata and QA receipt. It has no write path into Decision Revision, Approval, Monitoring or Validation state.

## Acceptance

C2 PASS requires:
- dedicated C2 CI = SUCCESS;
- human report JSON validates against its schema;
- Report QA validates against its schema;
- deterministic replay proves identical output from identical Publication + timestamp;
- source tampering or publication binding mismatch fails closed;
- a tampered report cannot pass QA;
- Markdown artifact is immutable and content-addressed;
- report generation does not mutate the Machine Publication;
- no investment semantics are changed;
- next product boundary remains C3 Second Company Acceptance.

## Explicitly out of scope

- C3 second company;
- C4 Expectation Gap production integration;
- C5 Positioning / Sizing;
- scheduler;
- alerts;
- automatic execution;
- new P3/P4 valuation-model families;
- any report-driven decision mutation.
