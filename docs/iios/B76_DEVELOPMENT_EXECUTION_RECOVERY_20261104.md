# B76 开发执行卡点定位与恢复记录

**日期：** 2026-11-04  
**分支：** `feat/b76-core-integrated-20261101`  
**首次问题 HEAD：** `90f444dfb98d8264b8e1f407b0fe79d280ccde63`  
**首轮修复：** `cbb3c991211499e0a2d9769d8b7ad9d7ef7766f1`  
**第二轮加固及已验证 HEAD：** `6ee0d2bae159f42481b4836f893be5a842993f1d`  
**性质：** 非 canonical 开发分支；不授权将 B73 历史链整体合并进 main。

## 1. 可复现的阻塞

### 1.1 macOS 报告打开动作阻塞向导退出

精确 HEAD 的 macOS Local Investment Pilot 日志显示：
- `python -m pytest` 已运行 445 项，444 项通过；
- 唯一失败位于 `tests/test_local_investment_pilot_v01.py::test_guided_wizard_collects_manual_price_source_claim_and_completes`；
- 向导已生成 `report.md`、`analysis.json` 和运行结果，状态为 `PILOT_CREATED`；
- 随后的 `subprocess.run(["open", report_path], timeout=5)` 抛出 `subprocess.TimeoutExpired`。

根因：把 GUI 应用启动/交接误当成同步核心步骤。报告文件已落盘，GUI 命令不返回不应使分析结果失败。

### 1.2 C0 把非主线 proposal 当作 canonical main

精确 HEAD 的 C0 失败原因是测试要求分支副本 `docs/PROJECT_STATE_INDEX.md` 包含 `State classification: **CANONICAL**`，而该分支按治理要求必须标记 `BRANCH PROPOSAL — NOT CANONICAL`。

根因：C0 工作流没有按 PR base branch 限定 canonical 权威检查。现有 State Hygiene 已有 main-target-only 条件，C0 未同步这一边界。

### 1.3 不属于这两次失败的内容

同一精确 HEAD 的 Ubuntu Local Pilot 作业通过；Investment Core CI、B00-B、B2、MVP Pilot、Post-B04 Red-team、State Hygiene 等关联工作流通过。B76 本身的算术测试不是这两项失败的触发点。真实公司 B76 数值输入包仍不完整，旧案例测试只证明缺字段时正确 BLOCKED/UNKNOWN。

### 1.4 Round A / Round B 桌面交接的同类超时风险

继续扫描后发现 Round A / Round B 还有同步 `open`（ChatGPT、TextEdit）和 `pbcopy` 调用。它们在首轮失败日志中没有触发错误，但仍属于相同的 GUI 进程边界风险。第二轮加固将：
- ChatGPT、TextEdit、报告打开统一改为异步 `Popen`，不等待 LaunchServices 返回；
- CI/headless 环境跳过浏览器、编辑器和剪贴板调用，直接打印已保存的 Round A / Round B 提示；
- `pbcopy` 保留 5 秒硬上限，但超时或异常改为提示回退，不中止分析；原始提示仍保存于本机文件，修复提示会输出在终端；
- 用户主动调用的 AppleScript 文件选择器保留 120 秒显式人工操作超时，不属于无提示 GUI 启动，不在本轮取消。

## 2. 本次修复

- 将报告、ChatGPT 页面和 TextEdit 自动打开统一为 best-effort 异步动作：仅在本地 macOS 非 CI 环境启动；不等待 GUI 结束；对启动异常只提示用户手动打开已生成的报告或响应文件。
- 将 Round A / Round B 正常提示与修复提示的剪贴板操作改为 best-effort；CI/headless 跳过桌面交接，剪贴板超时只显示手动复制回退，不中止向导。
- 向导集成测试显式设置 CI 标记，避免测试启动 GUI 应用；另加回归测试覆盖 CI skip、异步参数和启动异常。
- C0 测试及 validator 只在非 PR 事件或 PR 目标为 `main` 时执行；proposal PR 仍保留 compile 和 diff 检查。
- 不变更 B76 算术、投资语义、15% 年化收益门槛、Required Return、估值、MIE、Decision 或执行权限。

## 3. 修复后验收结果（2026-11-04）

**精确 HEAD：** `6ee0d2bae159f42481b4836f893be5a842993f1d`

- B76 Local Investment Pilot + Replay 相关组合测试：macOS 451 passed（测试命令 7.71 秒）；Ubuntu 451 passed（测试命令 4.17 秒）。
- 本次提交触发 15/15 关联工作流成功，包括 B76 Local Investment Pilot、Investment Core CI、MVP Pilot、C0、State Hygiene、B00-B、B2、Post-B04 Red-team、B2-F、CORE-00、B1、P0、M1.2、B2-D 和 PILOT-02。
- C0 在非 main 目标 PR 中按设计跳过 canonical 内容断言，仍执行 compile 与 diff 检查；这不是对 main canonical 状态本身的重新验收。
- macOS 是 GitHub-hosted headless Runner，不代表用户桌面环境的完整双轮流程已完成。真实 Mac 全流程 + Replay 仍 OPEN / NOT VERIFIED。
- 002001 / 002422 旧案例只证明缺新字段时正确 BLOCKED/UNKNOWN；没有真实公司 B76-ready EPS_MULTIPLE/SOTP 数值包，不能宣称真实案例数值链已闭合。

## 4. 后续验收边界

必须检查：
已在精确 HEAD 完成的验证见第 3 节。下一阶段不得把 CI PASS 冒充真实 Mac 接受，也不得把 legacy fail-closed 测试冒充真实公司 B76 数值案例。

GitHub headless macOS CI 只验证无 GUI 条件下的核心流程；真实用户桌面自动打开行为与用户 Mac 全流程 + Replay 接受仍然分开记录。不得因 CI PASS 而把真实 Mac 验收标为 PASS。

