# C0 Acceptance — Governance Hygiene / Stage Baseline

Date: 2026-10-06
Status: CANDIDATE — READY FOR CANONICAL MERGE

## Acceptance decision

C0 source-level governance boundary = PASS.

## Implemented

- README aligned with B1 v0.3 return/horizon semantics and current Stage C roadmap.
- superseded IIOS_CURRENT_STATE_INDEX explicitly demoted to historical continuity evidence.
- Stage C roadmap restored onto the active development line.
- deterministic state-authority validator added.
- dedicated C0 CI workflow and regression test added.
- PROJECT_STATE_INDEX and STATUS explicitly identify C0 as the current development boundary.

## Verification

Dedicated C0 GitHub Actions run #5:
- compileall: PASS;
- tests/test_c0_state_authority.py: PASS;
- c0_state_authority_validator.py: PASS;
- git diff --check: PASS;
- overall C0 job: SUCCESS.

CORE-00 Scope Reconciliation run #268: SUCCESS.

Investment Core CI run #560:
- 407 tests passed;
- 4 pre-existing CORE-04 assertion failures;
- all four failures are in tests not modified by C0 and match the previously recorded unrelated CORE-04 regression pattern;
- C0 does not modify Decision Kernel, valuation, forecast, MIE, Trust, Quality, Risk, Portfolio, Trigger, Monitoring, or Validation implementation.

Therefore the Investment Core CI failures are recorded as an existing non-C0 blocker and are not silently relabeled as PASS.

## Host configuration note

GitHub main branch protection was observed disabled and no ruleset was exposed through the available management interface. C0 records this as an external repository-configuration follow-up. No source-level acceptance claim treats it as enabled.

## Boundary

C0 does not introduce:
- investment-semantic changes;
- new valuation/MIE capability;
- scheduler;
- alerts/notifications;
- automatic execution/order placement;
- new P3/P4 model families;
- production Kelly/optimizer sizing.

## Next canonical boundary

After C0 merge:

Machine Publication (C1)
→ Human Report / Report Quality Gate (C2)
→ Second Company Acceptance (C3)
