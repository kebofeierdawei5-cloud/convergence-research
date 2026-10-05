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

CORE-04 vertical decision closure is complete. A1 company-side evidence closure is now in progress.

Current next substantive batch:

**A1-03 Quality Gate Integration**

No new P3/P4/MIE model work is on the critical path.

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

A1-01 has established the deterministic CAPEX → D&A → FCF, Earnings → OCF → FCF, Working Capital and Incremental ROIC proxy layer for the real 300750 case. The bridge is CONDITIONAL and has no direct Decision Kernel gate effect.

A1-01 established the deterministic economic bridge; A1-02 established the capital-allocation and Trust/Governance evidence bridge. Both are upstream evidence layers with no direct Decision Kernel gate effect.

A1 remains incomplete until the closed company-side evidence is integrated into existing Quality semantics and tested end-to-end.

Acceptance records:
- `docs/iios/A1_01_ACCEPTANCE_2026-10-05.md`
- `docs/iios/A1_02_ACCEPTANCE_2026-10-05.md`

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