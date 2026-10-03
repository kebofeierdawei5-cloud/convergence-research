# IIOS MVP v0.1 — Minimal Investment Decision Product

## Objective

在不等待 A02、完整 M1.2、G2/R0 治理重建的情况下，先形成一个可实际使用的单家公司投资决策闭环。

## One vertical slice

一家公司 + As-of cutoff → 证据 → Trust → Reality → Independent Forecast → Valuation → Market Implied Expectation → Expectation Gap → Risk → AI Decision Proposal → Human Approval → Immutable Snapshot → Replay

## First-version product surfaces

1. JSON case contract：人或 LLM 都可以填写。
2. Deterministic decision engine：负责 PIT、门槛、估值、隐含预期、预期差、风险与 action。
3. Markdown investor report：供实战阅读。
4. Immutable snapshot：内容哈希命名，禁止覆盖。
5. Separate human approval record：AI proposal 与 human decision 不合并。
6. Replay：对同一 snapshot 重算并逐项比较。

## Deliberately not in v0.1

- CSI800 历史成分与完整 A02 PIT Security Master
- Forecast Model Selection / rolling-origin research
- 多模型估值路由器
- 完整 G1/G2 权限图与服务身份隔离
- 自动交易、券商下单
- 组合优化与自动仓位推荐
- 多公司筛选

## Reuse decisions

AdvancingTitans/stock-analysis：MIT；借鉴 evidence-first、source/time validation、claim/thesis/workspace、deterministic derivation、investor-facing report contract 与真实业务验收思路。第一版不直接复制其大型代码库，避免把 IIOS 需求反向绑定到其产品结构。

xbtlin/ai-berkshire：MIT；借鉴价值投资研究技能/检查清单、as-of date discipline、反向质询与成本控制方法。第一版不引入其多 Agent 产品规模。

SignalLayerLabs/Blum：Apache-2.0；借鉴 evidence → thesis → risk-gated decision → measured outcome 的验证方向。第一版只保留 snapshot/replay/后续 outcome validation 的最小骨架。

## Acceptance

- demo case：BUY path PASS。
- future evidence：PIT leak → fail closed。
- Trust FAIL：新 BUY/ADD 被阻断；已有仓位不自动 EXIT。
- missing forecast input：不能由模型补值，必须 BLOCKED。
- snapshot：不可被不同内容覆盖。
- replay：相同输入必须得到完全相同 decision。
- auto_execution：恒为 false。

## Product rule

开源项目是实现参考，不是 IIOS 需求来源；每一个后续功能必须先能回答“它提升哪个原始投资决策能力”。
