# B51 — Side-Specific Evidence Linkage for Driver-Level FCF Measures

**Status:** implemented on the feature branch; unmerged and non-canonical. **Validation:** three additional regression cases are authored but not run. Tests, Replay, CI, and real macOS acceptance remain deferred / not verified.

## Red-team finding

B50 required the combined union of B4-side and normalized-side evidence to overlap a review trigger, and allowed the parent attribution amount to overlap either side's evidence. That did not prove each side was independently linked: one side could have evidence unrelated to the driver trigger, while the other side satisfied the union-level check. The normalized-side measurement could also cite a trigger but fail to link to the normalized aggregate component input being decomposed.

## Implementation

For every structured `driver_component_measure`, the engine now independently checks:

1. **B4-side → same-driver trigger:** B4 component measurement evidence must intersect the evidence references on that driver's `review_trigger_id`.
2. **Normalized-side → same-driver trigger:** normalized-side component measurement evidence must independently intersect the same trigger evidence.
3. **Parent amount → both sides:** the parent `amount_cny` evidence references must intersect the B4-side measure evidence and the normalized-side measure evidence separately. Intersection with only their combined union is insufficient.
4. **Normalized-side → aggregate component inputs:** normalized-side evidence must intersect every corresponding normalized-FCF component input used to substantiate the category. For `OPERATING_CASH_CONVERSION`, this is checked separately against both normalized EBIT and tax-rate evidence; for other categories, the component fields follow the existing B49/B50 category and inventory-treatment contract.
5. **Visible audit result:** the machine-readable measurement object records each linkage result and a field-by-field normalized-component linkage map. The Chinese report prints those outcomes alongside both side-specific reference sets and the computed contribution.

A missing trigger reference, an unlinked B4 or normalized side, a parent amount not linked to either side, or a normalized component provenance gap blocks the driver measure. The scenario remains `REVIEW_REQUIRED`; the engine still does not create valuation eligibility or decision authority.

## Boundary

These controls validate *reference linkage*, evidence timing/resolution under the existing evidence-register rules, and numerical reconciliation. They do **not** semantically inspect source documents to prove that their contents support the exact amount; that remains a research/adjudication task. A shared citation is not proof of causal attribution. If independent driver amounts cannot actually be substantiated, retain the single-row B49 diagnostic path or `REVIEW_REQUIRED`; do not invent an allocation.

B51 does not change B4/B5/B6, the selected valuation model, required-return hurdle, entry-price calculations, portfolio constraints, formal Evidence/PIT admission, Decision, or execution authority.

## Regression cases and verification status

Three new cases are authored in `tests/test_cycle_earnings_monitor_v01.py`:

- A B4-side evidence set that fails to overlap the driver trigger is rejected even when normalized-side evidence overlaps it.
- Parent attribution evidence that links to only one measurement side is rejected.
- Normalized-side evidence that does not link to the aggregate normalized component input is rejected.

The B50 success fixture now explicitly includes references that satisfy the stricter individual links and asserts the reported linkage flags. The source/test changes have **not been executed**. No test pass, Replay match, CI pass, macOS acceptance, formal Forecast/Valuation admission, or execution authority is claimed.
