# C1 Acceptance — Machine Publication

Date: 2026-10-06
Status: ACCEPTED / CANONICAL

## Acceptance decision

C1 = PASS / MERGED / CANONICAL.

Canonical merge commit: b9a8ff0fe1341a56f363fb058677dbd50a4f87b8.

C1 source-level Machine Publication boundary = PASS.

## Implemented

- Added immutable, content-addressed Machine Publication projection.
- Bound publication to an exact Decision Revision and Snapshot.
- Preserved AI Decision and Human Approval as distinct fields.
- Exposed current-projection status without mutating canonical lifecycle state.
- Included bound Trigger / Monitoring / Validation references.
- Added source-binding and integrity-hash checks.
- Added idempotent immutable persistence.
- Added the iios-mvp publish CLI command.
- Added JSON Schema and dedicated C1 CI.
- Added unit, schema, lifecycle-binding, immutability, tamper, and CLI tests.

## Verification

Dedicated C1 GitHub Actions run #6:
- compileall: PASS;
- tests/test_machine_publication.py: PASS;
- machine-publication JSON Schema syntax: PASS;
- git diff --check: PASS;
- overall C1 job: SUCCESS.

Relevant existing module regression workflows on the same head also passed:
- CORE-01 = SUCCESS;
- CORE-02 = SUCCESS;
- CORE-03 real 300750 = SUCCESS;
- DR-02 = SUCCESS;
- TR-01 = SUCCESS;
- TR-02 = SUCCESS;
- TR-03 = SUCCESS.

Investment Core CI remains a separate existing regression issue:
- 407 tests passed;
- 4 existing CORE-04 assertion failures;
- failure set is the same known QUALITY_GATE_UNRESOLVED / TRUST_NOT_PASS_REQUIRES_REVIEW regression pattern;
- C1 changed only publication/schema/CLI/test/workflow files and did not modify Decision Kernel or those failing tests.

## Red-team boundary

Verified design constraints:
- Publication is a projection, not a Decision source.
- Publication cannot approve/reject a decision.
- Publication cannot mutate Decision Revision, Monitoring State, or Validation State.
- Trigger / Monitoring / Validation references are checked against the exact Decision Revision.
- Source tampering fails closed.
- Re-publishing unchanged content is idempotent.
- Changed publication input produces a new content-addressed artifact; old bytes are retained.
- Missing approval/lifecycle objects are not fabricated.
- No scheduler, alerts, automatic execution, automatic order placement, or new P3/P4/MIE capability is introduced.

## Next boundary

C2 — Human Report + Report Quality Gate.