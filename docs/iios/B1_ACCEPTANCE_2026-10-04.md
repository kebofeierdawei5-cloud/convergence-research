# IIOS B1 — Investment Semantics v0.3 Acceptance

Date: 2026-10-04
Status: APPROVED FOR IMPLEMENTATION MIGRATION
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

## Next step

Create a successor code-migration branch from this exact semantic head. The first migration slice must replace the single v0.2 return-hurdle semantics with explicit v0.3 fields and deterministic calculations, while preserving old v0.2 behavior only as immutable historical/legacy-isolation reference.