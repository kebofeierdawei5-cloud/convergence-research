# IIOS B1-LCE — Canonical Research Orchestrator Design v0.1

Date: 2026-10-07
Status: IMPLEMENTATION CANDIDATE — READY FOR INDEPENDENT CI / CANONICAL MERGE
Parent: B0 LLM Canonical Execution Governance Boundary Freeze 2026-10-07

## 1. Objective

Close P0-LLM-001 by making the Canonical Research Orchestrator the only product entry path that can produce a canonical IIOS investment decision.

This batch does not change the economic meaning of Trust, Quality, Thesis, Forecast, Valuation, Return, Risk, Portfolio, MIE or Decision. Existing v0.3 semantics remain the downstream rule authority until separately superseded.

## 2. Product boundary

The supported canonical path is:

```text
Natural-Language Request
  -> Request Admission
  -> Research Case / Run Envelope
  -> Evidence Admission
  -> Semantic Workbench
  -> Forecast Admission
  -> Valuation Admission
  -> Return / Risk / Portfolio evaluation
  -> Decision Admission
  -> Human Approval
  -> Machine Publication
  -> Human Report
  -> Monitoring / Validation / Replay
```

A direct call to `engine.run_case`, `decide_v03`, or a lower-level module is not a canonical product execution path unless invoked by the orchestrator with a valid run envelope.

## 3. Run envelope

Every canonical run carries:

- `run_id`
- `case_id`
- `market`
- `symbol`
- `cutoff_date`
- `as_of_date`
- `request_type`
- `orchestrator_version`
- `research_case_hash`
- `stage_state`
- `non_canonical_reason` when applicable
- `artifact_refs`
- append-only stage receipts
- `created_at`

## 4. Stage machine

Canonical states:

```text
REQUEST_RECEIVED
REQUEST_ADMITTED
CASE_CREATED
EVIDENCE_PENDING
EVIDENCE_ADMITTED
SEMANTIC_PENDING
SEMANTIC_ADMITTED
FORECAST_PENDING
FORECAST_ADMITTED
VALUATION_PENDING
VALUATION_ADMITTED
DECISION_PENDING
DECISION_ADMITTED
HUMAN_APPROVAL_PENDING
PUBLISHED
REPORTED
COMPLETE
```

Terminal negative states:

```text
BLOCKED
NON_CANONICAL
FAILED
```

Allowed transitions are explicit and monotonic. No transition may skip a required stage.

## 5. Canonicality rule

```text
No run envelope                       -> NON_CANONICAL
No admitted Research Case            -> BLOCKED
Evidence not admitted                -> BLOCKED
Required semantic artifact missing  -> BLOCKED
Forecast not admitted                -> BLOCKED
Valuation not admitted               -> BLOCKED
Decision not admitted                -> BLOCKED
Human approval missing               -> pending, not canonical completion
Invalid / incomplete run receipt     -> NON_CANONICAL
```

A readable report is never sufficient to upgrade `NON_CANONICAL` to canonical.

## 6. Natural-language normalization

The orchestrator may normalize a user request into structured intent, but deterministic identity and temporal constraints remain code-owned.

Minimum request fields:

```text
market
symbol / company reference
as_of / cutoff
current position context
requested output mode
```

Ambiguous or conflicting identity/cutoff input must resolve to `BLOCKED` rather than inferred silently.

## 7. Bypass prevention

The following are explicit non-canonical paths:

- free-form answer that claims to be a final IIOS decision;
- direct `run_case` execution from a chat tool without an orchestrator envelope;
- direct construction of a canonical decision from externally supplied JSON;
- a report rendered from a non-admitted snapshot;
- mutation of authoritative state by an LLM;
- synthetic receipt creation after the fact without stage receipts.

Non-canonical output may still be useful as research discussion, but must be labeled `NON-CANONICAL ANALYSIS` and cannot enter Decision Admission.

## 8. Stage gating contract

Each stage emits an append-only receipt containing:

```text
stage_id
stage_version
input_refs
input_hashes
output_refs
output_hashes
producer_type
producer_version
status
cutoff
created_at
```

For semantic stages, `producer_type` identifies an authorized semantic producer. B2 defines the concrete LLM producer contracts.

For deterministic stages, `producer_type` is `CODE` and the implementation version is recorded.

## 9. Authority boundary

```text
LLM
  produces interpretations / forecasts / proposals

Code
  admits, validates, gates, hashes, transitions and persists

Human
  approves / rejects / overrides / executes capital decisions
```

The orchestrator does not make economic judgments. It controls whether those judgments are allowed to reach the decision kernel.

## 10. Test boundary

Lower-level modules remain directly testable for unit and regression tests. Such test execution is not product evidence of canonical research execution.

Dedicated conformance tests distinguish:

1. module correctness;
2. orchestrator conformance;
3. end-to-end canonical run conformance.

## 11. Acceptance criteria

B1-LCE passes when:

1. one canonical natural-language entry is defined;
2. every canonical run receives an immutable run envelope;
3. required stages and terminal negative states are explicit;
4. stage skipping is structurally forbidden;
5. direct lower-level execution is classified non-canonical unless orchestrated;
6. semantic producer authenticity is reserved for B2 and is already represented as a required stage receipt field;
7. human approval remains downstream and mandatory;
8. automatic trading remains disabled;
9. no existing v0.3 economic formula is changed.

## 12. Out of scope

- LLM prompt/model integration;
- semantic producer implementation;
- valuation model role correction;
- new MIE policy;
- portfolio optimization;
- automatic execution;
- A02 / CSI800.
