# C3 Acceptance — 2026-10-06

Status: ACCEPTED / CANONICAL

## Scope

C3 validates the existing canonical investment product chain against a second real company with materially different economics.

Company: 四川科伦药业股份有限公司
Market: CN-A
Symbol: 002422
Case ID: RC-CN-A-002422-20261004

## Evidence

The company-side factual anchors use the 2026 H1 CNINFO disclosure. The 2026-09-30 market-price observation is a separately captured public historical-quote evidence packet.

Price evidence packet:
- observation date: 2026-09-30
- close: 40.85 CNY/share
- SHA-256: b59d6844530261896569dcd071f2fecb670fc26ad162a6ecbf31ccca1f464d7f

The price packet is explicitly not represented as retained SZSE raw-response bytes.

## Architecture result

C3 exercised the existing path without adding investment semantics:

Decision
→ Machine Publication
→ Human Report
→ Report QA
→ Trigger Contract
→ Monitoring State
→ Validation / Replay

Distinct second-company characteristics:
- economic structure: PHARMA_MANUFACTURING_AND_CONTROLLED_BIOTECH
- primary valuation model: SOTP
- forecast assumption set: C3-KOLUN-FORECAST-ASSUMPTIONS-0.1
- risk emphasis: core pharmaceutical cash conversion, R&D return, pipeline value and governance/shareholder treatment

## Canonical decision result

Decision action: REVIEW_REQUIRED
Decision status: REVIEW_REQUIRED
Primary reason: QUALITY_GATE_UNRESOLVED
New capital allowed: FALSE

The incremental_return_on_capital quality dimension remains CONDITIONAL by design for this acceptance case. The engine therefore does not admit new capital.

The explicit model nevertheless passes:
- fundamental target return gate;
- required return gate;
- risk gate.

Model output:
- expected annualized return: 0.412484700122399020807833537

This number is a model output under the explicit C3 assumptions, not an observed return and not a guarantee.

## Lifecycle result

- Decision Revision: 1
- Decision replay: PASS
- Trigger Event: MATCHED
- Monitoring evaluation: VALID
- TR-03 validation: PASS

## Publication / report result

Dedicated C3 Actions:
- workflow: IIOS C3 Second Company — Kolun
- run: #11
- run ID: 37406518061
- head: 6fca8a62ba601fc75bcd61bdfada976bf5153128
- conclusion: SUCCESS

CI gates:
- compileall: PASS
- C3 tests: 4 passed
- executable acceptance harness: PASS
- git diff --check: PASS

Content-addressed outputs, generated_at = 2026-10-06T10:05:00+08:00:
- publication_hash: 8625e4f23bf1e7560d4bbaab320483226047c3dda62702b18a9d633e3e56df81
- report_hash: c92dd6d31c7d3ac03f73dcf1a7d414319fc841ea8c42b5d4c799be6360db50c2
- qa_hash: 60ed50529daa934c7127b896d577b5b3c241fb486de94d7f577e4c906f1c2e28
- report deterministic replay: TRUE
- report QA: PASS

Authority boundary:
- human approval required: TRUE
- automatic execution: FALSE
- report policy effect: REPORT_ONLY_PROJECTION
- validation policy effect: NO_DIRECT_DECISION_PRECEDENCE_CHANGE

## Acceptance criteria

1. Real second-company canonical Decision result: PASS
2. Decision Revision persistence/replay: PASS
3. Trigger Contract exact-revision binding: PASS
4. PIT-valid Trigger Event to Monitoring State: PASS
5. TR-03 Validation / Replay: PASS
6. C1 Machine Publication exact-revision binding: PASS
7. C2 Human Report and Report QA: PASS
8. Deterministic report replay: PASS
9. SOTP and second-company forecast assumptions exercised: PASS
10. Publication/report remain projections only: PASS

## Canonical merge

C3 implementation PR: #103
C3 implementation merge commit: eb0f9fc965f9ce6aa09685776d2ec8a0522e3b47

This acceptance record is canonical only after the accompanying state-sync change is merged to main.

## Boundary after C3

Next development boundary: C4 Expectation Gap Production Integration.

C3 does not include C4 work, positioning/sizing, scheduler, alerts, or automatic execution.
