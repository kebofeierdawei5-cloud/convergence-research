# IIOS — Intelligent Investment Operating System

## Personal local use — simplest launch

For the personal Mac workflow, update to the latest `main` and double-click the repository-root **`启动IIOS投资分析.command`**. The guided flow asks for the company/code, market, cutoff, position and manually checked price; opens ChatGPT, the input template, and a dedicated JSON response file. Paste the full ChatGPT response into that file, save it, then press Enter in Terminal; the program validates it and opens the Chinese report automatically. The full response is no longer read from the clipboard or pasted into Terminal. No long terminal command, manual JSON path, paid API key, or local model is required.

This first-run path is explicitly `PILOT_NON_CANONICAL`: it is for real-world workflow testing, not formal evidence admission or a canonical Decision. Use [the short guide](docs/iios/LOCAL_INVESTMENT_PILOT_V01_GUIDE_20261011.md).

For **real macOS end-to-end acceptance + output hash checks + genuine Replay**, use the [current 2026-10-21 runbook](docs/iios/MACOS_REAL_E2E_ACCEPTANCE_RUNBOOK_20261021.md). Recommended path: download a successful ZIP artifact from the [IIOS macOS launcher distribution workflow](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/workflows/macos-launcher-distribution.yml), unzip it, and run **IIOS_一键启用并验收.command**. The ZIP contains only one launcher: `IIOS_一键启用并验收.command`. Double-clicking it checks the latest public `main` SHA, runs an isolated verified copy under `~/.iios-private/source/`, and automatically enters full first-run + Replay acceptance without a second menu. If macOS says the script lacks execute permission, run it through `/bin/bash` as shown in the runbook; do not keep repeating `chmod` or disable Gatekeeper. The response-file flow validates one complete JSON object, retries through a generated repair prompt, restores operator-owned input fields from the trusted local template, then runs first-bundle checks + Replay + Replay-bundle checks. See the [historical detailed guide](docs/iios/MACOS_FULL_RUN_AND_REPLAY_ACCEPTANCE_20261015.md) for additional context, but use the 2026-10-21 runbook when instructions differ. The harness remains `PILOT_NON_CANONICAL`; the acceptance must run on the operator's Mac, not just in CI.

---

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

## Canonical return semantics

B1 v0.3 keeps these as separate semantic objects:

- Entry Return Cushion: non-annualized entry safety threshold, currently 15% for standard BUY/ADD;
- Margin of Safety: separate value-relative diagnostic;
- Expected Total Return_H;
- Expected Annualized Return_H: standard fundamental BUY/ADD target is at least 15%;
- Required Return: independent risk/opportunity-cost benchmark;
- Horizon H: 1Y default, with explicit 3Y override only when justified by policy.

The two 15% policies are numerically equal but are never aliases and are not added together.

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
