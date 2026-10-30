# B59 — Primary EPS difference attribution

Date: 2026-10-30  
Status: **BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## Goal

B58 establishes whether B57 all-items EPS and the EPS actually used by EPS_MULTIPLE can be compared. B59 answers the next question: where does the signed numerical gap come from? It attributes the parent-profit numerator difference through the B57 and primary earnings bridges, then decomposes the per-share gap into numerator, diluted-share denominator and primary adapter EPS-input effects.

## Placement

The output is nested at `operating_driver_forecast.baseline_transition.primary_eps_difference_attribution` inside the existing B4 node. It is attached after the final EPS bridge/B5 revalidation and after B58, so it reads the same finalized primary EPS and earnings bridge. It adds no top-level analysis key and is automatically included by the existing B4 Replay field.

## Profit numerator attribution

For each Bear/Base/Bull scenario, the B57-to-primary parent-attributable profit difference is decomposed as:

- B56 modeled net-profit proxy gap: B57 B56 after-tax proxy minus primary EPS-bridge B4 net-profit proxy.
- Recurring non-operating after-tax effect from B57.
- Non-recurring after-tax effect from B57.
- NCI attribution difference: primary bridge NCI less B57 all-items NCI.
- Unmapped primary other after-tax attribution adjustment, shown with the subtractive sign used in the primary bridge.

The component sum must reconcile to the observed difference between B57 all-items parent-attributable profit and primary bridge parent-attributable profit within CNY 1. B57 and primary profit-component identities are independently recalculated before attribution.

## Per-share attribution

B59 decomposes:

`B57 all-items EPS − EPS_MULTIPLE declared EPS` =
- profit-numerator effect;
- diluted-share denominator effect; and
- primary bridge calculated EPS minus the declared EPS actually used by the adapter.

When share counts differ, numerator and denominator effects use a symmetric Shapley-style split so the two contributions sum to the total EPS difference without choosing an arbitrary calculation order. The denominator mismatch remains an explicit comparability flag. No false like-for-like status is granted.

## Guardrails

- COMPANY_WIDE scope, CNY currency, matching B58 forecast period, reconciled B57 and a CALCULATED primary earnings bridge are prerequisites.
- Missing components, invalid units, non-positive shares, unreconciled parent-profit identities or a primary EPS that does not match primary parent profit divided by diluted shares remain blocked or mismatched.
- Non-zero primary after-tax attribution adjustments are separately quantified but flagged as unmapped; denominator mismatches are decomposed mathematically but remain not comparable.
- Assumption-only primary EPS receives no fabricated profit attribution.
- B59 is explanatory only: it does not select the correct earnings path, replace any EPS input, adjust P/E or terminal values, alter B5/B6, return metrics, target entry price, the 15% annualized hurdle, Decision, formal admission or execution authority.

## Regression cases and validation

Four regression cases are authored: signed profit-component decomposition plus adapter EPS-input gap; denominator Shapley effect plus explicit unmapped adjustment; assumption-only upstream bridge blocking; and report visibility/boundary. They have not been executed. No Replay, CI, merge or macOS acceptance is claimed.
