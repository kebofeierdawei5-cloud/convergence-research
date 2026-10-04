# IIOS B1 — Return Semantics Red-Team v0.3

Date: 2026-10-04
Status: REVIEW OF PROPOSED SEMANTICS
Parent: B1 Return Semantics ADR v0.3

## Attacks

1. Same 15% hidden under two field names
Attack: target_annualized_return = entry_hurdle = 15%.
Expected: FAIL.
Reason: different economic objects and bases.

2. Annualize the old intrinsic-value ratio
Attack: BaseIntrinsicValue / EntryPrice − 1 is labeled as 1–3Y annualized expected return.
Expected: FAIL.
Reason: current intrinsic value is not automatically terminal wealth at H.

3. Probability-weight scenario annualized returns directly
Attack: Σ p_s × annualized_return_s.
Expected: FAIL as primary metric.
Reason: primary metric annualizes probability-weighted terminal wealth.

4. Add Required Return to the 15% entry threshold
Attack: required_threshold = 15% + RR.
Expected: FAIL.
Reason: entry cushion and risk compensation are distinct non-additive conditions.

5. Put Margin of Safety inside Required Return
Attack: RR = opportunity cost + risk premium + MoS premium.
Expected: FAIL unless a future contract proves non-overlap.
Reason: valuation protection and risk compensation cannot silently charge the same uncertainty twice.

6. Treat 15% return cushion as 15% conventional MoS
Attack: MoS = EntryReturnCushion = 15%.
Expected: FAIL.
Reason: 15% return cushion corresponds to about 13.0435% conventional MoS.

7. Make H implicit
Attack: annualized return without a declared H.
Expected: FAIL.
Reason: annualization requires explicit elapsed horizon.

8. Use different H across scenarios
Attack: Bear=1y, Base=2y, Bull=3y and combine directly.
Expected: FAIL.
Reason: primary scenario wealth must be comparable at one common H.

9. Use historical cost basis for HOLD
Attack: current opportunity is weak but historical cost basis is low, so HOLD.
Expected: FAIL as economic rationale.
Reason: current capital allocation is assessed from current opportunity economics.

10. Missing data defaults to 15%
Attack: missing H, probability or value reference is silently completed.
Expected: FAIL / BLOCKED.
Reason: semantic completion by placeholder is prohibited.

11. Treat target 15% as entry cushion
Attack: set BUY_ENTRY_RETURN_CUSHION_THRESHOLD = FUNDAMENTAL_TARGET_ANNUALIZED_RETURN.
Expected: FAIL semantically even if both values equal 15%.
Reason: different basis and role.

12. Convert 15% annualized target into 15% total return for 3 years
Attack: H=3, require total return >=15%.
Expected: FAIL.
Correct target total return: 52.0875%.

13. Circular conservative value
Attack: derive V_entry_ref from current market price so the 15% cushion is almost guaranteed.
Expected: FAIL.
Reason: entry reference must be independently derived.

14. False probability precision
Attack: use 0.30/0.50/0.20 without forecast rationale.
Expected: FAIL for decision-grade probability use.
Reason: arithmetic validity is not evidentiary validity.

15. Hidden risk haircut plus separate RR
Attack: valuation applies a risk haircut and RR separately charges the same risk.
Expected: FAIL unless separate purposes are proven.
Reason: prevents double counting.

## Red-team conclusion

The proposed return mathematics is internally coherent and blocks the major known failure modes.

The target-gate ambiguity is resolved for the standard fundamental strategy: Expected Annualized Return_H >= 15% is a hard BUY/ADD qualification condition. A Human override, if ever permitted, must be explicit as a strategy-policy exception and cannot silently repurpose the entry threshold.
