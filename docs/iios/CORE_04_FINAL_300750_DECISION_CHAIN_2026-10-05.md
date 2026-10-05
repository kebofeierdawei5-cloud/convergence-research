# CORE-04 × 300750 Final Decision Chain — 2026-10-05

## Acceptance status

**VERTICAL E2E PASS / DECISION REVIEW_REQUIRED / NO NEW CAPITAL**

Canonical main base for this E2E:
`91f18cc1c8b4bdc6f80053462ec5e9ce7b89d0cb`

This is the final vertical execution after PR #72 merged the Quality Gate and Thesis Admission layer.

## Decision chain

```
Reality
  ↓
Quality Gate
  ↓
Value Driver
  ↓
Primary Valuation
  ↓
Independent Forecast
  ↓
Return H
  ↓
Risk
  ↓
Portfolio
  ↓
Optional MIE
  ↓
Decision
```

## Horizon semantics

IIOS default horizon is **1Y**.

The CATL real case uses an explicit **3Y Horizon Override** because the case satisfies both existing exception bases:

- `MAJOR_INDUSTRY_LEADER`
- `MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX`

The E2E explicitly verifies:

`DEFAULT_HORIZON_YEARS = 1`

and independently:

`SELECTED_HORIZON_YEARS = 3`

This prevents an exception from silently becoming the global default.

## Upstream admission

For case `RC-CN-A-300750-20261004`:

- Reality = **PASS**
- Quality Gate = **CONDITIONAL**
- Value Driver = **PASS**
- Primary Valuation = **PASS**
- Independent Forecast = **PASS**
- Thesis Admission = **ADMITTED**
- Thesis = **INTACT**
- Trust = **REVALIDATION**

The Quality Gate remains conditional because CORE-02 still does not have a fully admitted incremental-ROIC bridge and several earnings/cash-flow quality dimensions remain conditional.

## Primary valuation / forecast

Primary DCF reference carried from the admitted CORE-03 case:

- Bear = 258.32 CNY/share
- Base = 418.49 CNY/share
- Bull = 638.97 CNY/share
- Probability = 25% / 50% / 25%
- Probability-weighted value = 433.5675 CNY/share

Independent forecast remains the admitted 2027–2029 bottom-up scenario package. No broker consensus and no FM01 production router are introduced.

## Return / Risk / Portfolio

At current price **291.11 CNY/share**:

- Entry Return Cushion = **48.94%** → PASS
- Margin of Safety = **32.86%**
- Expected Total Return over 3Y = **48.94%**
- Expected Annualized Return = **14.2001%** → FAIL versus 15% target
- Required Return = **10%** → PASS
- Risk Gate = **PASS**
- Return/risk target-entry price = **285.08 CNY/share**
- Portfolio position = **0%**
- Portfolio constraint = **PASS**
- Buy/add package = structurally complete

Therefore the current price does not clear the 15% annualized-return target even before considering the unresolved upstream Quality/Trust gates.

## Optional MIE

MIE is absent in this case.

CORE-04 policy remains:

`OPTIONAL_EXPLANATORY`

Absence of MIE does not veto or create the investment decision.

The P3/P4 outside-historical-support condition remains independently fail-closed; no market-implied expectation is substituted for intrinsic-value analysis.

## Final Decision

### Strict real case

```
Trust = REVALIDATION
Quality = CONDITIONAL
Thesis Admission = ADMITTED
Expected Annualized Return = 14.2001%
MIE = OPTIONAL_EXPLANATORY
        ↓
REVIEW_REQUIRED
        ↓
new_capital_allowed = FALSE
```

Primary reason:

`TRUST_NOT_PASS_REQUIRES_REVIEW`

### Quality-isolated diagnostic

The same case was run with Trust explicitly normalized to PASS, without changing the other real inputs:

```
Quality = CONDITIONAL
        ↓
REVIEW_REQUIRED
        ↓
QUALITY_GATE_UNRESOLVED
        ↓
new_capital_allowed = FALSE
```

This proves the Quality Gate is now actually connected to the production decision boundary rather than merely stored as descriptive analysis.

## System acceptance

Final CI checkpoint:

- Investment Core CI #468 — **PASS**
- CORE-00 #205 — **PASS**
- Full pytest — **380 passed**
- compileall — **PASS**
- JSON schema parsing — **PASS**
- existing P2/P3 real 300750 E2E — **PASS**
- final CORE-04 decision-chain tests — **PASS**

## Engineering conclusion

CORE-04 now has a functioning vertical decision boundary for a real company.

The remaining blocker is **not** another MIE / P3 / P4 model.

The remaining substantive investment-core gap is upstream evidence completeness:

1. incremental ROIC / cash-conversion evidence must be upgraded from conditional to admitted when justified;
2. Trust must be fully revalidated when the governance/disclosure history is complete;
3. further price/decision monitoring must operate downstream of this frozen decision boundary.

No automatic execution is authorized. Human approval remains mandatory.
