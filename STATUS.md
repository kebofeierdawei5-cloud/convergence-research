# IIOS Project Status

State classification: **CANONICAL SUMMARY**
Date: 2026-10-05

Authoritative current-state record:
`docs/PROJECT_STATE_INDEX.md`

This file is a concise human-readable summary. When it conflicts with the Current State Index, the Current State Index wins.

## Current stage

**A0 Governance / State Cleanup = PASS / MERGED**

**A1-01 Economic Evidence Bridge = PASS / MERGED**

**A1-02 Capital Allocation + Trust/Governance Evidence Closure = PASS / MERGED**

**A1-03 Quality Gate Integration = PASS / MERGED**

**A1 Company-side Evidence Closure = PASS / MERGED**

CORE-04 vertical decision closure is complete. A1 company-side evidence closure is now complete.

No P3/P4/MIE model work was added to A1.

## Canonical Investment Core

```
Reality
→ Quality / Thesis / Value Driver
→ Primary Valuation
→ Independent Forecast
→ Return H
→ Risk
→ Portfolio
→ Optional MIE
→ Decision
```

The production Decision Kernel is merged and the real 300750 chain has passed E2E.

## 300750 accepted result

- Price: 291.11 CNY/share
- Quality: CONDITIONAL
- Thesis: INTACT / ADMITTED
- Trust: REVALIDATION
- H: 3Y explicit override; system default remains 1Y
- Expected Annualized Return: about 14.20%
- Required Return: 10%
- Risk: PASS
- MIE: OPTIONAL / absent
- Decision: REVIEW_REQUIRED
- New capital: FALSE

## Development boundary

Investment Core remains single-company and PIT-bound.

CSI800 / CSI Industry / historical-universe reconstruction and FM forecast research remain separate Research Track workstreams and do not block the core.

## A1 status

A1-01 established the deterministic CAPEX → D&A → FCF, Earnings → OCF → FCF, Working Capital and Incremental ROIC proxy layer for the real 300750 case. The bridge is CONDITIONAL and has no direct Decision Kernel gate effect.

A1-02 established the deterministic capital-allocation and Trust/Governance evidence bridge. It is CONDITIONAL where the evidence does not establish broader economics, fairness or governance history.

A1-03 integrates both evidence bridges into the existing Quality / Trust / Quality Gate semantics with fail-closed status capping and no direct Decision Kernel semantic change.

For the canonical 300750 case, A1 leaves Quality Gate = CONDITIONAL, Trust = CONDITIONAL, capital admission = FALSE, and decision_effect = NO_DIRECT_GATE_EFFECT.

Acceptance records:
- docs/iios/A1_01_ACCEPTANCE_2026-10-05.md
- docs/iios/A1_02_ACCEPTANCE_2026-10-05.md
- docs/iios/A1_03_QUALITY_GATE_INTEGRATION_v0.1.md
- docs/iios/A1_ACCEPTANCE_2026-10-05.md

## Product gaps after CORE-04

- Company-side evidence completeness
- Risk / Portfolio production contract
- Decision Revision / Human Approval lifecycle
- Trigger / Monitoring / Validation
- Machine Publication
- Human Report / Report Quality Gate
- second-company acceptance
- final independent red-team

## Governance rule

All new development starts from:

```
canonical main
    ↓
docs/PROJECT_STATE_INDEX.md
    ↓
relevant normative contract
```

Historical documents are context only. Diagnostic branches / PRs are not capability until merged.