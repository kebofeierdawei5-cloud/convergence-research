# IIOS 项目有效性与原始需求符合性审计

- 审计日期：2026-10-10
- 审计类型：产品有效性 / 架构边界 / 工程验收证据审计
- 审计基线：canonical main，审计时 HEAD 为 0e6ab65764298afa1fe723ad0a16b8683eb93276
- 结论等级：**NOT ACCEPTED AS A PRODUCTION-READY INVESTMENT DECISION PRODUCT**
- P0：规范自然语言入口与实际用户入口之间的生产级衔接仍未通过验收
- 本文件是审计记录，不是实现变更、生产验收或投资决策

## 1. 执行摘要

本次反复出现的“用户要求使用新版 IIOS，LLM 却绕过设计框架自由发挥并直接写出报告”不是单篇报告的风格问题，而是已知 P0 控制边界在实际产品使用路径中仍未被证明闭合的问题。

仓库已实现相当数量的投资核心语义、准入契约、确定性决策、授权、出版与报告组件。它们的局部测试和控制面验收不应被否定。但它们也不能被当作实际产品端到端通过的替代证据。

直接证据：
1. B0 治理冻结文档将 P0-LLM-001 明确记录为 CONFIRMED：自然语言投资请求可以绕过 Canonical Research Orchestrator 而得到自由文本分析。
2. B0 同时记录 P0-LLM-004：历史 PILOT 主要验证预构造语义输入下的生命周期，而不是自然语言请求到真实 LLM 推理、语义准入及规范决策的完整链。
3. 当前 PROJECT_STATE_INDEX 顶部仍将 P0-LLM-001 / P0-LLM-004 标记为 OPEN / REAL-HOST ACCEPTANCE REQUIRED。
4. 当前状态索引记录：真实生产 Host-origin 运行尚未证明完成真实公司 Evidence/PIT、语义、Forecast/Valuation、Decision、Publication、报告及完整 Run Receipt replay。
5. P0 Batch B1 与 B2 的规范文档明确说明：CLI 合约测试和首方 Host 代码不是生产部署验收；未识别/未证明有一个真实用户界面已经调用 canonical-run。
6. Free ChatGPT Web Runtime 文档明确其是操作员手动复制/导入的回调候选路径，provider_origin_verified=false；它只承接 request-intent 与 thesis-semantic 两个回调，不能替代价格/证据、独立预测、估值、正式准入或完整生产凭据。
7. 最近 605016 证据记录仍说明本地私有持久化未验证，且暂时没有正式签名准入、生产 Host 接受和完整正式决策链。

因此，本次审计判定：
- **投资核心组件：部分实现，有可保留的技术资产。**
- **控制面与局部 CI：多个范围 PASS，但证据类别有限。**
- **真实用户入口到完整规范决策：生产级未验收。**
- **当前 ChatGPT 对话中的“按新版 IIOS 运行”承诺：不能自动等同于仓库运行。**
- **MVP 产品可用性：不接受为已完成。**

该结论不意味着所有代码无效，也不意味着每个历史 PASS 都是错误；它意味着组件级 PASS 未能证明用户实际依赖的产品行为。

## 2. 对照原始需求与工程原则

### 2.1 原始 MVP 的核心目标

MVP v0.1 定义要求的一条垂直链是：

用户选择的一家公司 + as-of cutoff
→ Evidence
→ Trust / Reality
→ Independent Forecast
→ Valuation
→ Market Implied Expectation
→ Expectation Gap
→ Risk
→ AI Decision Proposal
→ Human Approval
→ Immutable Snapshot
→ Replay

第一版明确要求：
- deterministic decision engine 负责 PIT、门槛、估值、隐含预期、预期差、风险与 action；
- missing forecast input 不允许模型补值，必须 BLOCKED；
- 同一输入必须得到同一 Decision；
- Trust FAIL 阻止新 BUY/ADD，但不能自动 EXIT；
- Human Approval 与 AI Proposal 分开；
- 自动执行恒为 false；
- 研究产品首先是用户给定标的的公司级决策工具，不是为了扩大研究基础设施而无限增加模块。

### 2.2 不可妥协的工程原则

AGENTS.md 要求：不捏造缺失数据；UNKNOWN/缺失/过期/冲突/不可验证证据必须关闭受影响权限；Trust、Thesis、Valuation 和投资吸引力必须分离；确定性计算、状态转换、权限、日期、哈希和持久化不能交给 LLM；不得让 LLM 直接写入权威状态；不得只为得到 PASS 而修改测试。

B0 进一步冻结：任何声称是 canonical investment decision 的自然语言请求必须进入 Canonical Research Orchestrator；LLM 语义产物必须经过带 producer identity/version 和输入输出血缘的 deterministic admission；没有完整 Run Receipt 的输出必须是 NON-CANONICAL ANALYSIS / BLOCKED，而不能因为报告可读就升级为正式决策。

## 3. 主要审计发现

### F-01 — P0：实际用户入口未被证明强制接入规范执行链

**状态：已证实为未关闭的生产验收项。**

仓库中存在 canonical-run、首方 Host 和可信 runtime factory。但当前状态索引仍要求识别、部署并证明真正的用户入口调用该链。B1 Host 集成文档明确称它验证 repository-resident CLI 的控制流程，并没有识别或验证外部生产用户界面。

因此，用户在通用 ChatGPT 对话中输入“使用新版 IIOS 分析……”并不会仅凭这句话自动调用仓库中的 Python CLI、运行时注册、证据准入和报告 QA。除非一个受支持的 Host / tool connector 实际调用了规范入口，否则 LLM 仍可直接回答研究问题。这与其是否能写出高质量的 prompt 无关。

**产品影响：**用户意图与产品控制面分离，最重要的 fail-closed 规则无法约束对话层自由文本。用户反复看到的行为正是这一边界尚未在真实入口闭合的结果。

证据：
- [B0 LLM Canonical Execution Governance Freeze](B0_LLM_CANONICAL_EXECUTION_GOVERNANCE_FREEZE_20261007.md)
- [P0 Batch B1 CLI Host Integration](P0_BATCH_B1_CLI_HOST_INTEGRATION_20261010.md)
- [P0 Batch B2 First-Party Host](P0_BATCH_B2_FIRST_PARTY_HOST_20261010.md)
- [PROJECT_STATE_INDEX](../PROJECT_STATE_INDEX.md)

### F-02 — P0：用控制面 PASS 替代产品端到端 PASS

**状态：已证实。**

B2-E 文档说明，其 conformance suite 使用 fixture request interpreter、fixture semantic producer 和既有 CATL case/resolvers，因此证明的是控制流程与 authority boundary，不是生产 LLM 运行。B1/B2 Host 文档也明确将合成证据、fixture producer 和测试 Host 的结果限定为控制面证据。

然而项目进展容易被多个独立的 PASS 状态组合成“产品已能真实执行完整分析”的印象。实际状态索引同时写明 P0-LLM-001 / P0-LLM-004 仍为 OPEN。这两种状态只有在清楚区分验收范围时才不矛盾：前者是限定范围的组件验收，后者是未完成的产品验收。

**产品影响：**团队可能持续增加 CI 与防护测试，但用户最关心的真实入口、真实模型推理、真实公司证据和最终报告仍未通过同一条链验收。

### F-03 — P0：LLM 语义产物没有在生产路径中证明因果进入经济决策

**状态：架构缺陷已被识别并部分修复；生产因果链仍未验收。**

B2-F 独立红队曾指出 admitted semantic artifact 与 Decision Kernel 的经济输入之间存在因果边缺失：语义产物被接受，但 Forecast/Valuation/Risk/Expectation Gap/Decision 可能来自另行提供的 Investment Core case。后续 FR 修复和 B3 persisted upstream write authorization 加强了持久化对象、hash、schema、case/cutoff 和 stage receipt 的正式写入校验。

但当前文档仍明确声明这些是控制面回归，并不证明真实生产的 Natural Language → Semantic → Forecast → Valuation → Decision 因果链已完整通过。

**产品影响：**即使报告有所有章节，仍可能是 LLM 自由撰写的分析和结构化决策对象并未共享同一组经准入的上游事实/推理依据。必须通过真实输入/输出绑定和完整 Run Receipt 证明此因果关系，而不是靠报告文字推断。

### F-04 — P0：证据准入和当前股票案例未连成可用流程

**状态：公司级证据工具存在；实时、可持久化、可决策的完整链未普遍证明。**

当前主分支对 RC-CN-A-605016-20261009 的记录显示，官方 HTTPS 证据已通过 ephemeral B2/PIT 校验，但本地 Mac 私有持久化仍待实际验证；状态索引亦说在真实 Host、公司 Evidence/PIT 和正式 Run Receipt 完成之前，不得创建正式决策报告。

涛涛车业 301345 本次对话没有形成与该标的绑定的正式 Research Case、公司证据 manifest、全部所需 Evidence/PIT admissions、Forecast/Valuation admissions 或 complete Run Receipt。以前其他公司的证据链或 demo 不可转移为 301345 的证据。

**产品影响：**用户可输入一家公司，但系统尚未证明能够稳定把任意合规候选公司推进到正式、可复核的决策输出。如果数据阻塞，产品应反馈准确缺项并停止正式决策，而不是以网页搜索摘要和模型假设填补空白。

### F-05 — P0：报告生成器只管规范产物，无法约束生成器之外的自由文本

**状态：架构边界可证；本次对话未经过正式报告生成器。**

v0.2 Investor Review Report 是 Machine Publication 的只读投影，带有机器报告、中文报告、确定性 QA 及 provenance hash 的设计。它不是一个把随意生成的文本“套上 IIOS 标题”就能变成正式报告的组件。

上一次涛涛车业回答没有提供正式 publication/report/QA artifact 和 complete Run Receipt；因此无法将它视为已通过 report writer 的产物。即使报告 writer 的单元测试和语义矩阵检查通过，也不会拦截运行路径之外的通用 ChatGPT 回答。

**产品影响：**报告质量门只对调用它的那条路径有效。产品必须在 UI/工具级别建立“正式 IIOS 输出只能引用规范运行返回的 artifact”的约束。

### F-06 — P1：项目状态与产品验收范围容易被误读

**状态：已观察到范围表达风险。**

当前 PROJECT_STATE_INDEX 将 Investor Review Report v0.2 + Human Acceptance 标为 PASS/CANONICAL，但同一份索引将 P0-LLM-001/P0-LLM-004、真实用户 Host 与生产公司证据链保留为 OPEN。正确解释可能是报告投影组件及某个已接受的真实 Publication 满足了其专属验收，而不是整个 ChatGPT 交互产品已经达到生产可用。

该区别应当以机器可读的不同状态明确表达：
- component_contract_status
- synthetic_control_plane_status
- real_company_e2e_status
- production_host_status
- operator_usability_status
- canonical_mvp_acceptance_status

任何子组件 PASS 都不得自动提升更高层状态。操作员对实际产品反复提出相同的严重可用性问题，应触发新的正式 Human Acceptance rejection，而不是被历史某个样例的 PASS 覆盖。

### F-07 — P1：验收体系偏重可测试的代码边界，未把用户关键路径设为唯一发布门

**状态：从验收文档与当前阻塞状态可支持的系统性判断。**

仓库有大量局部契约和回归测试，这是有价值的工程资产；但 B0 已提醒 PILOT 通过的类别错误，而当前 Host 生产验收仍未关闭。说明项目不能再以“新增一个测试”“一个 PR 合并”或“某个单独工作流 PASS”作为完整产品能力的证据。

所有验收报告必须回答：在受支持的用户入口中，输入一家公司与 cutoff，是否在不人工补造状态的情况下完成规范分析；若阻塞，是否给出可解释的缺项；若成功，是否交付完整可重放的机器/人工报告与凭据。

### F-08 — P1：优先级未持续围绕“可用的一条垂直切片”收敛

**状态：需要调整开发治理与工作排序。**

MVP fast-launch plan 明确要求尽早把公司级 Investment Core 作为产品测试，而不是持续扩张研究基础设施；A02 / 跨截面 Forecast Research 是 non-blocking track。与此同时，最近若干批次继续修复数据抓取、运行时、入口和授权的局部细节，而完整生产 Host /真实公司闭环仍未通过。

这些底层修复并非不必要，但在当前阻塞未关闭时，不能把更多旁路工具或新模块视为比最终用户路径集成更优先。应停止扩展非必要功能，冻结现有投资语义与模块，集中资源通过单一真实案例。

## 4. 本次输出的定性与可信边界

涛涛车业报告应标记为：

**NON-CANONICAL / REJECTED AS AN IIOS DECISION ARTIFACT**

可作为非正式研究草稿保留；不能作为正式 IIOS Decision、Machine Publication 或 Investor Review Report 使用。

此标记不等于断言其中每个公开财务数字都错误。具体问题是这些数字和假设未由本次规范 Evidence/PIT、semantic、forecast、valuation、decision、report/QA 与 complete Run Receipt 链证明。

本次审计依据当前 main 的代码和文档，没有声称实际启动了仓库生产 Host、实际运行了新的 301345 案例，或者独立执行了生产 Run Receipt replay。

## 5. 必须暂停的开发模式

在 P0 关闭前：
1. 暂停非必要的新估值模型、新研究轨道和非关键数据工具扩展。
2. 不接受仅有 unit test、fixture E2E、mock provider、schema/hash 通过的记录作为生产 MVP 验收。
3. 不再将用户交互中的自由文本答案默认称为“新版 IIOS 输出”。
4. 不得生成伪装为正式产物的手工 Markdown 报告；缺少规范链时只能输出明确的 BLOCKED/NON_CANONICAL 状态。
5. 所有状态变更必须从 canonical main、PROJECT_STATE_INDEX 和对应规范合同开始，并记录精准基线。

## 6. 下一批执行计划：P0 Product Vertical-Slice Acceptance

### Batch V0 — Freeze & Contract

交付：
- 冻结当前 Investment Core 语义、报告 schema 与权限合同，不扩模型。
- 建立一个明确的“正式 IIOS 运行”产品入口契约。
- 将当前对话输出与正式 IIOS artifact 明确分隔：没有绑定 run_id / publication hash / report QA / complete Run Receipt 的结果不得标称 canonical。
- 把组件通过、控制面通过、真实案例通过、生产 Host 通过、人工可用性通过区分成独立状态。

验收：
- 没有 Host 或运行时的请求，必须返回 BLOCKED/NON_CANONICAL。
- 对话层不能直接使用 LLM 文本生成正式 Decision/Report。
- 状态机和权限由代码约束而不是 prompt 提醒。

### Batch V1 — One Real User-Entry Integration

交付：
- 明确唯一实际使用入口（本地首方 Host 或受支持的 tool connector）。
- 证明用户请求确实生成 durable Run Envelope 与 append-only stage receipts。
- 真实配置获准语义生产器；若使用 ChatGPT Free 手动交接，必须保留其 provider_origin_verified=false，并不得将其冒充为 API 签名证明。
- 所有手动交接必须继续相同 run_id、request_id、case_id、cutoff 与 prompt hash，不得跳过 resolver 或创建合成 admission。

验收：
- 对用户入口做真实请求运行，不用仅基于测试夹具的调用替代。
- 缺少任何必要上游阶段必须停在精确状态，并且无正式报告副作用。

### Batch V2 — One Real Company End-to-End

首个验证案例建议沿用当前用户的 301345.SZ 请求，截止日期 2026-10-10，并按规范确定其最近交易日价格口径。

从官方披露与可复核价格源开始，产生 exact-byte / SHA-256 / source authority / PIT / licensing provenance records；然后依次完成 semantic admission、Independent Forecast、Valuation、Return、Risk/Portfolio、Decision Admission、human approval pending/decision state、Publication、Investor Report、QA 和 complete Run Receipt。

验收：
- 报告中每个数字都能追溯至已准入证据或显式模型假设。
- Bear/Base/Bull 概率、预期收益、Required Return、entry return cushion 与 margin of safety 可分别重建。
- 缺少的 MIE/Expectation Gap、筹码/Positioning 或监控状态不得省略或被推断成 PASS。
- 在实际入口生成的所有正式文件与哈希绑定可从持久化记录重放。
- 不允许把 AI proposal 当作 Human Approval，也不允许自动下单。

### Batch V3 — Independent Acceptance

独立审计者应从原始请求开始，而不是从已生成的报告反推：
- 验证同一输入的 stage order 与 hash binding；
- 验证任一必需输入删除、篡改或更换 case/cutoff 后会 BLOCK；
- 验证自由文本绕过路径不会产生正式 artifact；
- 验证同一已冻结输入可重放到相同语义决策与 publication/report 内容；
- 由用户对实际入口和完整报告进行明确人审；以本次拒绝为未关闭的问题记录，不能沿用旧样例的 usability PASS。

只有 V1–V3 全部通过，才能重新评估 canonical MVP acceptance。局部 P0 控制面 PR 的合并不得直接关闭生产 P0。

## 7. 审计证据索引

- [MVP v0.1 Definition](MVP_V0.1_DEFINITION.md)
- [IIOS Investment Core Contract v0.3](IIOS_INVESTMENT_CORE_CONTRACT_v0.3.md)
- [Agent Engineering Constitution](../../AGENTS.md)
- [B0 LLM Canonical Execution Governance Freeze](B0_LLM_CANONICAL_EXECUTION_GOVERNANCE_FREEZE_20261007.md)
- [B2-E Natural Language → Semantic → Decision E2E](B2_E_NL_SEMANTIC_DECISION_E2E_20261008.md)
- [B2-F Historical Red-Team Findings](B2_F_CANONICAL_FINDINGS_20261008.md)
- [P0 Canonical Entry Incident Reproduction](P0_CANONICAL_ENTRY_INCIDENT_REPRODUCTION_20261009.md)
- [P0 Batch B1 CLI Host Integration](P0_BATCH_B1_CLI_HOST_INTEGRATION_20261010.md)
- [P0 Batch B2 First-Party Host](P0_BATCH_B2_FIRST_PARTY_HOST_20261010.md)
- [P0 Batch B3 Persisted Upstream Write Authorization](P0_BATCH_B3_PERSISTED_UPSTREAM_WRITE_AUTHORIZATION_20261010.md)
- [P0 Free ChatGPT Web Runtime](P0_CHATGPT_FREE_WEB_RUNTIME_20261010.md)
- [Current Project State Index](../PROJECT_STATE_INDEX.md)

## Final verdict

**项目当前阶段应该定义为：投资核心与治理组件建设已有实质进展，但生产级用户入口与完整真实公司决策闭环尚未被验收；在该闭环通过之前，不能声称新版 IIOS 已能稳定替代 LLM 自由发挥。**

真正的下一步不是再增加 prompt、报告模板或单元测试，而是把这条原本已被定义、但仍未生产验收的真实用户垂直切片打通，并用负向阻塞测试和完整可重放的真实运行凭据证明它无法绕过。
