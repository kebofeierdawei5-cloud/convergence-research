# IIOS 最终架构方案与低成本快速交付计划

- 日期：2026-10-11
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

## 5. 实施计划：嵌入现有规范路线，不新建平行批次体系

### 5.1 当前权威状态与路线约束

本计划不创建新的 B0–B5 或 S0–S6 生命周期，避免与仓库已有 B0 治理冻结、P0-LLM 问题编号及 PILOT-00～PILOT-04 发生冲突。

唯一当前状态依据仍是 \`docs/PROJECT_STATE_INDEX.md\`。现有 PILOT-00～04 的历史 PASS 继续保留原有意义，但它们主要证明已覆盖的 lifecycle / deterministic behavior；不能推断真实生产者来源、真实入口、完整语义产物链或 production Host 已验收。

本轮工作的实际目标，是关闭现存的产品关键缺口，尤其是：

- 当前明确开放的 P0-LLM-001：真实用户投资请求必须进入唯一 Canonical Research Orchestrator；
- 当前明确开放的 P0-LLM-004：真实自然语言/用户输入 → 模型推理 → 语义准入 → 正式决策的产品验收；
- 对 ChatGPT Free Web 人工交接路径，单独核对 P0-LLM-003 的生产者真实性和 lineage 契约。现有 B2-C 的 signed external provider binding PASS 不能自动证明人工网页路径符合契约；同样也不能据此声称 P0-LLM-003 在所有路径上仍未解决。
- 当前真实公司证据链的 source-by-source Evidence/PIT admission 与本地私有持久化；
- 完整正式 Decision / Publication / Human Report / Run Receipt / independent replay。

每个开发任务仍须遵守 AGENTS.md 的 Objective / User Value / Product Surface / Test-Acceptance / Out-of-Scope 契约。完成一个任务后更新权威状态依据，再从最新 canonical main 开始下一项任务。不得把本文件中的建议批次直接当作已完成状态或新的 canonical policy。

### 5.2 优化后的执行次序

#### Action A — 一次性差距核对与治理裁定（低成本，先做）

**目标：** 用仓库真实代码和测试证据确定最小工作量，而不是重做一遍架构。

检查现有 Orchestrator、Case/Run Envelope、Store、Evidence/PIT、semantic producer、Forecast/Valuation admission、Decision write gates、Publication、Report QA、Run Receipt 和 Replay。对每项标明具体路径、调用入口、现有测试、测试范围与仍未证明的内容，分类为：

- ACCEPTED / 可直接复用；
- IMPLEMENTED / 仅有有限范围验收；
- CONTRACT-ONLY / fixture-only；
- MISSING / 真实缺口；
- OPTIONAL / 暂缓。

同时完成 ChatGPT Free Web 人工交接的治理决策。不得先假定 \`MANUAL_WEB_OPERATOR_ASSERTED\` 可以进入正式语义准入。必须由版本化的 B0 successor/amendment 明确此来源等级能否被接受、哪些语义产物可用、禁止声称什么，以及失败时的 BLOCKED / NON_CANONICAL 处理。在裁定完成前，人工网页输出只可作为非规范辅助材料，不得产生正式决策级产物。

**验收：**
- 输出一份有文件路径、调用关系、测试证据和具体缺口的能力映射；
- 与 PROJECT_STATE_INDEX 和现有 PILOT 路线一致，不重开已通过且范围明确的旧批次；
- 明确 ChatGPT Web 生产者契约 Go/No-Go；
- 本动作不更改经济语义、不改运行时权限、不修改或弱化测试。

#### Action B — 先在现有本地路径证明真实输入与证据持久化（低至中成本）

**目标：** 不先造安装器或 UI，先验证已有本地入口、官方材料 intake 和私有存储能否在操作者环境真正工作。

优先复用现有官方证据采集/私有导入工具及真实 Case；从现有候选中选取证据与截止时点最可验证的一家公司，不先假设某个候选一定通过。针对 605016，现有状态明确要求在操作者 Mac 上重新运行私有 B2 ingest 并确认本地持久化；若当前执行环境无法触达操作者 Mac，则必须把它记为待操作者运行的验收项，不将 GitHub CI 的 PASS_EPHEMERAL_B2 当成本地持久化证据。

**验收：**
- 原始文件按清单逐字节校验并写入用户私有目录；
- 在持久化副本上重新执行原有核心 Evidence/PIT validator；
- 重新启动后仍能读取相同案例和记录；
- 源不可用、字节变化、cutoff 错误或准入缺项均安全阻断；
- 私有数据不进入 GitHub commits、公开 workflow artifacts 或不受控日志。

**成本控制：** 先用现有 launcher / CLI；只有实际运行证明它不能可靠启动或错误信息无法诊断时，才修补启动体验。不要在证明内核可工作前重写启动系统。

#### Action C — 关闭语义生产者契约并完成最小 AI 交接（中等成本，依赖 Action A）

**目标：** 使免费网页人工交接能按明确保证等级工作，而不是把它伪装成 API 或密码学 attestation。

治理允许的前提下，先实现两个可重试的研究交接包，降低人工操作次数：

1. **Price-blind Round：** 仅使用截止时点内允许的经营/财务证据；输出 Reality、Quality、Thesis、Value Drivers、Independent Forecast、证据引用、假设与未知项。输入不得包含当前价格、估值、MIE 或仓位信息。
2. **Price-aware Round：** 使用已准入的 Round 结果、正式行情证据与持仓约束；输出 Valuation/MIE 的推理与不确定性、Expectation Gap、Risk、Position 和 AI Decision Proposal。

这两轮是用于降低交接成本的初始假设，不代表所有阶段可以失去独立的 schema / artifact / admission。导入器必须保存实际提交的 prompt 与原始回答、Case/cutoff/stage/input refs、导入者声明、时间和 hash。模型输出不得自行把状态标记为 admitted。若输出有问题，仅重试受影响的阶段，不自动修复为 PASS。

若治理裁定不允许网页人工输出进入正式 semantic admission，则此路径必须明确保持 NON-CANONICAL；正式决策暂停在对应门禁。项目不能绕过该决定去宣称完整 MVP。

**验收：**
- producer assurance 声明真实、边界明确；
- 正确的身份、截止时点和输入引用绑定到每项产物；
- 模型无法写入权威状态、改写 admission 或绕过 Orchestrator；
- price-blind 输入不存在当前价格泄漏；
- 错公司、错 cutoff、错误 Evidence ID、伪造 producer 声明、缺项、格式异常等对抗测试均失败关闭；
- 对两轮方案记录人工交接数、重试率与修订率，避免把两轮未经验证地固定成永久要求。

#### Action D — 在现有 PILOT / Investment Core 路线上完成一家公司端到端闭环（高价值、不可省略）

**目标：** 以真实用户输入和真实材料，验证正式研究链路，而不是手工预构造 admitted semantic/forecast/valuation objects 来冒充生产执行。

执行链至少包括：

用户输入与 Case identity
→ 官方证据及 PIT
→ Trust / Reality / Quality / Thesis / Value Drivers
→ Independent Forecast
→ Valuation / MIE / Expectation Gap
→ Risk / Portfolio / Position
→ AI Decision Proposal
→ Deterministic Decision Admission
→ Human Approval（未批准前保持 pending）
→ Immutable Decision Revision / Machine Publication / Human Report / QA
→ 完整 Run Receipt / Replay。

**验收：**
- 实际用户入口进入唯一 Orchestrator；
- 正式产物均绑定正确市场、证券、cutoff、证据清单、producer policy 与 stage lineage；
- 所有适用数值来自确定性内核，报告与机器对象一致；
- 缺少关键输入时输出可读的阻塞诊断，但不得伪造完整投资决策；
- 真实 Run Receipt 覆盖 B0 所需的完整上游与下游引用；
- 从冻结输入执行独立 replay；不能以局部 CI、预制产物或报告可读性代替成功。

此 Action 的首个真实公司可以沿用现有案例或新用户候选，以 source completeness 与明确 cutoff 为准。它首先是工程运行可靠性验收，不是投资策略预测有效性证明。

#### Action E — 对抗性回归，并回到既有 PILOT 接受标准（中至高成本）

不建立新的平行 MVP 接受体系；把新增的真实入口、producer lineage、Evidence/PIT 和 Run Receipt 验收加入现有规范的试点/红队执行协议中。

至少验证：

- 缺数据、错公司、错 cutoff、过期或冲突证据；
- 原始字节被修改、来源错误、PIT 不合格；
- Forecast 缺失或受到 current price 污染；
- MIE 不可识别却被强行标记为确定结论；
- 自带 admitted 字段的外部 JSON、未授权 producer、stage lineage 断裂；
- 绕过 Orchestrator、Decision write gate 或 Human Approval；
- Report 与 Machine Publication / Decision 不一致；
- 中断后恢复、重复执行、旧 Revision 不被覆盖、独立 replay；
- 私有数据流入 GitHub 或不受控日志；
- ChatGPT 限额/回答截断/格式异常时误报成功。

验收应继承现有 Fast Launch Plan 对真实公司、fresh candidate、无未决 P0、无证据替换及确定性重放的要求。现有历史 PILOT PASS 继续只表示原来覆盖的范围；当新增真实 LLM 路径验收未完成时，不得宣称 P0-LLM-001 / P0-LLM-004 已关闭。

#### Action F — 只在测量后做安装与交互优化（可选）

等实际运行路径已经成立，再根据故障和使用记录决定是否：
- 改善一键启动与本地诊断；
- 提供轻量本地页面；
- 提供 Chrome Side Panel 以辅助生成/复制 prompt、粘贴 response 和查看本地状态。

任何 UI 只能调用现有应用服务，不允许创建第二套业务状态或决策逻辑。不得构建自动读取 ChatGPT 网页响应的浏览器抓取路径。交互优化的验收依据是实测的操作次数、失败率、重试次数和恢复成本降低，而不是界面上线本身。

## 6. 依赖关系与 Go/No-Go 门槛

建议按下列依赖推进，不把每个箭头理解成一个新的永久批次命名空间：

~~~text
                    ┌─ Action B: verify local intake + evidence persistence ─┐
Action A ───────────┤                                                        ├─→ Action D
                    └─ Action C: approved AI producer contract / handoff ────┘
                                                                                 ↓
                                                           Action E: red-team + existing PILOT gates
                                                                                 ↓
                                                           Action F: measured UX / installer (optional)
~~~

Action A 必须先完成；其后的 B 与 C 可在不互相重复实现的前提下并行推进，以减少总工期。Action B 的操作者本机持久化验证如果暂时无法执行，不应阻止无依赖的 C 类契约/导入器开发，但在真实公司正式运行前必须补齐。D 依赖 B 与 C 的相关门槛均通过。若 Action A 判定人工 ChatGPT Free 输出不允许进入正式语义准入，Action C 只能完成 non-canonical auxiliary workflow；必须另选一个符合现行治理的推理来源来继续正式路径，不能将正式决策门禁降级。
## 7. 成本控制原则

- **先复用，再新增：**每个新模块都必须指出现有实现为什么不能满足需求。
- **不先做 UI：**用 CLI/现有入口验证后再决定安装器或本地页面。
- **不先迁移存储：**除非实测发现现有 Store 无法满足单机运行，不重写持久化。
- **不清理全仓库：**不因 workflow 数量较多就批量删除；只有明确不在默认路径且确认没有依赖的才通过独立窄 PR 退役。
- **以阻塞项为单位交付：**每个 PR 只关闭一个有证据支持的 P0/P1 缺口，并附带相应测试，不将不相关的治理/数据/交互改动捆绑。
- **不编造工期或节省金额：**Action A 先把未知复用成本变成事实；在一家公司真实试点之前，只给出相对成本等级。

## 8. 正式产品验收标准

LOCAL_SINGLE_USER 只有同时满足以下条件才可标记为 MVP usable：

1. 一条真实用户入口进入唯一 Canonical Research Orchestrator。
2. 至少一个真实公司在固定 cutoff 下运行完成；无法完成时提供明确、可审计的阻塞原因。
3. 所有正式证据均有来源、字节清单、时间边界和明确准入范围。
4. 独立 Forecast 的输入保持 price-blind；所有适用数字由确定性核心计算。
5. 语义生产者保证等级和输入/输出 lineage 符合经批准的契约。
6. Decision、Approval、Publication、Report QA、Run Receipt 之间引用一致。
7. 历史决策 append-only，并能从冻结输入独立重放。
8. 未获批准的 AI Proposal 不替代 Human Decision；auto execution 恒为 false。
9. 负向测试证明缺失、冲突、错绑、未授权来源及旁路不能产生正式 PASS。
10. 本地原始资料和用户私有信息不进入 GitHub 公共产物。
11. 完成现有 Fast Launch Plan 要求的控制公司与 fresh user-selected candidate 验收；任何旧 PASS 都不能代替新增真实 LLM 路径的验收。
12. 实际测量安装/恢复成本、人工交接数、重试率和用户需要提供的材料量。

## 9. 治理与状态同步

- 此文档仍是提议；未被审阅和合并前不改变 canonical policy。
- PR #310 / #311 是审计记录，不修改运行时、不关闭 P0。
- PR #312 的内容不得被作为已实现架构或 MVP 通过的证明；它不关闭规范状态索引中仍开放的 P0-LLM-001 / P0-LLM-004，也不预判 ChatGPT Web 路径的 producer 契约已经批准。
- 正式接受后，按 AGENTS.md 和项目状态政策更新唯一权威 State Index，明确最新主线和下一项实际任务。
- 已完成阶段按证据保留历史状态；不得为了使用新计划而重命名、重开或抹除已有 PILOT 结果。
- 任何治理边界变更都必须有版本化 successor/adjudication、测试和明确非声明。

## 10. 最终建议

保留 LOCAL_SINGLE_USER 与现有核心复用方向；不采纳另起一套 B0–B5 / S0–S6 生命周期的做法。把工作映射回现有权威状态与 PILOT 接受框架，先做一次有证据的能力/缺口盘点，再优先验证本地真实输入和证据持久化、AI 生产者准入和一家公司完整链路。

**最快的可信交付不是先搭建更多界面，而是尽快证明现有内核能通过唯一用户入口完成一次真实、合规、可重放的投资决策；然后只修复这条路径上已证实的阻塞。**


## 11. 独立中立审查与本次优化记录（2026-10-11）

本节记录对方案本身的审查，不表示其已在生产环境实现或通过。

### 11.1 审查结论

**架构方向：建议保留。开发路线：经过本次调整后有条件接受；仍需 Action A 的代码和治理证据才能冻结为执行指令。**

| 维度 | 评估 | 依据与限制 |
|---|---|---|
| 原始投资需求匹配 | 强 | 单公司、价格决策、证据/PIT、独立预测、回报/风险、人工审批和回放被保留 |
| 工程治理匹配 | 强但有条件 | Orchestrator 和权限边界保留；人工 Web producer 的正式资格尚未裁定 |
| 开发经济性 | 中上 | 避免重写和重复服务；可复用 API 的实际范围尚需代码盘点 |
| 部署简化潜力 | 中上 | LOCAL_SINGLE_USER 能缩减远程基础设施，但真实 Mac 安装、升级和恢复尚未验证 |
| 单次使用成本 | 未证实 | 两轮交接是待测假设；免费网页额度和输出格式可影响失败率及重试量 |
| 计划依赖清晰度 | 本次改善 | B 与 C 可并行准备；正式端到端运行仍须同时满足证据与生产者门槛 |

### 11.2 仍然存在的风险

1. **免费网页的治理决策具有架构影响。** 不应先实现正式导入，再补写准入规则；必须先作有版本记录的 Go/No-Go。
2. **现有能力的名称不等同于生产验收。** 每个“可复用”组件必须引用代码入口和对应测试范围；fixture-only 或 preconstructed artifacts 不能用于证明端到端通过。
3. **本地运行依然依赖网络获取部分官方来源。** Local-first 不等于完全离线；网络失败时需要稳定、可诊断的 BLOCKED 状态和受控官方文件导入路径。
4. **两轮交接不是硬性产品约束。** 它应以试点的人工交接次数、重试率、输出缺项率和人工改写量评估；若拆成更少或更多轮有可测收益，应以数据决定。
5. **一家公司通过不等于策略有效或整个 MVP 已接受。** 单公司闭环是技术主路径证据；现有 Fast Launch Plan 对控制案例、fresh candidate 和独立重放的更高接受标准仍须执行。
6. **低部署成本还包含升级与数据迁移。** 不仅要证明首次启动，也要验证版本升级、旧记录可读、失败恢复与私有数据不会泄漏。

### 11.3 本次已做的优化

- 取消另起一套 B0–B5 / S0–S6 生命周期的含义，明确本文件是现有 canonical 状态和 PILOT 路线之下的实施建议，而非新的状态权威。
- 将 Action A 定为唯一先决步骤，优先确认现有能力、真实缺口与 ChatGPT Web 来源保证契约。
- 调整依赖关系：Action B（本地证据和持久化实证）与 Action C（AI 交接契约/实现准备）可在 Action A 之后并行，避免操作环境的暂时阻塞拖延独立工作；Action D 仍必须等待两者相关门槛通过。
- 将现有 605016 Mac 私有持久化待验证问题视为真实验收工作，但不把单一案例/操作者机器阻塞绝对化为所有开发的前置条件；若另一个候选拥有更完整且可合法使用的证据，可用于端到端试点，同时保留 605016 的真实状态。
- 明确两轮 ChatGPT 交接是成本假设而非永久硬规则，必须用实际使用数据评估。
- 明确不能把旧 PILOT PASS、局部 CI、哈希匹配或可读报告扩张解释为真实 LLM 产品验收。
- 不新增技术组件、不更改经济语义、不修改权威 State Index，也不宣称 P0 已关闭。

### 11.4 评审后的执行决定

下一步只进入 Action A：基于最新 canonical main 完成逐文件能力映射、调用路径和测试证据盘点，并作出人工 Web producer 的正式治理 Go/No-Go。Action A 结束后更新唯一权威状态索引和当前任务指令，再依据真实差距启动 B/C 窄 PR。

在 Action A 以前，不应先开发新的浏览器扩展、本地网页、数据库替换、多 Provider 路由或重新实现报告/编排系统。
