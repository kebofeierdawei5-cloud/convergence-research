# B76 开发执行卡点定位与恢复记录

**日期：** 2026-11-04  
**分支：** `feat/b76-core-integrated-20261101`  
**修复基线：** `90f444dfb98d8264b8e1f407b0fe79d280ccde63`  
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

## 2. 本次修复

- 将报告自动打开提取为 best-effort 辅助动作：仅在本地 macOS 非 CI 环境启动；使用异步 `subprocess.Popen`，不等待 GUI 结束；对启动异常只提示用户手动打开已生成的报告。
- 向导集成测试显式设置 CI 标记，避免测试启动 GUI 应用；另加回归测试覆盖 CI skip、异步参数和启动异常。
- C0 测试及 validator 只在非 PR 事件或 PR 目标为 `main` 时执行；proposal PR 仍保留 compile 和 diff 检查。
- 不变更 B76 算术、投资语义、15% 年化收益门槛、Required Return、估值、MIE、Decision 或执行权限。

## 3. 修复后验收

必须检查：
1. 新精确 HEAD 的 B76 EPS_MULTIPLE 与 SOTP 算术回归；
2. 002001/002422 legacy real-case 缺字段时维持 BLOCKED/UNKNOWN；
3. Local Pilot + Replay 原有合同测试；
4. macOS workflow 不再等待 GUI 命令；
5. C0 在 PR base 非 `main` 时正确 skip canonical check，在 main-target PR / main push 时仍实际执行；
6. 记录精确 SHA、每个关键工作流的结论和失败日志，不用旧 HEAD 的 PASS 覆盖新 HEAD 的结果。

GitHub headless macOS CI 只验证无 GUI 条件下的核心流程；真实用户桌面自动打开行为与用户 Mac 全流程 + Replay 接受仍然分开记录。不得因 CI PASS 而把真实 Mac 验收标为 PASS。

