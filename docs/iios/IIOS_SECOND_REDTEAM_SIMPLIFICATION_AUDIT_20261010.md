# IIOS 二次红队审计：开发与部署复杂度是否偏离原始需求

- 审计日期：2026-10-10
- 基线：canonical main @ 0e6ab65764298afa1fe723ad0a16b8683eb93276
- 类型：架构复杂度 / 部署成本 / 产品范围 / 原始需求符合性
- 判定：**NEEDS ARCHITECTURAL SIMPLIFICATION — DO NOT ACCEPT CURRENT PATH AS THE ONLY PRODUCT DELIVERY MODEL**
- 范围：文档和代码结构静态审计；未部署 Host、未运行真实公司案例、未测量实际现金成本或人时。
- 本文仅为审计记录，不修改投资语义、不关闭现存 P0，也不代表产品通过验收。

## 1. 执行摘要

原始需求是个人使用的单家公司投资决策工具：手动选择一个预筛选公司，输入研究截止日和必要组合约束；系统基于可验证资料、基本面、独立预测、估值、预期差、风险与收益门槛输出 BUY / ADD / HOLD / REDUCE / EXIT / WATCH / NO-BUY / REVIEW_REQUIRED；缺少材料时应明确阻塞；最终审批归人；不自动交易。

原始需求没有要求必须依赖 GitHub Actions 运行投资决策，也没有要求部署多用户 SaaS、远程微服务、公共 API 服务或多模型集群。

当前架构作出了正确的技术选择——把确定性计算、状态转换、权限、日期、哈希与持久化交给代码——但把“通过代码实现可靠性”与“必须建设复杂的运行时/部署控制面”过度绑定。仓库已包含约 80 个 GitHub Actions workflow 文件、73 个 iios_mvp 目录条目与 108 个 tests 目录条目（这些包括不同研究/治理轨道，不等于 80 个生产服务）。当前首方 Host、可信 runtime factory、签名 provider receipt、多个 canonical admission stores、请求 bundle、多个环境变量、外部/本地模型边界和人工 ChatGPT handoff，使真实运行仍需大量操作准备。当前状态索引仍将真实生产 Host 及 P0-LLM-001/P0-LLM-004 验收列为 OPEN。

本次红队结论不是“GitHub 或代码是错的”，而是：
1. **GitHub 是合理的开发治理、版本和 CI 工具；它不应该成为个人投资者使用 IIOS 的运行前置条件。**
2. 确定性投资内核是必须的；远程 Host、网络认证、多提供者签名体系、复杂的 admission-store 运维并不都是个人版 MVP 必需品。
3. 当前最大的产品成本是“代码组件已实现，但用户要先满足一系列工程配置，才能尝试完整分析”，这违反最小完整垂直切片与快速开始真实用户试用的初衷。
4. 推荐走 **Local-first 单用户 IIOS**：一条启动命令/一个本地应用进程、一个规范入口、一个本地数据目录、一个权威存储、一个报告产出链。GitHub 保留为代码仓库、版本控制、PR 审查和 CI，但移出个人运行关键路径。

## 2. 原始需求与不可妥协原则

### 2.1 产品目标

MVP v0.1 定义了一条完整而狭窄的垂直切片：
Company + As-of cutoff → Evidence → Trust / Reality → Independent Forecast → Valuation → MIE / Expectation Gap → Risk → AI Decision Proposal → Human Approval → Immutable Snapshot → Replay。

MVP v0.1.1 明确要求最小启动入口只需 Market、Symbol、As-of Date 和 Current Position；用户不应直接填写 Evidence / Reality / Forecast / Valuation。它同时明确排除微服务拆分、消息队列、自动交易、CSI800/A02 完整研究基础设施、完整估值路由器及多公司自动筛选。

工程章程要求 deterministic calculations、state transitions、permissions、dates、hashes、persistence 在 LLM 之外执行；不得捏造缺失数据；UNKNOWN / 缺失 / 过期 / 冲突 / 不可验证状态必须关闭受影响权限；AI Proposal 和 Human Decision 分离；不自动下单。

### 2.2 关键区分

原始需求要求的**复杂度是投资问题与证据治理的复杂度**，不是部署方式的复杂度。

必须保留：
- PIT 与来源证据，准确区分来源真实性、可知时间与字节完整性；
- 结构化 LLM 解释，经 schema / case / cutoff / evidence binding 验证后才能进入决策；
- 独立 Forecast、Valuation、Expected Return、Required Return、Entry Return Cushion、Margin of Safety 语义不混淆；
- Risk / Portfolio / Decision 权限约束；
- 缺失即 UNKNOWN / BLOCKED / REVIEW_REQUIRED，不得由模型补齐为 PASS；
- 不可变决策历史、hash、replay、报告一致性与人类审批边界。

不应默认成为个人版运行必需：
- 远程生产 HTTP Host；
- 对外网络绑定、Bearer 认证、反向代理/TLS 终止；
- 每个本地 LLM 回调都必须模拟外部生产者签名的运维流程；
- 一个需要操作者手动准备多个目录、bundle、manifest、provider key、runtime key、admission objects 和 environment variables 的启动过程；
- 多个 provider backend 作为首版同时支持；
- 把 GitHub Actions 当作每一次投资分析的执行平台；
- 把 A02/CSI800/M1.2 预测研究轨道纳入公司级 MVP 的运行依赖。

这些技术在远程、多用户、自动化运行、跨主机信任边界下可能合理，应留作可选部署 profile，而不是个人版启动门槛。

## 3. 发现与风险排序

### F-01 — P0：开发治理平台与产品运行平台被混为一体

**已证实的架构风险。**

GitHub 适合做 source control、branch/PR review、CI 和可审计变更。个人在本地研究一家上市公司，并不需要每次运行都依赖 GitHub Actions，也不应将个人原始资料写入公开仓库或 CI artifacts。

当前仓库的运行时和数据工作流有大量 GitHub Actions。80 个 workflow 文件本身不证明架构错误，但说明维护面已明显扩大。真正的问题是：当前生产入口/真实运行还未验收，工程活动却已发展为大量工作流、签名、主机和来源抓取子系统；这增加了维护成本，却没有先交付一个用户可直接启动的完整垂直切片。

**风险：**开发过程可以持续“有活动、有 CI、有 PR”，而最终用户依旧无法直接完成一次规范的投资研究。

**建议：**GitHub 留在开发和发布边界。用户端消费一个已版本化的发布包或本地检出，不要求熟悉 PR、Actions、artifact、分支和 SHA 才能分析一家公司。

### F-02 — P0：生产级远程 Host 模型不适合成为个人 MVP 默认

当前首方 Host 要求 bundle root、data root、durable output root、Bearer secret、可信 runtime factory 以及相应 provider/admission store 环境配置。可信工厂还需要模型 ID、模型版本、协议、provider endpoint、runtime signing keypair 和 pinned public key等配置。

这些要求对于将来部署一个远程生产 Host 有治理价值；对于一个只在用户自己 Mac 上使用的单用户程序，大部分都构成非必要启动负担。

一个仅绑定 loopback、本地运行、无远程访问且无其他租户的程序，可以使用更小的威胁模型：
- 只开放一个本地入口；
- 固定本地数据/输出目录；
- 权限限制在当前用户；
- 原始文件、结构化记录和报告不离开本机；
- LLM 响应作为不可信输入，统一经过结构/schema、身份、证据 ID、截止日和业务一致性验证；
- 以哈希和 append-only run record 支持完整性检测和 replay；
- 不将“hash 证明 bytes integrity”误称为“证明远程 provider 真实生成”。

本地 profile 不意味着取消数据来源验证或允许 LLM 写 Decision。它只是把远程网络认证与跨主机签名的复杂性移出默认单用户路径。

### F-03 — P0：免费 ChatGPT 网页交接仍然复杂，并且并未解决“自动调用代码”的产品问题

当前 ChatGPT Free Web Runtime 要求：
1. 在本地运行 canonical CLI；
2. 复制指定 prompt 到 ChatGPT；
3. 把原始 JSON 响应存进文件；
4. 手动导入响应；
5. 重跑同一 canonical 命令；
6. 对不同回调阶段重复此过程。

文档同时明确 provider_origin_verified=false，且手动交接不会自动提供来源准入、市场价格、Forecast、Valuation、Decision、报告或完整 Run Receipt。

因此此方案减少了 API 金钱支出，但把集成成本转移给操作者，并没有提供“一句自然语言即可可靠运行整个 IIOS”的体验。

**建议选择并明确其中一种产品承诺，不再模糊混用：**
- 个人版默认采用本地应用入口，由结构化表单收集 ticker/cutoff/position，LLM 解释通过清晰的本地输入输出交接完成；
- 将免费 ChatGPT 手动交接标为可选的辅助工作流，不声称它是自动集成或来源已认证；
- 若未来要求真正无人工粘贴的 ChatGPT/API 调用，则作为独立的高级连接器方案评估运行成本，不能把它伪装成免费、本地且零部署。

对于手动选择单一公司的核心用例，不必让 LLM 先解析一段任意自然语言才能确定 market/symbol/cutoff。由本地 UI 明确收集这些少量字段，可以去掉一个不必要的 LLM callback/stage，同时减少 instrument/cutoff 错绑风险。自然语言接口可以继续提供为可选入口。

### F-04 — P1：多种运行模式并存，导致产品承诺不清晰

当前存在 repository CLI、first-party HTTP Host、trusted runtime factory、local Ollama、free ChatGPT manual handoff 等路径。每种路径都有各自的配置、运行条件、验收和 non-claims。

这些路线不是不能共存，但在 MVP 阶段同时开发和维护会扩大组合空间：CLI × Host × provider type × source/admission state × report/receipt flow 的组合需要更多测试，而用户仍不知道从哪里开始。

**建议：**MVP 只认一个默认入口和一种默认运行 profile。其余接口保持模块化但标为 experimental/optional；没有端到端用户价值的 profile 暂停迭代。

### F-05 — P1：复杂的阶段准入对象向用户泄漏为运维责任

Evidence Manifest、多个 admission records、runtime receipts、bundle IDs 和多组 environment variables 应是系统内部实现，而不是让用户自己拼装的原始输入。

当前设计中一些对象只能被可信 resolver 读取，不能由工厂自动生成；该权限边界是正确的。但是如果没有一个上游 intake/preparation 工具把普通用户输入和官方材料转成经过验证的候选对象，用户就可能被迫手动准备内部 JSON 结构，或要求工程人员临时造 records。

**建议：**用户只提供公司代码、市场、截止时间、现有仓位及组合限制；系统自己创建私有 case workspace、拉取/接收证据、验证并显示缺项。仅正式 admission 与决策代码可以将内部对象标为 admitted，不能让 UI/LLM/操作者直接填状态字段越权。

### F-06 — P1：跨主机数字签名的采用边界需要与单用户威胁模型匹配

Ed25519 对由远程 provider 生成的 receipt、跨服务传递和固定公钥验收是合理的。但对单机同进程/同用户的纯本地模型调用，若本地进程和本地磁盘均属于同一信任域，维护一组 deployment private/public keys 可能只增加安装失败、密钥轮换、环境配置和诊断成本，并不能自动证明模型推理的经济正确性。

**建议：**区分两种 Provenance Profile：
- Local single-user profile：记录固定模型标识/版本（可选模型文件摘要）、prompt hash、输入 evidence refs、输出 bytes hash、代码版本及运行时间；所有输出仍不可信且必须过确定性准入。它记录本地可复核的来源，但不声称有抗恶意本机管理员的密码学证明。
- Remote/provider profile：才要求强 provider attestation、签名 receipt、独立公钥 pinning、外部传输安全及相关运维流程。

若将来需要远程、多用户或可抵御宿主篡改的保证，再单独升级这一安全边界。不能将本地 hash 记录错误宣称成远程 provider 真实性证明。

### F-07 — P1：数据来源体系需要按公司级 MVP 收敛，而不是被更广泛研究数据拖动

Free-first 官方证据是正确方向；A02 / CSI800 与完整跨截面预测研究在原始 MVP 中明确是非阻塞研究轨道。当前状态记录亦指出它们不应成为 company-level Investment Core 的依赖。

官方源抓取、原始字节存储与来源条款核查确实复杂，不能通过改成随意网页摘要来删除。简化的方向应当是：
- 默认只覆盖当前一个候选公司实际所需的权威资料类型；
- 先用官方披露/交易所资料，公开端点不可用时保留 BLOCKED 并给出精确缺项；
- 允许用户下载/上传官方原始文件到私有 intake，再复核原始 bytes、SHA-256、来源、发布时间/PIT 和可复用范围；
- 把二级网站/卖方预测明确分为 supplementary / non-admitted，不能静默替换；
- 不为了让单一案例通过而扩展完整市场数据基础设施。

这保持证据标准，但避免为未使用的市场广度构建长期数据平台。

## 4. 简化方案对照

| 方案 | 开发复杂度 | 部署/运维 | 模型路径 | 本地数据隐私 | 与原始需求的匹配 |
|---|---|---|---|---|---|
| A. Local-first 单用户 IIOS（推荐） | 中低：复用现有 Python 内核，移除默认远程组件 | 低：一个安装/启动入口，一个本地工作区 | 本地模型自动调用，或有明确标注的人工 ChatGPT 交接 | 原始证据与输出默认仅本机 | **最高**，最贴合个人投资、free-first、单公司 |
| B. 本地程序 + ChatGPT Free 手动交接（快速过渡） | 低到中 | 低到中；需要复制/导入多次 | 可免费用 Web 模型，但不是真正自动集成 | 文件留本地，用户要手动搬运 prompt/response | 符合预算，但 UX 与模型来源证明有明确妥协 |
| C. 远程 Host + provider/API/工具连接 | 高 | 高：部署、身份、密钥、访问控制、监控 | 可实现更流畅的在线调用，取决于受支持的接口 | 需管理网络和数据传输边界 | 只有将来明确需要跨设备/自动化/多用户时才值得 |

### 对方案 A 的建议边界

方案 A 不是删掉 IIOS 规则，而是把系统部署成一个本地单用户应用：

```
一个启动命令
    ↓
一个本地入口（CLI 或仅 loopback 的轻量 UI）
    ↓
一个本地 Case Workspace
    ├── case.json
    ├── raw evidence + manifest
    ├── semantic records
    ├── forecast / valuation / decision
    ├── immutable run log / hashes
    └── human + machine reports
    ↓
确定性准入与决策内核
    ↓
明确状态 + 人工审批
```

建议内部存储采用本地 SQLite + 文件系统：
- SQLite：case、stage status、decision revision、run/event metadata、source refs；
- 文件系统：原始财报/公告、机器对象、Markdown/PDF 报告、哈希清单；
- 同一事务内记录阶段状态和引用；输出工件 write-once；replay 从被冻结的输入和记录重建；
- 默认不上传原始资料、报告或私有组合约束；
- 不运行后台 scheduler，不需要公开网络端口，也不需要部署运维服务。

CLI 与 UI 应复用同一 application service，不能各自实现一套决策流。正式入口是本地应用；底层函数并不是新的用户入口。

## 5. 应当保留、简化、暂缓的工程资产

### 保留（不可妥协）

- 现有 Investment Core v0.3 决策语义与收益语义；
- 确定性投资计算、权限、状态机和 write authorization；
- B2 Evidence/PIT 的来源、时间、hash 和缺失阻塞契约；
- 语义产物 schema / case binding / evidence lineage / deterministic admission；
- Decision Revision、Human Approval、Machine Publication、报告 QA 和 replay 的概念；
- GitHub 作为源代码版本控制、代码评审、CI 与审计记录。

### 简化（优先做）

- 单用户默认仅本地运行；远程 Host 不作为运行前置；
- 单一用户入口，默认表单/固定字段输入，不要求 LLM 解析所有基本身份字段；
- 一个本地数据根目录，由系统自行建立 workspace 和内部文件；
- 一个统一的运行控制器协调各阶段，不由对话文字来决定阶段；
- 一个模型调用适配器，其他 provider backend 暂停扩展；
- 本地模型 profile 采用轻量 provenance；远程签名 profile 保留为独立扩展；
- 一个正式报告写出路径和一套确定性 QA，不允许通用 LLM 直接把自由文本声明为正式结果；
- GitHub Actions 仅执行开发/回归/发布验证，不参与用户每次的研究执行。

### 暂缓（除非产生明确用户价值）

- 公共/外部可访问的 HTTP Host；
- 多用户认证、远程代理、TLS 终止等部署功能；
- 多 provider / 多 runtime 交叉兼容扩展；
- 每次本地模型调用都跨机器验证的签名基础设施；
- A02/CSI800、全市场筛选、M1.2 扩展和新估值模型族进入产品关键路径；
- scheduler、告警、自动交易与自动组合优化。

注意：暂缓不等于删除代码；先保留在现有仓库中，停止作为 MVP 必需功能和验收依赖。

## 6. 简化后的实施计划

### Batch S0 — Architecture Freeze / MVP Simplification ADR

先冻结本次架构决定，指定：
- 唯一的默认运行 profile：LOCAL_SINGLE_USER；
- 唯一的正式用户入口；
- 一套 workspace layout；
- 一套 artifact/receipt contract；
- provider 适配器作为可选层；
- 远程 Host 为 optional/experimental；
- no-new-features 约束，直到单公司真实垂直切片通过。

验收：用户版启动和成功/阻塞路径均有一份短文档；组件通过不能标成产品通过。

### Batch S1 — One-Command Local Launch

交付目标：在全新 Mac 用户环境中，用一个带版本的安装/启动命令创建虚拟环境、安装锁定依赖、准备私有目录、启动本地入口。禁止要求操作者先手工配置十多个环境变量、私钥、bundle path 和 admission root。

运行时数据绝不写入 GitHub。启动器不得伪造、预填或“升级”任何 Evidence/Forecast/Valuation admission。错误必须呈现成明确、可操作的缺项，而不是 Python traceback 或模糊的 BLOCKED。

验收：在一台干净环境完成安装；断网/资料缺失时能够安全 BLOCKED；重启后历史 run 与报告仍可读取。

### Batch S2 — One Real Company Vertical Slice

使用一个新用户指定候选（可沿用 301345.SZ）完成：
1. 由 UI 明确采集证券市场、代码、截止日/ as-of、持仓和组合限制。
2. 建立私有证据 workspace；取得官方披露/股价，或者请用户提供原始官方文件；逐项保留来源、原始字节 hash、时间口径、用途和复用限制。
3. 依次执行 Trust / Reality / Quality / Thesis / Value Drivers、Forecast、Valuation、Return / Risk / Portfolio、Decision。
4. 缺少任一关键材料时，显示当前 stage 与具体缺项，禁止正式决策/报告越权完成。
5. 生成 machine JSON、中文报告、QA 收据和完整可重放 Run Record。

验收不是“报告看起来完整”，而是每个结论都有 admitted evidence / explicit model assumption 引用，且整个输出能从冻结输入独立重放。

### Batch S3 — Adversarial Acceptance

必须测试：
- 直接要求对话模型“按 IIOS 分析”而没有应用入口：不得把自由文本包装成正式 artifact；
- 删除/修改原始文件：哈希或来源校验失败并 BLOCK；
- 缺少 Forecast、Valuation 或必需 semantic object：禁止创建完整 Decision/Report；
- 变更公司代码、截止日或当前价格来源：case/PIT binding 失败；
- 把 MIE absent 当 NOT_IDENTIFIABLE/PASS：失败；
- 用报告/CI PASS 覆盖 Human Approval：失败；
- 同一输入重复运行：语义结果、决策状态和输出内容保持可重放；
- local/private 数据不会流入 GitHub commits、公开 Actions artifacts 或远程日志。

只有真实应用入口、完整真实公司案例和独立重放全部通过，才允许把 LOCAL_SINGLE_USER profile 标记为 MVP usable。

### Batch S4 — 只有在真实需要出现时再评估 Remote

当且仅当用户明确需要远程访问、自动化调用、跨设备/多人使用时，才重新评估 HTTPS Host、认证、签名 provider receipts、密钥管理、部署监控和多用户隔离。Remote profile 不能反向迫使本地个人版使用同样复杂的运维方式。

## 7. 红队反驳：简化会不会牺牲可信度？

### 可以简化的部分
部署 topology、服务数量、环境变量、provider 扩展、每个请求的运行开销以及人工配置。单机应用可以把多个内部模块作为同一进程中的纯函数/服务调用，并以 SQLite/本地文件完成持久化。

### 绝不能简化的部分
证据来源真实性、PIT、缺失处理、计算正确性、上下游对象的 case/cutoff binding、LLM 输出 schema 验证、Decision/approval 权限分离、不可变历史以及 replay。

### 需要明确的取舍
Local-first 不会魔法般地使免费 ChatGPT 网页变成可以直接调用本机脚本的 API。若坚持完全不使用 API key，同时又要求在 ChatGPT 网页内无人工交接、一步完成正式 IIOS 运行，则需要受支持的连接器/Host 机制；这是另一个产品需求，会增加部署和运维。对个人 MVP，建议优先交付可启动的本地 app；ChatGPT Free handoff 是一个 optional assisted workflow，并将其 provider-origin evidence 明确降级，不能冒充 cryptographic attestation。

同样，哈希只能证明当前保存文件相对于清单的完整性，不能证明外部来源真实性；本地模型版本/输入/输出记录也只能提供本机审计线索，不能提供抵御拥有本机管理员权限的攻击者的强远程 attestation。这些限制要如实说明，而非靠简化措辞隐藏。

## 8. 最终判定

**现有路线的主要问题是过早为生产化、远程化和可插拔模型提供者建立完整的控制面，却没有先以最低运维成本交付可实际使用的个人投资垂直切片。**

建议：
- 保留 GitHub 与已有代码，停止把 GitHub/CI 当作用户运行依赖；
- 冻结投资语义，不再增加新模块；
- 把 LOCAL_SINGLE_USER 设为默认产品架构；
- 在 S1 里把部署压缩到一个安装/启动命令和一个本地工作区；
- 在 S2/S3 里用真实公司端到端与失败关闭回归证明可信度；
- 远程 Host、签名外部 provider 和多租户控制面后置。

以上是架构重收敛建议，尚未对当前生产环境执行部署，因此没有声称已实现或通过这套简化方案。
