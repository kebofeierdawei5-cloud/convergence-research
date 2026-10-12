# IIOS 本地投资分析：最简启动指南

## 只记住一个入口

更新仓库到最新 main 后，在仓库根目录**双击 `启动IIOS投资分析.command`**。

首次运行若 macOS 阻止打开，可在 Finder 中右键该文件并选择“打开”。需要 Python 3.10 或更新版本；无需安装 Python 包、配置 API key 或安装本地模型。

## 启动后怎么做

1. 按提示填写公司名称、股票代码、市场、分析截止日、当前持仓、人工核实价格、价格观察日期和来源简述。大部分字段有默认值。A 股代码可输入 `SZ002810`、`002810.SZ` 或 `002810`；`SH600000`、`BJ430047` 也会自动规范化。港股可输入 `HK00700` 或 `00700.HK`。价格按人工输入处理，不会被标记为官方行情已验证。
2. 价格观察日期默认跳过周末，回到上一个工作日；程序不会自动判断交易所节假日，请核对是否为真实交易日。若观察日期与分析截止日相同，因日级 PIT 截止按当日 00:00 处理，该价格不会用于回报/目标买入价计算；应优先使用截止日前已完成交易日的价格。程序会打开 ChatGPT、在剪贴板中放好研究提示，并在 Finder 中定位输入模板。
3. 让 ChatGPT 基于材料补充 Trust、Reality、Quality、Thesis、价值驱动排序、Bear/Base/Bull 情景、MIE/预期差和风险。资料不够就填写 `UNKNOWN`；MIE 不可识别时填写 `NOT_IDENTIFIABLE`，不要编造。
4. ChatGPT 返回完整 JSON 后，将它复制到程序自动打开的 `pilot-chatgpt-response-标的代码-时间戳.json` 文件里并保存（macOS TextEdit 使用 Command+S）。回到终端**只按回车**。程序从该文件读取并校验，成功后运行分析并打开中文报告；失败则显示原因，可修复文件后再次按回车，不必重跑向导。

**不要把完整 JSON 粘贴到终端。** 长回答不再依赖剪贴板读取，也不用手动输入文件路径。结果文件和输入模板保存在 `~/.iios-private/local-pilot/inputs/`。

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
