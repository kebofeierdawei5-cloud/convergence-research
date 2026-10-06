# C8 — Final Independent Red-team / MVP Acceptance

Date: 2026-10-06
Status: RED-TEAM EXECUTED / ACCEPTANCE BLOCKED

## Canonical baseline

- canonical `main` at C8 entry: `5b56bf59f602734540182fcd1dd6393a1bcdf65f`
- C7 canonical state-sync merge: `a5ac4b8451041bbd38bcaa73fa39954ec6533f02`

Real-company minimum set:
- CATL / CN-A / 300750 / `RC-CN-A-300750-20261004`
- 四川科伦药业股份有限公司 / CN-A / 002422 / `RC-CN-A-002422-20261004`

## Acceptance rule

C8 is acceptance-only and does not modify production behavior.

A safe-control test passes when the attack is rejected or the protected invariant remains intact.

Any unresolved CRITICAL authority or identity bypass blocks final MVP acceptance.

## Red-team surface

PIT leakage; evidence substitution/hash binding; Trust/Quality bypass; forecast contamination; valuation/MIE semantic mismatch; MIE false-identifiability; 15% return gate; Required Return; revision overwrite; approval mismatch; stale/revision-bound triggers; monitoring tampering; replay mismatch; Publication/Report drift; LLM authority escalation; cross-company coupling; hidden automatic execution.

## Dedicated CI evidence

- C8 workflow run #3
- run ID: `37470375959`
- pull-request head: `127f6247c01cfcad3699536c936a9c2643b17f0a`
- Actions job: `112291993869`
- conclusion: SUCCESS
- compileall: PASS
- C8 tests: 14 passed
- executable red-team harness: PASS (reports C8 BLOCKED by reproduced findings)
- git diff --check: PASS

## Result

### Safe controls

The suite exercises:
- both real-company case fixtures;
- current-price PIT rejection;
- independent-forecast PIT rejection;
- expectation-gap unit incompatibility;
- non-unique MIE;
- return/Required Return fail-closed decision state;
- immutable Decision Revision overwrite protection;
- cross-revision Approval binding;
- Monitoring history replay tamper detection;
- Publication/Report deterministic drift detection;
- Execution Receipt rejection without HUMAN_APPROVED status.

### C8-AUTH-001 — CRITICAL

Decision Revision persistence accepts a caller-crafted BUY snapshot whose embedded Trust gate is FAIL and Fundamental Target is false. The persistence boundary verifies integrity/action shape but does not independently verify canonical Decision Kernel provenance.

### C8-AUTH-002 — CRITICAL

Decision Revision persistence accepts a CATL snapshot (`300750`) when the destination decision series is 科伦药业 (`CN-A-002422`). The resulting revision ID is `CN-A-002422-r001`; series/symbol/company identity is not enforced against snapshot identity.

### C8-AUTH-003 — HIGH

Human Approval binds the exact Revision/Revision Hash/Snapshot Hash, but the approval record has no actor identity. The codebase therefore does not technically prove that the approving caller is a human rather than another automated/LLM caller; this is an external authorization boundary.

## Overall disposition

**C8 = BLOCKED / NOT MVP ACCEPTED.**

The red-team controls are mostly fail-closed, but two CRITICAL authority/identity bypasses are reproducible. The production code must not be marked MVP-accepted while these remain exploitable.

No production fix is included in this red-team batch.

## Required remediation before C8 re-run

1. Bind Decision Revision creation to a canonical validated Decision artifact/admission receipt that proves exact Decision Kernel execution, version, case identity and decision outcome.
2. Bind decision series identity (market / symbol / company / case) to the persisted Revision and reject mismatches against the snapshot.
3. Add explicit human-approval actor/authentication evidence, or formally govern an external authorization layer and make the boundary auditable.
4. Re-run the entire C8 suite from a fresh canonical `main` after remediation.

## Separate pre-existing CI debt

The broader Investment Core CI still contains the separately tracked 300750 `primary_reason` regression (407 passed / 4 failed in the governance cleanup validation run). That is not the source of the C8 authority findings and is not reclassified as a Stage C capability gap.
