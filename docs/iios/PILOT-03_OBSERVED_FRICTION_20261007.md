# PILOT-03 — Observed Friction Remediation — 2026-10-07

Status: TECHNICAL PASS / CANONICAL AFTER MERGE

## Trigger

PILOT-02 exposed three classes of findings:

1. External market-data endpoint instability (Yahoo HTTP 429 / alternative endpoint failures).
2. A pilot-harness provenance mismatch where the case declared Yahoo while canonical admission used Tencent.
3. An initial Bear scenario that failed the declared 25% maximum-loss boundary.
4. Duplicate CI execution caused by both pull-request and branch-push triggers.

Only items 2–4 were within the IIOS pilot/test surface. No P0 Investment Core semantic bypass was found.

## Finding classification

### F0 — External data-source instability
Classification: EXTERNAL / NON-CANONICAL

The runner correctly fail-closed when external endpoints returned 429 / 502 / connection-reset responses. No production investment semantics were changed for this issue.

The accepted PILOT-02 run subsequently captured exact historical market-price bytes from a functioning endpoint and admitted them with provenance and SHA-256.

### F1 — Price provenance mismatch
Classification: TEST-HARNESS DEFECT / P2

The first full Decision Admission attempt correctly rejected the candidate because the case declared a Yahoo source while the admitted canonical price record used Tencent.

The fix aligned the test fixture with the admitted source. The canonical price resolver already behaved correctly and was not weakened.

### F2 — Bear-case risk-boundary failure
Classification: TEST-INPUT DISCIPLINE / P2

The initial Bear value of CNY 19.00 against entry CNY 25.95 implied a loss greater than the declared 25% maximum-loss constraint.

This correctly failed the Risk gate.

The accepted test fixture now uses CNY 19.95. PILOT-03 adds regression tests requiring the fixture's Bear case to satisfy the declared Risk boundary and requiring the valuation/scenario Bear values to stay aligned.

The Risk calculation and production Risk semantics are unchanged.

### F3 — Duplicate CI trigger
Classification: PILOT INFRASTRUCTURE / P2

PILOT-02 used both pull_request and a branch-specific push trigger, which caused duplicate concurrent workflow runs for the same commit.

PILOT-03 removes the branch-specific push trigger. pull_request remains the canonical review execution path and workflow_dispatch remains available for explicit reruns.

This changes CI execution hygiene only. It does not change Investment Core semantics.

## Regression boundary

PILOT-03 explicitly preserves:

- Trust precedence;
- PIT / provenance fail-closed behavior;
- current-price canonical binding;
- Risk semantics;
- Human Approval boundary;
- no automatic execution;
- no scheduler / alerts;
- no CSI800 / A02 dependency;
- no full-market screening.

Targeted regression suite includes:

- PILOT-02 Bear/Risk discipline;
- canonical current-price binding;
- Decision Kernel Trust / Quality precedence.

## Acceptance

PILOT-03 is accepted only when:

- scope check passes;
- touched code compiles;
- targeted regression suite passes;
- git diff --check passes;
- no production semantics are modified.

After merge, PILOT-02 remains the fresh-candidate technical PASS evidence. PILOT-03 does not retroactively change its canonical result.

## Next boundary

Next step is PILOT-04 independent clean replay.

PILOT-04 must replay the accepted PILOT-02 case from a clean canonical main without relying on the diagnostic branch and verify that the same Decision / lifecycle / publication outputs are reproduced.

Human usability observations remain a separate operator-review concern and cannot be inferred from automated tests.
