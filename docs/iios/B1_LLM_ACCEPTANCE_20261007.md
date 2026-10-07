# IIOS B1-LCE Acceptance — 2026-10-07

Status: **IMPLEMENTATION CANDIDATE — READY FOR INDEPENDENT CI / CANONICAL MERGE**

## Scope

B1-LCE implements the first canonical execution-control layer required by the 2026-10-07 P0 LLM red-team findings.

Included:

- `CanonicalResearchOrchestrator` run-envelope authority;
- monotonic stage machine with structural bypass rejection;
- append-only stage receipts;
- explicit semantic-producer type boundary;
- exact-stage authorization for downstream engine invocation;
- complete-run `IIOS_RUN_RECEIPT-0.1` builder;
- typed semantic-artifact common schema;
- regression tests for canonical/non-canonical execution boundaries;
- dedicated GitHub Actions verification workflow.

## Explicit non-goals

This batch does not implement:

- LLM model/API integration;
- domain-specific semantic reasoning;
- semantic artifact admission against live evidence stores;
- valuation role correction;
- automatic execution.

Those remain B2/B4 work.

## Local acceptance

Exact local checks on the candidate tree:

```text
pytest:       8 passed
compileall:   PASS
JSON syntax:  PASS
```

The initial test collection failure was environmental only (`PYTHONPATH` omitted) and was reproduced cleanly after setting the package root; no test logic was weakened to obtain PASS.

## Canonical integrity properties

1. Stage skipping fails closed.
2. `SEMANTIC_ADMITTED` rejects `EXTERNAL_JSON` / unrecognized producer types.
3. An admitted semantic artifact must have an output reference.
4. Downstream canonical execution authorization requires the exact expected stage.
5. A COMPLETE run cannot issue an incomplete run receipt.
6. A direct lower-level execution can be explicitly classified as `NON_CANONICAL`.
7. Stage hashes are lowercase SHA-256 values.
8. Both new JSON schemas are syntactically valid and the run-receipt schema accepts a canonical complete receipt while rejecting an external semantic producer.
9. No Investment Core v0.3 economic formula or decision precedence rule is modified.

## Remote acceptance

Dedicated workflow:

```text
.github/workflows/iios_b1_llm_orchestrator.yml
```

It runs:

- B1 orchestrator tests;
- B1 schema tests;
- compileall;
- JSON schema syntax validation;
- git diff --check.

## Next gate

After independent CI and canonical merge:

```text
B2 — LLM Semantic Workbench + Semantic Producer Admission
```
