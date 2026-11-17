# IIOS v0.3 macOS 完整操作指引（ChatGPT 回答接收版）

- 日期：2026-11-17
- 适用代码：B76 研究引擎 + B83 guided task / resume / one-shot clipboard
- 本说明所在修复分支：`fix/b83-chatgpt-response-handoff-20261117`
- 基础集成候选：`release/v03-integration-20261112`（PR #589）
- 重要状态：这是待审阅的候选版本，不等于 canonical `main`；不得把本指引理解为 main 已更新或 IIOS 已正式发布。

---

## 先记住这一条：ChatGPT 回答不填写在终端

新版把两种输入彻底分开：

| 内容 | 应该在哪里操作 | 操作方式 |
|---|---|---|
| 公司、代码、截止时点、持仓、价格 | IIOS Terminal | 按终端提示逐项键入并回车 |
| Round A / Round B 研究问题 | ChatGPT 对话输入框 | IIOS 自动复制提示词；切到 ChatGPT，按 Command+V 粘贴并发送 |
| Round A / Round B 的研究回答 | 不需要手工找输入文件 | 在 ChatGPT 复制完整回答，切回 IIOS Terminal，按一次回车；IIOS 读取剪贴板并自动保存、校验 |
| 组合约束、仓位和估值模型确认 | IIOS Terminal | ChatGPT 两轮通过后，按终端问题逐项键入 |
| 最终研究报告 | IIOS 自动打开 | 文件包校验通过后再打开；不需要把报告粘贴回 ChatGPT |

**核心动作只有四步：终端显示提示 → ChatGPT 粘贴并发送 → 复制 ChatGPT 完整回答 → 回 IIOS 终端按回车。**

不要把 ChatGPT 的 JSON 回答直接粘贴进终端；不要自行打开或编辑 `round-a-response.json` / `round-b-response.json`。终端打印的响应路径只是系统内部接收目标和排障信息，不是要求你手动填写的地方。

## 1. 启动当前候选版本

### 1.1 先确认使用的是候选分支

本说明针对上面列明的修复分支。不要把它与旧版 `main`、PR #588 的单独 B83 分支或旧版验收启动器混用。

在 Mac Terminal 执行以下命令。它会更新到本修复分支并启动 IIOS：

```bash
cd /Users/ccc/projects/convergence-research && git fetch origin fix/b83-chatgpt-response-handoff-20261117 && (git switch fix/b83-chatgpt-response-handoff-20261117 || git switch -c fix/b83-chatgpt-response-handoff-20261117 --track origin/fix/b83-chatgpt-response-handoff-20261117) && git pull --ff-only origin fix/b83-chatgpt-response-handoff-20261117 && bash ./IIOS.command
```

如果本机项目目录不是上述路径，只替换 `cd` 后面的目录。命令不会执行 `sudo`、`git reset`、`git clean`、`stash`，也不会覆盖未提交文件。如果 Git 因工作区存在修改而拒绝切换分支，先停止并检查修改；不要强制覆盖。

也可以在 Finder 中打开完整项目目录，双击 `IIOS.command`。如果 Finder 没有执行权限，使用上面的 `bash ./IIOS.command` 方式；不要关闭 Gatekeeper 或降低 macOS 安全设置。

### 1.2 启动器会做什么

`IIOS.command` 是本地启动器：

1. 检查项目入口和 Python 版本（要求 Python 3.10+）。
2. 优先使用项目自己的 `.venv/bin/python`；如果存在但不可执行，会停止，不会偷偷换用其他 Python。
3. 隔离用户级 Python 包，不自动联网安装依赖，不修改系统 Python。
4. 启动 quick-start：有唯一未完成任务时自动续接；没有未完成任务时才进入新研究；有多个未完成任务时显示编号供你选择。
5. 检查发现任务状态损坏或 BLOCKED 时会停止，不会猜测或另起一个任务掩盖问题。

---

## 2. 新建研究：此阶段所有回答都输入在 IIOS Terminal

没有未完成任务时，终端显示“简化入口”，依次询问：

| 终端提示 | 你应该输入什么 | 例子 / 规则 |
|---|---|---|
| 公司名称 | 公司全称 | 纽威股份 |
| 股票代码 | 证券代码 | `603699.SH`、`SH603699`、`002810.SZ`、`00700.HK` |
| 分析截止时点 | 研究所允许使用信息的截止时间 | 直接回车采用最近一个已完成工作日 15:30（中国时区）；也可输入 `YYYY-MM-DD` 或带时区的 ISO 时间 |
| 当前持仓百分比 | 该股票当前占组合的比例 | 空仓输入 `0`；输入 `10` 表示 10%，不是 0.10 |
| 你核实的股价 | 当前案例的人工核实价格 | `37.59`；或 `37.59@2026-10-16`；非收盘时点用 `37.59@2026-10-16T14:30:00+08:00` |

市场类型由代码格式推断：A 股代码应能明确识别为沪、深、北市场，港股代码应明确为港股。模糊或格式错误时，系统会要求重新输入，不会猜测。

### 价格和截止时点要特别注意

- 价格必须由你自己核实并输入。当前版本不会自动抓取实时行情；报告会明确标记为操作者输入、未独立核验。
- 价格观察时间不能晚于分析截止时间。
- 日期格式的价格按该交易日收盘价时点处理；盘中价格必须提供带时区的具体时间。
- 系统不以自动日历验证节假日，交易日和价格来源仍要由操作者检查。
- 输入完成后，终端会汇总公司、代码、市场、截止时点、价格观察日、价格时间和持仓。只有核对正确后才输入 `1` 继续；输入 `0` 退出。

**本节所有内容都直接输入 IIOS Terminal，不要输入 ChatGPT。**

---

## 3. Round A：价格盲公司研究

Round A 只做公司侧研究，不向模型提供结构化当前价格、当前持仓或估值选择。它先于 Round B，且必须先通过校验并冻结。

### 3.1 终端出现 Round A 提示后

新版会自动完成以下动作：

1. 将 Round A 提示保存到当前任务的私有工作区。
2. 尝试通过 macOS `pbcopy` 把提示词复制到剪贴板。
3. 尝试打开 ChatGPT 网页。
4. 在终端显示明确的交接步骤和本轮响应文件路径。

如果提示词没有自动复制成功，终端会明确提示，并把提示词显示出来供你手工复制；如果 ChatGPT 没有自动打开，请自行打开 ChatGPT 网页。

### 3.2 你只需照着做

1. 切换到 ChatGPT 页面，点击对话输入框。
2. 按 **Command+V**，粘贴 IIOS 刚复制的 Round A 提示词，然后发送。
3. 等待 ChatGPT 完整回答生成。
4. 点击该回答下方的“复制”按钮，复制**完整回答**，不要只复制一部分 JSON，也不要复制你刚才发送的问题。
5. 切回刚才运行 IIOS 的 **同一个 Terminal 窗口**。
6. 在终端等待处按**一次回车**。

此时 IIOS 会在这次明确的回车后调用一次 `pbpaste`，把剪贴板内容写入 Round A 响应文件，并执行 JSON 与字段白名单校验。你不用打开文件，也不用将回答粘贴到终端。

### 3.3 校验通过后

Round A 通过后，系统会把响应和公司侧研究结果作为不可变阶段记录保存，并冻结 Round A。接着自动生成 Round B 提示。

Round A 的结果不会因为 Round B 的后续估值或价格信息而被静默改写。若 Round A 未通过校验，先按第 5 节修正，不要跳过 Round A 直接做 Round B。

---

## 4. Round B：价格感知估值、MIE 与预期差

只有 Round A 已通过校验并冻结，系统才会显示 Round B。

操作方式与 Round A 完全相同：

1. IIOS 自动复制 Round B 提示并尝试打开 ChatGPT。
2. 切到 ChatGPT，按 Command+V 粘贴 Round B 提示并发送。
3. 等待完整回答，点击 ChatGPT 回答下方的“复制”按钮。
4. 切回原 IIOS Terminal 窗口，按一次回车。
5. IIOS 一次性读取剪贴板，将回答保存到 Round B 响应文件并校验。

Round B 才会使用当前价格输入和已冻结的 Round A 结果，处理估值、MIE 与可识别的预期差。它不能反向改写 Round A 的 Trust、Reality、Quality、Thesis、经营驱动预测等公司侧结论。

**不要把 Round A 的回答再次粘贴给 Round B，也不要把 Round B 的回答写入 Round A 响应位置。** 两轮是两个独立请求、两个独立接收阶段。

---

## 5. ChatGPT 回答格式不合格时怎么修正

出现 JSON 无法解析、字段不在本轮允许范围或必需研究字段缺失时，IIOS 不会继续估值，而会：

- 显示本轮未通过的校验原因；
- 尝试把本轮修正提示复制到剪贴板；
- 保留此前原始回答的不可变 attempt 记录；
- 继续等待修正后的回答。

修正步骤：

1. 留在**同一个 ChatGPT 对话**，不要新建研究任务。
2. 切回 ChatGPT，按 Command+V 粘贴 IIOS 刚复制的修正提示并发送。
3. 等待新的完整回答，点击新回答下方的“复制”按钮。
4. 切回原 IIOS Terminal 窗口，按一次回车。
5. IIOS 会把新回答写入本轮临时响应位置，再次进行原有校验。

本版本特别修正了旧回答已存在时的接收问题：修正阶段只有在临时响应文件仍与系统刚才观察到的旧版本完全一致时，才允许用新剪贴板回答替换它；旧回答已经进入不可变历史记录，不会被删除。若文件在此期间被其他程序修改，系统会拒绝覆盖并停止该次替换。

### 剪贴板接收失败时

若终端提示剪贴板为空或无法读取：

- 先确认你复制的是 ChatGPT **完整回答**，不是 Round 提示词；
- 回到 IIOS Terminal 再按一次回车，程序才会重新尝试一次性读取剪贴板；
- 若剪贴板仍不可用，macOS 可能弹出文件选择窗口。你可以把 ChatGPT 的完整 JSON 回答另存为一个本地 `.json` 文件，然后在文件选择窗口中选中它。IIOS 会把所选文件内容复制到本轮私有响应位置；你原来的文件不会被删除；
- 如果取消了文件选择窗口，程序会继续等待。再次复制正确回答、按回车即可重试。

如果你选择文件方式，文件应包含一个完整 JSON 对象。不要把两次回答拼在一起，不要在 JSON 前后添加解释性文字，也不要手工修改字段来绕过校验。

### 为什么正常情况下不需要知道响应文件路径

终端会打印路径，例如：

`~/.iios-private/local-pilot/inputs/tasks/<task-id>/working/round-a-response.json`

它是 IIOS 内部的暂存接收位置。接收成功后，程序会把原始字节保存为带哈希的不可变 attempt，再进入校验。日常操作不需要手动打开这个目录。

---

## 6. Round A/B 完成后：组合约束和估值模型要在 IIOS Terminal 回答

这是另一个容易混淆的地方：

**ChatGPT 两轮结束后，后续问题重新回到 IIOS Terminal。不是继续在 ChatGPT 回答。**

### 6.1 个人组合与仓位约束

终端询问是否填写组合风险预算与仓位限制：

- 输入 `1`：填写组合信息（默认项）。
- 输入 `0`：明确跳过，组合约束保持 UNKNOWN，不生成条件仓位，也不允许系统据此推断可以新增资金。

如果填写，按终端逐项提示输入：

1. 组合约束状态：`1=PASS`（已核实）、`2=BLOCKED`、`3=UNKNOWN)。
2. 只有选择 PASS 才继续确认是否允许增加该标的风险敞口。
3. 论点失效压力情景下，最多允许损失组合净资产的百分比。
4. 本标的入场价格区间下沿和上沿。
5. 初始建仓、目标仓位、最大单股仓位，三者必须满足：初始 ≤ 目标 ≤ 最大。

百分比按“百分数”输入，例如 `1` 表示组合净资产的 1%，`4` 表示 4%。价格区间是本标的专属输入，不会作为其他公司的默认价格区间。

如果状态是 BLOCKED 或 UNKNOWN，程序会保留该状态，不会继续采集条件仓位，也不会允许增加风险敞口。不要为了取得 PASS 而猜测数据。

### 6.2 本次主估值模型确认

终端会显示：

| 输入 | 选择 |
|---|---|
| `1` | EPS_MULTIPLE（EPS / 市盈率倍数） |
| `2` | FCF_DCF（自由现金流折现） |
| `3` | DDM（股利折现） |
| `4` | SOTP（分部估值） |
| `5` | RNPV（风险调整净现值） |
| `6` | OTHER（其他） |
| `0` | UNKNOWN（暂不确认） |

估值模型必须按当前公司的业务结构与利润来源重新确认。若选择 EPS_MULTIPLE，系统还会追问原有估值基线是否已经包含该项目/扩产价值：

- `1`：已包含，不得重复叠加；
- `2`：明确不包含，才可能在满足条件时传导增量；
- `0`：无法确认，保持 UNKNOWN，不叠加项目增量。

### 6.3 是否保存本机默认设置

系统可能询问是否把跨公司组合约束和上次估值模型选择保存为本机默认提示：

- `1`：明确同意保存；
- `0`：只用于本次，不保存或不更新。

保存的只是跨公司组合偏好和估值模型的建议默认项；不会保存本标的入场价格区间或项目是否已包含在估值基线。档案是本机明文文件，不是加密保险库，不会提交到 GitHub；不要把它放入不可信的同步或共享目录。

---

## 7. 报告生成、校验与输出目录

操作者输入完成后，IIOS 自动组装输入并执行本地研究计算。程序会验证首次运行文件包的哈希、字节数和权限。

成功时 quick-start 才会打开最终报告。报告与运行包位于：

`~/.iios-private/local-pilot/runs/<pilot_id>/`

主要文件：

- `input.json`：本次实际输入快照；
- `analysis.json`：结构化分析与计算结果；
- `report.md`：中文研究报告；
- `pilot_receipt.json`：运行回执及文件清单。

报告中重点核对：标的身份、价格及观察时点、分析截止时点、关键事实与 UNKNOWN、经营预测、主估值模型、MIE/预期差是否可识别、Bear/Base/Bull、年化回报门槛、目标入场价格、风险约束和最终状态。

如果哈希校验失败、程序显示 `[BLOCKED]` 或退出码非 0，不得把本次运行标记为成功。不要编辑 `input.json`、`analysis.json`、`report.md` 或 `pilot_receipt.json` 来消除错误；保留原文件和错误信息。

### 输出边界

- 这是 `PILOT_NON_CANONICAL` 研究输出，不是正式准入的 Forecast / Valuation / Decision。
- Replay MATCH 只能证明同一冻结输入可重复计算，不证明事实真实或估值结论正确。
- 不会自动下单，不代表真实成交，不赋予交易权限。
- 价格是操作者输入，除非另有独立证据核验，不得说成交易所或行情源已验证。
- 未知事实、数据缺口、无法识别的 MIE 和情景约束必须保留 UNKNOWN / NOT_IDENTIFIABLE，不为得到 PASS 而填造。

---

## 8. 中断后如何续接，不要重新开始

B83 将每个任务保存在本机私有目录。一般情况下，不需要记 Task ID，也不用手动选择阶段。

1. 如果要中断，先在运行 IIOS 的 Terminal 按 **Control+C**。
2. 再次运行同一个 `IIOS.command`。
3. 只有一个未完成任务时，系统自动识别并继续；多个未完成任务时，按终端显示的公司、代码和阶段选择编号。
4. 系统会从已保存的阶段继续：
   - Round A 等待回答：继续 Round A，不重新询问公司和价格；
   - Round A 已冻结：直接进入或继续 Round B；
   - Round B 已通过：继续尚未完成的组合约束或估值模型确认；
   - 某一项操作者输入已经保存：续接时复用已保存项，不要求重新填写；
   - 已完成任务：不会被自动当作未完成任务重新运行。

如果任务损坏、哈希不一致或状态不合法，IIOS 会停止并给出错误码。不要删除任务目录、修改 journal/manifest 或自行把状态改成完成。

---

## 9. 私有文件位置和数据安全边界

| 内容 | 本机路径 |
|---|---|
| 任务和输入根目录 | `~/.iios-private/local-pilot/inputs/tasks/` |
| Round A/B 暂存响应 | `~/.iios-private/local-pilot/inputs/tasks/<task-id>/working/round-a-response.json`、`round-b-response.json` |
| Round A 原始回答历史 | `~/.iios-private/local-pilot/inputs/tasks/<task-id>/artifacts/round_a_response_captured/` |
| Round B 原始回答历史 | `~/.iios-private/local-pilot/inputs/tasks/<task-id>/artifacts/round_b_response_captured/` |
| 本机默认档案（可选） | `~/.iios-private/local-pilot/profile/operator-defaults.json` |
| 首轮研究运行包 | `~/.iios-private/local-pilot/runs/<pilot_id>/` |

工作区使用本机私有目录和严格文件权限（目录通常 0700、文件通常 0600）。剪贴板不被后台轮询，不安装守护进程，不自动读取浏览器会话，也不使用 Accessibility 自动化。程序只在操作者按下回车后尝试读取一次当前剪贴板。

权限保护不等于加密：本机档案和研究文件不是加密存储。应保护 Mac 登录账户与磁盘，不要把包含持仓、价格、组合约束和完整研究输入的私有运行包上传到公共仓库或发送给不可信对象。

---

## 10. 常见问题的处理规则

| 现象 | 正确动作 | 不要做 |
|---|---|---|
| 不知道 ChatGPT 问题粘贴到哪里 | 切到 ChatGPT 对话输入框，Command+V，再发送 | 不要粘贴到 Terminal |
| 不知道 ChatGPT 回答填到哪里 | 复制完整回答，切回 IIOS Terminal，按一次回车 | 不要手动找响应 JSON 文件 |
| 按回车后提示剪贴板为空 | 重新复制 ChatGPT 完整回答，再按回车 | 不要把回答直接粘贴终端 |
| Round A/B JSON 校验不通过 | 用同一对话发送系统修正提示，复制新回答，回终端按回车 | 不要创建新研究或编辑原始 JSON |
| 修正时有旧回答 | 新版本会在精确检查旧文件未变化后安全替换暂存文件；旧 attempt 保留 | 不要自行删除历史 attempt |
| 出现多个未完成研究 | 依终端列出的公司、代码和阶段选择正确编号 | 不要手动删任务目录 |
| 程序中断 | 重启同一 `IIOS.command` 自动续接 | 不要重新输入同一公司并重复建任务 |
| Python / 环境检查失败 | 保留完整错误、停止操作并反馈 | 不要 sudo、不要自动换 Python、不要运行来源不明的安装脚本 |
| 出现 `[BLOCKED]`、哈希错误或退出码非 0 | 保留原文件、错误码和日志路径 | 不要改 JSON、receipt 或哈希清单制造 PASS |

---

## 11. 真实案例验收时需要检查什么

功能验收不只是确认脚本能运行。至少完成一轮真实 EPS_MULTIPLE 案例，并检查：

1. Finder / Terminal 能正常启动当前候选代码。
2. Round A 提示正确进入 ChatGPT；ChatGPT 回答经复制后能由回车一次性接收。
3. Round A 校验后真正冻结，Round B 消费同一冻结结果；Round B 不改写 Round A。
4. 人工中断并重启后，原 Task ID、已完成阶段和已保存的操作者输入都能续接，不重复创建任务。
5. 首轮 `input.json`、`analysis.json`、`report.md`、`pilot_receipt.json` 的哈希/字节数校验通过。
6. 若执行 Replay，必须是真正从冻结的首次输入重新计算，并满足 `replay_comparison.status=MATCH`、`hash_verification=PASS`、`mismatched_fields=[]`；不能用复制报告冒充 Replay。
7. 输出仍为 `PILOT_NON_CANONICAL`，不创建正式决策，不产生自动交易授权。

反馈时只需提供：候选分支/提交、是否完成真实 Round A/B、是否成功中断续接、文件包校验与 Replay 状态、终端错误码。不要粘贴完整持仓、个人价格、组合资产金额或原始私有研究文件。

---

## 12. 一页操作速记

```text
启动 IIOS.command
    |
    v
终端填写：公司 / 代码 / 截止时点 / 持仓 / 人工核实价格
    |
    v
Round A 提示自动复制 -> ChatGPT Command+V 发送
    |
    v
复制 ChatGPT 完整回答 -> 回 IIOS Terminal 按一次 Enter
    |
    v
Round A 校验通过并冻结
    |
    v
Round B 提示自动复制 -> ChatGPT Command+V 发送
    |
    v
复制 ChatGPT 完整回答 -> 回 IIOS Terminal 按一次 Enter
    |
    v
Round B 校验通过
    |
    v
终端填写：组合/仓位约束 -> 主估值模型 -> 项目是否已计入
    |
    v
IIOS 本地计算 -> 首轮运行包哈希校验 -> 打开报告
    |
    v
人工复核；需要时再执行独立 Replay
```

**最关键的记忆点：问题粘贴到 ChatGPT；回答复制后回到 IIOS Terminal 按回车；后面的组合和估值确认才是在 Terminal 逐项填写。**
