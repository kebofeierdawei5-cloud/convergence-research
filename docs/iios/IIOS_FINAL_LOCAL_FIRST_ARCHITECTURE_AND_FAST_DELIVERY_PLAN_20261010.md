# IIOS 最终架构方案与低成本快速交付计划

- 日期：2026-10-10
- 状态：**PROPOSED — REVIEW REQUIRED；未合并前不是 Canonical Policy**
- 范围：单用户 A/H 公司级投资决策 MVP 的产品边界、AI 交接、部署边界和分批验收计划
- 依据：AGENTS.md、docs/PROJECT_STATE_INDEX.md、MVP v0.1 / v0.1.1、MVP Fast Launch Plan、B0 LLM Governance Freeze，以及产品有效性与架构简化审计（PR #310 / #311）

## 1. 执行结论

**采用 LOCAL_SINGLE_USER 作为默认部署模式；复用现有 Canonical Research Orchestrator 和投资内核；把 ChatGPT Free Web 作为人工交接的 AI 推理适配器，而不是 API 或自动化浏览器接口；优先完成一个真实公司的完整投资决策闭环，再优化 UI。**

当前主要矛盾不是缺少 Host、Provider、数据库或更多测试，而是：部分组件与控制面已存在，用户仍未获得一条经过真实运行验收、从用户输入到正式 Decision、Report、Run Receipt 和 Replay 的完整路径。

方案要求：

1. 不重写投资内核，不建立第二套 Orchestrator、权限系统、Decision Store 或报告管线。
2. 用户日常研究不依赖 GitHub Actions、远程生产 Host、付费 API key 或多 Provider 运维。
3. 原始证据、PIT、UNKNOWN、来源与时间治理、确定性计算、权限隔离、不可变历史、人工审批和 Replay 均保留。
4. 对 ChatGPT Web 人工交接作出明确来源保证声明；不把哈希误称为模型来源证明，也不让外部 JSON 自行宣告 canonical。
5. 以一只真实公司、一次端到端运行、失败关闭测试和独立重放验收，而不是以组件 PASS、文档完整或 CI 数量代替产品验收。
6. Chrome 插件、浏览器自动化、远程 Host、多用户、多 Provider 和更广泛研究数据继续暂缓，直到真实用户证据证明它们有必要。

## 2. 产品目标与不可妥协语义

IIOS 是个人投资者的 A/H 单公司投资决策系统，不是全市场选股器、一般性研报生成器或自动交易平台。

它必须回答：

> 在给定 as-of/cutoff 时点，以当前价格是否值得买入？若当前价格不满足回报与风险要求，目标买入价格/价格区间是什么？什么事实会推翻判断？

正式决策链：

~~~text
Candidate + As-of/Cutoff + Position/Constraints
  → Evidence / Trust / PIT
  → Reality / Quality / Thesis / Value Drivers
  → Independent Forecast
  → Valuation
  → Market Implied Expectation (MIE) / Expectation Gap
  → Risk / Portfolio / Positioning
  → AI Decision Proposal
  → Deterministic Decision Admission
  → Human Approval
  → Immutable Decision Revision / Publication / Report
  → Run Receipt / Replay / Monitoring / Validation
~~~

投资语义和治理基线：

- 默认参考期限 H=1Y；只有满足规定条件并显式记录 Override=TRUE 及理由时，才用 3Y。
- 年化预期回报门槛默认 15%；这不是估值折现率。
- 决策动作应包括 BUY / ADD / HOLD / REDUCE / EXIT / WATCH / NO-BUY / REVIEW_REQUIRED（以当前规范枚举为准）。
- Trust FAIL 阻断新增 BUY/ADD 风险，但不自动触发卖出。
- 缺失、过期、冲突、来源不可信、PIT 不合格、预测不可审查或 MIE 不可识别时，只关闭受影响权限，不得静默补值或升级为 PASS。
- AI 只负责语义推理与提案；代码负责计算、状态、日期、权限、哈希、持久化和准入；Human 是资本与最终审批权威。
- 不自动下单。人类可读报告不是权威状态源；正式决策必须绑定权威结构化对象及完整运行记录。

## 3. 最终架构决策

### 3.1 默认运行形态：LOCAL_SINGLE_USER

~~~text
One local launch entry
        ↓
Existing Canonical Research Orchestrator
        ↓
Private Case Workspace + Existing Canonical Store/Runtime
        ├─ official raw evidence + manifest
        ├─ PIT / evidence admission records
        ├─ typed semantic artifacts + producer receipt
        ├─ forecast / valuation / risk / decision artifacts
        ├─ immutable decision revisions / event history
        └─ publication / human report / QA / Run Receipt / replay
~~~

- GitHub 继续用于源代码、PR、CI、发布和规范记录；不作为每次投资研究的运行依赖。
- 本地运行不得把个人原始证据、持仓约束或报告写入公开仓库或公共 Actions artifacts。
- 单用户本地应用默认不需要公开网络端口、远程访问、多租户隔离或独立的远程 Host。
- 一个用户入口和一个规范运行路径不等于把所有代码塞进单一模块。内部继续按现有 domain/runtime/store/analyst/calc 边界工作。
- 本地持久化采用现有 Store 优先。只有审计证明现有 Store 无法满足单机需求时，才评估 SQLite + filesystem；不得仅因 SQLite 简单就先重建一套数据层。
- 启动器是现有应用的薄壳，不拥有投资决策语义；CLI、轻量 UI 和未来浏览器伴侣只能调用同一个应用服务/Orchestrator。

### 3.2 唯一权威运行路径

所有声称是正式 IIOS 投资决策的任务，必须通过当前规范化 Canonical Research Orchestrator；不允许因本地运行方便而增加直接函数调用、Notebook、自由文本报告或第二套状态机旁路。

已有 Canonical Orchestrator、Decision Revision、Human Approval、Machine Publication、Report QA、Run Receipt、Replay 等实现先做代码级复用盘点。已实现且测试充分的直接复用；仅有契约/夹具的补真实端到端；尚未实现的只补关键缺口。不得重写整个链路来满足新 UI。

### 3.3 唯一默认用户输入

最小必需输入：

- Market
- Symbol
- As-of Date / Cutoff
- Current Position

Portfolio constraints 和特别期限等仅在相关时要求。用户不应手填 Evidence、Reality、Forecast、Valuation 或准入状态。

保留自然语言启动方式，但自然语言解析仅负责提出初始字段。系统须展示并确认 Market / Symbol / As-of / Position 后生成不可混淆的 Case identity；未经确认的字段不能启动规范决策。结构化输入与自然语言入口必须进入同一 Orchestrator，不能变成两套执行流。

### 3.4 Evidence-first、Free-first

- 默认只为当前一只候选公司获取决策所需的官方披露、财务、资本结构、治理与行情证据；不等待 A02 / CSI800 / 跨截面预测研究。
- 记录源、URL、发布时间/可知时间、取得时间、原始字节、SHA-256、适用范围与使用约束。
- 若公开接口阻断，允许人工取得官方原始文件后通过私有 intake 导入；重新验证来源与原始字节、日期、PIT 和用途。
- 其他媒体、二级网站和卖方预测可以作为显式 supplementary / non-admitted 背景，不能静默替换正式证据。
- URL 或标题匹配、HTTPS、哈希、JSON schema 与 payload shape 分别只能支持有限性质；不能单独证明来源真实性或 PIT 合格。
- 原始材料是否入库、是否准入、是否可重分发是不同决定，遵守各来源使用限制。

### 3.5 ChatGPT Free Web 的定位与来源契约

ChatGPT Free Web 是本 MVP 可选的、人工操作的语义推理入口；不是本地脚本可稳定调用的 API。不得以浏览器 DOM/内部网络响应抓取、自动读取服务输出或其他未经支持的网页自动化方式充当正式接口。

建议建立显式的生产者配置：

~~~text
MANUAL_WEB_OPERATOR_ASSERTED
assurance = OPERATOR_ASSERTED_NOT_CRYPTOGRAPHICALLY_VERIFIED
~~~

它表达的是：本地系统保存了操作者提交的确切 prompt / response 字节、绑定了 Case / cutoff / stage / input refs，并记录操作者对交接来源的确认；它**不**证明 ChatGPT 的服务端来源、模型版本或生成过程已经由密码学验证。

正式实现前，必须对 B0 governance 形成版本化的 successor/amendment，明确是否允许此类受限保证等级的 producer 进入正式 semantic admission，列出可准入的产物种类与禁止声明。不得直接修改/放宽现有规则以“让流程通过”。未经批准时，Web 输出只能是 NON-CANONICAL research assistance，正式 Decision 保持 BLOCKED / REVIEW_REQUIRED。

每次人工交接至少保存：

- Case ID、run ID、market / symbol / cutoff、研究阶段；
- 交给模型的精确任务文本及哈希、prompt/schema version；
- 导入的原始输出字节及哈希、导入时间；
- 当时可见的产品/模型标识（如果网页没有可靠显示则记 UNKNOWN，不推断）；
- 输入 Evidence refs / 先前准入产物 refs；
- operator assertion 与 producer assurance level；
- 校验状态、错误、重试或人工修订记录。

外部输出不得自带或自我声明 admitted。只有本地可信 importer / admission code 可以建立相应记录；人工编辑输出后必须保留原始输出与修改后的差异及人工修改记录。模型不获得正式状态写权限。

### 3.6 将人工交接控制在两轮主要推理任务

为控制使用成本，默认把多阶段 AI 语义工作合并成两个主要交接包，而不是对每个小阶段分别复制一次 prompt。合并不代表跳过独立产物 schema、阶段身份和准入检查。

**Round A — Price-blind business reasoning**

- 输入：截止时点内允许使用的官方证据/标准化事实、必要公司身份、历史经营事实与业务材料。
- 明确排除当前股价、估值结果、目标价、PE/PEG、市场隐含预期及仓位意见。
- 输出：Reality interpretation、Quality、Thesis、Value Drivers、Independent Forecast、关键假设、证据引用、未知项、反方解释。
- 目的：避免通过输入污染让“独立预测”反向拟合当前价格。
- 本地程序将一份回答分解为多个 typed artifacts，并按各自 schema / evidence / cutoff / stage lineage 验收；一个回答中的任一 artifact 不合格，不自动使其他 artifact 合格。

**Round B — Price-aware valuation and decision proposal**

- 输入：已准入的 Round A 产物、正式价格证据、估值输入与当前持仓/组合约束。
- 输出：估值模型选择建议和理由、MIE 可识别性/稳定性判断、预期差、风险、仓位建议、决策提案、逻辑失效条件、重新评估触发点和最强反方论证。
- 所有 PE/PEG、现金流、目标价、预期回报、Required Return、Entry Return Cushion 等适用数值由确定性内核计算并校验；模型提供假设和解释，不成为数字的权威计算者。

如果缺少证据、上下游产物或来源授权，本地程序可以只重发有问题的阶段，而不是重新执行整份研究。额外模型调用作为显式 exception，不是默认流程。

### 3.7 存储、报告与私有性

- 权威业务状态只存在于一套 canonical store / runtime；报告、Markdown 和网页界面均为投影。
- 原始证据、证据 manifest、语义产物、Forecast、Valuation、Decision Revision、Human Decision、Publication、QA 和 Run Receipt 必须可通过稳定 ID/hash 关联。
- 历史决策与事件 append-only，不覆盖旧 Revision。
- 报告与机器对象分别生成；QA 校验关键数字、动作、价格、截止日和来源引用一致性。
- 默认私有写入，不向 GitHub 上传用户的 raw evidence、持仓信息、人工 prompt/response 或报告。
- 本机哈希可检测字节变化，但不抵御拥有本机管理员权限的攻击者，也不证明外部模型来源或推理质量；所有对外保证都要按实际能力陈述。

## 4. 明确不作为首版默认路径的能力

在一个真实公司端到端验收通过之前，暂停以下方向的非必要开发：

- 远程生产 Host、公共监听端口、反向代理与多用户认证；
- 多 Provider / 多 Runtime 路由、外部签名部署体系的扩张；
- Chrome Companion、自动点击/发送/读取网页输出；
- 第二套本地 Orchestrator、第二套 Store、第二套报告管线；
- A02 / CSI800 / 全市场筛选成为公司级 MVP 依赖；
- 全估值模型路由器、自动组合优化、自动交易；
- 为某一案例临时制造 synthetic admissions 或放宽测试以获得 PASS。

保留已有代码和历史记录；“暂缓”不等于立即删除。是否退役要由依赖和测试盘点确定，以窄 PR 分批移除真正不再需要的部署入口。

## 5. 分批开发与落地计划

每批执行单一目标、单个窄 PR（若属于不同风险/接受者则拆分），必须在开始时写明 Objective / User Value / Product Surface / Tests & Acceptance / Out of Scope。每批完成后先核对 canonical main 和 State Index，再从更新后的基线开展后续批次。

### Batch S0 — Final ADR + Existing Capability Map

**目标：** 冻结产品/治理决定，并防止平行实现。

**工作：**
1. 审阅 canonical main 中 Orchestrator、Case/Run Envelope、Store、Evidence/PIT admission、semantic producer、Forecast/Valuation admission、Decision write gate、Report QA、Run Receipt 和 Replay。
2. 对每个能力分成：IMPLEMENTED + ACCEPTED、IMPLEMENTED BUT BOUNDED、CONTRACT/TEST-FIXTURE ONLY、MISSING、OPTIONAL/FUTURE。
3. 决定 MANUAL_WEB_OPERATOR_ASSERTED 的正式保证等级、允许/禁止的产物和相应 B0 successor amendment；没有此批准，不得在实现里默认它可正式准入。
4. 定义唯一默认入口、一个运行 profile、一个 artifact/receipt contract 与端到端验收。

**验收：**
- 文档列出真实 repo 路径、现有实现、可复用 API、缺口及测试证据。
- 明确任何 CI PASS 的作用范围与非声明。
- 无运行时代码变更，无经济语义变更。
- 后续工作不需要依赖聊天记录才能理解。

**成本等级：** S（低）；这是整个方案最重要的降重步骤。

### Batch S1 — Minimal Local Launch + Canonical Ingress

**目标：** 从单一入口创建真实 Case 并运行现有 Orchestrator；不先开发高级 UI。

**工作：**
1. 增加一个面向单用户的 launcher / 命令，自动处理本地环境检查、固定依赖、私有目录、版本和清晰错误提示。
2. 接受 Market、Symbol、As-of/Cutoff、Current Position；确认自然语言解析字段后才生成规范 Case。
3. 由应用代码创建工作区、run 状态、内部 bundle/manifest 路径和必要的私有 intake，不让用户手工编辑这些对象。
4. 确保用户端研究无需 GitHub Actions、远程 Host、API key 或多个手工 environment variables。
5. 优先复用现有 store；若需改变持久化策略，另出窄范围 ADR + migration / replay tests。

**验收：**
- 干净 Mac 用户环境下完成安装/启动测试。
- 启动成功时进入唯一 Orchestrator；缺依赖/网络/证据时错误具体且 fail-closed。
- 重新启动可发现既有 Case 与 run 记录；不覆盖旧数据。
- 本地私有数据不进入 GitHub commits / public artifacts / logs。
- 不声称 S1 就完成正式投资决策链。

**成本等级：** M（中）；以复用现有 API 为成本控制前提。

### Batch S2 — Official Evidence Intake + PIT Closure

**目标：** 让一个真实公司所需的证据可以从官方来源获取或通过私有 intake 导入，并进入现有 Evidence/PIT 核心。

**工作：**
1. 只实现当前案例需要的官方源适配器和原始文件导入路径。
2. 对每个原始文件验证允许的来源、HTTPS/传输规则、原始字节、size/hash、类型、日期、PIT 和复用/保存限制。
3. 把“下载成功”“原始字节一致”“来源获准”“PIT 合格”“正式 admitted”分成独立状态。
4. 当源不可用或 exact bytes 不符合合同，给出具体缺项并阻断受影响阶段；禁止静默使用二级来源替换。

**验收：**
- 至少一只真实公司覆盖当前要求的证据类别；每一类都有来源和 cutoff 说明。
- 使用更改过的文件、错日期、错公司、错误来源进行负向测试，正式 admission 必须失败。
- 本地私有持久化经过实际运行确认；CI artifact 仅含经审查的脱敏状态元数据。
- 不引入完整 A02 / CSI800 数据平台作为前置依赖。

**成本等级：** M–L（中至高，取决于官方端点和材料准入实际阻塞）。采用“一个当前案例需要的来源”控制范围。

### Batch S3 — Two-Round Free Web Handoff + Semantic Admission

**目标：** 用最少的人工交接让 ChatGPT Free 提供研究推理，同时严格绑定输入/输出和阶段准入。

**工作：**
1. 按 Round A / Round B 生成可复制任务包；不要求每个内部阶段分别手动执行一次 ChatGPT 回调。
2. 提供原始 response 导入命令/界面；导入前后保存 bytes、hash、case/cutoff/stage refs 和人工来源确认。
3. 实施经 S0 批准的 operator-asserted producer contract 和 B0 successor/amendment；输出未明确授权时只作 non-canonical assistance。
4. 将单份回答解析成独立 typed artifacts，逐项校验 schema、引用、身份、截止日、独立预测边界和阶段依赖。
5. 失败时只请求或重导入未通过的阶段；不自动把模型回答修成 PASS、不让模型写 admission status。
6. 记录 prompt version、原始回答、校验报告和所有人工修改。

**验收：**
- 两轮主要交接可产生完整必需的语义候选产物；有缺陷时仅受影响 artifact / stage 阻断。
- Price-blind Forecast 输入中不存在 current price / valuation / market-implied values。
- 结构正确但证据 ID 错误、case/cutoff 错误、模型来源声明自封、缺少 producer receipt 等对抗样本全部失败关闭。
- 完整链路明确标记 provenance assurance；不会声称得到未验证的 ChatGPT server/model attestation。
- 如果 S0 决定人工网页模式不能进入正式 semantic admission，则 S3 仅交付辅助模式，正式 Decision 必须保持阻断；不得绕过治理合同。

**成本等级：** M；最大未知量是现有语义生产者/准入接口是否可在不建新路径的情况下复用。

### Batch S4 — One Real-Company Vertical Slice

**目标：** 以一只真实公司证明完整产品可用。建议优先从候选 301345.SZ 或已有真实公司案例中选一个，以证据可获得、cutoff 可固定、完整性可验收为选择标准；不预设未验证的公司一定能通过。

**工作：**
1. 使用冻结后的代码版本和 as-of/cutoff 运行。
2. 完成 Trust / Reality / Quality / Thesis / Value Drivers / Independent Forecast / Valuation / MIE / Expectation Gap / Risk / Position / Decision。
3. 以确定性内核计算所有数值并验证收益门槛、风险和仓位约束。
4. 生成 AI Proposal、Human Approval（未批准前标为 pending）、immutable Decision Revision、Machine Publication、中文人类报告、QA 与 complete Run Receipt。
5. 保存完整输入/输出与依赖版本，执行独立 replay。

**验收：**
- 从普通用户入口发起，不手工预构造关键 semantic / forecast / valuation admitted objects 来冒充完整产品运行。
- 每个正式结果均绑定到正确公司、cutoff、证据清单、producer profile 和 stage lineage。
- 缺失关键数据时可以产生完整的“阻塞报告/诊断记录”，但不得生成虚假的成功决策。
- AI 输出与正式计算、报告和机器记录一致；人类审批与 AI 建议分开。
- 完整 Run Receipt 可定位并重放依赖；独立检查者能复核本次运行。
- 一家公司 PASS 只证明流程完整，不宣称投资策略已经有预测有效性。

**成本等级：** L（高且不可省略）；这是对产品是否真的交付的核心验证。

### Batch S5 — Adversarial Acceptance + Pilot Usability

**目标：** 证明简化没有减弱关键约束，并量化实际使用成本。

**负向场景至少包括：**
- 缺证据、错公司、错 cutoff、陈旧/冲突数据；
- 修改原始文件、改变输出字节、伪造来源字段、非法语义 schema；
- missing Forecast / Valuation / MIE 不可识别却被当成 PASS；
- 在 forecast prompt 中注入 current price；
- 通过 CLI、普通自由文本、报告或旧 artifact 绕过 Orchestrator / write gate；
- 报告与 canonical decision 数值不一致；
- Human Approval 未完成就替换 current approved decision；
- 进程中断/重启、重复运行、replay；
- 私有数据意外进入 GitHub 或日志；
- ChatGPT 额度限制、输出格式异常、复制不完整时仍错误标记为成功。

**验收：**
- 所有决策权限相关负向场景必须 BLOCK / NON_CANONICAL / REVIEW_REQUIRED，不准弱化测试以获得 PASS。
- 在真实 Mac 环境独立重放，审计者不依赖原开发者临场解释。
- 以一次真实案例记录实际手工交接次数、每轮失败率、人工修订次数、运行耗时和部署问题；用数据决定是否值得做 UI。
- 有限用户 pilot 通过后，才能标记 LOCAL_SINGLE_USER MVP usable。

**成本等级：** M–L。

### Batch S6 — 只有观察到真实摩擦后再优化交互

第一阶段不开发 Chrome Companion 或网页自动读取。若 S5 的实际使用数据证明交互成为主要瓶颈，再选择：
- 薄本地页面，复用同一个应用服务；或
- Chrome Side Panel，仅用于生成/复制 prompt、粘贴 response 与展示本地状态；不读取/抓取 ChatGPT 内部响应，不拥有正式业务逻辑。

UI 不得建立第二套 Case/Run/Store，不参与准入决定，也不改变任何经济语义。S6 的验收以人工交互次数和错误率下降为依据，不以页面上线作为成功。

## 6. 成本控制与进度控制

### 6.1 不做未经差距审计的全面重构

禁止一次性“清理整个 iios_mvp”“删掉大量 workflows”或重写 Store。先在 S0 标出依赖图、真实用户路径和已验收能力。删除或退役只通过独立窄 PR 进行，且需证明没有仍被 canonical 路径调用。

### 6.2 每个批次设置 Stop/Go Gate

- S0 不通过：暂停运行代码修改，不可先造 UI。
- S1 不通过：不能声称本地部署完成。
- S2 不通过：不能启动正式公司投资决策；具体缺项显示给用户。
- S3 的 producer governance 未通过：Web 输出仅可用于 non-canonical 辅助分析。
- S4 不通过：不能标记 MVP accepted。
- S5 不通过：不开展交互美化或远程扩张。

### 6.3 不以未测量的时间或金额承诺“快速”

当前属于静态架构规划，尚未完成本地干净环境实测，也未逐个复核所有现有 runtime/store API 的复用成本，因此不应编造绝对工期或现金成本。初步相对工作量是：S0 低；S1 中；S2 中至高；S3 中（有较大接口复用不确定性）；S4 高；S5 中至高；S6 可选。S0 的唯一目标就是尽快将未知量变成有证据的差距清单，以避免昂贵的试错重构。

## 7. 产品验收的量化指标

MVP 通过须同时满足：

1. **一条正式入口：**真实用户输入最终到达现有 Canonical Research Orchestrator；没有平行的正式路径。
2. **一个真实公司：**在固定 cutoff 下完成合法的端到端运行，或在资料确实缺失时得到明确且可审计的阻塞状态。
3. **来源和时间可追溯：**所有正式证据有明示来源、时间、字节清单与准入范围。
4. **预测独立：**Forecast 阶段输入不包含 current price / valuation / MIE；不存在隐藏价格泄漏。
5. **所有数字可复算：**估值、预期回报、门槛、仓位及价格区间来自确定性内核，单位/币种明示。
6. **正式推理有授权契约：**生产者保证等级、prompt、原始输出、stage lineage 与导入记录完整；不能把人工网页输出冒充密码学 attestation。
7. **阻断有效：**关键事实缺失、输入冲突、producer 未获授权或 stage lineage 断裂时，不创建声称完整的正式 Decision。
8. **输出一致：**Human report、Machine Publication、Decision Revision 和 Run Receipt 的关键字段完全一致。
9. **历史可回放：**已冻结输入可重放，旧决策不会被覆盖。
10. **隐私得到保护：**原始资料和用户持仓不进入 GitHub 公共产物。
11. **人工批准保持独立：**AI proposal 不自动成为 Human-approved decision；auto execution 恒为 false。
12. **实际成本可观察：**至少记录一次 pilot 的安装步骤、模型交接数、重试、失败和恢复成本。

## 8. 对现有审计和 State Index 的治理处理

- PR #310 / #311 是审计文档；它们不修改代码或投资语义，也没有关闭 P0-LLM-001 / P0-LLM-004。
- 本文件合并前仅是提议，不改变 docs/PROJECT_STATE_INDEX.md 的唯一权威地位。
- 本 ADR 被正式接受后，先更新 canonical State Index 的当前指令与批次入口，再执行 S1；不得把历史的 “next boundary” 直接解释成当前状态。
- 各批次必须以最新 canonical main 为基线，按 AGENTS.md 保持窄 PR、测试和验收声明同步。
- 不把某个历史 PASS、CI 结果、哈希匹配或可读报告扩张解释成更广泛的产品 PASS。

## 9. 最终决策建议

**选择 Local-first + 现有 Orchestrator 复用 + 明确保证等级的人工 ChatGPT Web 适配器 + 单公司真实端到端验收。**

这一方案最贴合原始个人投资需求，并把复杂度集中在真正有价值的地方：证据可信、预测独立、估值可复算、决策受权限控制和结果可复现。

低成本的关键不是把治理移除，而是避免重复实现；快速交付的关键不是跳过真实验收，而是先交付一条最短的完整垂直切片。先做 S0 的能力/缺口盘点与治理裁定，再按 S1–S5 逐批实现。UI/Chrome 交互增强只能在完整链路通过并观察到真实摩擦后进入可选 S6。
