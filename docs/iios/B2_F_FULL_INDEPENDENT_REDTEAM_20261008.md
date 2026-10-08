# B2-F — Full Independent Red-team — 2026-10-08

Status: **BLOCKED — FINDINGS REPRODUCED**

This is an independent clean-room security / authority audit of the B2-E control-plane implementation. The red-team does not modify product code.

## Method

The red-team attacks the current canonical B2-E surface through:
- AST/source inspection independent of B2-E implementation tests;
- contract/schema inspection;
- lifecycle boundary inspection;
- targeted authority and lineage probes.

The target is not model quality. The target is whether a malicious or malformed semantic producer, caller, or orchestrator invocation can create a misleading path toward Decision authority.

## Finding F-001 — P0 — Semantic → Economic Causal Edge Missing

### Reproduction

B2-E admits and hashes a semantic artifact, then separately calls:

```
canonical_decision = decide_v03(dict(case), ...)
```

The supplied expanded Investment Core `case` is not constructed from the semantic artifact's output.

The semantic artifact only contributes lineage metadata to the orchestrator / binding receipt and is not transformed into the Forecast, Valuation, Risk, Expectation Gap or Decision input set.

### Impact

A real LLM can produce a perfectly admitted semantic artifact while the Decision remains unchanged because the Decision Kernel consumes an independently supplied case.

Therefore:

```
Natural Language → Semantic
```

and

```
Expanded Case → Decision
```

are both valid paths, but they are not yet one causal E2E path.

This does not permit direct unauthorized capital allocation, but it means B2-E cannot honestly claim production **Natural Language → LLM Reasoning → Canonical Economic Decision** once D3 becomes live.

### Required repair

Introduce an explicit canonical semantic-to-economic transformation boundary, for example:

```
Semantic Artifact
      ↓
Semantic-to-Core transformation / adjudication
      ↓
Canonical Forecast / Thesis / Quality / Valuation inputs
      ↓
validated Investment Core Case
      ↓
Decision Kernel
```

The transformation itself must be deterministic, versioned, provenance-bound and fail-closed.

## Finding F-002 — P1 — Forecast / Valuation Stage Admission Is Not Independently Validator-backed

B2-E's pre-decision transition extracts `case["forecast"]` and `case["valuation"]`, hashes them, then records `FORECAST_ADMITTED` and `VALUATION_ADMITTED`.

No dedicated canonical Forecast or Valuation admission validator is invoked by this stage transition.

The later Decision Admission performs full case validation and therefore provides a secondary safety barrier, but the orchestrator's stage receipts can claim admitted Forecast / Valuation states before those stage-specific contracts have been independently admitted.

### Impact

The stage receipt semantics are weaker than the project's general Admission / Receipt authority model.

## Finding F-003 — P1 — Nested Semantic Authority Fields Can Evade the Guard

B2-E checks:

```
FORBIDDEN_FIELDS ∩ output.keys()
```

Only top-level keys are inspected.

A payload such as:

```json
{"decision": {"action": "BUY"}}
```

is not blocked by this specific guard.

The canonical Decision Kernel still does not trust that field, so this is an authority-boundary ambiguity rather than a direct capital-escalation path. It should nevertheless be closed before a production semantic producer is admitted.

## Finding F-004 — P1 — Decision Series Identity Depends on Caller-Supplied Series ID

The lifecycle builder accepts an arbitrary `decision_series_id` and records only the caller-supplied value plus `case_id` / cutoff.

Market, symbol and company are available in the Decision Admission snapshot but are not structurally part of the lifecycle series identity record.

### Impact

The current contract relies on caller discipline to prevent cross-company series collisions or semantic identity substitution.

## Existing controls that passed

- Research Case identity binding;
- canonical Decision Kernel re-execution;
- Decision Admission requirement;
- `AI_PROPOSED` lifecycle state;
- mandatory Human Approval flag;
- `auto_execution=false`;
- no order/live-provider imports in B2-E;
- closed B2-E schema.

## Finding F-005 — P1 — Live Workflow Trigger Discrepancy

The repository workflow source declares B2-D3 as workflow_dispatch-only, but GitHub Actions recorded repeated B2-D3 runs with event=push on commits that touched unrelated B2-F documentation/test branches.

Observed examples include B2-D3 run #35 on head 6a5e3decaf096bd614bbf8d3f8eac0cde35efbf4 and earlier runs #31 and #30 on B2-F audit commits.

No live request was admitted because production credentials were absent and the workflow failed closed. Nevertheless, the observed trigger behavior contradicts the intended “manual-only” spending boundary.

This must be resolved before any production provider credentials are admitted. A push-triggered live workflow could otherwise spend provider quota or produce live evidence without explicit operator dispatch.

## Overall disposition

**B2-F = BLOCKED.**

The independent red-team reproduced one P0 and three P1 findings.

The most important blocker is F-001. B2-E currently proves a secure control-plane composition, but not a causal Semantic → Economic Decision pipeline.

### Next repair order

```
F-001 Semantic → Economic transformation boundary
        ↓
F-002 Canonical Forecast / Valuation admission binding
        ↓
F-003 Recursive semantic authority-field guard
        ↓
F-004 Decision Series identity hardening
        ↓
rerun B2-F independent red-team
        ↓
B2-F PASS / FAIL
```

B2-D3 live-provider evidence remains a separate prerequisite for production-backed execution and is not altered by this red-team result.
