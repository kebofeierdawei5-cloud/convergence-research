# IIOS 真实 macOS 端到端验收操作手册（2026-10-21）

> **本手册是当前执行入口。** 权限故障与 ChatGPT JSON 交接问题的处理方式以本文件为准；若旧指南与本文冲突，使用本文。验收必须在操作者自己的 Mac 上完成。GitHub CI 通过不等于 Mac 验收通过。

## 1. 只使用一个入口：当前主线安全启动器

推荐从 GitHub Actions 获取带权限元数据的启动器 ZIP，而不是逐个下载 .command 文本文件：

1. 打开 [IIOS macOS launcher distribution 工作流](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/workflows/macos-launcher-distribution.yml)。
2. 打开最新一次 **main 分支成功运行**，确认状态为 **Success**，下载名称形如 `IIOS-macos-launchers-<完整提交 SHA>` 的 artifact。GitHub 页面上的 artifact 标签通常不带 `.zip` 后缀；下载 artifact 得到的外层 ZIP 内，才包含发行包 `IIOS-macos-launchers-<SHA 前 12 位>.zip`。核对运行分支为 `main` 和该运行的 head SHA；只使用成功运行的产物。若没有新的成功运行，再选择 `main` 手动点击 **Run workflow**。
3. 在 Finder 中先解压 GitHub artifact 下载得到的外层 ZIP；找到里面的发行 ZIP `IIOS-macos-launchers-<SHA 前 12 位>.zip`，再解压一次。第二次解压后的目录才包含 **IIOS_一键启用并验收.command** 和 **先看我_只需双击.txt**；请先阅读说明文件。
4. 首选启动 **IIOS_一键启用并验收.command**。该启动器先解析公开仓库 main 的准确 SHA，再在 **~/.iios-private/source/** 内复用或建立经过校验的独立副本；不会 reset、stash、覆盖或清理你已有的项目目录。
5. **如果 Finder 报“没有执行权限”，不要运行 chmod、不要关闭 Gatekeeper，也不要再反复双击。** 打开 Terminal，输入 **/bin/bash **（末尾保留一个空格），把刚解压的 **IIOS_一键启用并验收.command** 拖进终端，按回车。也可将下面路径替换成文件的真实位置后运行：

~~~~bash
/bin/bash "$HOME/Downloads/IIOS_一键启用并验收.command"
~~~~

ZIP 打包测试会检查唯一启动器在 ZIP 中的 POSIX mode 为 **100755**；显式 /bin/bash 调用是不依赖文件执行位的回退。不要把单独下载的旧脚本当成当前版本。

如果启动器报告 Python 版本低于 3.10、找不到 Git、网络无法访问 GitHub 或无法建立独立副本，停止并保留屏幕上的完整错误。不要临时运行另一个未经审计的修复脚本。

## 2. 本次验收案例和边界

本次沿用状态索引中记录的 603699 测试案例，目的是重放固定时点的研究流程，不是报价更新或投资建议：

| 字段 | 本轮固定值 |
|---|---|
| 公司 / 代码 | 纽威股份 / 603699.SH |
| 参考价格 | 37.59 CNY（历史测试输入，不代表今天的股价） |
| 价格观察时点 | 2026-10-16 15:00 +08:00 |
| 分析截止时点 | 2026-10-16 15:30 +08:00 |
| 当前持仓 | 0% |

如向导再次询问上述字段，请逐项录入并确认。若操作者决定使用新案例，必须明确作为新案例启动，不得把不同输入的运行包与本次验收混在一起。

所有运行必须维持 **PILOT_NON_CANONICAL**。本流程不会生成正式 Decision、不代表真实成交或分红资格，也不自动下单。

## 3. 一键进入完整验收

解压后只需双击 **IIOS_一键启用并验收.command**。发行 ZIP 中只包含这一个可执行启动器和一份简短说明，不再暴露多个容易选错的启动入口。

启动器会自动解析并核验公开仓库 canonical main 的 SHA，在 **~/.iios-private/source/** 内复用或建立隔离副本，然后**自动进入完整分析流程：新建分析 → 首轮运行包哈希校验 → 真正 Replay → Replay 包哈希校验**，不再要求你先选 1/2/3 菜单。

你仍然需要按向导完成标的、价格/截止时间、Round A 与 Round B 两次 ChatGPT 研究响应，以及组合风险和主估值模型等必要人工确认。这些不是启动障碍，而是研究输入与投资授权边界，不能为了做到一键而预填或绕过。

不需要手动执行 Git 命令，不需要安装本地 LLM 或配置付费 API。启动器使用 GitHub 公开仓库获取代码；研究和估值交接仍通过浏览器 ChatGPT 完成。

## 4. ChatGPT 研究回答：必须分两轮，分别保存两个 JSON 补丁

**B33 起，独立经营预测与价格感知估值分成两次独立请求。不要把两轮合并成一次，也不要跳过 Round A。**

### Round A — 价格盲公司研究（先执行）

向导先复制 Round A 专用提示，并打开单独文件 `pilot-chatgpt-round-a-response-标的代码-时间戳.json`。第一轮只接收公司身份、分析截止时点、证据登记、Trust/Reality/Quality/Thesis/价值驱动/Risk 与经营驱动预测字段；不接收结构化当前价格、当前持仓、操作者估值选择、MIE、预期差或组合约束。

1. 切换到 ChatGPT，粘贴 Round A 提示并发送。
2. 等待第一轮完整回答，只复制一个符合 `IIOS-RESEARCH-PATCH-0.1` 协议的紧凑 JSON 对象，保存到 **Round A 专用响应文件**，按 Command+S。
3. 本地会验证该补丁只能更新公司侧字段，并检查 JSON、输入保护和文件稳定性。通过后，将公司侧 artifact 冻结并生成 SHA-256。只有通过此步骤，程序才会生成 Round B 提示。

Round A 不得输出 MIE、expectation_gap、主估值、目标入场价或 BUY/ADD/HOLD/REDUCE/EXIT。不要把第一轮复制到 Round B 文件。

### Round B — 价格感知估值与预期差（Round A 冻结后执行）

Round A 验证成功后，程序才会复制 Round B 提示并打开另一个文件 `pilot-chatgpt-round-b-response-标的代码-时间戳.json`。第二轮接收受保护的价格输入和冻结的 Round A 公司侧研究结果，用于估值、MIE、预期差和价格相关分析。Round B 不得改写 Round A 的 Trust/Reality/Quality/Thesis/价值驱动/Risk 或经营驱动预测；需要修改第一轮结论时，当前工作流应失败/复核，不得静默覆盖。

1. 切换到 ChatGPT，粘贴新复制的 Round B 提示并发送。
2. 复制一个紧凑补丁 JSON 对象，保存到 **Round B 专用响应文件**，按 Command+S。
3. 程序会合并 Round B 补丁到第一轮冻结输入，恢复并保护操作者字段，执行完整字段与估值计算校验；通过后才生成分析报告。

### JSON 格式不通过时的恢复流程

程序支持 `IIOS-RESEARCH-PATCH-0.1` 紧凑补丁，并兼容旧版完整对象输入。当前向导的两阶段路径要求分别通过 Round A 和 Round B 的字段白名单；不允许用完整对象绕过阶段隔离。程序将补丁递归合并到本地可信模板并保留人工控制字段；数组整体替换。解析阶段会在内存中修复明确、无歧义的 URL 反斜杠和字符串外、闭合符号前的尾随逗号，原始响应文件不会被改写。截断响应、未闭合字符串、对象后的多余文字或跨阶段字段仍然失败关闭。

- **Round A 字段越界**：不要手动改补丁；程序会给出本轮修复提示。使用同一 ChatGPT 对话修正 Round A 响应并保存到原 Round A 文件。Round A 尚未冻结时不应开始 Round B。
- **Round B 字段越界或试图改写首轮预测**：按提示修复 Round B 响应并覆盖保存到原 Round B 文件。已冻结的 Round A 不会因第二轮格式错误而重做。
- **CHATGPT_JSON_INVALID_COPY_THE_COMPLETE_JSON_OBJECT**：仅保留一个完整 JSON 对象；使用自动复制的修复提示重新生成本轮补丁。不要手工补写尾部或拼接两个对象。
- **CHATGPT_JSON_TRAILING_CONTENT_AFTER_OBJECT**：删除对象后的解释文字、第二个对象或未配对代码围栏，让 ChatGPT 输出单个完整 JSON 对象。
- **CHATGPT_RESPONSE_FILE_EMPTY / NOT_FOUND**：核对终端显示的本轮准确文件路径，先保存 TextEdit；若另存他处，按回车并选择真实文件。不要在 Round A 和 Round B 之间选错文件，也不要重新填写标的和价格。
- **CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS**：本地仍会从可信模板恢复人工控制字段并记录恢复清单；原始响应文件不被改写。恢复不意味着系统可以自行改变价格或投资政策。

**重要：** Round A 与 Round B 的提示文本、原始响应哈希、冻结 artifact 哈希及阶段状态会进入本地输入的研究阶段来源链，报告和回执会显示摘要，Replay 会检查摘要一致性。哈希证明字节关联与阶段输入边界，不证明 AI 事实正确，也不构成正式 Evidence/PIT、Forecast 或 Valuation Admission。
## 5. 向导继续执行后的操作者输入

JSON 通过后，向导会要求你回答组合/风险上下文，并独立确认主估值模型。请基于实际情况填写，不要为了得到 PASS 而虚构数据：

- 组合风险预算、是否允许增加敞口、压力损失约束、入场区间以及初始/目标/最大单股仓位由操作者控制。
- 主估值模型也由操作者确认。选择 EPS_MULTIPLE 时，明确原有基准估值是否已经包含项目利润。若未知就保留 UNKNOWN；不得重复计价。
- 15% 年化门槛、操作者的最大损失政策和必要回报政策不会由 AI 擅自覆盖。
- B27 的 eps_earnings_bridge 会核查整家公司利润代理、上市公司股东归属调整和同期间加权平均稀释股数。申报 EPS 与复算 EPS 不匹配、引用来源类别/域名不一致、B4 不属于 COMPANY_WIDE、期间/币种/股数口径不一致或项目利润重复计入风险都会阻断主估值、回报、目标入场价及 B6。

## 6. 脚本自动执行的验收步骤

验收包装器按顺序完成以下操作，不需要用户自己拼接另一套 Replay 命令：

1. **首次运行包校验**：对 input.json、analysis.json、report.md 及 Round B 的 chatgpt_response_raw.txt 按 pilot_receipt.json 中 SHA-256/字节数清单核对。Round A 的实际提示、原始响应文本、哈希和冻结 artifact 摘要存于 input.json 的 _local_research_round_a_provenance；核对其提示内容确实只含价格盲 allowlist，且其 hash/byte_size 与 analysis/report/receipt 的 research_rounds 摘要一致。Round B 的 prompt/context/frozen-artifact SHA 也应绑定到 input.json。旧运行包若无双阶段谱系，只标记 legacy/not captured，不补造阶段记录。
2. **结构与权限校验**：检查运行 ID、必需字段、目录/文件权限、假设入场语义、分红权益条件语义、B5/B6 和 EPS 盈利桥接字段；正式决策与自动交易权限必须保持关闭。
3. **真正的 Replay**：读取首次运行保存的原始 input.json 重新计算，而非复制报告。
4. **决策材料比较**：要求 PILOT_REPLAY_MATCHED、比较状态 MATCH、hash_verification=PASS 且 mismatched_fields=[]；原始响应来源链的 SHA-256/字节数也进入 analysis.json 的 Replay 比较字段。
5. **Replay 自身包校验**：对 Replay 输出的文件再次核对哈希/字节数，并验证 replay_of 指回首次运行。
6. **本机私有审计 ZIP + 免解压摘要**：生成包含首次运行、Replay、Round B 原始响应的首轮/Replay 逐字节快照（若本次运行具备）、Round A 原始响应与提示的 input.json 谱系、收据、哈希/字节数清单、research_rounds 阶段摘要、比较结果和所选验收日志的交接包。打包器会独立重核 input.json 对原始回答的声明，若输入、收据、原文快照之间的 SHA-256 或字节数不匹配，将拒绝生成 ZIP。另在同一私有目录写出与 ZIP 内 `AUDIT_SUMMARY.md` 逐字节一致的独立摘要副本；不会覆盖已有文件，POSIX 权限为 `0600`。在 macOS 上，脚本会尝试自动打开这份摘要；自动打开失败或摘要副本不可用时，ZIP 内摘要仍保留为后备入口。 摘要中“核心分析链路状态”并排显示首轮和 Replay 已保存的主模型选择/计算类别、经营驱动、B5、EPS 盈利桥、EPS_MULTIPLE/SOTP、估值时点、回报指标可用性及组合输入状态；它只读取现成 `analysis.json`，不重新计算，不把 UNKNOWN/NOT_READY 提升为 PASS。

独立摘要新增的“核心分析链路状态”用于快速定位首轮/Replay 的研究链路缺口，不替代 JSON、报告、回执和 SHA-256 manifest 的逐项审核，也不是投资结论或正式准入结果。

脚本终端最后必须显示首轮包哈希 PASS、Replay 包哈希 PASS 以及 MATCH 才算技术验收通过。若出现 [BLOCKED]、REPLAY_MISMATCH、mismatched_fields 非空或退出码非 0，不要记为通过。

## 7. 文件位置与失败反馈

所有输入和结果仅保存在 Mac 本地私有目录：

- 输入模板、原始响应、修复后的完成输入：**~/.iios-private/local-pilot/inputs/**
- 首轮和 Replay：**~/.iios-private/local-pilot/runs/<pilot_id>/**
- 验收日志：**~/.iios-private/local-pilot/acceptance-logs/**
- 验收交接 ZIP 与免解压审核摘要：**~/.iios-private/local-pilot/acceptance-bundles/**（同一目录；摘要以 `.AUDIT_SUMMARY.md` 结尾）
- 当前主线独立代码副本：**~/.iios-private/source/convergence-research-main-<SHA>/**

遇到失败请保留原始文件，不要直接改 analysis.json、report.md、pilot_receipt.json 或 input.json 来修饰结果。记下终端的完整错误、退出码和日志路径。可先直接打开同目录的独立 `.AUDIT_SUMMARY.md` 查看状态，无需解压 ZIP；完整审计时仍以 ZIP 内文件、manifest 和收据为准。可以将验收交接 ZIP 提供给审计者检查；不要把含价格、完整研究输入和组合细节的文件提交到 GitHub。

## 8. 人工红队复核清单

即使 Replay 完全 MATCH，仍需查看首次运行和 Replay 两份中文报告及 analysis.json：

- 标的、价格、观察时点、known_at、截止时点与币种是否准确；价格是否明确为人工输入、未独立核验。
- 实际 Round A 提示上下文是否仅由公司身份、截止时点、证据登记与公司侧字段构成；不得包含 `price_input`、`case.current_position_pct`、`operator_valuation_context`、MIE 或预期差字段。
- Round A 原始提示/响应 SHA-256 与冻结 artifact SHA-256 是否一致；Round B 是否消费同一个冻结 artifact；Round B 是否未改写首轮 assessment 与 operating_driver_forecast。
- `analysis.json` 与 `pilot_receipt.json` 的 `research_rounds` 是否完全一致；Replay 的比较字段包含 `research_rounds` 且状态为 MATCH。
- eps_earnings_bridge 的公司范围、预测期间、非控股股东损益、其他税后归属调整、稀释股数单位/期间、EPS 差异与来源引用是否可复核。
- B4/B5 是否把项目增量利润误当成集团净利润或重复加总；B6 绑定约束及 90%/100%/110% 梯度是否与回报和目标入场价一致。
- 来源时间是否符合截止日；未知事实是否保留 UNKNOWN；报告和 JSON 的判断、价值情景与风险是否一致。
- governance.formal_decision_created、canonical_run_receipt_created、execution_authorized、auto_execution 必须为 false；这仍然不是正式投资决策或交易授权。
- B62 分部对账：B4 是否为 COMPANY_WIDE，是否只使用相邻完整年度；每个 B4 产品是否有显式 business_segment_id，多个产品归集是否有业务依据且 ID 一致；历史/前瞻分部财务八项 typed measures 的期间、单位、data_class、basis、source/cutoff 是否合格；缺失字段是否保留 UNKNOWN 而非默认为零。
- B62 盈利桥：B55 每个产品贡献是否已经 CALCULATED_AND_RECONCILED；产品→分部 ID 是否前后保持一致；分部正常化归母利润是否剔除非经常性项目、按正常化少数股东损益扣除，且分解残差均在 CNY 1 内。
- B62/SOTP 比较：B4、SOTP、B61 的 forecast_period 是否完全一致；SOTP 每个 segment 是否显式声明 earnings_basis=NORMALIZED_PARENT_ATTRIBUTABLE 并与 B4 business_segment_id 精确对应；当前 SOTP P/E 是否被固定；B4 全分部利润向量形成的价值池是否与 B61 Required Return（未计分红）要求池按同一母公司调整和股数口径比较；单个分部在其他分部按 B4 预测不变时所需的 P/E 是否与当前选定 P/E 分开显示。
- B61 单变量盈利要求不得相加；它是假设其他分部利润不变的替代敏感性。只有 B62 全分部 B4 预测价值池才代表多个分部同时变化的情景结果。若无独立前瞻母公司成本/净现金/其他调整预测，不得给这些因素虚构变化金额。
- 报告/analysis.json/Replay 应同时保留 B4 分部利润桥、SOTP earnings_basis、B61 要求、B62 比较与所有 UNKNOWN/NOT_COMPARABLE 标记；不允许以 B62 诊断结果反向覆盖 SOTP 主估值、外部 MIE、expectation_gap、B5/B6 或 Decision。

## 9. 已发生故障与防重复清单

| 历史故障 | 当前防护 | 遇到时该怎么做 |
|---|---|---|
| .command 下载后执行权限缺失，用户确认曾重复发生四次 | ZIP 内检查 mode 100755；提供 /bin/bash 回退；推荐打包 artifact 而非 raw 文件 | 直接使用 /bin/bash 调用解压后的安全启动器；不要再反复 chmod |
| ChatGPT JSON 在长 URL 前插入非法反斜杠 | 只对 https\\://、www\\. 做窄范围修复；其余解析错误保留行/列 | 使用程序生成的修复提示，覆盖保存新回答 |
| JSON 对象后附带解释文字、多个对象或不完整 Markdown 围栏 | 红队补强为单对象+无非空尾部内容校验，代码围栏必须成对 | 要求 ChatGPT 只返回一个完整 JSON 对象 |
| ChatGPT 改写标的、价格、截止时间或风险政策字段 | 从可信本地模板恢复；列出字段路径；原始响应保留 | 不手工改真实价格/风险政策；先审阅恢复警告 |
| 保存了错误文件或文件大小没变，程序持续等待 | 唯一响应文件路径、稳定写入检测、mtime+SHA-256 签名、回车触发文件选择/复核 | 先确认真实保存路径；选择正确文件，勿重复新建向导 |
| 旧脚本出现类似 log.chmod(...) 的独立辅助代码异常 | 统一使用 canonical main 的验收模块；不再用聊天中临时拼装的旧 Replay 脚本代替 | 停止旧脚本，保留错误和日志；从当前主线安全启动器重跑 |
| 本机旧仓库分叉/有本地修改，更新器拒绝覆盖 | 本次安全启动器在私有目录创建按 SHA 隔离副本，不触碰旧工作区 | 使用安全启动器而非旧仓库内的本地更新入口 |

每次出现新失败，都要记录准确报错、触发步骤、代码版本/提交 SHA、根因、修复、回归测试和复测结果，再关闭事件。只改说明但不补回归测试，不能算完成根因修复。
