# IIOS 本地投资研究试运行 v0.1

本工具用于把个人投资研究尽快跑完一遍：标的输入 → 来源/截止时点记录 → Trust / Reality / Quality / Thesis / Value Drivers → Forecast / Valuation 情景 → 15% 年化门槛与目标入场价 → MIE / 预期差 → 风险与持仓约束 → 中文报告 → 本地回放。

它是明确隔离的 PILOT_NON_CANONICAL 路径，不是正式 canonical Decision。这里的信任、质量、MIE 和预期差状态，是 AI/操作者提交的研究评估，不会被伪装成正式证据准入结果。人工价格只保持 OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED。

## 1. 创建一份本地私有输入模板

在仓库根目录运行：

\`\`\`bash
python -m iios_mvp.local_investment_pilot_v01 \\
  --create-template \\
  --company "填写公司名" \\
  --symbol "填写 A/H 股票代码" \\
  --market CN-A \\
  --as-of "YYYY-MM-DD" \\
  --position 0 \\
  --price "填写当前价" \\
  --price-date "YYYY-MM-DD" \\
  --price-known-at "YYYY-MM-DDTHH:MM:SS+08:00" \\
  --price-source-claim "填写人工核对的价格来源说明"
\`\`\`

默认生成位置在用户目录下的 \`~/.iios-private/local-pilot/inputs/\`，不会写入 Git 仓库。行情观察日期/已知时点必须严格早于日期型 cutoff 的上海时间当日零点；因此通常应把收盘价的 cutoff 设为下一日。若未通过该条件，程序会显示时间问题并阻止回报计算。

## 2. 补齐研究输入

打开命令输出的 \`pilot-input-*.json\` 与 \`pilot-prompt-*.md\`。把相关正式公告/财报中的事实摘要和来源信息填入 \`evidence_register\`，再将完整 JSON 与源材料摘要提供给 ChatGPT，要求按提示返回填写后的 JSON。

最低需要覆盖：

- Trust：治理、诚信、重大诉讼和股东风险。
- Reality：实际经营、财务、现金流、资本开支、资本结构。
- Quality：竞争优势、盈利质量、资本回报、再投资空间。
- Thesis：核心论点、价值驱动排序、失效条件、重新评估触发器。
- Forecast / Valuation：Bear/Base/Bull 三情景、概率、期末每股价值、分红/现金分配、模型选择理由、入场安全边际参考价值。
- MIE / 预期差：市场隐含预期的可识别性/稳定性/历史支持及相对独立预测的差异。
- Risk：最大损失边界、关键风险与组合约束。

不要为了填满字段编造数据。缺失信息填 \`UNKNOWN\`；无法从公开历史支持中识别 MIE 时填 \`NOT_IDENTIFIABLE\`。情景概率未校准时保留 \`probabilities_calibrated=false\`，并说明假设。把完整输入保存到仓库以外的本地私有目录。

## 3. 实际运行

\`\`\`bash
python -m iios_mvp.local_investment_pilot_v01 --input "/绝对路径/pilot-input-xxxx.json"
\`\`\`

程序会在 \`~/.iios-private/local-pilot/runs/\` 中生成私有 bundle，包含：

- \`report.md\`：中文试运行报告。
- \`analysis.json\`：机器可读的模块状态、回报计算、临时建议和治理边界。
- \`pilot_receipt.json\`：绑定输入/输出哈希的本地试运行收据；不是正式 Run Receipt。
- \`input.json\`：用于本地复算的私有输入副本。

报告中的动作是 provisional action。若回报或 Bear 风险门槛不通过且当前空仓，价格筛选输出 NO-BUY；若 MIE、预期差或关键模块不足，输出 REVIEW_REQUIRED。已有持仓不会因价格筛选失败而被自动卖出或降低仓位。

## 4. 回放复核

\`\`\`bash
python -m iios_mvp.local_investment_pilot_v01 --replay-run "/绝对路径/pilot-run-xxxx"
\`\`\`

回放会从保存的输入重新计算 JSON 和报告，报告/分析有差异会失败。这个机制只检查本地文件与计算是否可复现，不证明外部来源真实性或版权/使用权。

## 5. 试运行边界

当前版本会复用 IIOS 的研究 intake、期限语义与 deterministic return/entry-price solver；公司事实摘要、估值情景及 MIE / 预期差判断由 AI/操作者提供，再按明确状态进入试运行报告。该路径不调用 formal semantic admission，也不绕过 canonical 的正式门槛。

- 不创建正式 Evidence/PIT Admission、Forecast/Valuation Admission、Decision Admission 或 Machine Publication。
- 不创建 canonical \`IIOS_RUN_RECEIPT\`，本地 \`pilot_receipt.json\` 不得冒充它。
- 不启用自动下单；AI 建议与人工最终审批分离。
- 输入、报告、价格和来源细节只放本机私有目录，不放入 GitHub / CI artifact。

**第一轮目标是实际跑出报告，发现真实的研究质量、计算或易用性问题，再据此迭代；不是先把试运行变成正式化平台。**
