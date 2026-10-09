# P0 Canonical Entry Incident Reproduction & Acceptance Contract

Date: 2026-10-09
Record class: DIAGNOSTIC / CONTRACT FREEZE
Status: PROPOSED ON ISOLATED BATCH-0 BRANCH — NOT CANONICAL UNTIL MERGED
Scope: IIOS Investment Core canonical research execution only
Canonical baseline: `main@664ef3429358a59ce6c0ccd963b67667cac1a80d`

## 1. Incident identity

Original user request:

> 使用新版本iios分析百龙创园 605016，产能增长型B端成长股，截止2026-10-09

Case identity to be used by the future end-to-end regression:
- market: `CN-A`
- symbol: `605016.SH`
- company: 百龙创园
- cutoff_date: `2026-10-09`
- requested classification: capacity-growth B2B growth company

Observed assistant execution path in the incident:
1. ad hoc public-web lookup;
2. manual prose synthesis of company facts;
3. manual construction of Bear/Base/Bull earnings scenarios and scenario weights;
4. manual valuation multiples and a derived entry-price interval;
5. direct presentation as an IIOS investment decision/report.

No matching Run Envelope, append-only stage receipts, admitted 605016 Research Case, B2 Evidence/PIT Admission, canonical Forecast/Valuation Admission, Decision Admission, Machine Publication binding, or complete `IIOS_RUN_RECEIPT` was provided with the answer.

This is an incident finding, not a claim that web research or a provisional human analysis is prohibited. The prohibited behavior is presenting an un-orchestrated answer as a canonical IIOS decision.

## 2. Baseline facts to preserve

At freeze time, current canonical `main` resolves to:
`664ef3429358a59ce6c0ccd963b67667cac1a80d`.

Observed control gaps:
- `iios_mvp/canonical_research_orchestrator.py` defines an in-memory stage machine and receipt builder.
- `iios_mvp/cli.py` does not import or invoke that orchestrator in `cmd_run`; `cmd_run` directly invokes `run_case(case)`.
- The same CLI has direct `publish`, `report`, `investor-report`, and `investor-report-v02` commands. These use publication/report writers without a Run Envelope or complete Run Receipt parameter.
- The legacy engine validation checks selected fields such as evidence source, claim and date, but these checks are not equivalent to exact-byte source provenance and B2 Evidence/PIT Admission.
- B2-E conformance has explicitly been described as fixture-backed control-plane evidence, not proof of live production LLM economic reasoning.

The probes in `tests/test_p0_canonical_entry_incident_reproduction.py` characterize these observed paths. Their PASS means the incident/bypass was reproduced, NOT that production compliance passed.

## 3. Normative contract frozen by Batch 0

A response may be called a canonical IIOS investment decision only if all of the following are true:

1. The original natural-language request is bound to a durable Run Envelope with deterministic `run_id`, `case_id`, market, symbol, cutoff/as-of dates, version and request hash.
2. The allowed stage sequence is monotonic; every stage writes an append-only receipt bound to exact input/output references and hashes.
3. The Research Case is schema-valid and admitted for the exact company/cutoff.
4. Required company Evidence is independently admitted under the B2 Evidence/PIT contract. Raw-byte capture, a URL, a citation, or a self-declared date alone is not admission.
5. Required semantic artifacts have an authorized producer identity/version, admitted input lineage and deterministic admission receipt. Fixture output or externally supplied JSON cannot claim production semantic provenance.
6. Forecast and Valuation are independently admitted and bound to the same Case/cutoff and accepted evidence lineage.
7. Return, Risk, Portfolio and Thesis/Trust/Quality gates are evaluated by the canonical v0.3 decision path. No economic formula or threshold is changed in Batch 0.
8. Decision Admission is bound to the actual Decision snapshot and series identity.
9. Formal Decision Revision, Machine Publication and Investor Review Report are reachable only from the authorized canonical run. Report generation is a read-only projection of the exact Machine Publication.
10. A complete `IIOS_RUN_RECEIPT` binds Case, evidence manifest, semantic artifacts, forecast, valuation, return, risk/portfolio, decision admission/revision, publication and report hashes.
11. If any required authorization or artifact is missing, the result is `BLOCKED` or `NON_CANONICAL`; it cannot be labelled canonical and cannot authorize capital.
12. Human approval remains separate from AI proposal; no batch authorizes order execution.

## 4. Required negative probes

| ID | Attack / missing prerequisite | Required result after remediation | Batch-0 purpose |
|---|---|---|---|
| P0-CE-01 | No Run Envelope; invoke product decision path directly | `NON_CANONICAL` | Reproduce direct-entry bypass |
| P0-CE-02 | Evidence absent, captured-only, or not B2/PIT-admitted | `BLOCKED` | Reproduce evidence-gate bypass |
| P0-CE-03 | Required semantic artifact / authorized producer receipt missing | `BLOCKED` | Reproduce semantic-stage bypass |
| P0-CE-04 | Direct call to lower-level `run_case` / decision kernel outside authorized run | `NON_CANONICAL` | Reproduce lower-level bypass |
| P0-CE-05 | Direct Decision Revision / Machine Publication / Report write without authorized run receipt | `BLOCKED` or `NON_CANONICAL` | Reproduce final-write bypass |
| P0-CE-06 | Tampered, incomplete, cross-case or hash-mismatched Run Receipt | `BLOCKED` or `NON_CANONICAL` | Required for Batch 2 security tests |
| P0-CE-07 | Correctly orchestrated but insufficient evidence | `BLOCKED`, with explicit missing groups | Prove fail-closed path |
| P0-CE-08 | Complete admitted case through full path | Decision may be produced; canonical completion requires all stage receipts + QA and human-approval state explicitly represented | Prove positive path after remediation |

## 5. Batch-0 test interpretation

Batch 0 is a read-only incident reproduction and contract-freeze batch. It intentionally does not change production code, economic formulas, thresholds, Decision Semantics, schemas, or production permissions.

The characterization tests are expected to demonstrate the current bypass where it exists. Thus:
- `INCIDENT_REPRODUCED` is evidence of the defect;
- CI PASS for the probe means the reproducer ran as designed;
- neither means production compliance PASS;
- the required negative outcomes in Section 4 remain open acceptance gates for Batch 1/2.

This distinction prevents a regression probe from being misreported as a fix.

## 6. Exit criteria

Batch 0 is complete only when:
- the original incident request, cutoff, canonical SHA and observed execution path are frozen;
- all five requested negative paths (P0-CE-01 through P0-CE-05) have executable probes or explicit characterization tests;
- each finding distinguishes an observed behavior from the desired post-fix behavior;
- no production economics or authorization behavior was changed;
- the canonical State Index is updated only at canonical promotion, with this record correctly classified during PR review.

Batch 0 does NOT close P0-LLM-001 or P0-LLM-004. Their closure requires enforcement changes and fresh production-path acceptance.

## 7. Next boundary

Batch 1: Connect a real natural-language request entry to the canonical Orchestrator.

Batch 2: Persist and bind run receipts; make Decision Revision, Machine Publication and formal report writes enforce run authorization; close all entry/write bypasses.

Batch 3+: Complete real-company evidence admission and production semantic/forecast/valuation chain without relaxing the fail-closed contract.
