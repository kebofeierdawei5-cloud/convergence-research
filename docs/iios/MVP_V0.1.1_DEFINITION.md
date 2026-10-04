# IIOS MVP v0.1.1 — Versioned Decision Core & Human/Machine Output Contract

## 1. Purpose

在 v0.1 单家公司投资决策垂直切片基础上，补齐长期可用所必需的四类能力：

1. 同一公司多次分析的不可变版本与可回溯历史。
2. 投资组合只引用当前最新有效的评估决策，不承载历史决策账本。
3. 统一、机器可读的 Trigger Contract，使人工、定时、价格、关键数据、状态变化等入口能够复用同一触发语义。
4. 后台机器标准化存储与对外人类可读报告/机器发布接口分离，避免数据库结构直接污染投资报告可读性。

v0.1.1 仍坚持“最小完整垂直切片”原则，不引入完整事件总线、微服务、自动交易、完整 M1.2 预测研究基础设施或多公司筛选。

---

## 2. Product Boundary

### 2.1 Core vertical slice

一家公司 + As-of cutoff
→ Normalized Trigger
→ Evidence
→ Trust
→ Reality
→ Independent Forecast
→ Valuation
→ Market Implied Expectation
→ Expectation Gap
→ Risk
→ AI Decision Proposal
→ Human Approval
→ Immutable Decision Revision
→ Current Decision Projection
→ Machine Publication
→ Human-readable Report
→ Trigger Contracts
→ New Trigger / New Revision

### 2.2 v0.1.1 must provide

- 自然语言最小启动入口：Market + Symbol + As-of Date + Current Position。
- 内部自动形成标准 Case Contract；用户不直接填写 Evidence / Reality / Forecast / Valuation。
- run_id 与 decision_revision 分离。
- 同一 Decision Series 下的多次有效决策不可覆盖。
- Snapshot 不可变、可 hash 校验、可 replay。
- AI Proposal 与 Human Decision 分离。
- Portfolio 只引用最新 Human-approved Decision Revision。
- Active Trigger Contract 从当前有效决策读取。
- Trigger Event 采用统一机器结构，可来自不同入口。
- Decision Publication 提供稳定机器消费字段。
- Human Report 独立渲染，面向投资者阅读。
- Report Quality Gate 对数字一致性、结论一致性与可读性进行最低校验。

### 2.3 Explicitly not in v0.1.1

- 自动下单/券商交易。
- Kafka、消息队列、复杂事件总线、微服务拆分。
- 全量市场实时监控。
- CSI800 完整历史成分、A02 PIT Security Master。
- Forecast Model Selection / rolling-origin research。
- 完整估值模型路由器。
- 多公司筛选/组合自动优化。
- LLM 自主修改确定性投资结论。
- 用报告评分反向改变投资决策。

---

## 3. Canonical Object Model

IIOS v0.1.1 使用“三平面”：

~~~
                 Decision Series
                       |
                Decision Revision
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
Canonical Store   Machine Publication  Human Report
机器权威存储       对外机器接口         人类阅读层
        |              |              |
   audit/replay     integration      decision/review
~~~

### 3.1 Company

表示一个被分析的证券主体/上市标的。

最小字段：

~~~
company_id
market
symbol
company_name
~~~

### 3.2 Decision Series

定义“同一公司/证券在时间上的决策历史”。

规则：

- 一个标的一个长期 Decision Series。
- 历史 Revision 永不覆盖。
- Series 作为复盘、审计、时间序列追踪的顶层标识。

最小字段：

~~~
decision_series_id
company_id
market
symbol
created_at
~~~

### 3.3 Run

表示一次系统执行。

run_id 与 Revision 不等同：

- 相同输入的 replay 不应制造新的投资决策 Revision。
- 一个新的实际决策运行，可以形成新的 Revision。
- Run 用于技术执行审计；Revision 用于投资决策历史。

最小字段：

~~~
run_id
decision_series_id
started_at
as_of_date
cutoff_date
trigger_event_id
engine_version
schema_version
run_status
~~~

### 3.4 Decision Revision

表示一项不可变投资决策版本。

建议标识：

~~~
decision_id = <decision_series_id>-r<revision>
~~~

例如：

~~~
CATL-r001
CATL-r002
CATL-r003
~~~

最小字段：

~~~
decision_id
decision_series_id
revision
as_of_date
cutoff_date
snapshot_hash
ai_decision
human_decision
decision_status
engine_version
decision_schema_version
~~~

Revision 的状态建议：

~~~
AI_PROPOSED
HUMAN_APPROVED
HUMAN_REJECTED
SUPERSEDED
~~~

其中：

- HUMAN_APPROVED 才能成为 Portfolio Current Decision。
- 后续新 Revision 成为有效版本后，旧的 Approved Revision 标记为 SUPERSEDED。
- AI 新提案即使更新，也不得自动替换 Portfolio 当前有效决策。

---

## 4. Immutable History vs Current Portfolio Projection

必须严格分开：

~~~
Immutable Decision Ledger
        |
        +-- r001
        +-- r002
        +-- r003
        |
        v
Current Decision Projection
        |
        v
Investment Portfolio
~~~

### 4.1 Immutable Decision Ledger

保存所有历史 Decision Revision、Snapshot、Approval、Trigger Contract。

任何历史 Revision：

- 不修改。
- 不删除。
- 不被新 Revision 覆盖。
- 可以通过 hash + replay 回溯。

### 4.2 Current Decision Projection

保存当前有效决策的指针/投影，而不是复制完整历史。

建议：

~~~
company_id
current_approved_decision_id
current_decision_updated_at
~~~

### 4.3 Portfolio

Portfolio 负责“现在”。

最少保存：

~~~
company_id
actual_position_pct
current_approved_decision_id
position_updated_at
~~~

禁止：

- 把历史 r001/r002/r003 全部混入 Portfolio 当前状态。
- AI_PROPOSED 未获人工批准时直接替换 current_approved_decision_id。

因此：

~~~
AI r004 = ADD
Human = PENDING

Portfolio
current_approved_decision_id = r003
~~~

只有：

~~~
Human r004 = APPROVED
~~~

才更新：

~~~
Portfolio.current_approved_decision_id = r004
~~~

---

## 5. Version Semantics

必须区分以下版本，不得混用：

~~~
Decision Revision
Engine Version
Schema Version
Prompt Version
Evidence Snapshot / Manifest
Trigger Contract Version
Report Version
~~~

原因：

- Decision Revision：回答“当时做了哪个投资判断”。
- Engine Version：回答“用哪个确定性算法计算”。
- Prompt Version：回答“LLM 使用什么指令生成研究/叙事”。
- Evidence Manifest：回答“当时看到了哪些证据”。
- Trigger Contract Version：回答“当时什么条件会触发重新运行”。
- Report Version：回答“当时对人呈现了什么报告”。

任何复盘必须能够从 Decision Revision 定位到上述依赖。

---

## 6. Standardized Trigger Model

Trigger 由两个对象组成：

### 6.1 Trigger Contract

表示“在什么条件下重新触发/复核”。

最小结构：

~~~json
{
  "trigger_id": "CATL-r003-price-001",
  "decision_id": "CATL-r003",
  "trigger_type": "PRICE",
  "metric": "market_price",
  "operator": "<=",
  "threshold": 350,
  "unit": "CNY",
  "action": "REVIEW",
  "effective_from": "2026-10-04",
  "expires_at": null,
  "cooldown": "24h",
  "enabled": true
}
~~~

### 6.2 Trigger Event

表示“外部发生了什么”。

例如：

~~~json
{
  "trigger_event_id": "evt-20261010-001",
  "source": "market_data",
  "event_type": "PRICE",
  "occurred_at": "2026-10-10T10:15:00",
  "metric": "market_price",
  "value": 349.5,
  "symbol": "300750",
  "source_version": "provider-x-v1"
}
~~~

IIOS 只消费标准化 Event，不要求不同外部系统理解 IIOS 内部结构。

### 6.3 v0.1.1 trigger types

至少支持：

~~~
MANUAL
SCHEDULED
PRICE
FUNDAMENTAL_DATA
STATE_CHANGE
PORTFOLIO_STATE
~~~

### 6.4 Trigger actions

v0.1.1 最少：

~~~
RUN
REVIEW
ALERT
~~~

Trigger 不直接执行交易。

### 6.5 Trigger lifecycle

~~~
Current Approved Revision
        |
        v
Active Trigger Contracts
        |
        v
External Trigger Event
        |
        v
Trigger Evaluation
        |
   +----+----+
   |         |
No Match   Match
             |
             v
         New Run
             |
             v
       New Revision
~~~

旧 Revision 的 Trigger 不应在其被 SUPERSEDED 后继续作为当前有效触发规则。

---

## 7. Natural-language Trigger Entry

用户对系统的最小输入原则：

~~~
Market
Symbol
As-of Date
Current Position
~~~

推荐用户入口：

~~~
IIOS v0.1.1：A股 300750，As-of 2026-10-04，仓位 10%。启动完整投资决策。
~~~

内部流程：

~~~
Natural Language Trigger
        ↓
Trigger Adapter
        ↓
Standard Trigger Event / Case Skeleton
        ↓
Research / Data Collection
        ↓
Deterministic Decision Engine
~~~

用户不应被迫填写：

- Evidence
- Reality
- Forecast
- Valuation
- Market Implied Expectation
- Risk model internals

这些属于系统内部研究与决策输入。

---

## 8. Machine Canonical Storage

后台数据库/文件存储以机器标准化为最高优先级。

要求：

- 字段稳定。
- 类型明确。
- 日期、金额、百分比单位明确。
- 枚举值固定。
- 所有核心对象有 schema version。
- 所有 Revision 可通过 ID/hash 精确定位。
- JSON/数据库不得依赖自然语言句子的语义才能恢复关键状态。
- 不使用 Markdown 报告作为权威数据源。

Canonical Store 的原则：

~~~
Database ≠ Report
Database ≠ Human Narrative
Database = Source of Truth for Decision State
~~~

---

## 9. Machine Publication Contract

对外开放给其他系统的数据不直接暴露内部数据库，而是提供稳定的 Machine Publication。

最小结构建议：

~~~json
{
  "decision_id": "CATL-r003",
  "decision_series_id": "CATL",
  "revision": 3,
  "as_of_date": "2026-10-04",

  "decision_status": "HUMAN_APPROVED",
  "ai_action": "HOLD",
  "human_action": "HOLD",

  "actual_position_pct": 10,
  "target_position_pct": 10,

  "intrinsic_value": 420,
  "current_price": 360,
  "expected_return_pct": 16.7,
  "required_return_pct": 15.0,
  "expectation_gap_pct": 18.0,

  "trust_status": "PASS",
  "thesis_status": "INTACT",
  "risk_status": "PASS",

  "active_triggers": [],
  "next_review_date": null,

  "engine_version": "0.1.1",
  "decision_schema_version": "1.0"
}
~~~

对外系统只依赖 Publication Contract，不依赖内部数据库字段。

---

## 10. Human-readable Report Contract

同一份 Canonical Decision 必须生成独立的人类阅读版本。

报告目标不是“显示全部数据”，而是帮助投资者快速回答：

1. 现在是什么结论？
2. 为什么？
3. 什么假设支撑这个结论？
4. 市场价格隐含了什么？
5. 安全边际够不够？
6. 什么情况下会改变判断？

### 10.1 Report structure

建议固定为：

~~~
1. 一页投资结论
2. 投资 Thesis
3. Trust & Evidence
4. Reality
5. Independent Forecast
6. Valuation
7. Market Implied Expectation
8. Expectation Gap
9. Risk & Thesis Breaks
10. Decision & Position Package
11. Monitoring & Trigger Conditions
12. Audit Appendix
~~~

### 10.2 Human readability rules

主报告必须：

- 先结论，后论证。
- 关键数字必须有语义解释。
- 重要判断使用自然语言说明因果关系。
- 不把内部 JSON、字段名、状态码直接堆进正文。
- 不重复同一结论。
- 不为了“完整”把所有中间计算塞入主文。
- 机器字段放入附录或结构化查看层。
- 允许表格，但表格必须服务于比较，而不是替代解释。

推荐阅读层次：

~~~
首屏：结论 / 价格 / 仓位 / 风险 / 触发条件
正文：为什么
附录：如何证明
~~~

---

## 11. Report Quality Gate

报告质量是产品验收的一部分，但不得改变投资结论。

### 11.1 Deterministic checks

至少检查：

- 关键数字与 Canonical Snapshot 一致。
- Decision 与正文结论一致。
- Human Decision 与当前 Portfolio Projection 一致。
- Trust Gate 与允许的 Action 一致。
- Trigger Contract 与报告中的触发条件一致。
- Report 引用的 As-of / Cutoff 与 Revision 一致。

### 11.2 Readability checks

至少检查：

- 是否存在首屏核心结论。
- 是否存在无法解释的机器字段。
- 是否过度重复。
- 是否出现结论与正文冲突。
- 是否存在明显过长的数据堆砌。
- 是否把关键风险隐藏在附录。
- 是否能在有限阅读时间内定位行动建议和改变判断的条件。

### 11.3 Status

~~~
REPORT_DRAFT
REPORT_VALIDATED
REPORT_PUBLISHED
REPORT_BLOCKED
~~~

Report Blocked 不改变 Decision 本身，但禁止将该版本标记为最终发布报告。

---

## 12. Decision / Report / Trigger Independence

三种结果必须保持独立：

~~~
Investment Decision
Machine Publication
Human Report
Trigger Contract
~~~

关系：

~~~
Canonical Decision Revision
   ├── Machine Publication
   ├── Human Report
   └── Trigger Contracts
~~~

因此：

- 报告改版不会改变 Decision Revision。
- Machine API 字段扩展不会改变投资结论。
- Trigger 表达方式优化不会改变历史 Revision。
- 新 Revision 生成后，旧 Report / Publication / Trigger 都仍然可审计。

---

## 13. Deterministic / LLM Boundary

### Code-owned

- PIT validation
- required fields
- decision gates
- valuation arithmetic
- market-implied expectation arithmetic
- expectation gap arithmetic
- Revision numbering
- Current Decision Projection
- Trigger matching
- Snapshot hashing
- Replay
- Report consistency checks
- Human approval persistence

### LLM-owned

- 对证据进行研究性解释。
- 形成独立预测的文字推理与假设说明。
- 对投资 Thesis 的自然语言组织。
- 将结构化结果转换成可读投资报告。

### Prohibited

LLM 不得：

- 自行覆盖历史 Revision。
- 自行更新 Portfolio 当前决策。
- 自行伪造 Trigger Event。
- 自行绕过 Trust / PIT / Risk Gate。
- 自行改变确定性计算结果。
- 自行发起交易。

---

## 14. Minimum Acceptance Tests

### Versioning

- 同一公司两次不同 As-of 分析产生不同 Revision。
- 新 Revision 不覆盖旧 Revision。
- 两个 Revision 可以独立 Replay。

### Portfolio projection

- AI 新 Proposal 不自动改变 Portfolio。
- Human Approval 后 Current Decision 才切换。
- Portfolio 只保存当前有效决策引用，不承载历史 Revision。

### Trigger

- 人工、定时、价格、基本面、状态五类入口均可转换为统一 Trigger Event。
- Trigger Contract 能从 Current Decision Revision 读取。
- Superseded Revision 的 Trigger 自动失去 current-active 资格。

### Publication

- Machine Publication 可被另一个程序直接读取。
- Publication 字段不依赖 Markdown 文本解析。
- Schema version 可识别。

### Report

- 报告中的关键数字与 Snapshot 一致。
- Report action 与 Decision action 一致。
- 报告具备“结论 → 依据 → 风险 → 触发”的阅读结构。
- 原始 JSON / 内部字段不出现在主报告。

### Core safety

- PIT leak → fail closed。
- Trust FAIL → 新 BUY/ADD 禁止。
- 缺失关键输入 → fail closed。
- AI/Human decision 分离。
- 无 auto_execution。
- Snapshot immutable。
- Replay PASS 对相同输入必须成立。

---

## 15. v0.1.1 Implementation Order

严格按照最小增量实施：

~~~
Step 1
DecisionSeries + Run + DecisionRevision
        ↓
Step 2
Immutable Revision Store + Current Decision Projection
        ↓
Step 3
Standard Trigger Contract + Trigger Event
        ↓
Step 4
Machine Decision Publication
        ↓
Step 5
Human Report Renderer + Report Quality Gate
        ↓
Step 6
Natural-language Trigger Adapter
        ↓
Step 7
Unit / Negative / Replay / Real-company Acceptance
~~~

不在此阶段扩张到完整事件驱动架构。

---

## 16. Design Principles

### Principle 1 — Historical truth is append-only

历史决策必须可以回答：

> “在当时的信息和系统版本下，IIOS 到底做了什么判断？”

### Principle 2 — Portfolio represents now

Portfolio 只表达当前有效的、经人工确认的投资状态；历史留在 Decision Ledger。

### Principle 3 — Trigger is a reusable contract

不同触发来源统一成标准 Event；不同系统不需要理解 IIOS 内部实现。

### Principle 4 — One canonical truth, multiple projections

同一个 Canonical Decision Revision 同时服务于：

~~~
Audit
Machine Integration
Portfolio
Human Report
Trigger Monitoring
~~~

但不同消费者使用不同的表示层。

### Principle 5 — Human readability is a product requirement

“机器可验证”与“人类可理解”必须同时成立。

报告不是数据库 dump，也不是 LLM 自由发挥；它是 Canonical Decision 的受控人类表达。

### Principle 6 — Open source remains implementation reference only

开源项目用于复用成熟实现，不反向定义 IIOS 产品需求。

---

## 17. v0.1.1 Definition of Done

只有同时满足以下条件，才可认为 v0.1.1 完成：

~~~
[1] 单家公司可产生多 Revision
[2] 历史 Revision 不可覆盖
[3] Portfolio 只引用当前 Human-approved Revision
[4] Trigger Contract / Trigger Event 标准化
[5] Machine Publication 可被外部系统直接消费
[6] Human Report 可独立阅读且与 Canonical Decision 一致
[7] Report Quality Gate PASS
[8] Snapshot / Replay PASS
[9] PIT / Trust / Missing Evidence / AI-Human separation 安全门 PASS
[10] 至少一家公司真实案例跑通完整闭环
~~~

v0.1.1 的目标不是“做完整 IIOS”，而是把 v0.1 从“可运行的一次性分析脚本”提升为：

> **一个具有历史版本、当前决策、标准触发接口、机器输出和人类可读报告的最小投资决策内核。**
