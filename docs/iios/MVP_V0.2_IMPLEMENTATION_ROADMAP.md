# IIOS MVP v0.2 — Macro Development Roadmap

## 1. North Star

IIOS 的核心不是生成一份“估值报告”，而是把投资判断变成可复核、可执行的概率决策：

```
Company Economics
    ↓
Valuation Model Router
    ↓
Independent Forecast
    ↓
Intrinsic Value
    ↓
Market Model Identification
    ↓
Market Implied Expectation
    ↓
Expectation Gap
    ↓
Win Probability + Payoff / Odds
    ↓
Risk / Margin of Safety
    ↓
BUY / ADD / HOLD / REDUCE / EXIT / NO-BUY
    ↓
Entry Price + Position Size
    ↓
Monitoring / Validation / Review
```

最终验收问题只有一个：

> 给定一家真实公司、一个严格 PIT 的 As-of 日期和当前仓位，IIOS 是否能选择与公司经济学匹配的估值模型，得到更接近真实的内在价值；识别市场当前主要采用的估值模型及其隐含预期；判断两者之间是否存在可兑现的正收益预期差；再结合胜率、赔率、风险和组合约束决定“买不买、什么价格买、买多少”。

## 2. Current Baseline Assessment

### 已有且保留

- PIT / Trust / Missing Evidence fail-closed 基础门。
- Snapshot hash + Replay。
- Decision Series / Revision / Human Approval / Current Projection 基础持久化。
- Trigger Contract / Event 基础结构。
- 既有 CLI / CI 骨架。
- “AI 提案 ≠ Human 决策 ≠ Auto Execution”边界。

### 必须重构

现有引擎存在结构性问题：

- 估值模型固定为 `forward_pe`。
- 公司经济学没有驱动模型选择。
- SOTP / DCF / DDM 等模型无法进入同一决策内核。
- 市场隐含预期只实现了“价格 ÷ 倍数”的单一 PE 反推。
- 没有真正的 Market Model Identification。
- 没有 Feasible Solution Set / Identifiability / Stability 的机器语义。
- 没有基于情景概率的胜率、赔率、Edge。
- 仓位建议尚未由风险收益结构确定性计算。
- 当前执行报告/Execution Receipt 尚未形成可验证的标准记录。

因此，不能继续把 v0.1.1 的 PE-only 实现当作投资内核完成。

## 3. Development Layers

### Batch 0 — Baseline Closure & Product Contract

目标：先把开发边界、版本和验收标准统一。

交付：

- 本路线图与 Core Decision Contract。
- 清除当前 CI replay 误读问题。
- 明确 `Engine / Schema / Prompt / Evidence / Revision / Report` 版本语义。
- 确保旧的 Revision / Snapshot 不被新版本覆盖。

验收：

- compileall PASS。
- 单元测试 PASS。
- CLI run → persisted artifacts → replay PASS。
- CI PASS。

### Batch 1 — Valuation Model Router + Intrinsic Value Engine

目标：从“PE 计算器”升级为“公司经济学 → 模型 → 估值”。

首期模型族：

- PE / earnings multiple。
- DCF。
- DDM。
- SOTP。

设计原则：

```
Company Economics
       ↓
Model Selection Evidence
       ↓
Primary Model + Alternative Models
       ↓
Deterministic Valuation
```

要求：

- 不允许代码默认所有公司使用 PE。
- 允许显式指定 primary model。
- 可记录 model-selection rationale / confidence / alternatives。
- SOTP 支持不同业务/资产独立价值后再汇总。
- 模型缺失关键输入时 fail-closed。
- 估值计算必须 deterministic。

直接解决的历史问题：

> 科伦药业的创新药、川宁生物、成熟输注/仿制药等不能再被强行塞入同一个 PE。

### Batch 2 — Market Model Identification + Implied Expectation

目标：回答“市场价格现在到底在定价什么”。

统一结构：

```
Current Price
   ↓
Candidate Market Models
   ↓
Model-specific Inversion
   ↓
Feasible Solution Set
   ↓
Identifiability
   ↓
Stability
   ↓
Market Implied Expectation
```

首期至少支持：

- PE → implied earnings / EPS。
- SOTP → implied residual segment value。
- DCF / DDM → implied growth / terminal assumptions。

原则：

- 市场模型不是拍脑袋选择。
- 多模型都能解释价格时必须标记 ambiguous，而不是伪装成确定答案。
- 可识别性不足时，Expectation Gap 必须降级，不能直接转成 BUY。
- 市场隐含预期与独立预测必须使用相同经济变量比较。

### Batch 3 — Expectation Gap + Probability / Odds / Edge

目标：把“看起来便宜”升级成真正的正期望决策。

核心输出：

- Expected Value / Expected Return。
- Positive-return probability。
- Hurdle-win probability。
- Expected upside / expected downside。
- Payoff Ratio / Odds。
- Edge。
- Required Return。
- Max Loss。
- Entry Ceiling。
- Kelly-derived capped position recommendation。

最小决策逻辑：

```
Independent View
    vs
Market Implied View
    ↓
Expectation Gap
    ↓
Probability
    +
Payoff / Odds
    ↓
Edge
    ↓
Risk Limits
    ↓
Position Size
```

### Batch 4 — Decision Persistence / Execution Receipt / Publication

目标：解决“后台到底有没有保存这一次标准化执行结果”的可见性问题。

Canonical Execution Receipt 至少记录：

- execution_id。
- decision_series_id。
- decision_revision。
- as_of / cutoff。
- engine / schema / prompt / evidence manifest versions.
- input snapshot hash。
- decision snapshot hash。
- decision_id。
- machine publication status。
- human report status。
- replay status。
- execution status。

要求：

> 每一次真实 run 都能通过 execution_id 独立回答“何时、对谁、在什么信息截止点、用什么版本、算出什么、保存在哪里、是否 replay 成功”。

### Batch 5 — Human Report + Machine Publication + Trigger

目标：把 Canonical Decision 变成可读、可接入、可持续监控的产品。

首屏：

- BUY / ADD / HOLD / REDUCE / EXIT / NO-BUY。
- 当前价格。
- 内在价值。
- Entry Ceiling。
- 胜率。
- 赔率。
- Edge。
- 最大风险。
- 推荐仓位。
- Thesis Break。

正文：

- Thesis。
- Trust & Evidence。
- Reality。
- Forecast。
- Valuation / Model Selection。
- Market Implied Expectation。
- Expectation Gap。
- Probability / Odds / Edge。
- Decision / Position.
- Monitoring / Triggers。

附录：

- PIT / versions / evidence manifest / snapshot / replay。

### Batch 6 — Real Company Acceptance & Audit

至少用两个经济结构明显不同的真实案例：

1. CATL：适合检验 earnings / cash-flow / cyclical valuation 路由。
2. 科伦药业：必须检验 SOTP、成熟业务与创新药分部估值不能混用。

每个案例都必须：

- 严格 PIT。
- 有证据来源与已知时间。
- 有独立预测。
- 有模型选择记录。
- 有市场模型识别。
- 有隐含预期。
- 有 expectation gap。
- 有概率 / odds / edge。
- 有 buy/add/no-buy 与仓位。
- 有 Execution Receipt。
- 可 replay。

## 4. What We Do Not Build Yet

在上述主链完成前，不扩张：

- Kafka / event bus / microservices。
- 全市场实时扫描。
- 自动交易。
- CSI800 完整历史数据基础设施。
- 多公司自动选股。
- 复杂组合优化。
- 为“治理完整”而添加与投资核心无关的安全层。
- 用 LLM 自由决定确定性数值。

## 5. Dependency Order

```
Batch 0
  ↓
Batch 1 Valuation
  ↓
Batch 2 Market Model
  ↓
Batch 3 Probability / Odds / Sizing
  ↓
Batch 4 Execution Receipt
  ↓
Batch 5 Report / Publication / Trigger
  ↓
Batch 6 Real Cases / Independent Audit
```

任何批次未通过验收，不向后继续叠加新的“完成”声明。

## 6. Definition of Done for the Investment Core

核心内核只有在以下条件同时成立后，才能称为“可用于真实投资决策”：

- 模型路由不是 PE-only。
- 公司经济学能够解释模型选择。
- 至少 PE / DCF / DDM / SOTP 可执行。
- 市场模型能够显式识别并给出 implied expectation。
- 多解时能识别 ambiguous / low-identifiability。
- Expectation Gap 可用经济变量表示。
- 胜率、赔率、Edge 可确定性计算。
- 推荐仓位由概率、赔率、风险和组合约束共同决定。
- 人工最终批准仍然独立。
- 每次真实运行都有 Execution Receipt + Snapshot + Replay。

---

**版本：v0.2 Roadmap**  
**定位：开发总控基线，不直接作为运行时输入。**
