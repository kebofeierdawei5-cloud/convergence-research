# B76 — 现价条件性要求与独立预测对照、胜率赔率边界

**开发分支：** `feat/b76-core-integrated-20261101`  
**开发基线：** B73 `faeee544238dd4b6154e2b0a7a4a53c8a88a6815`  
**最新批次提交：** 见本分支 HEAD。  
**状态：** 已完成代码与文档提交；未运行测试；未 Replay / CI / macOS 验收；未合并 main。

## 1. 为什么重建正确开发基线

上一条 B76 分支 `feat/b76-expectation-gap-win-odds-20261101` 是从 canonical main 创建的，因此不包含另一条未合并开发链上的 B60–B73。该链包含：
- B60 EPS 现价条件要求反推；
- B61 SOTP 现价反推；
- B62 B4 分部盈利与 SOTP 对账；
- B63 SOTP 估值缺口归因；
- B64–B68 证据、可比性、P/E 校准、价值可信度及经营要求反向工程；
- B69–B73 经营可行性诊断。

B73 分支较 main 超前 321 个提交。**本批仅在该分支上继续开发，不把这 321 个提交整体合并到 main。** 原 main-based B76 分支保留为隔离试验，不作为后续核心集成基线。

## 2. B76 真正要回答的问题

同一预测期间、同一分部范围、同一单位下：
- B4 的独立 Bear/Base/Bull 前瞻盈利和经营假设是什么；
- B61 在其他分部保持当前 SOTP 利润时，单个分部需要达到什么利润；
- B63 在完整 B4 分部利润向量下，Required Return 所需总价值池和条件倍数是什么；
- B68 将上述利润门槛映射成哪些单变量销量、净售价、单位成本替代敏感性；
- 独立 B4 预测相对 Required Return 价值池要求有多少余量/缺口；
- 同一价格和期限下的情景上行/下行幅度如何；
- 胜率是否有足够证据识别。

这是一种**现价条件性比较**，不是外部 MIE，不是独立预测，也不自动构成正式 expectation gap。

## 3. 新增只读比较适配器

新文件：`iios_mvp/expectation_gap_comparison_v01.py`

**适用范围：**本批 B76 数值对照聚焦操作者选定且本地成功复算的 SOTP 路径（B61/B62/B63/B68）。非 SOTP 主模型返回 `NOT_APPLICABLE_NON_SOTP`；EPS_MULTIPLE 的 B60 现价 EPS 反推保留原有展示和计算，本批没有新增 B60 与 B4 的独立数值对照。

输入复用现有结果：
- B62 `segment_earnings_reconciliation`
- B63 `valuation_gap_attribution`
- B68 `operating_requirement_reverse_engineering`
- 现有 `return_metrics`
- 现有 `thesis_break_stress_review`

输出挂载：
`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.expectation_gap_comparison`

### 数值对照

每个 Bear/Base/Bull 场景：
- 对照 B4 完整前瞻分部价值池与 B63 Required Return 所需分部价值池；
- 计算价值池差额、相对要求的余量百分比；
- 对照 B4 隐含每股终值与 Required Return 每股终值要求；
- 逐分部展示 B4 独立归母利润与 B61 单变量要求、B63 单变量敏感性要求之间的差额；
- 展示 B63 Required Common P/E 与当前选定 SOTP P/E；
- 展示 B68 对应的产品销量、净售价、单位变动成本单变量替代要求。

### 必须保留的边界

- B61 的分部 Required Profit 是其他分部保持选定 SOTP 利润的单变量敏感性；不能跨分部相加。
- B63 的 per-segment Required Profit 是其他分部保持完整 B4 预测的单变量敏感性；不能跨分部相加。
- B63 full-vector value-pool gap 才是完整 B4 分部利润向量与 Required Return 价值池要求之间的整体比较。
- B68 销量、售价、单位成本是不同替代方案，不是同时要达到的经营目标。
- B63 Required Common P/E 是全分部统一倍数缩放条件敏感性，不是单一分部公平 P/E。
- B76 不修改 B4、B61、B62、B63、B68、SOTP、MIE、expectation_gap、15% 收益门槛、Required Return、目标入场价、组合约束或 Decision。

## 4. 胜率、赔率与失败代价

- 胜率固定为 `NOT_IDENTIFIABLE`。只有可比投资案例的历史胜负样本或经独立验证的概率校准模型，才可能支持投资胜率量化；事件概率、管理层目标、分析师主观判断和 Bear/Base/Bull 权重均不足以单独证明投资胜率。
- 同一入场价格、同一持有期下，分别展示 Base 上行 / Bear 下行、Bull 上行 / Bear 下行的幅度比。该比例是 payoff asymmetry，不是概率。
- 显示既有回报计算器按提交情景权重得到的年化收益，但明确它不是胜率，也不代表权重已经校准。
- 展示独立 thesis-break stress 的总回报与下行幅度；它不参与情景概率加权。
- 展示实际资金占用年限；缺乏明确替代投资基准时，机会成本金额保持 `NOT_PROVIDED`，不伪造金额。
- 事件时间差保持 `NOT_IDENTIFIABLE`，因为 B61/B63/B68 没有独立的逐事件市场定价窗口。

## 5. B74 / B75 在本开发基线上的集成

由于 B74/B75 原先在 main-based 独立分支开发，本批已将其 Prompt 与一屏报告表达移植到 B73 核心链：
- B74：一项主要矛盾、最多两项次要矛盾；rank=1 首要决定因素；支持/反证；重要性取舍；关键变量及每股价值传导。
- B75：从主要矛盾推导 2–4 个未来事件；事件先后依赖；触发条件、截止时点证据和反证；映射到 B4 输入；Bear/Base/Bull 路径；不伪造事件概率。
- Round A 仍价格盲；Round B 仍只处理价格感知估值/MIE；B76 数值对照在本地计算完成后执行，不把操作者字段或本地后置计算结果提前泄露到 Round A。

## 6. 验证与剩余风险

本批新增：
- `iios_mvp/expectation_gap_comparison_v01.py`
- `tests/test_expectation_gap_comparison_v01.py`
- B76 本地报告一屏摘要；
- B74/B75 Prompt 与报告表达移植；
- 回归断言更新。

**测试没有运行。** 不能声称 Python 导入、算术、报告、Replay、CI 或 macOS 运行通过。下一次统一验证应重点核对：
1. B63 waterfall 的 step 3/step 5 是否与 B62/B61 期间、口径和金额精确一致；
2. B68 的 B61/B63 两类 driver alternatives 是否被正确展示为替代敏感性；
3. Decimal 计算和小数输出；
4. EPS_MULTIPLE 非 SOTP 路径是否明确 NOT_APPLICABLE，不受影响；
5. MIE 与 decision-usable expectation_gap 原值是否保持不变；
6. Return Metrics、thesis-break stress 与 payoff asymmetry 是否同价、同期间；
7. Replay 完整性和真实 macOS 一键流程。

## 7. 决策权限

本模块仅提供只读研究比较：
- `external_mie_modified=False`
- `expectation_gap_modified=False`
- `b4_forecast_modified=False`
- `b61_b63_b68_modified=False`
- `valuation_modified=False`
- `decision_authority=False`

不会生成 BUY/ADD/HOLD/REDUCE/EXIT，不创建正式证据/预测/估值准入，不授权交易或自动下单。
