# B70 — Operating feasibility evidence contract and threshold linkage

Date: 2026-10-31

**Status: BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## 1. Objective

B69 can identify nameplate-capacity arithmetic constraints, but the current B4 contract does not contain structured, cutoff-aware claims for customer demand, price realization, product unit cost, effective capacity/ramp timing or incremental expansion funding.

B70 adds an optional typed input contract, links each claim to the existing evidence register, validates its product/scenario/period/unit and point-in-time source references, and compares the linked value with the corresponding B69 threshold. The B69 result is not overwritten.

## 2. Input placement

The optional top-level pilot input is:

`operating_feasibility_evidence`

Schema:

`IIOS-OPERATING-FEASIBILITY-EVIDENCE-0.1`

Each row in `records` must contain:

- `record_id`: unique claim-row ID;
- `claim_type`: one of the enumerated claim types below;
- `product_id`: exact B4/B68 product ID;
- `scenario`: exactly `bear`, `base` or `bull`;
- `forecast_period`: exact B69/B4 forecast period label;
- `value` and `unit`: numeric value/unit, except date claims;
- `data_class`: `OBSERVED_ACTUAL`, `ISSUER_FORECAST` or `ANALYST_ASSUMPTION`;
- `basis`: what the measure represents, including its scope and measurement basis;
- `evidence_refs`: one or more source IDs already present in the case evidence register; and
- `comparison_basis`: required for incremental funding claims.

Example:

```json
{
  "schema_version": "IIOS-OPERATING-FEASIBILITY-EVIDENCE-0.1",
  "records": [
    {
      "record_id": "DEMAND-BASE-P1-01",
      "claim_type": "SUPPORTED_SALES_VOLUME",
      "product_id": "P1",
      "scenario": "base",
      "forecast_period": "FY2027",
      "value": "12000",
      "unit": "tonnes",
      "data_class": "ISSUER_FORECAST",
      "basis": "Non-overlapping signed customer orders deliverable in FY2027",
      "evidence_refs": ["EVIDENCE-001"]
    }
  ]
}
```

No record is auto-created from B68's own mathematical requirement. A derived target must never be recycled as its own supporting evidence.

## 3. Enumerated claim types

| Claim type | Unit | Comparison |
|---|---|---|
| `SUPPORTED_SALES_VOLUME` | tonnes | Must be at least the B68 volume-only requirement |
| `SUPPORTED_NET_ASP` | CNY/tonne | Must be at least the B68 ASP-only requirement |
| `SUPPORTED_UNIT_VARIABLE_COST` | CNY/tonne | Must be no higher than the B68 cost-only requirement |
| `EFFECTIVE_CAPACITY_AVAILABLE` | tonnes/year | Must cover B69 required production |
| `CAPACITY_AVAILABLE_DATE` | date | Must be available by the full-year forecast end |
| `INCREMENTAL_CAPEX_REQUIRED` | CNY | Compared with funded capex |
| `INCREMENTAL_CAPEX_FUNDED` | CNY | Funding available against required capex |
| `INCREMENTAL_WORKING_CAPITAL_REQUIRED` | CNY | Compared with funded working capital |
| `INCREMENTAL_WORKING_CAPITAL_FUNDED` | CNY | Funding available against required working capital |

Both sides of an incremental funding comparison must declare:

`comparison_basis = INCREMENTAL_TO_B4_FORWARD_PLAN`

All funding claims are incremental to the existing B4 forward plan. B70 does not infer an incremental funding need by subtracting or reusing an unrelated B4 cash-capex/working-capital total.

## 4. Source, PIT and semantic safeguards

Every reference must resolve to one unique row in the existing evidence register, be known by the case cutoff, and declare one of `ISSUER_PRIMARY`, `EXCHANGE_PRIMARY` or `REGULATOR_PRIMARY`. A source-class/domain mismatch, duplicate ID, after-cutoff source, unknown/insufficient timing, missing source or analyst-only assumption blocks the numerical comparison.

A link marked `PIT_COMPATIBLE_PRIMARY_CLASS_DECLARED_NOT_ADMITTED` means only that the source ID is unique, its known time is cutoff-compatible and its declared source class is primary. It does not prove the URL's content, the claim's semantic relationship to the source, or formal Evidence/PIT admission. The report retains source class/domain status and record basis for human review.

`ANALYST_ASSUMPTION` records are visible but cannot corroborate operating feasibility. An analyst cannot create evidence by attaching a source ID to a model-generated assumption.

## 5. Duplicate and alignment rules

- Exact `product_id`, `scenario` and `forecast_period` matching is mandatory. A FY2028 record cannot support a FY2027 requirement; a base record cannot support bear/bull.
- At most one aggregate record is permitted for each `scenario + product_id + forecast_period + claim_type`. Duplicate rows are flagged as ambiguous and are **never summed**, because order backlog/contracts can overlap.
- Each record ID must be unique.
- The required annual capacity availability date is derived only for a supported full-year period. Half-year, quarter or unknown periods do not inherit December 31 as an invented period end.
- The sales-volume, ASP, unit-cost and capacity comparisons remain independent conditional comparisons. B70 does not model demand elasticity, a price/volume feedback loop, product substitution, supply-chain yield, utilization ramp or production-line constraints.

## 6. Output and status

New module: `iios_mvp/operating_feasibility_evidence_v01.py`

Nested output:

`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.operating_feasibility_evidence_assessment`

B70 displays record-level status and references, per-product threshold comparisons, capacity availability date and paired capex/working-capital funding comparisons.

Status vocabulary includes:
- `EVIDENCE_NOT_PROVIDED`;
- `INVALID_INPUT_SCHEMA` / `INVALID_RECORDS`;
- `EVIDENCE_LINKAGE_NOT_ELIGIBLE`;
- `LINKED_EVIDENCE_IDENTIFIES_CONDITION_GAP`; and
- `PARTIAL_EVIDENCE_LINKAGE`.

Even when a linked claim numerically covers a threshold, the overall operating feasibility status remains `NOT_IDENTIFIABLE_PENDING_HUMAN_SOURCE_CONTENT_REVIEW_AND_COMPLETE_COVERAGE`. This is deliberate: a number can be traceable without its source meaning being independently checked.

## 7. No-change boundary

B70 is optional and backward-compatible when omitted. It does not modify B4/B42/B43/B55/B61–B69, the selected SOTP, external MIE, expectation_gap, the 15% annualized return hurdle, target entry price, portfolio constraints or Decision. It creates no formal evidence/forecast/valuation admission and no execution authority.

## 8. Regression coverage and acceptance

Eighteen regression cases are authored in `tests/test_operating_feasibility_evidence_v01.py`, covering:
- missing/invalid evidence input;
- exact numeric comparison of supported sales, net ASP, unit cost and effective capacity;
- linked-claim shortfall;
- after-cutoff, non-primary, domain-mismatch, analyst-only, duplicate-source and duplicate-record blocking;
- strict scenario/period alignment and unresolved-reference blocking;
- non-additive duplicate claim handling;
- full-year-only capacity availability date;
- late capacity commissioning overriding a sufficient capacity quantity; and
- incremental capex / working-capital requirement-to-funding comparisons.

Tests have not been executed. Replay, CI, unified tests and real macOS acceptance remain deferred / not verified. No PASS is claimed.
