# CORE-02 Company Economic Core — Acceptance Record

Date: 2026-10-04
Status: PASS / MERGED

## Scope

CORE-02 implements the minimum company-economic transformation:

admitted company evidence → Reality → Trust → Quality → Value Core → Value Driver Ranking → valuation route.

## Acceptance criteria

- CORE-01 case is validated before economic-core processing.
- All seven CORE-01 evidence groups are mandatory for admission.
- Evidence status must be ADMITTED.
- Evidence subject must equal case_id.
- Evidence must satisfy known_at <= cutoff.
- Exact-byte/source/artifact/SHA provenance is required.
- Reality facts are evidence-linked and require four economic domains.
- Trust dimensions are explicit and aggregate fail-closed.
- Quality dimensions are explicit and aggregate fail-closed.
- Value Core reuses the existing deterministic scan and requires evidence-linked nodes.
- Value Driver Ranking is explicit, contiguous, evidence-linked and rank-1 must be HIGH materiality.
- Valuation route exposes candidate models only; model selection remains HUMAN.
- CORE-02 contains no import from the historical research.* namespace.
- Audit hashes are generated and the core hash is replay-validated.
- No CSI800 / CSI Industry / A02 dependency is introduced.

## Evidence

- PR #29: MERGED
- merge commit: `2a1c376e2bf3c608ebdf88a95d8be5aeaf8580b9`
- CORE-02 CI run #6 / `37209264413`: SUCCESS
- CORE-02 regression: **30 passed**
- CORE-02 compileall: SUCCESS
- CORE-02 JSON Schema validation: SUCCESS
- CORE-01 CLI intake regression: SUCCESS
- Investment Core CI run #214 / `37209264423`: SUCCESS
- CORE-01 CI run #10 / `37209264528`: SUCCESS
- Red-team hardening: evidence-domain binding, effective interval validation, derived-parent lineage validation, and Value Core evidence binding.
- No CSI800 / CSI Industry / A02 dependency introduced.

## Acceptance judgment

**PASS** — CORE-02 is now canonical on `main`.

Boundary remains strictly:
admitted company evidence → Reality → Trust → Quality → Value Core / Value Driver Ranking → valuation route.

It does not implement forecast, valuation execution, Market Implied Expectation, Expectation Gap or investment decision.
