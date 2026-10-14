# B4 — Operating-driver forecast bridge (2026-10-14)

## Decision on sequencing

The B3 real macOS rerun is deferred, not waived. PR #422 changed the operator prompt default and its exact-head CI passed; the local acceptance is still pending. B4 is code-independent of the Mac prompt path and can proceed on canonical main while that operator-environment check remains open. Do not mark the B3 real-run criterion complete.

## Objective

Extend the existing local, non-canonical research handoff with a typed operating-driver tree that separates reported actuals, issuer forecasts, analyst assumptions and unknowns. Reuse the current local runner, return/entry-price solver, decision kernel and report. This is not a second forecast admission or valuation engine.

## Input contract

IIOS-OPERATING-DRIVER-FORECAST-0.1 carries:

- Scope: PROJECT_INCREMENTAL, PRODUCT_LINE, COMPANY_WIDE or UNKNOWN.
- Product/line capacity and historical actuals: production, sales volume, net realized ASP and variable cost per unit.
- Bear/Base/Bull operating inputs: production, sales volume, net ASP, variable unit cost, cash fixed operating expenses (excluding D&A), depreciation/amortization, finance costs, tax-rate ratio, cash capex and working-capital change.
- Each scalar carries value, unit, data_class, basis, evidence_refs and note.
- Historical actuals are calculation-eligible only as `OBSERVED_ACTUAL`; issuer forecasts or analyst assumptions cannot leak into the actuals bridge. Bear/Base/Bull forward scenarios accept only `ISSUER_FORECAST` or `ANALYST_ASSUMPTION`; do not move a realized-actual label into a forward scenario without building an explicit forecast.
- Known reported/issuer numbers require resolved source references and cutoff-compatible source timing for use in calculations. Analyst assumptions are permitted only as labeled assumptions. Unknown fields remain null.
- Duplicate/malformed product rows invalidate that scenario's aggregate totals; the engine must not choose one conflicting duplicate silently.

## Deterministic calculations

For each product: revenue = sales volume × net ASP; variable cost = sales volume × variable unit cost. The scenario bridge calculates contribution after variable cost, EBITDA, EBIT, pre-tax profit and simplified after-tax net profit when required inputs are available. A free-cash-flow proxy is calculated only when EBIT/tax, D&A, capex and working-capital change are all available. Production utilization is shown only when production and annual capacity are both available and the relevant period is explicitly a full year (for example `2026FY`). Quarter, half-year, multi-year and unknown period labels do not permit dividing production by annual nameplate capacity; utilization remains UNKNOWN with `CAPACITY_PERIOD_ALIGNMENT_UNKNOWN`. An aligned full-year over-capacity result produces a review finding rather than silent adjustment.

## Explicit non-claims

- Source timing compatibility does not prove formal Evidence/PIT admission.
- Issuer capacity-release/project-year values are not actual shipments or realized earnings.
- Product revenue divided by production is not an accepted realized ASP shortcut.
- Project net profit is not automatically company EPS or per-share value. Project attribution versus demand migration/cannibalization, diluted shares/convertible-bond scenarios and valuation-model transmission remain explicit B5 inputs.
- The operating bridge cannot override the existing price/return gates, human model selection, unknown evidence, shared decision kernel or human approval boundary.
- No formal Forecast Admission, Decision Revision, trade permission or automatic execution is created.

## 605016-specific controls

Keep the domestic functional-sugar drying expansion separate from the Thailand plant. The disclosed planned output/price/profit table is an issuer forecast only. The 7,800/10,400/13,000-tonne ramp plan versus the prospectus project-year 3/4/5 basis remains RAMP_CALENDAR_BASIS_UNRECONCILED until cutoff-appropriate evidence reconciles it. Product-specific actual shipments, net ASP, unit variable costs and attributable profit remain unidentified unless later disclosures support them.

## Acceptance

1. The existing one-click handoff asks for the driver tree and permits explicit unknowns without inventing data.
2. Unit/schema validation prevents wrong-unit values or unsourced claims labeled actual/issuer forecast from being used in arithmetic.
3. Bear/Base/Bull outputs show missing drivers and intermediate results instead of filling gaps with inferred values.
4. Report displays the operating bridge and existing per-share values side by side while plainly marking value transmission as not linked.
5. Focused CI passes; Mac acceptance remains a separate, later user-environment action.
