# IIOS State Reconciliation — 2026-10-04

## 1. Purpose
本文件是 2026-10-04 对 IIOS 当前 Git / CI / Investment Core / Forecast Research 状态进行统一核对后的 canonical state reconciliation。
用于消除旧状态文档、历史审计快照与当前 Git 实际状态之间的漂移。

原则：
- 当前 Git 实际状态优先于旧聊天记录。
- 历史审计记录保留原貌，不被回写成“从未存在”。
- 未合并分支/PR 不视为 current main capability。
- CI PASS 只证明对应代码/契约的测试闭环，不扩大为投资有效性证明。
- 收益率目标定义为“正收益率 > 15%”；不设置固定 1–3 年持有期要求，也不使用“年化 >15%”作为当前核心 Gate。

## 2. Canonical Repository State

Repository: `kebofeierdawei5-cloud/convergence-research`

Default branch: `main`

Current main HEAD: `572387e18fd0e1c551a10f6412700d7618e13e43`

Commit: `docs(iios): record 2026-10-04 investment-core architecture decisions`

Parent: `af2a1a6a019872c76ee9a49c4e05c0702b0c7e20`

2026-10-04 HEAD is documentation-only. Its parent contains the latest investment-core implementation and successful CI.

## 3. Merged Investment-Core History

### PR #1 — Initial Investment Decision Vertical Slice
Status: MERGED.
Scope included the initial single-company decision loop, PIT / Trust validation, independent forecast, valuation, market-implied expectation, expectation gap, deterministic action proposal, human approval, immutable snapshot and replay.

### PR #2 — Batch 1-B Company Value Core Scan
Status: MERGED.
Current main therefore DOES contain the Batch 1-B Value Core implementation.

Current main includes:
- structured Value Construction Map / value nodes
- economic attribute validation and deterministic classification
- core-asset scan
- candidate valuation model routing
- decision-engine integration
- profile/model consistency checks
- Tencent / CATL / Kolun structural acceptance tests

Boundary: Batch 1-B is a structured deterministic scanner. It does not claim automatic discovery of all company assets from raw filings, automatic evidence collection, or complete capital-allocation transmission modeling.

### PR #4 — Human-authoritative Company Valuation Model Selection
Status: MERGED.

Canonical boundary:
`Company Value Core Scan → Economic Profile → Candidate Models → HUMAN Primary Model → Model Consistency Gate → Valuation`

The Model Router is advisory only.

Human owns the Primary Model, rationale, material Secondary / Cross-check choices, explicit override decisions, and final investment approval.

Missing human selection / rationale / invalid model / invalid override must fail closed.

Successful CI on the merge parent:
- IIOS MVP v0.1.1 workflow run #53: SUCCESS
- IIOS FM00 Baseline workflow run #52: SUCCESS

## 4. Unmerged / Blocked Investment-Core Work

### PR #3 — Batch 2 Market Model Identification
Status: OPEN, NOT MERGED.

Head: `4f9ed8b6d8bac2b3bc7992772ba0be9188c0a23e`

Canonical disposition: `RED-TEAM BLOCKED`

It must not be treated as a current production capability.

The existing implementation is retained only conceptually as a low-level reverse-valuation primitive.

Do not merge the current Batch 2 v0.1 definition.

Required successor:
`Batch 2 v0.2 Market Model Identification Contract / Implementation`

Target semantics:
`Market Observable Evidence → Candidate Market Models → Historical / Current Fit → Feasible Solution Set → Identifiability → Stability → Reverse Valuation → Market Implied Expectation`

## 5. Current Investment-Core Capability Matrix

| Capability | Current status |
|---|---|
| PIT / Trust / fail-closed validation | IMPLEMENTED |
| Snapshot hashing / Replay | IMPLEMENTED |
| Decision Series / Revision skeleton | IMPLEMENTED |
| Human Approval boundary | IMPLEMENTED |
| Auto execution prohibition | IMPLEMENTED |
| Company Value Core Scan | IMPLEMENTED v1.x |
| Value Construction Map | IMPLEMENTED as structured input/output contract |
| Economic attribute classification | IMPLEMENTED as deterministic classifier |
| Candidate valuation-model generation | IMPLEMENTED |
| Human Primary Model authority | IMPLEMENTED |
| PE / DCF / DDM / SOTP | IMPLEMENTED |
| PS / PB / EV/EBITDA | IMPLEMENTED |
| rNPV basic pipeline support | IMPLEMENTED / EARLY |
| Intrinsic valuation aggregation | IMPLEMENTED / EARLY |
| Bear / Base / Bull valuation range | IMPLEMENTED |
| Model cross-check dispersion | IMPLEMENTED |
| True Market Model Identification | NOT IMPLEMENTED |
| Evidence-based Feasible Solution Set | NOT IMPLEMENTED |
| Evidence-based Identifiability | NOT IMPLEMENTED |
| Temporal / regime Stability | NOT IMPLEMENTED |
| Correct multi-model Market Implied Expectation | NOT IMPLEMENTED |
| General semantic Expectation Gap | NOT IMPLEMENTED |
| Probability / Odds / Edge | EXPERIMENTAL PRIMITIVE, NOT FROZEN |
| Position sizing | EXPERIMENTAL PRIMITIVE, NOT FROZEN |
| Execution Receipt | PARTIAL / NOT COMPLETE |
| Full Trigger lifecycle | PARTIAL / NOT COMPLETE |
| Final production investment decision kernel | NOT YET |

## 6. Return-Target Clarification

Canonical hurdle: **Positive expected return > 15%.**

Current semantics:
- No fixed 1–3 year holding-period requirement.
- No requirement to annualize the return for the core decision gate.
- The system must not reject an opportunity solely because no fixed holding horizon has been declared.
- A future version may separately model holding-period and annualized return, but that is a distinct enhancement and is not part of the current acceptance criterion.
- Current core comparison remains based on the investment opportunity's positive return relative to entry price, with applicable valuation and scenario assumptions explicitly recorded.

The prior proposal to make `Annualized Expected Return > 15%` a mandatory Gate is superseded.

## 7. Forecast Research State

M1.2 remains a separate workstream.

### FM-00
Status: PASS.
PASS means the research-control contracts are internally consistent and defined negative controls reject the targeted leakage / purity violations. It does not prove forecast-model predictive validity.

### FM-01
Implementation foundation: PASS.
CATL historical data population: `BLOCKED_DATA_INGRESS`.

Current repository evidence:
- target driver history: 2021Q1–2026Q2
- expected quarters: 22
- ingested records: 0
- verified records: 0
- exact M1.1 source snapshot: absent

No numeric CATL history may be fabricated or inferred to satisfy coverage.

Next research gate remains exact source admission before FM-02.

## 8. Canonical Research / Investment Tracks

Track A — Investment Decision Core:
`Company Reality → Independent Company Value + Market Observable Reality / Price → Market Implied Expectation → Expectation Gap → Positive Return > 15% → Risk / Trust / Thesis → Decision`

Track B — Forecast Research:
`Historical Driver Data → PIT Feature Builder → State Engine → Conditional Backtest → Validated Forecast Capability → Independent Forecast`

The tracks are independent but eventually meet at Independent Forecast.

## 9. Authority Precedence

1. Frozen governance artifacts and accepted evidence chains.
2. Current canonical Git repository state.
3. Independent CI / execution evidence.
4. Historical audit records, interpreted as point-in-time records.
5. Chat context.

## 10. Immediate Next State

State Reconciliation is complete once current main HEAD, merged/unmerged work, PR #3 BLOCKED status, corrected return hurdle, and separated FM00/FM01 research state are reflected consistently in the canonical continuity documents.

Next engineering work should resume from this reconciled state, not from the older Batch-2-first roadmap.
