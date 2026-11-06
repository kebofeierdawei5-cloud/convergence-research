# B78 — EPS_MULTIPLE 来源谱系与传导准入审计

Date: 2026-11-06  
Branch: feat/b76-core-integrated-20261101  
Status: Draft proposal only; not merged to main.

## Objective

Audit the actual code path from B57 forward all-items EPS through B58 consistency, the B60 price-conditioned EPS requirement inversion, and B76 arithmetic comparison. Preserve the current investment-policy and fail-closed boundaries. This batch does not redesign B55/B56 or relax missing-input rules.

## Findings and changes

### 1. B57 carries mixed input provenance

B77 calculates a conditional FY all-items EPS from a reconciled reported-period financial-statement amount bridge plus explicit Q4 analyst assumptions and a separately supplied annual weighted-average diluted-share assumption. Its output previously retained a legacy data_class=ANALYST_ASSUMPTION label without explicitly disclosing that the numerator also includes reported actual periods.

B78 adds source_data_classes, combined_output_data_class and provenance_components. The B77 path now identifies MIXED_OBSERVED_ACTUAL_AND_ANALYST_ASSUMPTION and separately labels reported actual periods, Q4 assumptions, and the annual diluted-share assumption. The legacy data_class remains for compatibility and is documented as describing the conditional forecast inputs, not the entire actual-plus-assumption calculation.

The ordinary B55/B56/B57 path carries source classes from forward B55 product-driver measures, B56 forward financial measure lineage, and B57 forward attribution inputs. It does not turn analyst assumptions into issuer forecasts or verified actuals.

### 2. B58 separates numeric similarity from reconciliation

For a primary EPS bridge with status ASSUMPTION_ONLY, B58 may display whether the B57 EPS proxy is numerically close to the declared primary EPS. It now sets:
- numeric_similarity_to_primary_declared_eps: boolean diagnostic
- eps_match: null
- status: PRIMARY_EPS_ASSUMPTION_ONLY
- independent_confirmation_status: NOT_ESTABLISHED_PRIMARY_EPS_ASSUMPTION_ONLY

For a fully calculated primary earnings bridge, B58 can still emit MATCH, but explicitly states this is arithmetic reconciliation only, not independent source confirmation or formal admission.

### 3. B60 preserves provenance into the price-inversion path

B60 carries B57 combined source class and the primary adapter EPS source class / evidence references. This is metadata relay only; it does not alter the existing inversion arithmetic.

### 4. B76 uses explicit fail-closed provenance gates

B76 requires:
- B60 scenario calculation complete;
- B57 scenario in an allowed forward EPS state;
- B58 status exactly MATCH and same-period confirmation;
- B57 combined source class identified;
- primary adapter EPS source class identified;
- price reference matches the structured operator price;
- EPS, P/E, Required Return, Fundamental Target and validated-distribution arithmetic reconcile.

If B58 is PRIMARY_EPS_ASSUMPTION_ONLY, or source class is missing, the scenario remains NOT_IDENTIFIABLE; B76 does not publish Required Return / Fundamental Target EPS headroom for that scenario.

B76 keeps three separate concepts:
- Required Return: the existing decision_parameters.required_return_annualized input;
- Fundamental Target: the separately configured fundamental_target_annualized_return;
- Target entry price: read-only relay of the existing Return Solver output.

No B76 code substitutes one hurdle for the other, changes the solver, or modifies MIE / the valuation / Decision.

## Regression coverage added

- B76 blocks B58 PRIMARY_EPS_ASSUMPTION_ONLY.
- B76 blocks missing B57 forward data class.
- B58 does not publish eps_match=true for an assumption-only primary EPS bridge.
- B77 output explicitly reports mixed actual / analyst-assumption provenance.
- B76 test fixture reports data classes for both B57 and the primary EPS and checks the target-entry-price relay.

## Real-case limitation

The Xinhecheng case still lacks Q4 Bear/Base/Bull inputs, annual weighted-average diluted shares, and operator-attested current price. No genuine FY2026 EPS, B60 inversion, or BUY / NO-BUY decision is produced. B55/B56 physical-driver blockers and historical normalization UNKNOWN remain unchanged.

## Validation boundary

The prior exact-head Linux run at B77 had 463 passed / 1 failed; the sole failure was an invalid test setup combining 2026Q1-Q3 with a 2026FY bridge while expecting a comparable full-year baseline. The current PR head had already corrected that fixture to 2025FY → 2026FY. B78 adds new code and tests, so only Actions results attached to the new exact commit can validate this batch.

macOS workflow cancellation is not treated as a test failure or a pass. Real operator Mac full-flow and Replay acceptance remain NOT VERIFIED. PR #587 remains Draft and must not be merged to main.
