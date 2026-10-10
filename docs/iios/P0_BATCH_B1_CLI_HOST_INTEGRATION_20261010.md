# P0 Batch 1 — Canonical CLI Host Integration — 2026-10-10

**Record class:** implementation / exact-head acceptance record  
**Canonical base:** `main@7ba1adcf99532b2de10bc7f405b66b4affd4647d`  
**Scope:** prove that the repository-resident command-line host enters through the canonical natural-language path and persists run/stage lineage.  
**Authority boundary:** control-plane integration only; not production host acceptance.

## Objective

After the Batch-0 incident was fixed at the code/control-plane boundary, exercise the supported repository-resident host entry all the way through its real CLI dispatcher:

```text
host request bundle
  -> iios_mvp.cli.main()
  -> canonical-run
  -> trusted runtime-factory resolution
  -> canonical B2-E orchestration
  -> persisted Run Envelope + append-only stage receipts
```

The test must use a fresh run ID, prove the expected stage order, and assert that the entry remains an AI proposal with human approval required and automatic execution disabled.

## User value

This closes a test gap between calling the B2-E function directly and exercising the CLI entry actually present in the repository. It prevents a future host adapter from accidentally calling the legacy `run` route or bypassing durable run authorization.

## Product surface inspected

The repository contains the `iios_mvp.cli` command dispatcher and an explicit `canonical-run` command with a trusted `--runtime-factory module:callable` / `IIOS_CANONICAL_RUNTIME_FACTORY` handoff. A separate deployable web/server/front-end composition root was not identified in the repository tree. This batch therefore verifies the repository-resident CLI host boundary, not an unobserved external product deployment.

The runtime factory selector remains host/CLI-controlled. It is not read from the request bundle.

## Implementation and acceptance probe

- Added `tests/test_canonical_cli_host_integration.py`.
- The test invokes `iios_mvp.cli.main()` with `canonical-run`, rather than calling `run_b2e_conformance` directly.
- It creates a unique test run ID and a byte-verified synthetic manifest, injects a test-only factory through the trusted CLI argument, and verifies a persisted envelope and the ordered receipts through `HUMAN_APPROVAL_PENDING`.
- It asserts that the proposal keeps `human_approval_required=true`, `auto_execution=false`, and that the CLI itself did not publish a report or issue the complete Run Receipt.
- The dedicated P0 workflow now runs this integration test with the existing fail-closed regressions, compile check and diff check.

## Test fixture and non-claims

Every evidence row in this integration test is marked `license_status=TEST_ONLY`; the semantic producer is the repository's deterministic `FixtureSemanticProducer`. This proves route wiring and persistence only. It is **not** production semantic conformance, source admission for an actual company, or evidence of investment decision quality.

This test deliberately does not auto-install or default-register a runtime. An absent/invalid production factory must remain blocked.

## Out of scope / remaining blocker

- No external LLM callback or production model has been configured or invoked.
- No production user-facing deployment has been identified or shown to call this CLI entry.
- No real 605016 B2 Evidence/PIT bundle has been admitted by this change.
- This change does not publish a report, create a complete Run Receipt, approve a decision, or authorize any order.

**Batch result interpretation:** the repository CLI host path can be accepted only at the control-plane test level after exact-head CI passes. The production-host portion of Batch B remains **BLOCKED** until the real deployment entry is identified, a genuinely configured runtime is registered there, and a production-backed real-company run passes evidence, semantic/forecast/valuation admission, report and Run Receipt replay plus independent red-team. P0-LLM-001 and P0-LLM-004 remain OPEN.
