# IIOS B1 Horizon Semantics Amendment AM-01

Date: 2026-10-04
Status: OWNER-APPROVED — PENDING CI / MERGE
Parent: IIOS Investment Core Contract v0.3

## Decision

The B1 horizon semantics are formally amended to:

1Y default, 3Y explicit exception, 1–3Y actual holding cycle.

## Normative rules

- Default Decision / Expected Return reference horizon: H = 1 year.
- H = 3 years requires horizon_override = true.
- A 3Y override must explicitly cite MAJOR_INDUSTRY_LEADER and/or MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX.
- Every case records horizon_selection_rationale.
- horizon_override is false for H other than exactly 3.
- Entry Return Cushion remains non-annualized and independent of H.
- Actual holding cycle remains 1–3 years; H is a reference/evaluation horizon, not an expiry date.
- DCF explicit forecast length is independent of H. A 5Y DCF does not create a 5Y investment-return CAGR.

## Implementation boundary

The shared runtime module iios_mvp/horizon_semantics.py is the single semantic validator used by:
- B1 Investment Core return / decision runtime;
- CORE-03 forecast contract validation.

The JSON Schema and adversarial tests enforce the same rule.

## CATL

CATL uses:
- H = 3;
- horizon_override = true;
- basis = MAJOR_INDUSTRY_LEADER + MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX.

The existing ~14.20% figure is therefore a CATL 3Y Expected Return Reference, not the IIOS default return horizon.

## Non-claims

This amendment does not change the 15% Entry Return Cushion, change the 15% Fundamental Target, turn H into a holding-period deadline, require DCF explicit forecast length to equal H, make MIE mandatory, or authorize automatic execution.
