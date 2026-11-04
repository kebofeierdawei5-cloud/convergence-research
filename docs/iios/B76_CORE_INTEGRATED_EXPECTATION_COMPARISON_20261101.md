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

**适用范围：**B76 现在分别支持两条互不混用的主估值对照路径：

- **SOTP：**比较 B4 独立 Bear/Base/Bull 分部正常化归母利润与 B61/B62/B63/B68 的现价条件要求。
- **EPS_MULTIPLE：**新增 `eps_multiple_comparison`，读取已经本地计算完成的 B60 与 B57/B58 结果，将 B4/B57 公司整体 all-items 归母稀释 EPS 与 B60 Required Return 所需终端 EPS 在相同期间、CNY/share 单位和同一利润口径下比较。

EPS_MULTIPLE 对照的 fail-closed 条件：B60 计算成功、主模型族为 EPS_MULTIPLE、币种为 CNY、B58 的情景状态为 `MATCH` 且 `forecast_period_match=True`，并且 B4 EPS / B60 所需 EPS 都有有效数值。B58 必须复核同公司范围、同币种/期间、同稀释股数与税后归属调整；仅期间匹配但股数或归属调整不匹配不能显示数值余量。B57 完整正常化桥可为 `CALCULATED_AND_RECONCILED`；若历史正常化基线缺失，但 B56 前瞻利润/税率、前瞻经常与非经常税前项目、前瞻少数股东总额和正的前瞻稀释股数齐全，B57 可明确标记 `FORWARD_ALL_ITEMS_EPS_CALCULATED_HISTORICAL_NORMALIZATION_NOT_IDENTIFIABLE`。这一部分状态只证明前瞻 all-items EPS 可复算，不代表历史正常化桥通过；B58 仍须重新核对公司范围、相同期间、相同稀释股数和税后归属调整。历史正常化 EPS / 增长率必须继续 UNKNOWN。若前瞻分母或 all-items 利润输入缺失/无效，仍完全阻断。B58 的期间核验覆盖 B4 forecast period、B57 forward period、主 EPS bridge period 和 EPS_MULTIPLE forecast period。估值终点日期独立展示，不得代替盈利参考期间。任何条件不满足时，差额和余量保持 UNKNOWN，不由 Round B 猜测。

主比较使用不含分红的 B60 Required Return EPS；只有 B60 的分红状态为 `VALIDATED_DATED_CASH_FLOWS` 或 `VALIDATED_NO_FUTURE_DISTRIBUTIONS` 时，才额外展示分红调整口径。B60 Fundamental Target EPS 单独列示，不与 Required Return 混用。B57 normalized EPS 不作为 all-items 比较值；EPS_MULTIPLE 适配器自报 EPS 也不冒充 B4 独立预测。

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


## 3A. EPS_MULTIPLE：B4/B57 与 B60 数值对照（2026-11-02 follow-up）

新增只读输出：`eps_multiple_comparison`。B76 在本地 B60 完成计算后再读取它，不把价格、Required Return EPS 或主估值倍数要求提前给 Round A / B4 预测使用。

每个 Bear/Base/Bull 情景展示：
- B4/B57 all-items parent-attributable diluted EPS proxy（CNY/share）；
- B60 Required Return 所需终端 EPS（不含分红）；
- 两者差额、相对所需 EPS 的余量百分比和方向；
- 只有分红经过既有收益求解器验证时，才展示分红调整后的 Required Return 对照；
- Fundamental Target EPS 单列展示，不能与 Required Return EPS 合并。

**期间/口径守门：**仅接受 B60 场景状态 `CALCULATED_CONDITIONAL`、B57 `CALCULATED_AND_RECONCILED`、B58 `forecast_period_match=True`。B58 已核对 B4 驱动预测期间、B57 前瞻期间、主 EPS bridge 期间和 EPS_MULTIPLE 盈利期间一致；B60 的 `valuation_terminal_date` 只用于持有期年化，单独保留。币种必须为 CNY，EPS 单位为 CNY/share。

**关键区分：**比较对象是 B4/B57 all-items 归母稀释 EPS proxy，不是 B57 normalized EPS，也不是 EPS_MULTIPLE 主适配器自报 EPS。后者只属于原主估值链，不代表独立预测。

本比较仅用于说明在 B60 既定现价、终端 P/E、持有期限和 Required Return 下，B4 EPS 预测是否高于所需 EPS。它既不是外部 MIE，也不证明 B4 假设可靠；不修改 B60、B4、B5/B6、估值、回报、目标价、MIE、正式 expectation_gap 或 Decision 权限。


## 3B. 统一算术与口径二次核查（2026-11-03）

本轮不是重算或替换上游估值，而是在 B76 只读比较层对 B57/B58/B60 及 B61/B62/B63/B68 做独立复核；任何关键算术输入缺失或不一致，预测余量必须保持 UNKNOWN。

### EPS_MULTIPLE：B57 → B58 → B60 → B76

B76 对每个 Bear/Base/Bull 情景复核：

1. **B57 分母链：**`B57 all-items 归母净利润 ÷ 加权平均稀释股数 = B57 all-items EPS`。只接受公司整体范围、B57 `CALCULATED_AND_RECONCILED` 和 B58 `forecast_period_match=True`；同时要求 B57 forward period 与 B60 earnings forecast period 明确一致。
2. **主适配器终值：**`主估值 EPS × 选定终端 P/E = EPS_MULTIPLE adapter terminal value/share`。这是主模型内部算术对账，不把主适配器 EPS 充当独立预测。
3. **Required Return：**使用与 B60 相同的结构化现价、ACT 年化期间、终端 P/E 和 Required Return 年化门槛，独立复算不含分红的所需 EPS。
4. **Fundamental Target：**按单独目标收益率复算；不与 Required Return 混用。
5. **分红调整：**只有 B60 已验证定时现金分配时，才复核 hurdle / target 各自的现金分配现值及调整后 Required Return / Fundamental Target EPS。未经验证的分红值不参与余量计算。
6. **唯一价格：**B60 reference price 必须与本次结构化 `price_input.price` 一致；不一致时整个 EPS 价格比较返回 `PRICE_REFERENCE_MISMATCH`。

任一项算术复核失败时，该情景返回 `ARITHMETIC_RECONCILIATION_MISMATCH`，保留输入来源值供审计，但不输出预测 EPS 与所需 EPS 的数值差额/余量。期间、分母、单位或数值缺失则保持 `NOT_IDENTIFIABLE`。EPS 余量均以 CNY/share 表示，估值终点日期独立展示，不与盈利期间互换。

### B57 historical / forward EPS partial semantics

B57 now separates the historical normalized-profit bridge from the forward all-items parent-attributable EPS calculation. When historical one-off NCI attribution or another historical normalization input is missing, but B56 forward profit/tax, forward recurring/non-recurring non-operating components, forward total NCI and positive forward diluted shares are complete, B57 may return `FORWARD_ALL_ITEMS_EPS_CALCULATED_HISTORICAL_NORMALIZATION_NOT_IDENTIFIABLE`. In this state:
- Forward all-items parent-attributable profit and diluted EPS are calculated explicitly.
- Historical normalized parent profit/EPS, normalized EPS growth and historical-to-forward normalized profit attribution remain UNKNOWN.
- B58 may compare only that forward all-items EPS with the primary EPS on identical scope, period, currency, share denominator and tax attribution basis.
- B60 and B76 may use the forward all-items EPS only after B58 confirms the same-period bridge; the historical normalized EPS proxy is never substituted.
- Missing/zero forward diluted shares or missing forward all-items profit inputs still block the forward EPS and all dependent numerical headroom.


### B57 前瞻 all-items EPS 与历史正常化基线的独立可用性

B57 不再把历史正常化归属输入缺失与前瞻 all-items EPS 计算混为一谈：
- 若历史少数股东非经常项目份额或历史稀释股数等正常化基线输入缺失，但 B56 前瞻利润/税率、前瞻经常/非经常非经营项目、前瞻少数股东总额及正的前瞻稀释股数齐全，B57 可输出 `FORWARD_ALL_ITEMS_EPS_CALCULATED_HISTORICAL_NORMALIZATION_NOT_IDENTIFIABLE`。
- 该状态只提供前瞻 all-items 归母利润 / EPS；历史正常化归母利润、历史正常化 EPS、正常化 EPS 增长率与历史至前瞻的正常化利润归因全部 UNKNOWN。
- B58 只在公司整体范围、前瞻期间、币种、稀释股数及税后归属调整与主 EPS bridge 一致时，才可使用这项前瞻 all-items EPS。
- B60 / B76 仅继承 B58 已核对的前瞻 EPS；不以历史归属缺项补零，也不把部分桥升级为完整 B57 通过。
- 前瞻利润、总少数股东归属、税率、期间或正稀释股数任一缺失时，B57 前瞻 EPS 仍 UNKNOWN，B76 不显示数值余量。

### B59 差异诊断与 Required Return 余量的边界

B58 未确认 `MATCH` 时，B60 不得输出 B57 EPS 相对 Required Return 的 headroom；B76 同样不得展示预测 EPS 与 Required EPS 的差额。  
但如 B59 已独立把 B57 与主 EPS bridge 的归母利润分子差、稀释股数分母差、主估值实际使用 EPS 输入差拆解并算术对账，则 B60 可以保留 `B59 EPS difference × selected terminal P/E` 的每股终值影响诊断。该值必须标记 `diagnostic_only=True`，并显示“不是 Required Return 余量”；不得参与买入判断、估值覆盖或正式 expectation_gap。

### SOTP：B61 → B62 → B63 → B68

B76 对每个 Bear/Base/Bull 情景独立复核以下恒等式和交叉节点：

- B63 waterfall：`step 1 selected SOTP pool + step 2 B4 earnings effect = step 3 B4 full-vector pool`；`step 3 + step 4 residual requirement = step 5 B61 Required Return pool`；同时核对 B63 声明的 waterfall residual。
- 交叉 B62：step 1 对应 B62 selected SOTP pool；step 3 对应 B62 完整 B4 前瞻分部价值池；step 5 对应 B61 / B62 Required Return 所需分部价值池。
- 再从 B68 的每个分部 B4 正常化归母利润 × 该分部选定 SOTP P/E 重新求和，必须与 B63 step 3 相等。B61/B63 单分部利润敏感性不能加入这个全向量求和。
- 母公司调整：分别核对资本化中心成本、净现金/净负债、其他调整在 B61、B62、B63 之间的符号、金额和桥接恒等式。
- 稀释股数与每股传导：核对 B61/B62/B63 股数一致；B4 总股权价值 ÷ 稀释股数 = B4 每股终值；Required Return 总股权价值 ÷ 股数 = 所需每股终值；B63 每股差额方向与 B76 的 B4 减 Required Return 余量相反且金额一致。
- 价格/期间：B61 reference price 必须与结构化唯一现价相等；B62 必须同时保留 forecast period 与 valuation terminal date，后者须与 B61/SOTP 对齐。

**B63 PARTIAL 的窄例外：**若 B63 情景唯一问题是 `COMMON_PE_SCALE_NOT_IDENTIFIABLE_NONPOSITIVE_VALUE_POOL`，但上述价值池、母公司调整、股数、每股传导和 B68 全向量复核全部通过，则 B76 保留可识别的 B4 pool / Required Return pool / per-share 比较，状态标记 PARTIAL，公共倍数敏感性仍为 NOT_IDENTIFIABLE。其他 PARTIAL 原因、关键字段缺失或算术不一致不享受此例外；禁止显示假余量。

### 两条估值路径共用的结果

EPS_MULTIPLE 不再因早期分支返回而漏掉 payoff、thesis-break stress 和 time-cost 摘要。两种估值模型共用同一套已计算的赔率幅度比、独立失败压力和期限展示；胜率始终 NOT_IDENTIFIABLE，情景权重不升级为胜率。该共享层只读，不改变 MIE、decision-usable expectation_gap、估值、回报门槛或 Decision 权限。

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

本批新增/更新：
- `iios_mvp/expectation_gap_comparison_v01.py`：增加 EPS_MULTIPLE 的 B4/B57 ↔ B60 Required Return EPS 比较。
- `iios_mvp/local_investment_pilot_v01.py`：将 B60 实际结果传入 B76 并在第一屏展示数值对照。
- `tests/test_expectation_gap_comparison_v01.py`：现有 SOTP 对照 + 17 个 EPS_MULTIPLE / 价格 / B63 部分状态 / waterfall / B68 向量 fail-closed 回归场景，包括通过 B58 口径核验后的前瞻-only EPS。
- `tests/test_local_investment_pilot_v01.py`：增加 EPS_MULTIPLE 与 SOTP 两种第一屏报告测试，以及 B57 forward-only → B58 → B60 传导回归。
- B76 本地报告一屏摘要；
- B74/B75 Prompt 与报告表达移植；
- 回归断言更新。

**截至本次文档更新，测试尚未运行。** 当前环境未能通过本地 DNS 建立代码执行副本；已扩展 GitHub Actions 的 Local Investment Pilot 工作流，等待后续精确分支 CI 结果。因此当前不能声称 Python 导入、算术、报告、Replay、CI 或 macOS 运行通过。
1. B63 waterfall 的 step 3/step 5 是否与 B62/B61 期间、口径和金额精确一致；
2. B68 的 B61/B63 两类 driver alternatives 是否被正确展示为替代敏感性；
3. Decimal 计算和小数输出；
4. EPS_MULTIPLE 主路径是否读取 B60 并完成 B4/B57 数值对照；其他无对应反推合同的模型族是否继续 NOT_APPLICABLE；
5. MIE 与 decision-usable expectation_gap 原值是否保持不变；
6. Return Metrics、thesis-break stress 与 payoff asymmetry 是否同价、同期间；
7. Replay 完整性和真实 macOS 一键流程。


## 6A. 真实案例覆盖边界

已检查仓库 `examples/real_cases`。002001、002422 案例文件仍是早期输入契约，不具备 B4/B57/B58/B60 与 B61/B62/B63/B68 当前 local-pilot 一体化计算所需的全链字段。已新增 `tests/test_b76_legacy_real_case_readiness.py`，直接读取这两份真实公司旧案例，验证：

- 新和成 002001 的历史 normalized EPS/P/E 情景不会被误当作 B57 all-items EPS + B58 同口径对账 + B60 现价反推；B76 明确 `BLOCKED_BY_B60_RESULT_MISSING`，不显示 EPS 差额/余量。
- 科伦药业 002422 的历史 SOTP 每股估值组件不会被误当作分部归母盈利、选定 P/E 和 B61/B62/B63 价值池反推；缺 B61 参考反推时明确 `PRICE_REFERENCE_NOT_IDENTIFIABLE`，不显示价值池或每股余量。
- 这两项是真实案例的**旧契约 fail-closed 展示验收**，不是两条数值 B76 路径已在真实案例中完成。合成数值夹具仍只用于算术回归，不冒充真实公司结果。
- 要声称真实案例 EPS_MULTIPLE 和 SOTP 数值路径验收通过，仍分别需要补齐 B57/B58/B60-ready 的公司整体 all-items 预测包和 B61/B62/B63/B68-ready 的完整分部盈利/估值包，并保留期间、价格、利润、股数及倍数来源。
- 在真实 B76-ready 案例包到位前，报告对缺失字段输出 UNKNOWN / NOT_IDENTIFIABLE，不通过继承旧案例数值或模型猜测补齐。

## 7. 决策权限

本模块仅提供只读研究比较：
- `external_mie_modified=False`
- `expectation_gap_modified=False`
- `b4_forecast_modified=False`
- `b61_b63_b68_modified=False`
- `valuation_modified=False`
- `decision_authority=False`

不会生成 BUY/ADD/HOLD/REDUCE/EXIT，不创建正式证据/预测/估值准入，不授权交易或自动下单。
