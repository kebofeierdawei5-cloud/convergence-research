# IIOS B1-LCE Acceptance — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

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

## Acceptance evidence

Canonical branch lineage:

```text
B1 parent main:
de1fba8ccee403ce219455a35b12ea6fd712a0cb

B1 implementation head:
8bf658b65ce7430d814046f1301af9915f3dea2c

PR:
#198

merge commit:
f34c3325e6cfab75303f944124330289c1cb9444
```

Local verification:

```text
pytest:       8 passed
compileall:   PASS
JSON syntax:  PASS
```

Dedicated remote B1 workflow:

```text
workflow:
IIOS B1 Canonical Research Orchestrator

run:
37644825682

status:
completed / success
```

The remote run executed the B1 tests, schema tests, compileall, JSON syntax checks and git diff --check.

## Canonical integrity properties

1. Stage skipping fails closed.
2. `SEMANTIC_ADMITTED` rejects `EXTERNAL_JSON` / unrecognized producer types.
3. An admitted semantic artifact must have an output reference.
4. Downstream canonical execution authorization requires the exact expected stage.
5. A COMPLETE run cannot issue an incomplete run receipt.
6. A direct lower-level execution can be explicitly classified as `NON_CANONICAL`.
7. Stage hashes are lowercase SHA-256 values.
8. The run-receipt schema requires a complete canonical dependency chain.
9. No Investment Core v0.3 economic formula or decision precedence rule is modified.

## Result

**B1-LCE = PASS / MERGED / CANONICAL**

Next canonical gate:

```text
B2 — LLM Semantic Workbench + Semantic Producer Admission
```
