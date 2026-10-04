
# IIOS｜腾讯会话优化 → 当前开发代码逐项映射审计
## 2026-10-04 阶段性总结

## 1. 审计目的

本审计用于回答：

2026-10-04 之前腾讯控股 IIOS v0.1.1 测试会话中形成的 Company Value Core Scan 及相关投资分析优化，哪些已经进入当前开发分支，哪些仍停留在设计/会话层，哪些完全遗漏；以及这些内容后续应归入 Batch 1-B 还是 Batch 2。

硬原则：

- 不以“记得曾经讨论过”作为代码已实现的证据。
- 不以“现在已有一个类似字段”作为语义已实现的证据。
- 必须区分：EXACT_HISTORICAL_SOURCE / CODE_IMPLEMENTED / DESIGN_ONLY / MISSING / UNCERTAIN。
- 未能 exact recovery 的历史优化，不直接并入主核心分支。
- main 未经验收不得吸收当前开发分支的候选实现。

## 2. Git 基线

### main

当前 main HEAD：

0aaece3aa5cac53cedba18c3ccb2082473e9e0c5

main 当前不包含 iios_mvp 投资决策垂直切片，也未搜索到：

- Company Value Core Scan
- economic_profile
- business_segments
- core_assets
- asset_scan
- intrinsic_value
- market_implied
- expectation_gap

### 当前开发分支

mvp/investment-decision-v0.1

与 main：

- ahead_by = 28
- behind_by = 0

当前最新开发 HEAD：

0d8c15831626b43ac58cae9addc9f1227ab50109

因此当前估值内核修改仍属于开发候选，不属于 main 已合入能力。

## 3. 历史腾讯优化源的证据状态

### 3.1 Exact Source Recovery

在当前可检索的会话/Library 文档中，对以下精确术语进行了检索：

- Company Value Core Scan
- 腾讯控股 + Company Value
- 公司价值构成
- 业务分层
- 经济属性识别
- 核心资产扫描

当前未找到一份可直接作为 exact historical source 的“Company Value Core Scan”独立文件/代码提交。

因此：

腾讯会话原始优化文本目前 NOT EXACTLY RECOVERED。

这意味着以下审计不是声称已经恢复了该会话逐字原文，而是以当前会话长期保留的产品语义 + 已知腾讯测试改进方向 + 当前代码事实做结构化映射。

### 3.2 已知优化主题

当前可确认的优化主题包括：

1. 从“直接估值”前移到“公司价值构成扫描”。
2. 从“公司整体”前移到“业务/资产分层”。
3. 从静态行业标签前移到“经济属性/价值驱动因素识别”。
4. 估值模型选择必须由公司经济结构驱动，而不是默认 PE。
5. 核心资产/核心价值来源需要显式扫描，不能漏掉子公司、创新资产、管线、投资性资产等。
6. 企业资本开支、现金流、资本回报等必须进入价值链，而不能只停留在利润表。
7. 估值与市场隐含预期必须分开：先建立独立价值，再识别市场在押什么。

## 4. 逐项映射矩阵

| 优化能力 | 当前代码 | 状态 | 结论 |
|---|---|---|---|
| Company Value Core Scan | 无独立 scanner | MISSING | 完全遗漏 |
| 公司价值构成地图 | 无 Value Map / Value Tree | MISSING | 完全遗漏 |
| 业务分层 | 仅 SOTP 要求调用方预先提供 segments | PARTIAL | 有估值承载，没有发现/识别 |
| 核心资产扫描 | 无 Asset Scan / Asset Inventory | MISSING | 完全遗漏 |
| 经济属性识别 | economic_profile 字段 + 固定画像表 | PARTIAL | 输入已有，识别过程没有 |
| Model Suitability | MODEL_SUITABILITY + route | IMPLEMENTED | 第一版已实现 |
| Primary / Secondary / Cross-check | 已实现 | IMPLEMENTED | 已进入开发分支 |
| PE / DCF / DDM / SOTP | 已实现 | IMPLEMENTED | 已进入开发分支 |
| PS / PB / EV/EBITDA | 已实现 | IMPLEMENTED | 已进入开发分支 |
| rNPV | 已实现基础版并支持 pipeline | PARTIAL | 仍需药物级经济驱动深化 |
| SOTP 多模型分部估值 | 已实现 | IMPLEMENTED | 估值承载已有 |
| Intrinsic Value Aggregation | 已实现 | IMPLEMENTED | Primary 权威 + 显式加权 |
| Bear/Base/Bull | 已实现 | IMPLEMENTED | 第一版已进入 engine |
| Intrinsic Value Range | 已实现 | IMPLEMENTED | 已进入 engine |
| Model Cross-check Dispersion | 已实现 | IMPLEMENTED | 已进入 engine |
| Capital Structure / Event → Valuation transmission | 当前 engine 无完整通用传导链 | MISSING | 后续应补 |
| AI CAPEX → FCF → Shareholder Return | 当前无通用变量链 | MISSING | 后续应补 |
| 增发/稀释 → EPS/价值 | 当前无通用传导链 | MISSING | 后续应补 |
| 折旧/资本化 → 利润/FCF | 当前无通用传导链 | MISSING | 后续应补 |
| Market Model Identification | 当前无 | MISSING | Batch 2 |
| Feasible Solution Set | 当前无 | MISSING | Batch 2 |
| Identifiability | 当前无 | MISSING | Batch 2 |
| Stability | 当前无 | MISSING | Batch 2 |
| Market Implied Expectation | 仅 legacy PE 单值反推 | PARTIAL / wrong abstraction | Batch 2 必须重构 |
| Expectation Gap | 当前仍主要是 PE/盈利差异 | PARTIAL | Batch 2 必须重构 |
| Probability / Odds / Edge | 当前无 | MISSING | Batch 3 |
| Position Sizing mechanical mapping | 当前主要仍为输入包 | PARTIAL | Batch 3 |

## 5. Company Value Core Scan 是否已经进入当前核心？

结论：没有。

当前系统实际上是：

Company
→ Economic Profile（人工输入）
→ Model Router
→ Valuation

缺少：

Company
→ Company Value Core Scan
→ Value Construction Map
→ Business / Asset Segmentation
→ Economic Attribute Classification
→ Core Value Drivers
→ Candidate Valuation Models
→ Model Suitability
→ Intrinsic Valuation

所以当前的 economic_profile 不是 Company Value Core Scan。

它只是：

已知经济画像 → 模型路由

而真正应该实现的是：

公司事实/业务结构 → 自动/结构化识别经济画像。

## 6. 当前代码已经实现的部分

### 6.1 Model Suitability

iios_mvp/valuation.py 已存在：

- MODEL_SUITABILITY
- assess_model_suitability()
- route_model()
- Primary / Secondary / Cross-check

这是对历史优化的真实代码吸收。

### 6.2 估值模型族

当前开发分支支持：

- forward_pe
- dcf
- ddm
- sotp
- ps
- pb
- ev_ebitda
- rnpv

这已经超越最初 PE-only。

### 6.3 SOTP

当前 SOTP 已能承载不同分部使用不同模型，并支持：

- ownership
- other assets
- net debt
- PE / PS / PB / EV/EBITDA / DCF / DDM / rNPV

但注意：

它要求上游已经知道有哪些 segments。

因此它解决了：

“如何给已经识别出的分部估值”

没有解决：

“系统如何发现/识别这些分部及核心资产”。

## 7. 当前真正遗漏的上游核心

### P0 — Value Construction Map

应该建立：

Company
├─ Core Operating Business
├─ Growth Business
├─ Subsidiaries
├─ Investment Assets
├─ Pipeline / Optionality
├─ Cash / Financial Assets
├─ Debt / Other Claims
└─ Minority Interests

并记录：

- economic_role
- value_driver
- maturity
- cash_flow_characteristic
- asset_status
- ownership
- valuation_candidate
- materiality

### P0 — Business / Asset Segmentation

不是行业标签，而是：

哪些经济资产需要分别估值？

例如科伦药业：

成熟医药
川宁生物
科伦博泰
其他创新管线
现金/金融资产
净负债
少数股东

例如腾讯：

核心现金牛业务
游戏
广告
金融科技
云
投资组合
AI / 新业务
现金及金融资产
资本开支与回购

### P0 — Economic Attribute Classification

至少形成：

- earnings stability
- cash-flow visibility
- capital intensity
- cyclicality
- asset intensity
- growth/reinvestment
- payout characteristics
- pipeline optionality
- segment heterogeneity
- leverage
- accounting sensitivity

它才是 Model Router 的上游。

### P0 — Core Asset Scan

必须回答：

如果把公司拆开，真正决定未来价值的资产有哪些？

并判断：

- 是否 material
- 是否被当前市场单独定价
- 是否需要独立估值
- 是否容易被母公司平均 PE 掩盖

## 8. Batch 1-B / Batch 2 重新划界

### 必须补进 Batch 1-B

因为它们直接决定“我该怎么估值”：

1. Company Value Core Scan
2. Value Construction Map
3. Business / Asset Segmentation
4. Economic Attribute Classification
5. Core Asset Scan
6. Model Suitability
7. Primary / Secondary / Cross-check
8. Pipeline / rNPV
9. SOTP
10. Intrinsic Value Aggregation
11. Bear/Base/Bull
12. Intrinsic Value Range
13. Capital Structure / Material Event transmission

Batch 1-B 的终点应是：

系统知道公司由什么价值构成、哪些资产需要独立估值、为什么选择某个主模型，并得到一套可解释的内在价值范围。

### 必须留到 Batch 2

因为它们解决的是“市场怎么定价”：

1. Market Model Identification
2. Candidate Market Model Set
3. Market Model-specific Inversion
4. Feasible Solution Set
5. Identifiability
6. Stability
7. Market Implied Expectation

Batch 2 的核心问题：

当前市场价格究竟在隐含什么？

## 9. 对腾讯测试优化的特殊处理

腾讯会话中涉及的：

- 高 CAPEX
- AI 投入
- AI ROA / ROI 不确定性
- FCF 承压
- 回购能力变化
- 潜在稀释
- 折旧增加

不能全部直接做成“腾讯专属字段”。

正确抽象是：

Capital Allocation / Reinvestment Event
→ CAPEX
→ Depreciation / Amortization
→ FCF
→ Incremental Return on Capital
→ Shareholder Cash Return
→ Intrinsic Value

这样才会成为通用 IIOS 能力，而不是“腾讯特例”。

## 10. 对当前研发路线的修正

原 Batch 1-B：

Model Suitability
→ rNPV
→ SOTP
→ Aggregation

修正为：

Company Value Core Scan
→ Value Construction Map
→ Business / Asset Segmentation
→ Economic Attribute Classification
→ Core Asset Scan
→ Model Suitability
→ Primary / Secondary / Cross-check
→ rNPV / SOTP / Other Valuation Engines
→ Intrinsic Value Aggregation
→ Bear / Base / Bull
→ Intrinsic Value Range
→ Batch 1 Gate

这是更符合 IIOS 最终投资价值的 Batch 1-B。

## 11. Current Status

main
└── 0aaece3... canonical FM00 baseline

dev: mvp/investment-decision-v0.1
└── +28 commits
    ├── MVP decision core
    ├── valuation router
    ├── PE/DCF/DDM/SOTP
    ├── PS/PB/EV-EBITDA/rNPV
    ├── model suitability
    ├── intrinsic aggregation
    └── valuation gate

当前开发代码：

已经吸收“估值模型路由”这条优化，但没有吸收完整的 Company Value Core Scan。

因此不能把当前 Batch 1-B 视为完成。

## 12. 阶段性结论

### 明确已经实现

- 多估值模型族
- Model Suitability 第一版
- Primary / Secondary / Cross-check
- SOTP 多分部估值承载
- rNPV 基础 pipeline
- Intrinsic Value Aggregation
- Bear/Base/Bull
- Intrinsic Value Range
- Deterministic Valuation Gate

### 明确只实现了一半

- 经济属性：字段/路由已存在，但识别尚未实现
- 业务分层：SOTP 能承载，但上游发现尚未实现
- rNPV：计算框架有，药物经济学层次仍不足
- Expectation Gap：旧 PE 逻辑仍在，尚未进入 Market Model framework

### 明确遗漏

- Company Value Core Scan
- Value Construction Map
- Core Asset Scan
- Business / Asset discovery
- Economic Attribute inference
- Generic Capital Allocation / CAPEX transmission
- Market Model Identification
- Feasible Solution Set
- Identifiability
- Stability

## 13. Next development decision

在把未知历史优化直接带入 main 之前，先完成：

Tencent Optimization Mapping
→ Batch 1-B Core Scan Contract
→ Code Implementation
→ Unit / Negative Tests
→ CATL + 科伦药业 Acceptance
→ Batch 1 Gate

只有通过这一链条，才允许开始 Batch 2 Market Model Identification。

本文件是阶段性导航/审计记录，不替代 exact historical source，也不宣布任何未验证能力 PASS。
