# IIOS CORE-02 — Company Economic Core v0.1

Date: 2026-10-04
Status: CANDIDATE FOR ACCEPTANCE

## Objective

Turn an admitted single-company Research Case into an auditable company economic representation:

```
admitted company evidence
        ↓
Reality
        ↓
Trust
        ↓
Quality
        ↓
Value Core / Value Driver Ranking
        ↓
Valuation Route
```

CORE-02 is the first layer that makes the case economically researchable. It is not the valuation engine and it does not produce an investment decision.

## Input boundary

CORE-02 consumes:

1. A valid CORE-01 Research Case.
2. Company evidence records whose status is exactly `ADMITTED`.
3. Evidence bound to the exact `case_id`.
4. Evidence satisfying `known_at <= cutoff`.
5. Evidence with exact bytes, source/artifact identity, provenance class and SHA-256.
6. Explicit evidence-linked analytical assessments for Reality facts, Trust, Quality, Value Core and Value Driver Ranking.

CORE-02 does not acquire CSI800, CSI Industry, A02 or universe-level Security Master data.

## Evidence admission

All seven CORE-01 evidence groups remain mandatory for the CORE-02 admission boundary:

- security_identity
- market_price
- corporate_disclosures
- business_reality
- financial_reality
- capital_structure
- trust_governance_events

Non-`ADMITTED`, wrong-subject, duplicate, missing, malformed or post-cutoff evidence fails closed.

The module owns a small core-side evidence admission adapter to preserve the Investment Core namespace boundary. It does not import the historical `research.*` namespace.

## Reality

Reality is an evidence-linked fact set, not a narrative summary.

Each fact carries:

- fact identity and economic field identity;
- observed value and unit;
- observation date;
- explicit basis;
- evidence IDs;
- status: ESTABLISHED / CONDITIONAL / UNKNOWN.

Required coverage spans corporate disclosures, business reality, financial reality and capital structure.

No current-state substitution is permitted for a historical cutoff.

## Trust

Trust is a separate gate from economic quality.

CORE-02 requires explicit assessment of:

- identity;
- disclosure integrity;
- governance integrity;
- shareholder treatment.

Each assessment is evidence-linked and has status PASS / CONDITIONAL / UNKNOWN / BLOCKED.

Aggregate semantics:

- any BLOCKED → BLOCKED;
- any CONDITIONAL or UNKNOWN → CONDITIONAL;
- otherwise → PASS.

## Quality

Quality is not reduced to a single score.

The first six evidence-linked dimensions are:

- competitive advantage;
- incremental return on capital;
- earnings quality;
- cash-flow conversion;
- balance-sheet resilience;
- reinvestment runway.

The aggregate follows the same fail-closed status precedence.

In particular, CORE-02 explicitly exposes the economic chain that later analysis must validate:

```
growth
  → volume / price / mix
  → revenue / gross margin / operating margin
  → reinvestment / CAPEX / D&A
  → FCF
  → incremental ROIC
  → value creation
```

The software does not infer this chain from unverified prose; it requires the analyst/LLM assessment to be evidence-linked.

## Value Core

CORE-02 reuses the existing `scan_company_value_core()` engine.

Each value node must be evidence-linked and include an explicit `assessment_basis`.

The scan derives:

- economic profile;
- core value nodes;
- candidate valuation models;
- deterministic model-suitability route.

The router is advisory only.

## Value Driver Ranking

Value drivers are ordered explicitly by economic importance.

Each driver requires:

- unique ID;
- contiguous rank starting at 1;
- materiality;
- causal mechanism;
- one or more economic variables;
- evidence IDs.

The rank-1 driver must be HIGH materiality.

Supported economic variables include volume, price, mix, revenue, margins, working capital, CAPEX, depreciation/amortization, FCF, incremental ROIC, net debt, share count and payout.

No arbitrary numeric importance score is introduced at CORE-02.

## Valuation Route

The output is:

```
CANDIDATE_SET_ONLY
```

It exposes the economic profile and candidate valuation models from the existing router.

No primary valuation model is automatically selected. Human selection remains the authority under the existing valuation contract.

## Overall CORE-02 status

```
BLOCKED
  if Trust or Quality is BLOCKED

CONDITIONAL
  if Reality is not ESTABLISHED
  or Trust is not PASS
  or Quality is not PASS

PASS
  otherwise
```

A CORE-02 PASS means the company has a sufficiently admitted and explicitly assessed economic representation for the next research layer. It does not mean the company is investable, fairly valued or buyable.

## CLI

Input JSON structure:

```json
{
  "case": { "... CORE-01 Research Case ..." },
  "reality": { "facts": [] },
  "trust": { "dimensions": [] },
  "quality": { "dimensions": [] },
  "value_core": { "version": "1.0", "nodes": [] },
  "value_driver_ranking": []
}
```

Run:

```bash
PYTHONPATH=. python -m iios_mvp.cli economic-core path/to/core02_input.json --generated-at 2026-10-04T01:00:00+00:00
```

Use `--out PATH` to persist the CORE-02 artifact.

## Next boundary

CORE-03 should consume the admitted company economic core and connect:

```
independent forecast
        ↓
company valuation
        ↓
P4-F Market Implied Expectation Set
        ↓
Expectation Gap
```

CORE-03 must not bypass the PIT/provenance/replay guarantees established here.
