# C3 — Second Company Acceptance v0.1

Date: 2026-10-06
Status: ACCEPTED / CANONICAL

## Objective

Prove that the canonical Decision → Machine Publication → Human Report → QA → Monitoring → Validation architecture is not CATL-specific.

Default second company:

- 四川科伦药业股份有限公司
- CN-A / 002422
- Case: RC-CN-A-002422-20261004

## User Value

A real second company must cross the existing architecture using materially different economics and evidence rather than succeeding only because the first fixture and data shapes were designed around CATL.

## Required C3 acceptance surface

The real case must exercise:

- different economic structure: mature pharmaceutical manufacturing + controlled biotechnology R&D / pipeline optionality;
- different evidence chain: CNINFO company evidence plus a separately captured market-price evidence packet;
- different valuation path: SOTP as primary valuation rather than CATL's DCF path;
- different forecast assumptions: explicit core-business growth plus biotech option-value assumptions;
- different risk structure: manufacturing cash conversion, R&D return and pipeline/governance falsifiers;
- C1 Machine Publication;
- C2 Human Report and deterministic Report QA;
- TR-01 Trigger Contract;
- TR-02 Monitoring State;
- TR-03 Validation / Replay.

## Authority boundary

C3 adds no new investment semantics.

The test case must not:

- add a P3/P4 model family;
- productionize Expectation Gap;
- add positioning / sizing policy;
- create a scheduler;
- create alerts;
- create automatic execution;
- mutate a canonical Decision from Report, Monitoring or Validation.

## Acceptance evidence

C3 PASS requires:

1. the real company case reaches a valid canonical Decision result;
2. Decision Revision is persisted and replayable;
3. a Trigger Contract binds to the exact Decision Revision;
4. a Trigger Event is PIT-valid and produces Monitoring State;
5. TR-03 validation passes;
6. C1 Machine Publication succeeds and binds to the exact revision;
7. C2 Human Report succeeds and Report QA = PASS;
8. same publication + same generated_at reproduces the exact same report;
9. the case visibly exercises SOTP and the second-company forecast assumptions;
10. publication/report remain projections only.

Failure of any item is C3 BLOCKED.
