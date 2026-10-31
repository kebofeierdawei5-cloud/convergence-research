# B69 — Price-implied operating feasibility audit

Date: 2026-10-31

**Status: BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## 1. Objective

B68 translates B61/B63 price-implied normalized-profit requirements into alternative product sales-volume, net-ASP and unit-variable-cost solutions. B69 adds a separate feasibility layer: which parts can be checked against the current B4 operating plan, and which remain unidentified because the current typed input contract contains no supporting evidence.

B69 does not convert a mathematical sensitivity into a forecast. It is read-only and does not alter B4, B55, B61–B68, SOTP, MIE, expectation_gap, the 15% annualized hurdle, target entry price, portfolio constraints or Decision.

## 2. Capacity and production bridge

For each B61 and B63 lens, separately and non-additively:

- Read B68's product-specific \`sales_volume_only.required_sales_volume_tonnes\`.
- Read B4's forward production and sales, then independently reconcile \`inventory_change_tonnes = production_tonnes - sales_volume_tonnes\`.
- Calculate conditional required production as:

\`required_production = required_sales_volume + B4_forward_inventory_change\`

This explicitly holds the B4 forward production-sales inventory movement unchanged. It is not a claim that opening inventory is available, or that this inventory policy is operationally approved.

Only an explicitly full-year forecast period (FY2027 / 2027FY / equivalent supported full-year label) can be compared with the annual \`capacity_tonnes_per_year\` measure. A positive required production above positive nameplate capacity is marked \`EXCEEDS_NAMEPLATE_CAPACITY\`. A result within nameplate is only \`WITHIN_NAMEPLATE_CAPACITY_CONDITIONAL\`; it does not verify effective capacity, utilization ramp, maintenance, product changeover, yield, logistics or shared-line constraints.

Missing inventory movement, capacity, a full-year period or reconciled production-sales values remain \`NOT_IDENTIFIABLE\`. A production-sales balance mismatch blocks the capacity conclusion.

## 3. Non-capacity constraints

The current B4 typed schema supplies annual nameplate capacity, production, sales, ASP, unit variable cost, cash capex, effective working capital and FCF fields. It does not supply a complete typed, cross-referenced operating feasibility dataset for:

- order book coverage, customer demand, contracted volume or customer qualification;
- demand elasticity, competitive pricing and price realization under a required ASP change;
- product cost curves, raw-material/energy procurement, yield, labour productivity or executable cost-saving projects;
- expansion project commissioning date, ramp schedule, incremental effective capacity or bottleneck removal; and
- project-level incremental capex and incremental working-capital funding.

Accordingly, B69 displays the required ASP and unit-cost changes but labels their commercial feasibility \`NOT_IDENTIFIABLE\`. It never treats an ASP increase as achievable merely because the algebra is valid, nor a unit-cost reduction as achievable without a cost curve or executable initiative.

## 4. Inventory, working capital and cash

B69 reads the B4 inventory reconciliation status, effective working-capital amount, cash capex and FCF proxy. It does not add the B42 inventory cash proxy a second time, recompute FCF, or assume incremental expansion capex is zero. B69 does not independently rerun B43's cross-node comparison between effective B4 working capital and the valuation operating-financial bridge; that existing reconciliation remains a separate check and is not implied to pass by B69.

If B4 inventory/working-capital treatment is not reconciled, B69 records the blocker. Even when B4's current FCF bridge is usable, the additional cash requirements of the B68-implied volume, capacity expansion or working-capital build remain unidentified unless separately evidenced.

## 5. Output placement and statuses

New module: \`iios_mvp/sotp_operating_feasibility_audit_v01.py\`

Nested output: \`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.operating_feasibility_audit\`

Status vocabulary:
- \`CAPACITY_CONSTRAINT_IDENTIFIED\`: at least one required production level exceeds annual nameplate capacity under the unchanged-inventory assumption.
- \`CAPACITY_ARITHMETIC_CONDITIONALLY_WITHIN_NAMEPLATE\`: all evaluated capacity checks fit nameplate; demand, pricing, cost and incremental funding remain unverified.
- \`PARTIAL\`: some numerical capacity checks exist but one or more required inputs/periods/constraints are unidentified.
- \`NOT_IDENTIFIABLE\`: no usable capacity conclusion.
- \`BLOCKED_BY_B68_SCHEMA\`: B68 result schema is not the expected contract.

B61 and B63 required-profit lenses remain separate and are explicitly tagged non-additive. Overall operational feasibility is always NOT_IDENTIFIABLE while typed demand, pricing, cost-curve and incremental-funding evidence is absent. No composite score, probability of success or automatic risk haircut is introduced.

## 6. Regression coverage and acceptance

Nine cases are authored in \`tests/test_sotp_operating_feasibility_audit_v01.py\`:
1. required production exceeds nameplate capacity;
2. required production conditionally fits capacity;
3. missing inventory movement blocks production inversion;
4. annual capacity comparison rejects non-full-year period;
5. missing nameplate capacity remains unidentified;
6. demand, price elasticity, cost curve and incremental funding are not inferred;
7. B61/B63 thresholds remain separate and non-additive; and
8. production-sales balance is independently rechecked against the B4 scenario row and mismatches block the capacity result; and
9. B4 capex / effective working capital / FCF remain unchanged.

Per the operator's development preference, tests have not been executed. Replay, CI, unified test suite and real macOS acceptance remain deferred / not verified. No PASS is claimed.
