# B2-E — Natural Language → Semantic → Decision E2E

Date: 2026-10-08

Status: **IMPLEMENTATION / CONFORMANCE GATE**

## Purpose

B2-E closes the control-plane path from an admitted natural-language investment request through an admitted semantic artifact and into the canonical v0.3 Decision Kernel.

This batch does not claim economic validity of LLM reasoning.

## Canonical path

```
Natural-language request
        ↓
B2-B request admission
        ↓
Research Case
        ↓
admitted Evidence
        ↓
SEMANTIC_PENDING
        ↓
B2-A semantic admission
        ↓
Forecast / Valuation admission chain
        ↓
DECISION_PENDING
        ↓
canonical v0.3 Decision Kernel re-execution
        ↓
Decision Admission
        ↓
AI_PROPOSED Decision Revision
```

## Authority boundary

The semantic producer is untrusted until B2-A admission.

B2-E rejects semantic artifact outputs that attempt to write decision-authoritative fields such as `action`, `new_capital_allowed`, `human_approval_required` or `auto_execution`.

The Decision stage does not consume a model-declared action. It re-executes the canonical Decision Kernel against the validated Investment Core case and then issues a Decision Admission receipt.

The produced lifecycle record is always `AI_PROPOSED`, with `human_approval_required=true` and `auto_execution=false`.

## Current evidence class

The B2-E repository conformance suite uses fixture request interpreter, fixture semantic producer and the existing canonical 300750 case/resolvers.

Therefore this batch proves the **E2E control and authority boundary**, not a live production LLM invocation.

A real production path requires:

```
B2-D3 LIVE_RESPONSE_CAPTURED
        ↓
independent verification
        ↓
production request interpreter / semantic producer
        ↓
B2-E same canonical bridge
```

B2-D3 remains a separate prerequisite for upgrading this E2E conformance from fixture-backed to production-backed evidence.

## Explicit non-claims

- no LLM action is trusted as a Decision;
- no new-capital permission is emitted by the semantic producer;
- no Human Approval is created;
- no order/execution capability is introduced;
- no Investment Core formula is modified;
- no model-quality or return-prediction claim is made.
