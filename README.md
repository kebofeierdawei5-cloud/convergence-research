# IIOS — Intelligent Investment Operating System

## Project purpose

IIOS is a single-company, candidate-driven investment decision system for China A-shares and Hong Kong equities. Its purpose is to make investment analysis and decisions more repeatable, auditable, point-in-time reproducible, and resistant to LLM failure modes.

The canonical product boundary is:

```
User-selected company + PIT cutoff
        ↓
Evidence / Trust / Reality / Quality / Value Drivers / Thesis
        ↓
Human-authoritative Primary Valuation
        ↓
Independent Forecast
        ↓
Return / Required Return / Risk / Portfolio
        ↓
Decision
        ↓
Human Approval
        ↓
Monitoring
        ↓
Validation / Replay
```

Market Implied Expectation is currently an optional explanatory market-side layer. It does not silently replace the company-side valuation/forecast decision path.

## Current canonical state

The sole current-state authority is:

`docs/PROJECT_STATE_INDEX.md`

This repository is the continuity source for IIOS. Chat history and historical roadmaps do not define current capability.

As of 2026-10-06, the canonical development chain is:

```
G2 R10 Governance Runtime = FROZEN
        ↓
B1 Investment Semantics v0.3 = FROZEN
        ↓
CORE-00 → CORE-04 = PASS / MERGED
        ↓
A0 → A1 = PASS / MERGED
        ↓
RP-01 / DR-01 / DR-02
        ↓
TR-01 Trigger = PASS / CANONICAL
        ↓
TR-02 Monitoring = PASS / CANONICAL
        ↓
TR-03 Validation / Replay = PASS / CANONICAL
        ↓
Stage C Productization
```

Current real-company accepted case:

```
300750 / CATL
Quality = CONDITIONAL
Trust = REVALIDATION
Expected Annualized Return_H ≈ 14.20%
Required Return = 10%
Decision = REVIEW_REQUIRED
New Capital = FALSE
```

This is an accepted system result, not a recommendation to purchase the security.

## Stage C roadmap

The current next-stage development plan is:

`docs/iios/IIOS_STAGE_C_PRODUCTIZATION_PLAN_v0.1.md`

Sequence:

```
C0 Governance Hygiene / Stage Baseline
        ↓
C1 Machine Publication
        ↓
C2 Human Report + Report Quality Gate
        ↓
C3 Second Company Acceptance
        ↓
C4 Expectation Gap Production Integration
        ↓
C5 Positioning / Sizing
        ↓
C6 Human Execution Receipt
        ↓
C7 Full Lifecycle E2E
        ↓
C8 Final Independent Red-team / MVP Acceptance
```

The parallel Forecast Research Track remains separate:

```
FM-01 Exact Source Admission
        ↓
FM-02 PIT Feature Builder
        ↓
FM-03 Driver State Engine
        ↓
FM-04 Conditional Backtest
        ↓
Research Validation / Prospective Shadow
```

## Current product boundaries

Investment Core remains:

- single-company and candidate-only;
- PIT-bound;
- fail-closed for missing, stale, conflicting, or unverifiable material evidence;
- human-authoritative for final approval and execution.

The system does not automatically place orders.

The following are not currently authorized on the Stage C critical path:

- scheduler;
- alerts / notifications;
- automatic execution;
- automatic order placement;
- broad full-market stock screening;
- new P3/P4 market-model family expansion;
- production Kelly / portfolio optimizer sizing.

Scheduler and alerts require a separate explicit governance batch after the Validation boundary is already canonical.

## Repository authority

```
canonical main
    >
docs/PROJECT_STATE_INDEX.md
    >
normative contracts / schemas / production tests
    >
independent CI evidence
    >
historical records
    >
chat context
```

Known superseded state documents are retained for audit history and must not be treated as current requirements or roadmap.

## Engineering constitution

See `AGENTS.md`.

Core rules include:

- do not fabricate missing data;
- fail closed on material uncertainty;
- keep Trust, Thesis, Valuation, Quality and Investment Attractiveness distinct;
- keep AI Proposal and Human Decision separate;
- keep historical records append-only;
- keep deterministic state/calculation/permission/persistence outside LLM control;
- never weaken tests to obtain PASS;
- keep each development batch narrow and explicitly scoped.

## Forecast Research: FM-00 baseline

FM-00 is the research-control baseline, not proof of forecast predictive validity.

Validation:

```bash
python -m pytest -q research/fm00/tests/test_fm00.py

python research/fm00/fm00_validator.py \
  --epoch research/fm00/RE-EXPLORATORY-CATL-20260930.json \
  --plan research/fm00/RP-M12-FM00-EXP-001.json \
  --candidate-space research/fm00/CS-M12-FM00-CATL-001.json \
  --outer-universe research/fm00/OU-M12-FM00-CATL-001.json \
  --purity-boundary research/fm00/EPB-M12-FM00-EXP-001.json
```

Current FM-01 data population remains blocked until the exact hash-bound historical CATL source snapshot is admitted.
