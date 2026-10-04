# IIOS B1 — Investment Semantics v0.3 Acceptance

Date: 2026-10-04
Status: COMPLETE — SEMANTICS + RUNTIME MIGRATION ACCEPTED
Baseline: B0 branch repair/b0-authority-audit-freeze-20261004
Semantic branch: repair/b1-investment-semantics-v0.3-20261004

## Owner adjudication

The owner instruction for B1 explicitly requires the Decision Semantics to connect BUY / ADD / HOLD / REDUCE / EXIT / NO-BUY / WATCH / REVIEW_REQUIRED, Unknown, Trust, Investability, Portfolio Constraint and non-mandatory MIE to the repaired return semantics, followed by code migration.

The following B1 semantic package is therefore accepted as the implementation target:

1. 15% BUY Entry Return Cushion is a separate non-annualized entry safety condition.
2. 15% Fundamental Target Annualized Return is a separate 1–3 year hard qualification condition for standard fundamental BUY/ADD.
3. Expected Total Return_H and Expected Annualized Return_H are derived from probability-weighted terminal wealth.
4. Required Return is an independent annualized risk/opportunity-cost comparator and is not added to either 15% condition.
5. Conventional Margin of Safety is distinct from the 15% return-form Entry Cushion.
6. H is explicit and case-specific within 1–3 years.
7. Unknown is not HOLD; unresolved material Unknown states route to REVIEW_REQUIRED unless a definitive policy yields NO-BUY/BLOCKED.
8. Trust is distinct from Investability.
9. Portfolio Constraint is a permission/position layer and cannot rewrite intrinsic value, Quality, Thesis or Expected Return.
10. MIE is explanatory and non-mandatory for BUY/ADD in v0.3.
11. Existing-position decisions use current forward opportunity economics, not historical cost basis.
12. Human approval remains mandatory and no action authorizes automatic execution.

## Implementation boundary

This acceptance authorizes semantic schema/code migration only. It does not claim:
- completed implementation;
- validated Required Return construction methodology;
- validated Entry Value Reference methodology;
- decision-grade MIE necessity;
- production investment capability.

Those are separately testable implementation/evidence questions.

## Runtime acceptance

The v0.3 implementation migration is accepted after exact-head CI evidence:
- runtime/test head: cd4f510301a8a03d0884fe5d816384aef386921e;
- final checked migration tip: cd4f510301a8a03d0884fe5d816384aef386921e;
- 190/190 tests passed;
- compileall passed;
- schema JSON validation passed;
- CLI run passed;
- snapshot replay passed with same_decision=true and integrity_status=PASS;
- code red-team recorded in docs/iios/B1_CODE_MIGRATION_REDTEAM_v0.3.md;
- implementation acceptance recorded in docs/iios/B1_CODE_MIGRATION_ACCEPTANCE_2026-10-04.md.

## Result

B1 is complete. The next repair gate is B2 Data / Evidence / PIT Foundation. MIE remains non-mandatory and P5 feature expansion remains paused.