# A1-01 — Company Economic Evidence Bridge v0.1

Date: 2026-10-05
Status: IMPLEMENTATION TARGET

## Task contract

### Objective

Close the first company-side economic evidence gap with a deterministic, evidence-linked calculation layer for:

```
CAPEX → D&A → FCF
Earnings → OCF → FCF
Working Capital
Incremental ROIC
```

### User Value

The Investment Core must be able to distinguish:

- reported earnings from cash actually generated;
- maintenance/growth investment cash outflow from resulting FCF;
- balance-sheet working-capital cash effects from operating profit;
- incremental economic return from merely high historical ROIC.

The output is an auditable economic bridge, not an investment recommendation.

### Product Surface

New deterministic module:

`calc/company_economic_bridge.py`

Schema:

`schemas/company_economic_bridge_v0.1.schema.json`

The bridge is intentionally upstream of the production Decision Kernel.

### Calculation contract

All monetary inputs are CNY thousand in the current CATL fixture.

**FCF after CAPEX**

```
FCF_after_CAPEX = OCF - CAPEX_cash_paid
```

CAPEX is the reported cash paid for purchase/construction of fixed assets, intangible assets and other long-term assets captured by the existing company financial evidence.

**Core D&A**

```
Core_D&A =
    PPE depreciation
  + right-of-use-asset depreciation
  + intangible amortization
```

Long-term deferred-expense amortization is deliberately excluded from Core D&A in this first slice because it is not conventional D&A.

**Cash-flow conversion**

Primary conversion uses consolidated net income because the OCF is consolidated:

```
OCF_to_Net_Income = OCF / Consolidated_Net_Income
FCF_to_Net_Income = FCF_after_CAPEX / Consolidated_Net_Income
```

Attributable-net-income ratios are retained only as supplementary diagnostics.

**Operating working capital snapshot**

```
Operating_Current_Assets =
    Accounts_Receivable
  + Accounts_Receivable_Financing
  + Prepayments
  + Inventory
  + Contract_Assets

Operating_Current_Liabilities =
    Notes_Payable
  + Accounts_Payable
  + Contract_Liabilities
  + Employee_Benefits_Payable
  + Tax_Payable
  + Other_Payables

Core_Operating_NWC =
    Operating_Current_Assets
  - Operating_Current_Liabilities
```

Cash, trading/derivative financial assets, other receivables, other current assets, interest-bearing debt and other explicitly non-operating/current-financing items are excluded from this first-pass operating NWC policy.

**Working-capital cash bridge**

The cash-flow statement sign convention is preserved:

```
WC_cash_contribution =
    inventory_change_cash_effect
  + operating_receivables_change_cash_effect
  + operating_payables_change_cash_effect
```

A positive value is a net operating cash contribution; a negative value is a net operating cash use.

**NOPAT proxy**

```
Effective_Tax_Rate = Income_Tax / Profit_Before_Tax
NOPAT_proxy = Operating_Profit × (1 - Effective_Tax_Rate)
```

This is explicitly a proxy. It is not presented as a tax-adjusted operating profit reconstruction.

**Incremental ROIC proxy**

For comparable prior/current periods:

```
Incremental_ROIC_proxy =
    ΔNOPAT_proxy
  / ΔInvested_Capital_proxy
```

where:

```
Invested_Capital_proxy =
    Core_Operating_NWC
  + Fixed_Assets
  + Construction_In_Progress
  + ROU_Assets
  + Intangible_Assets
```

The calculation is permitted only when the incremental invested capital is positive. Otherwise the metric is UNKNOWN rather than allowing a misleading denominator.

This first slice is always marked:

```
interpretation_status = CONDITIONAL
investment_decision_effect = NO_DIRECT_GATE_EFFECT
```

A computed Incremental ROIC proxy therefore cannot silently upgrade Quality, Trust, Investability or Decision.

### CATL 300750 evidence closure

The A1-01 fixture uses comparable H1 periods ending 2025-06-30 and 2026-06-30. The 2025 H1 operating-capital anchor is captured in `E012_A1`; the 2026 H1 D&A and cash-working-capital bridge are captured in `E013_A1`. Existing E005/E010 evidence supplies the corresponding reported financial and working-capital observations.

The official 2025 H1 report provides the consolidated 2025-06-30 operating balance-sheet values, including AR, AR financing, prepayments, inventory, contract assets, operating liabilities, fixed assets, construction in progress, ROU assets and intangibles. The same report supplies the 2025 H1 OCF and CAPEX comparison. url2025 H1 CATL reporthttps://static.cninfo.com.cn/finalpage/2025-07-30/1224343223.PDF

The official 2026 H1 report supplies the 2026-06-30 balance-sheet values and the cash-flow supplement with 2026 H1 / 2025 H1 depreciation, amortization and working-capital cash-flow bridge values. url2026 H1 CATL reporthttps://static.cninfo.com.cn/finalpage/2026-07-24/1225442062.PDF

### Expected 300750 result

Using the frozen deterministic fixture:

| Metric | H1 2025 | H1 2026 |
| --- | ---: | ---: |
| Revenue | 178,886,253 | 276,916,580 |
| Consolidated net income | 32,365,447 | 47,030,638 |
| OCF | 58,687,066 | 60,216,851 |
| CAPEX cash paid | 20,212,919 | 25,072,772 |
| FCF after CAPEX | 38,474,147 | 35,144,079 |
| Core D&A | 11,706,109 | 14,817,432 |
| OCF / net income | 181.33% | 128.04% |
| FCF / net income | 118.87% | 74.73% |
| Core operating NWC | -104,711,962 | -139,878,029 |
| Invested capital proxy | 64,803,300 | 81,808,176 |

The comparable-period calculation gives:

```
ΔNOPAT_proxy              ≈ 14,572,399
ΔInvested_Capital_proxy   = 17,004,876
Incremental_ROIC_proxy    ≈ 85.70%
```

This figure is **not** a canonical Quality PASS signal. It is a conditional diagnostic because the invested-capital perimeter and operating-tax treatment are intentionally still conservative proxies.

The more immediate evidence signal is the cash-flow deterioration: the working-capital cash contribution falls from approximately CNY 17.62bn in H1 2025 to approximately CNY 0.80bn in H1 2026, while CAPEX rises and reported earnings grow. This is precisely why A1 must close cash conversion before upgrading Quality.

## Tests / Acceptance

A1-01 passes only when:

1. exact raw-byte size and SHA-256 checks for E012_A1 and E013_A1 pass;
2. deterministic FCF, Core D&A and working-capital cash bridge calculations pass against the CATL fixture;
3. comparable-period Incremental ROIC proxy is deterministic and hash-audited;
4. non-positive incremental invested capital routes to UNKNOWN;
5. evidence-reference duplication and missing inputs fail closed;
6. schema validation passes;
7. tampering is detected by the bridge hash;
8. CI compiles and executes the A1-01 test suite;
9. no P3/P4/MIE logic is added or modified.

## Out of Scope

A1-01 does not:

- change the production Quality Gate semantics;
- automatically upgrade Quality from CONDITIONAL to PASS;
- add valuation models;
- add P3/P4/MIE capability;
- add forecast research capability;
- alter Decision Kernel precedence;
- alter portfolio constraints;
- authorize trading or automatic execution.

## Next A1 slice

After A1-01 is merged, the next narrow slice should close **Capital Allocation + Trust/Governance evidence**, then integrate the completed company-side evidence bridge into the production Quality Gate with explicit status semantics.

