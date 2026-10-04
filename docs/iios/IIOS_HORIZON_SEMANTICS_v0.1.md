# IIOS Horizon Semantics v0.1

Date: 2026-10-04
Status: OWNER-APPROVED SEMANTIC FOUNDATION

## Canonical rule

1Y default, 3Y explicit exception, 1–3Y actual holding cycle.

## Decision / Expected Return horizon

1 <= H <= 3 years.
Default: H = 1 year.
H is explicit case data and must not be silently defaulted by code when absent.

H = 3 is permitted only with horizon_override=true plus a qualifying basis:
- MAJOR_INDUSTRY_LEADER
- MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX

Every case must provide horizon_selection_rationale.

H is a reference horizon for return evaluation, not a mandatory exit date.

## Actual holding cycle

IIOS fundamental positions may be held for 1–3 years. The actual holding period is governed by thesis, economics, valuation, risk, market conditions and monitoring, not by automatic expiration of H.

## DCF / valuation explicit forecast length

Valuation models may use a longer explicit operating forecast to model economics and terminal value.
Therefore a 5Y DCF does not imply a 5Y investment-return CAGR.
Valuation forecast length and Decision H are separate fields and semantics.

## Entry Return Cushion

Entry Return Cushion = V_entry_ref / P_entry - 1.
It is non-annualized and independent of H.

## Required Return

Required Return remains an independently constructed annualized comparator. Changing H does not create or alter the Required Return policy.

## Provenance

H, override basis and rationale are case-level policy inputs and must be retained in the case snapshot, decision output and replay lineage.
