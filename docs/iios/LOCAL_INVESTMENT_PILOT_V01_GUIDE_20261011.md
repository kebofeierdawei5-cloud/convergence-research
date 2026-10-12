# IIOS 本地投资分析：最简启动指南

## 只记住一个入口

更新仓库到最新 main 后，在仓库根目录**双击 `启动IIOS投资分析.command`**。

首次运行若 macOS 阻止打开，可在 Finder 中右键该文件并选择“打开”。需要 Python 3.10 或更新版本；无需安装 Python 包、配置 API key 或安装本地模型。

## 启动后怎么做

1. 按提示填写公司名称、股票代码、市场、分析截止日、当前持仓、人工核实价格、价格观察日期和来源简述。大部分字段有默认值。价格按人工输入处理，不会被标记为官方行情已验证。
2. 程序会打开 ChatGPT、在剪贴板中放好研究提示，并在 Finder 中定位输入模板。将提示粘贴到 ChatGPT，上传模板 JSON 和你希望引用的公司公告/财报材料。
3. 让 ChatGPT 基于材料补充 Trust、Reality、Quality、Thesis、价值驱动排序、Bear/Base/Bull 情景、MIE/预期差和风险。资料不够就填写 `UNKNOWN`；MIE 不可识别时填写 `NOT_IDENTIFIABLE`，不要编造。
4. 复制 ChatGPT 返回的完整 JSON，切回原来的终端窗口按回车。程序会自动读取剪贴板、运行试分析并打开中文报告。不需要另存 JSON 或手动输入文件路径。

如果剪贴板没有完整 JSON，程序会给出具体错误。重新复制完整回答后再次运行向导即可。

## 输出在哪里

输入和结果仅保存在本机私有目录：

- 输入模板与 AI 完成的输入：`~/.iios-private/local-pilot/inputs/`
- 分析结果：`~/.iios-private/local-pilot/runs/`

每次分析会生成中文 `report.md`、机器可读 `analysis.json`、本地运行记录 `pilot_receipt.json` 和输入副本。报告运行后自动打开。

## 重要边界

该路径复用 IIOS 既有标的、期限与确定性回报/入场价计算，目标是尽快完成真实个人使用测试。但它仍是 **PILOT_NON_CANONICAL**：

- 人工价格、来源摘要、AI 研究评估和情景假设并未自动完成正式 Evidence/PIT、Forecast 或 Valuation Admission。
- 试运行建议不是正式 IIOS Decision，也不等于 canonical `IIOS_RUN_RECEIPT`。
- MIE、证据和关键模块存在未知项时，报告应显示 `REVIEW_REQUIRED`，不应该用内部估值替代不可识别的市场隐含预期。
- 人工最终审批仍必需；不会自动下单或执行交易。

首轮只需跑出一份真实标的报告。后续优先修复实际运行暴露的问题，不让额外的防篡改工作阻塞使用。
