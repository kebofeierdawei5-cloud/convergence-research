# C8 Acceptance — 2026-10-06

Status: **PASS / MERGED / CANONICAL**

## Canonical baseline

- Canonical main SHA: `c99763a9eae957e59c238590ad64b00bc308e54b`
- Remediation PR: #116
- PR merge commit: `c99763a9eae957e59c238590ad64b00bc308e54b`
- C8 rerun: Actions Run #30
- C8 rerun event: `push` from canonical `main`
- C8 tested head: `c99763a9eae957e59c238590ad64b00bc308e54b`

## Scope

C8 remediated and then re-executed the complete authority boundary rather than adding a single regression test.

### AUTH-001 — Decision Revision authority binding

Canonical v0.3 Decision Revision persistence now requires a Decision Admission Receipt.

The production admission path re-validates the case and re-executes the canonical Decision Kernel. The admission receipt binds the validated case identity, snapshot hash, and canonical Decision projection. Revision replay reuses the exact stored admission binding.

Result: **PASS**.

### AUTH-002 — Decision Series identity binding

Decision Revision persistence now checks the target Decision Series against snapshot market, symbol and company identity. The admission receipt additionally binds case_id and cutoff_date.

Result: **PASS**.

### AUTH-003 — Human Approval authorization boundary

Human Approval now requires a non-empty `actor_identity` and `authorization_method = HUMAN_AUTHENTICATED`. Both fields are included in the immutable approval hash.

Result: **PASS**.

## Full C8 verification

The canonical-main C8 workflow reports:

- 36 tests passed;
- compileall passed;
- C3 second-company Kolun end-to-end harness: PASS;
- C7 full lifecycle harness: PASS;
- git diff --check: PASS.

The same canonical-main rerun also restored the dependent lifecycle checks:

- C1 Machine Publication: PASS;
- C2 Human Report: PASS;
- C3 Second Company: PASS;
- C6 Human Execution Receipt: PASS;
- C7 Full Lifecycle E2E: PASS;
- DR-01: PASS;
- DR-02: PASS;
- TR-01: PASS;
- TR-02: PASS;
- TR-03: PASS.

## Boundary conclusion

C8 does not add investment capability, scheduler/alerts, automatic execution, universe expansion, or new forecasting/valuation model families.

The three authority boundaries are now enforced at persistence/validation boundaries rather than only by test convention.

No post-C8 development boundary is inferred automatically; subsequent work requires an explicit canonical governance decision.
