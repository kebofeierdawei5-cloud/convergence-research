# IIOS 真实 macOS 端到端验收操作手册（2026-10-21）

> **本手册是当前执行入口。** 权限故障与 ChatGPT JSON 交接问题的处理方式以本文件为准；若旧指南与本文冲突，使用本文。验收必须在操作者自己的 Mac 上完成。GitHub CI 通过不等于 Mac 验收通过。

## 1. 只使用一个入口：当前主线安全启动器

推荐从 GitHub Actions 获取带权限元数据的启动器 ZIP，而不是逐个下载 .command 文本文件：

1. 打开 [IIOS macOS launcher distribution 工作流](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/workflows/macos-launcher-distribution.yml)。
2. 打开最新一次 **main 分支成功运行**，确认状态为 **Success**，下载名称形如 `IIOS-macos-launchers-<完整提交 SHA>` 的 artifact。注意：GitHub 页面上的 artifact 标签通常不带 `.zip` 后缀；下载 artifact 后得到的 ZIP 档案，内部才包含发行文件 `IIOS-macos-launchers-<SHA 前 12 位>.zip`。核对该运行的分支是 `main`，并留意关联的 head SHA；不要只凭文件名把非成功运行的产物当作当前版本。合并启动器打包相关文件后，工作流会自动运行；若没有新的成功运行，再选择 `main` 手动点击 **Run workflow**。只使用成功工作流产物。
3. 在 Finder 中先解压刚下载的 GitHub artifact ZIP；它里面会有一个发行包 `IIOS-macos-launchers-<SHA 前 12 位>.zip`。再把这个内层发行 ZIP 解压一次。第二次解压后的目录才包含 **IIOS_一键启用并验收.command** 与 **先看我_只需双击.txt**，请先阅读说明文件。
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

你仍然需要按向导完成标的、价格/截止时间、ChatGPT 研究响应，以及组合风险和主估值模型等必要人工确认。这些不是启动障碍，而是研究输入与投资授权边界，不能为了做到一键而预填或绕过。

不需要手动执行 Git 命令，不需要安装本地 LLM 或配置付费 API。启动器使用 GitHub 公开仓库获取代码；研究和估值交接仍通过浏览器 ChatGPT 完成。

## 4. ChatGPT 研究回答：必须保存完整、单一 JSON

向导会打开 ChatGPT 页面、一个专用 JSON 响应文件，并把完整研究提示和本次输入模板复制到剪贴板。

1. 切换到 ChatGPT，粘贴提示并发送。等待回答全部生成。
2. 复制 **完整 JSON 对象**，不是开头几百行、不是摘要，也不要复制两个候选 JSON 对象。若回答使用 JSON 代码围栏，应连同完整对象一起复制。
3. 切回向导自动打开的 **pilot-chatgpt-response-标的代码-时间戳.json**。全选文件现有内容，粘贴完整回答，再按 **Command+S** 保存。
4. 不要把 JSON 粘贴到 Terminal，不要手动把文本拆成多个文件，不要为了修错而直接改输入模板。保存后，等待程序检测到大小、修改时间和 SHA-256 内容签名稳定；一般无需再按回车。
5. 程序在生成分析前依次检查 JSON 语法、单对象边界、必需研究字段、数值/数据类别结构和 PIT 引用约束。任何一项失败都会阻止分析，不会因为 JSON 可解析就自动视为研究合格。

### JSON 格式不通过时的恢复流程

当前程序支持完整代码围栏、开头的简短说明文字，以及两类明确、无歧义的 URL 转义修复（**https\\://** 和 **www\\.**）。除此以外不猜测、不自动重写 JSON。

- **CHATGPT_JSON_INVALID_COPY_THE_COMPLETE_JSON_OBJECT**：按错误给出的行号/列号查看；当前程序会将包含本次模板、原始提示和失败回答的修复提示复制到剪贴板。切回同一 ChatGPT 对话粘贴并发送，让它返回新的完整 JSON；将新回答整体覆盖到同一个响应文件并保存。
- **CHATGPT_JSON_TRAILING_CONTENT_AFTER_OBJECT**：对象后还有解释文字、第二个 JSON 对象或未配对的代码围栏。只保留一个完整 JSON 对象后重试。
- **CHATGPT_JSON_INVALID_CODE_FENCE_NOT_CLOSED**：代码围栏没有完整结束。请让 ChatGPT 返回完整对象，或返回成不带代码围栏的纯 JSON。
- **CHATGPT_RESPONSE_FILE_EMPTY**、**CHATGPT_RESPONSE_FILE_NOT_FOUND**，或终端一直没有检测到更新：核对终端显示的准确文件路径与 TextEdit 标题。先在 TextEdit 中保存；如果响应确实保存在别处，按一次回车触发检查，并在文件选择窗口选择真正保存的 JSON。不要另起向导，也不要删掉旧输入。
- **CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS**：当前主线会先将 case、price_input、operator_valuation_context 以及 decision_parameters.max_loss_pct、decision_parameters.required_return_annualized 从可信本地模板恢复，并把恢复字段写入私有完成输入的 _local_operator_controlled_field_recovery 记录；原始 ChatGPT 响应文件不被改写。终端若显示 [WARN]，先阅读恢复清单；它本身不是让你手工更改真实价格或风险政策的指令。如果随后出现其他完整性错误，再按新错误的修复提示继续。
- 若修复后的内容与上次字节数相同也无需改名：程序以内容 SHA-256 辅助判断保存是否有变化。等待期间不要反复按回车；可按 Control-C 安全退出，已存在的文件会保留。

**重要：** ChatGPT 返回的研究数字、来源链接和结论仍需要审计。通过 JSON 格式校验不等于来源真实，也不等于所有字段已正式 Evidence/PIT 准入。

## 5. 向导继续执行后的操作者输入

JSON 通过后，向导会要求你回答组合/风险上下文，并独立确认主估值模型。请基于实际情况填写，不要为了得到 PASS 而虚构数据：

- 组合风险预算、是否允许增加敞口、压力损失约束、入场区间以及初始/目标/最大单股仓位由操作者控制。
- 主估值模型也由操作者确认。选择 EPS_MULTIPLE 时，明确原有基准估值是否已经包含项目利润。若未知就保留 UNKNOWN；不得重复计价。
- 15% 年化门槛、操作者的最大损失政策和必要回报政策不会由 AI 擅自覆盖。
- B27 的 eps_earnings_bridge 会核查整家公司利润代理、上市公司股东归属调整和同期间加权平均稀释股数。申报 EPS 与复算 EPS 不匹配、引用来源类别/域名不一致、B4 不属于 COMPANY_WIDE、期间/币种/股数口径不一致或项目利润重复计入风险都会阻断主估值、回报、目标入场价及 B6。

## 6. 脚本自动执行的验收步骤

验收包装器按顺序完成以下操作，不需要用户自己拼接另一套 Replay 命令：

1. **首次运行包校验**：对 input.json、analysis.json、report.md 以及新向导生成的 chatgpt_response_raw.txt 的 SHA-256/字节数与 pilot_receipt.json 清单核对；同时交叉核验 input.json 的原始响应声明、运行收据与响应文件的哈希/字节数；旧运行包若无原始响应，仅标记为 legacy/not captured，不补造响应文件。
2. **结构与权限校验**：检查运行 ID、必需字段、目录/文件权限、假设入场语义、分红权益条件语义、B5/B6 和 EPS 盈利桥接字段；正式决策与自动交易权限必须保持关闭。
3. **真正的 Replay**：读取首次运行保存的原始 input.json 重新计算，而非复制报告。
4. **决策材料比较**：要求 PILOT_REPLAY_MATCHED、比较状态 MATCH、hash_verification=PASS 且 mismatched_fields=[]；原始响应来源链的 SHA-256/字节数也进入 analysis.json 的 Replay 比较字段。
5. **Replay 自身包校验**：对 Replay 输出的文件再次核对哈希/字节数，并验证 replay_of 指回首次运行。
6. **本机私有审计 ZIP**：生成包含首次运行、Replay、两份逐字节一致的原始 ChatGPT 响应快照（若首次运行具备）、收据、哈希/字节数清单、比较结果和所选验收日志的交接包。打包器会独立重核 input.json 对原始回答的声明，若输入、收据、原文快照之间的 SHA-256 或字节数不匹配，将拒绝生成 ZIP。

脚本终端最后必须显示首轮包哈希 PASS、Replay 包哈希 PASS 以及 MATCH 才算技术验收通过。若出现 [BLOCKED]、REPLAY_MISMATCH、mismatched_fields 非空或退出码非 0，不要记为通过。

## 7. 文件位置与失败反馈

所有输入和结果仅保存在 Mac 本地私有目录：

- 输入模板、原始响应、修复后的完成输入：**~/.iios-private/local-pilot/inputs/**
- 首轮和 Replay：**~/.iios-private/local-pilot/runs/<pilot_id>/**
- 验收日志：**~/.iios-private/local-pilot/acceptance-logs/**
- 验收交接 ZIP：**~/.iios-private/local-pilot/acceptance-bundles/**
- 当前主线独立代码副本：**~/.iios-private/source/convergence-research-main-<SHA>/**

遇到失败请保留原始文件，不要直接改 analysis.json、report.md、pilot_receipt.json 或 input.json 来修饰结果。记下终端的完整错误、退出码和日志路径。可以将验收交接 ZIP 提供给审计者检查；不要把含价格、完整研究输入和组合细节的文件提交到 GitHub。

## 8. 人工红队复核清单

即使 Replay 完全 MATCH，仍需查看首次运行和 Replay 两份中文报告及 analysis.json：

- 标的、价格、观察时点、known_at、截止时点与币种是否准确；价格是否明确为人工输入、未独立核验。
- eps_earnings_bridge 的公司范围、预测期间、非控股股东损益、其他税后归属调整、稀释股数单位/期间、EPS 差异与来源引用是否可复核。
- B4/B5 是否把项目增量利润误当成集团净利润或重复加总；B6 绑定约束及 90%/100%/110% 梯度是否与回报和目标入场价一致。
- 来源时间是否符合截止日；未知事实是否保留 UNKNOWN；报告和 JSON 的判断、价值情景与风险是否一致。
- governance.formal_decision_created、canonical_run_receipt_created、execution_authorized、auto_execution 必须为 false；这仍然不是正式投资决策或交易授权。

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
