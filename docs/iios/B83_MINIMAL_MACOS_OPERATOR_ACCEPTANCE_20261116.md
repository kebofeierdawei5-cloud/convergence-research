# B83 最小 macOS 操作者验收（2026-11-16）

本说明对应 PR #589 的候选分支 `release/v03-integration-20261112`。

> **先阅读新版完整操作指引：** [IIOS v0.3 macOS 完整操作指引（ChatGPT 回答接收版）](IIOS_V03_MACOS_OPERATOR_GUIDE_20261117.md)。尤其注意：ChatGPT 的问题粘贴到 ChatGPT 输入框；ChatGPT 的完整回答复制后，切回 IIOS Terminal 按一次回车。终端打印的 `round-a-response.json` / `round-b-response.json` 路径是内部接收位置，正常不需要手工打开或编辑。本文仅用于最小人工验收，不替代完整操作指引。
不要用旧的 `验收IIOS全流程与Replay.command` 更新候选分支：该脚本的旧更新器目标是 `origin/main`，会离开本候选版本。

## 1. 更新并启动（只需粘贴一次）

在 Mac Terminal 粘贴这一行：

```bash
cd /Users/ccc/projects/convergence-research && git fetch origin release/v03-integration-20261112 && (git switch release/v03-integration-20261112 || git switch -c release/v03-integration-20261112 --track origin/release/v03-integration-20261112) && git pull --ff-only origin release/v03-integration-20261112 && chmod +x IIOS.command && open IIOS.command
```

- 不使用 sudo，不安装依赖，不改系统 Python，不执行 reset/clean。
- 若工作区有冲突或未提交修改，Git 会停止切换/更新；不要强制覆盖，保留错误输出。
- Finder/Terminal 打开 `IIOS.command` 后，唯一未完成任务会自动续接；没有未完成任务才新建。

## 2. 只完成一个真实 EPS_MULTIPLE 案例

1. 输入真实公司、代码、分析截止时点、持仓和本次核实的价格；检查价格观察日与可获得时点。价格来源仍是操作者输入、未独立核验。
2. Round A 提示自动复制到剪贴板并打开 ChatGPT。粘贴发送，等完整回答，复制完整 JSON，回到 IIOS Terminal 按一次回车。程序只在这次明确按键后调用一次 `pbpaste`，不轮询剪贴板；响应通过原有校验后才冻结。
3. Round B 同样操作。Round B 只有在 Round A 验证并冻结后才会出现。
4. 如在 Round B 等待响应时要验证断点恢复，按 Control-C 退出，再双击 `IIOS.command`。它应自动找到唯一未完成任务，重新显示同一阶段的已保存提示；不应重新创建任务或丢失已冻结的 Round A。
5. 完成 Round B 后，按提示确认组合约束与估值模型。若使用 EPS_MULTIPLE，确认基准 EPS / 项目是否已包含、必要回报门槛、入场区间等；未知项保持 UNKNOWN，不要为了验收填造 PASS。
6. 等待本地分析完成。核对报告中的公司、代码、截止时点、价格、模型、关键 UNKNOWN、收益门槛、入场价格和风险边界。输出应仍标记 `PILOT_NON_CANONICAL`。

## 3. 对刚生成的运行包执行 Replay

在同一个项目目录执行：

```bash
cd /Users/ccc/projects/convergence-research && if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi && PYTHONPATH=. "$PYTHON" -m iios_mvp.local_run_replay_acceptance_v01
```

选择 **2 — 对已有首次运行执行校验 + Replay**，再选择刚才的运行 ID。要求：
- 首轮 input / analysis / report / receipt 哈希与字节数校验通过；
- Replay 由冻结的首轮 input 真正重算，而非复制报告；
- `replay_comparison.status=MATCH`、`hash_verification=PASS`、`mismatched_fields=[]`；
- Replay 自身文件包哈希、权限和 no-trade 边界通过。

Replay MATCH 只证明相同输入下决策材料可重复，不证明研究事实正确或投资结论必然正确。

## 4. 验收回报只需提供三项

把以下三项结果发回本对话即可；不要上传含个人价格、持仓或原始研究内容的私有文件：

1. `IIOS.command` 是否正常启动并完成一轮真实 EPS_MULTIPLE 研究；
2. Control-C 后重新启动是否续接原 Task ID / Round B，而不是新建任务；
3. Replay 最终状态与输出的 `MATCH / PASS` 或具体错误码。

**通过边界：** GitHub 35/35 工作流、Ubuntu/macOS 15 各 538 tests 已通过；它们不代替操作者 Mac 的 Finder、剪贴板、真实中断/恢复和真实输入 Replay。真实 SOTP 案例仍以分部归属利润、倍数、母公司调整、净现金/债务和稀释股数资料完整为前提。正式 Evidence/PIT 与 Forecast Admission 当前仍不可用；不因此降低 UNKNOWN / fail-closed 规则。
