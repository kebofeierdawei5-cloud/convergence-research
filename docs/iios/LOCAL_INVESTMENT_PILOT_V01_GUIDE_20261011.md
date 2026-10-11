# IIOS 本地投资试运行 v0.1

目标是尽快用一个真实 A/H 标的跑通研究输入、价格/截止时点、核心模块评估、情景回报、中文报告与本地运行记录。此路径是 **PILOT_NON_CANONICAL**，不是正式 IIOS Decision。

## 1. 生成私有输入模板

在仓库根目录运行（将示例值替换成真实信息）：

```bash
python -m iios_mvp.local_investment_pilot_v01 \
  --create-template \
  --company "公司名称" \
  --symbol "300750" \
  --market CN-A \
  --as-of "2026-10-10" \
  --position 0 \
  --price "人工核实的当前价" \
  --price-date "2026-10-09" \
  --price-known-at "2026-10-09T15:00:00+08:00" \
  --price-source-claim "人工查看的价格来源"
```

默认输入放在 `~/.iios-private/local-pilot/inputs/`，不进入仓库。日期型 cutoff 按上海时间当日零点计算，所以价格观察/可知时点必须早于该零点；通常收盘价的 cutoff 应设为下一天。命令输出 JSON 模板与研究填写提示。

## 2. 填写研究输入

在模板的 `evidence_register` 中补公告/财报来源和事实摘要；在 `assessment` 中填写 Trust、Reality、Quality、Thesis、价值驱动排序、MIE、预期差及风险；在 `forecast_valuation` 中填写 Bear/Base/Bull 概率、终值、现金分配和入场参考价值。

将 JSON 和已有的原始公告/财报材料摘要交给 ChatGPT，按生成的提示要求返回完整 JSON，然后保存到仓库之外。资料不够就填 `UNKNOWN`；MIE 不可识别时填 `NOT_IDENTIFIABLE`。不要为填满字段编造数字。主观概率须声明未校准。

## 3. 运行

```bash
python -m iios_mvp.local_investment_pilot_v01 --input "/绝对路径/pilot-input.json"
```

默认输出到 `~/.iios-private/local-pilot/runs/`：
- `report.md`：中文报告，包含试运行建议、回报/入场价、MIE/预期差、主要驱动、失效条件、风险和待补证据。
- `analysis.json`：机器可读结果与试运行状态。
- `pilot_receipt.json`：本地运行记录，明确不具备正式 Decision / canonical Run Receipt 身份。
- `input.json`：本次运行使用的输入副本。

## 4. 重跑上一次输入

```bash
python -m iios_mvp.local_investment_pilot_v01 --replay-run "/绝对路径/先前试运行目录"
```

此命令会重新读取先前的 `input.json` 并生成一份新运行结果；它是便捷复算，不是哈希完整性审计，也不会验证外部来源真实性。

## 边界

工具复用 IIOS 的标的/期限校验和现有确定性回报/入场价计算。人工价格保持 `OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED`。它不创建正式 Evidence/PIT、Forecast/Valuation Admission、Decision Admission、Machine Publication 或 canonical `IIOS_RUN_RECEIPT`；未知信息必须可见，人工最终审批必需，不会自动下单。

**先用真实标的把完整流程跑起来，再按实际暴露的问题迭代。**
