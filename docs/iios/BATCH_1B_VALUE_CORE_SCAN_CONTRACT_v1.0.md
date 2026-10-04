# IIOS Batch 1-B｜Company Value Core Scan / Value Construction Map v1.1

## Purpose

将“公司价值构成 → 业务/资产分层 → 经济属性 → 核心资产 → 估值模型路由”做成确定性的最小上游契约。

它不是完整的公司研究 AI，也不是自动从互联网发现全部资产；它要求研究层先提供经过证据约束的结构化 value nodes，然后由代码完成校验、分类、路由和核心资产扫描。

## Contract

Input:

- version = 1.0
- nodes[]，至少一个
- 每个 node：
  - id
  - name
  - node_type
  - materiality
  - ownership_pct（默认 100）
  - economic_attributes

node_type:

- operating_business
- subsidiary
- pipeline
- investment_asset
- cash
- debt
- minority_interest
- financial

economic_attributes:

- earnings_stability
- cash_flow_visibility
- capital_intensity
- cyclicality
- asset_intensity
- reinvestment_intensity
- payout_characteristic
- pipeline_optionality
- maturity

level fields use NONE / LOW / MEDIUM / HIGH.

maturity uses MATURE / COMMERCIAL / DEVELOPMENT.

## Output

每个 value node 得到：

- derived_economic_profile
- candidate_valuation_models
- model_route（candidate models + suitability；不输出权威 primary selection）r_suggestion（仅提示，不具备决策权）
- independent_valuation_required
- core_value_reasons

公司级得到：

- overall_economic_profile
- model_router_input
- model_route
- value_structure
- core_assets

## Deterministic boundary

规则不由 LLM 自由决定：

Company Value Core Scan = 结构化节点 + 固定经济属性分类规则 + 固定 Model Suitability Router（仅生成候选集与适配性排序，不选择最终主模型）。

LLM 可以负责研究、证据解释和生成候选节点，但不能把未经结构化的自然语言结论直接当成确定性扫描结果。

## Materiality / Core Asset Rule

最小版本把以下节点视为需要独立关注：

- HIGH materiality
- subsidiary
- pipeline
- investment_asset

这不是最终“价值贡献百分比”模型；它只是防止重大业务/资产被整体公司倍数掩盖。

## Current limitation

v1.0 不声称自动完成：

- 财报业务段自动发现
- 子公司/投资资产自动全量发现
- 经济属性从原始财务数据自动推断
- 价值贡献率自动计算
- CAPEX → 折旧 → FCF → incremental ROIC 的完整计算链
- 市场是否单独给某资产定价

后两项分别在 Batch 1-B 后续增强 / Batch 2 完成。

## Acceptance cases

三类结构化验收：

1. 腾讯：mixed-segment platform + investment assets + capital-intensive AI/growth node。
2. 宁德时代：capital-intensive operating business。
3. 科伦药业：mature pharmaceutical + innovative pipeline + subsidiary。

验收目标不是证明三家公司真实估值已经正确，而是证明扫描器不会把三种经济结构错误压缩成同一种模型。

## Gate

Batch 1-B Core Scan Gate 至少要求：

- 三家公司均 PASS schema validation。
- 腾讯识别为 mixed_segments。
- 腾讯 AI/growth 节点被识别为高资本投入经营节点。
- 宁德时代识别为 enterprise_operating_business。
- 科伦药业识别为 mixed_segments。
- 科伦创新管线识别为 innovative_drug_pipeline，并路由到 rNPV。
- 缺失关键 economic attribute 必须 fail closed。
- scan 输出必须进入 decision engine。
- company value profile 与显式 model selection 不一致时必须 fail closed。

这只是 Batch 1-B 的 Core Scan Gate，不等于整个 Batch 1-B Gate PASS。
