# HISTORICAL PROPOSAL / SUPERSEDED — 2026-10-05

This ADR records the pre-adjudication B1 proposal. The authoritative accepted semantics are in IIOS_INVESTMENT_CORE_CONTRACT_v0.3.md, B1 Decision Semantics v0.3, and the accepted B1 migration package. Preserve this document for audit history; do not treat its PROPOSED status as current.

# IIOS B1 — Return Semantics ADR v0.3

Date: 2026-10-04
Status: PROPOSED FOR OWNER ADJUDICATION
Scope: Investment Core return, entry threshold, safety margin and horizon semantics
Parent baseline: d209b33b7f922866f2fdc1190785c27edb8a28e4
Repair branch: repair/b1-investment-semantics-v0.3-20261004

## 1. Decision intent

B1 replaces the incumbent single 15% hurdle concept with six semantically distinct objects:

1. BUY Entry Return Cushion
2. Margin of Safety
3. Expected Total Return
4. Expected Annualized Return
5. Required Return
6. Long-term Fundamental Investment Target Annualized Return

The fact that two policies currently use the number 15% MUST NOT cause them to share one variable, field, or calculation.

## 2. Owner-confirmed dual-15% distinction

The owner has explicitly confirmed:
- 15% is a BUY-entry threshold / desired safety-margin requirement.
- 1–3 year annualized return >=15% is a separate long-term expectation for a fundamental investment.

These are two different concepts.

B1 therefore treats them as distinct policy objects:
BUY_ENTRY_RETURN_CUSHION_THRESHOLD = 15%
FUNDAMENTAL_TARGET_ANNUALIZED_RETURN = 15%

They are not aliases.

## 3. Horizon semantics

A fundamental investment case has an explicit primary valuation horizon:
H ∈ [1, 3] years

H is selected per case according to the thesis and economics. There is no single mandatory H for all companies.
H is the period over which expected investment outcome is evaluated.

H is not:
- the definition of the entry threshold;
- a proxy for Required Return;
- permission to annualize an otherwise non-horizon-specific valuation result after the fact.

Scenario valuation outputs used for the primary annualized return calculation MUST use the same H.

## 4. Entry Return Cushion

Entry Return Cushion is the minimum return-like price cushion supplied by an independently derived conservative entry value.

Let:
- P_entry = intended entry price in the decision currency;
- V_entry_ref = independently derived conservative entry-value reference at the decision date.

Entry Return Cushion = V_entry_ref / P_entry − 1

Canonical BUY-entry threshold:
Entry Return Cushion >= 15%

The 15% threshold is a price-to-independent-value safety requirement, not an annualized holding-period performance forecast.

V_entry_ref MUST:
- be derived from the company-side independent valuation;
- be independent of current market price except for the final ratio comparison;
- carry its own model, assumptions, evidence and version;
- be deterministic/replayable once its inputs are frozen.

V_entry_ref is a valuation reference, not a market-implied expectation.
The exact construction of V_entry_ref is a B5 valuation-policy dependency and MUST be explicitly versioned.

## 5. Conventional Margin of Safety

To prevent terminology ambiguity, IIOS MAY report conventional value-relative Margin of Safety separately:

MoS = 1 − P_entry / V_entry_ref

This quantity is not numerically identical to Entry Return Cushion.

MoS = Entry Return Cushion / (1 + Entry Return Cushion)

At the policy threshold:
- Entry Return Cushion = 15%
- MoS = 13.043478...%

Conversely:
- MoS = 15%
- Entry Return Cushion = 17.647058...%

Therefore the system MUST NOT label a 15% return cushion as 15% MoS without qualification.

For repaired IIOS, the normative 15% entry policy is the return-form cushion. Conventional MoS is a derived diagnostic unless separately governed.

## 6. Horizon Wealth and Expected Return

The incumbent v0.2 calculation intrinsic value / entry price − 1 is not sufficient to represent a 1–3 year annualized fundamental-investment outcome because current intrinsic value and terminal investment wealth are different economic objects.

For each scenario s ∈ {Bear, Base, Bull}:
- V_H,s = expected equity value per share realizable at horizon H;
- D_H,s = cumulative per-share cash distributions received between entry and H;
- W_H,s = V_H,s + D_H,s = scenario terminal wealth per share attributable to entry capital.

All scenario values MUST use the same currency, share-count basis, corporate-action treatment and horizon.

## 7. Expected Total Return

With validated scenario probabilities p_s:

E[W_H] = Σ p_s × W_H,s

Expected Total Return_H = E[W_H] / P_entry − 1

This is a holding-period return, not an annualized rate.

## 8. Expected Annualized Return

For H > 0:

Expected Annualized Return_H = (E[W_H] / P_entry)^(1/H) − 1

This is the primary return metric for the 1–3 year fundamental-investment objective.

The system MUST NOT replace it with:
Σ p_s × AnnualizedReturn_s

as the primary calculation. Scenario probabilities are applied to terminal wealth first; annualization is applied once to expected wealth.

## 9. Long-term Fundamental Investment Target

FUNDAMENTAL_TARGET_ANNUALIZED_RETURN = 15%

For horizon H:
Target Total Return_H = (1 + 15%)^H − 1

Examples:
- H = 1.0 → 15.00%
- H = 2.0 → 32.25%
- H = 3.0 → 52.09%

Thus 15% annualized over 1–3 years is not equivalent to a single 15% total-return hurdle.

The target is a distinct strategic metric. For the standard fundamental-investment strategy, B1 adopts it as a hard qualification condition for BUY/ADD: Expected Annualized Return_H MUST be >= 15%. This does not turn the target into the Entry Return Cushion, and a Human override must be explicitly labeled as a strategy-policy exception rather than silently weakening the target.

## 10. Required Return

Required Return is the minimum annualized economic return required to compensate for opportunity cost and the investment's risk.

Define RR_annual as an annualized benchmark determined independently of the 15% target and Entry Return Cushion.

For horizon H:
RR_total_H = (1 + RR_annual)^H − 1

B1 policy:
- RR is a capital/risk compensation benchmark.
- RR MUST NOT contain the 15% Entry Return Cushion.
- RR MUST NOT contain the 15% long-term target.
- RR MUST NOT include an uncertainty premium that is also charged through the valuation entry cushion.
- required_return = 15% + risk_premium + MoS is invalid.

Comparison:
Expected Annualized Return_H >= RR_annual

RR is compared, not added.

## 11. Non-double-counting rule

The concepts have different jobs:

| Object | Meaning | Basis | Role |
|---|---|---|---|
| BUY Entry Return Cushion | Price-to-conservative-value safety buffer | non-annualized | Entry safety gate |
| Margin of Safety | Value-relative discount from reference value | ratio | Derived diagnostic unless separately governed |
| Expected Total Return_H | Probability-weighted wealth return over H | total return | Outcome metric |
| Expected Annualized Return_H | Annualized expected wealth return over H | annualized | Fundamental outcome / target comparison |
| Required Return | Risk/opportunity-cost compensation | annualized | Risk adequacy comparison |
| Fundamental Target Annualized Return | Long-term strategy objective | annualized | Strategy target |

No object may silently absorb another object's semantics.

## 12. Proposed BUY return gate

Subject to Decision Semantics, B1 proposes:
1. Entry Return Cushion >= 15%;
2. valid scenario probabilities when probability-weighted Expected Return is used;
3. Expected Annualized Return_H >= RR_annual;
4. Expected Annualized Return_H >= FUNDAMENTAL_TARGET_ANNUALIZED_RETURN for standard fundamental BUY/ADD.

This is a conjunction, not an additive hurdle.

15% + RR is invalid.
15% + target 15% is invalid.

## 13. Existing-position rule

For HOLD / REDUCE / EXIT, return analysis MUST use current decision price and current forward economics.
Historical cost basis MAY be displayed but MUST NOT determine whether newly deployed capital is attractive.

## 14. Missing-data and fail-closed rules

The repaired return layer MUST fail closed for BUY/ADD when material inputs are missing, ambiguous or unverifiable:
- entry price;
- conservative entry-value reference;
- horizon H;
- scenario terminal wealth;
- valid probabilities when required;
- currency/share-count/adjustment mismatch;
- PIT-invalid valuation inputs;
- semantic version mismatch.

The system MUST NOT fabricate 15%, probabilities, H or valuation inputs.

## 15. Migration mapping from v0.2

Incumbent:
RETURN_HURDLE = 15%
expected_return_pct = expected_value / entry_price − 1
hurdle_pass = expected_return > 15%

These are historical v0.2 semantics and MUST NOT be copied forward as v0.3 meanings.

Migration requires explicit fields for:
- entry return cushion policy;
- conventional MoS diagnostic;
- horizon H;
- scenario terminal wealth;
- expected total return;
- expected annualized return;
- required return;
- long-term target annualized return.

## 16. B1 acceptance criteria

B1 Return Semantics is PASS only when:
1. dual 15% distinction is explicit;
2. Entry Return Cushion is mathematically defined;
3. conventional MoS is distinguished from the return-form cushion;
4. H is explicit and case-specific within 1–3 years;
5. Expected Total Return and Expected Annualized Return are distinct;
6. annualization is applied to expected terminal wealth, not average annualized scenario returns;
7. Required Return is independent and non-additive;
8. risk/safety double counting is prevented;
9. current price/cost basis semantics are separated;
10. implementation fields can map one-to-one to these meanings.

## 17. Status

B1 Return Semantics: PROPOSED — READY FOR OWNER ADJUDICATION

This ADR freezes the proposed economic definitions and calculation relationships. It does not authorize implementation/schema changes until the complete B1 semantic package, including Decision Semantics, is accepted.
