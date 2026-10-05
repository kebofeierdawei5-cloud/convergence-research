# DR-01 Acceptance — Decision Revision / Human Approval Lifecycle Contract

Date: 2026-10-05
State classification: **CANONICAL**

## Acceptance decision

**DR-01 = PASS / MERGED**

Canonical merge:
- PR #85;
- merge commit: 60e054db6454ec33c01c166e86eafe342c9feb37.

## Accepted semantics

- immutable decision revision;
- exact snapshot-hash binding;
- exact revision-hash + snapshot-hash approval binding;
- monotonic current projection;
- rejected/older revisions cannot replace current approved state;
- conflicting approval for the same current revision is rejected;
- human approval does not mutate AI action;
- auto_execution is always false;
- no Decision Precedence / valuation / forecast / P3 / P4 / MIE semantic change.

## Verification

Independent execution of the canonical module/test logic after the regression-fixture correction:
- compileall = PASS;
- pytest = **8 passed**;
- decision lifecycle schema JSON validation = PASS.

The original regression exposed a stale/non-canonical previous-projection fixture. It was corrected to use a real canonical prior projection.

GitHub Actions workflow: .github/workflows/iios_dr_01.yml.
The available GitHub workflow interface did not expose a runtime result for PR #85 or the merge commit. Therefore:
- independent execution = PASS;
- GitHub Actions telemetry = UNOBSERVED.

No claim is made that an unobserved workflow run passed.

## Canonical boundary

DR-01 freezes lifecycle semantics but does not yet integrate them into store.py / CLI.

Next:
**DR-02 Persistence + CLI Integration**.

No P3/P4/MIE work is part of DR-01.