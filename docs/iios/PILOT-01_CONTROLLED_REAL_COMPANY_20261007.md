# PILOT-01 — Controlled Real-Company Pilot Evidence

Status: **TECHNICAL PASS / HUMAN OBSERVATION PENDING**
Date: 2026-10-07

## Scope

PILOT-01 tests the existing company-level Investment Core on the two accepted materially different real-company cases:

- CATL / 300750
- 科伦药业 / 002422

This is workflow evidence, not evidence that either security is a good investment.

## Exact execution

Baseline main:
`a14e561b266fb288a696bb9c70d853a2e6e218f2`

Dedicated Pilot CI:
- run `37605725511`;
- job `112740590739`;
- conclusion: SUCCESS;
- pytest: 57 passed;
- compileall: PASS;
- git diff --check: PASS.

Both real-company E2E tools passed and the full lifecycle E2E passed.

## Case observations

### CATL / 300750

- Decision: REVIEW_REQUIRED.
- New capital: FALSE.
- Quality: CONDITIONAL.
- Trust: REVALIDATION.
- Expected annualized return: approximately 14.20%.
- Required Return gate: PASS.
- Risk gate: PASS.
- Fundamental 15% target gate: FAIL.

This demonstrates that the return gate and Trust/Quality constraints are not collapsed into a single buy signal.

### 科伦药业 / 002422

- Decision: REVIEW_REQUIRED.
- New capital: FALSE.
- Quality: CONDITIONAL.
- Primary valuation model: SOTP.
- Expected annualized return: approximately 41.25%.
- Required Return: PASS.
- Risk: PASS.
- Decision replay: PASS.
- Monitoring evaluation: VALID.
- Validation: PASS.
- Publication QA: PASS.
- Human approval required: TRUE.
- Automatic execution: FALSE.
- Report deterministic replay: TRUE.

The lifecycle and projection boundaries therefore work on a structurally different company case.

## Technical conclusion

PILOT-01 technical acceptance is PASS.

No authority, PIT, provenance, decision-revision, publication/report mutation, or automatic-execution bypass was observed in this controlled run.

## Human observation boundary

CI cannot establish whether an actual operator can comfortably use the system or understand the report.

The remaining PILOT-01 action is a real human review of the two outputs, recording:

- confusing or missing information;
- information the user had to manually reconstruct;
- places where the workflow is too cumbersome;
- whether the final Decision/Report is actionable;
- any unexpected BLOCKED/REVIEW_REQUIRED behavior.

Human observations are not allowed to silently modify normative investment semantics. They become PILOT-03 candidate findings.

## Downstream

Until human observation is recorded:

`PILOT-02` is not started.

A02 / CSI800 remains non-blocking.
