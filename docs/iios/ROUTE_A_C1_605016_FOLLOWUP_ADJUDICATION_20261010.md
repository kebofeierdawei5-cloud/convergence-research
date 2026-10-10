# 百龙创园 605016：股息实施事实与价格 PIT 缺口补充审查

日期：2026-10-10  
Case：`RC-CN-A-605016-20261009`  
原始 cutoff：`2026-10-09`（日期型；按当前 core B2/PIT 合同解释为当日开始，不改成收盘/日末）

## 一、正式分红实施公告已逐字节核验

**结论：可将具体实施事实用于内部个人研究；原始 PDF 不可复制到 Git 或对外再分发。**

- 上交所官方公告查询 API 返回匹配行：证券代码 `605016`、简称“百龙创园”、标题“2026年半年度权益分派实施公告”、`SSEDATE=2026-09-22`、公告编号为正文中的 `2026-043`。
- 官方 API 列表响应：3,079 bytes，SHA-256 `8c7f84e0161d4db6162c1af4ec32cd29092a3e515435c46887419f6dd2909aa0`。
- 正文最终从官方 SSE big5 PDF host 取得：146,499 bytes，SHA-256 `1a153c20f908abbd48fdd63a651ecb0edde269f3e7dd0ea27a0b8ce420e5ea8c`，PDF magic `%PDF-1.7`；3 页。
- PDF 元数据创建时间为 `2026-09-21 16:42:58+08:00`；官方列表 `ADDDATE` 为 `2026-09-21 16:44:10`，公告展示日/正文落款日为 `2026-09-22`。由于没有正式文档说明 `ADDDATE` 精确语义，证据记录采用 `known_at/published_at=2026-09-22` 的日精度，不声称具体的首次公开秒数。此日期明确早于本案 cutoff。
- 逐页视觉与文本复核结果：代码/简称/公告编号/标题匹配；A 股含税每股现金红利 0.075 元；股权登记日 2026-09-28；除权日和现金红利发放日均为 2026-09-29；分配基数 420,012,320 股；合计现金红利 31,500,924 元。
- 复用级别：`RESTRICTED_NO_REDISTRIBUTION`。只保留事实字段、页码定位、源链接和摘要；原 PDF 仅位于短期 Actions artifact，没有提交到 Git。

机器记录：`evidence/real_cases/RC-CN-A-605016-20261009/DIVIDEND_IMPLEMENTATION_ADJUDICATION_20261010.json`。

## 二、实际 B2/PIT 重新运行

组合审查工作流 [#38039463649](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38039463649) 成功完成，组合输出 artifact #11665325858；它把真实 Attempt 10 的原始证据与上述实际分红公告组合，重新调用未修改的 `research.b2.company_evidence.build_company_evidence_manifest`。

- 组合候选 manifest SHA-256：`7b91b2531ab82f8f53a7a06887564eb5f8b3938d2f5d4d8e6f867a4057fc6f74`。
- 证据记录共 11 条，其中 10 条状态为 `ADMITTED`，1 条价格候选仍为 `UNKNOWN`。
- 六组通过：`security_identity`、`corporate_disclosures`、`business_reality`、`financial_reality`、`capital_structure`、`trust_governance_events`。
- 核心校验器仅剩两条阻断：
  1. `EVIDENCE[605016-PRICE-CANDIDATE-20261009]:PIT:PIT_UNKNOWN: source availability/provenance is not established`
  2. `REQUIRED_FIELD_GROUPS_UNCOVERED:market_price`
- 结果仍为 `BLOCKED`，`evidence_admission=false`、`pit_admission=false`。没有生成正式估值、Decision Revision、Publication、投资报告或完整 Run Receipt。

## 三、市场收盘价：已找回数据行，但未通过来源准入

严格日期型 cutoff `2026-10-09` 的含义是只使用当日开始前已知的价格。因此本案应核验最后一个完整交易日 **2026-10-08** 的收盘，不应把 2026-10-09 的收盘倒灌进当日开始时点。

- 上交所官方日 K 服务的 HTTPS 入口无法取得响应：标准 HTTPS 主机报网络不可达；同一服务的 HTTPS:32041 返回 SSL 协议不匹配；另一个尝试的 HTTPS 查询路由返回 404。
- 旧的 HTTP:32041 路由返回过 2026-10-08 的日 K 候选，但未加密传输不满足 intake 契约。原始响应只有 124 bytes，SHA-256 `45c8eece737c57ec11deb34ad099dcc8f9f88f9c5e080be53992d2ec707b3480`；具体行情值不在公共仓库重复发布。
- **不准入原因明确：**当前原始证据 intake contract 要求 HTTPS。虽然 HTTP 响应来自 SSE 官方域名、日期和数值结构匹配，未加密传输不能满足该合同，故状态是 `BLOCKED_HTTP_TRANSPORT_NOT_ADMISSIBLE`。没有把它写进 B2 manifest。
- 二级来源仅用于诊断日期/字段冲突，具体行情值不在公共仓库重发。Eastmoney 官网法律声明已被检查：其条款要求未获书面许可不得复制/转载网站内容，并特别要求未经上交所/深交所事先书面同意不得复制、传播、转播或展示行情信息。没有书面授权，Eastmoney 数据被排除；Yahoo 的条款又要求自动化采集须事先许可，因此也被排除。
- 所以当前唯一缺口仍为 `market_price`。官方数据通道的问题是 HTTPS 不可达且 HTTP 不符合 intake 合同；二级数据通道的问题是网站法律声明要求书面授权复制行情数据，而授权尚未取得。两条都不能变为 ADMITTED。不允许把 HTTP 原始行、未经授权的二级来源或检索时间伪造成已知 PIT 事实，也不放宽 HTTPS intake 或 cutoff。

- Eastmoney 法律声明原始页已在 [Follow-up capture run #38039773596](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38039773596) 中捕获；法律页面 URL `https://about.eastmoney.com/home/legal`，原始 HTML SHA-256 `2f669b80d2ca640e0d4f2995c3cdbb77c4abc4c150e761492f2aab44b06d78ca`。本结论只记录该声明的文本，不构成法律意见；但按 IIOS “授权复用必须单独通过”的原则，没有书面授权就不准入该行情源。

机器记录：`evidence/real_cases/RC-CN-A-605016-20261009/PRICE_CUTOFF_SOURCE_ADJUDICATION_20261010.json` 与 `FOLLOWUP_B2_RUN_20261010.json`。

## 四、最新官方 HTTPS B2/PIT 重跑 — 2026-10-10

最新 exact-head 工作流 [#38041208974](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38041208974) 使用上交所官方 HTTPS/TLS 日 K 接口，对 2026-10-08 的完整交易日记录进行一行精确匹配，并将实际字节哈希、临时事实记录与 Attempt 10 + 正式分红实施公告组合，调用**未修改**的核心 B2/PIT 校验器。

- 核心候选 manifest 状态：**PASS**；11 条记录通过，七组必需字段全部覆盖，校验错误为零。
- 行情接口响应大小及 SHA-256：124 bytes，`45c8eece737c57ec11deb34ad099dcc8f9f88f9c5e080be53992d2ec707b3480`。公开报告 artifact [#11665881455](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38041208974/artifacts/11665881455) 只保存了源 URL、日期、字段形状、哈希和校验状态，没有保存原始字节、具体行情值或完整 manifest。
- PIT 处理：本案原始日期型 cutoff 仍是 `2026-10-09`，核心将其解释为当日开始。候选使用前一交易日的收盘观察时点 `2026-10-08T15:00:00+08:00`，不是把 10 月 9 日收盘倒灌到 cutoff。
- **首次公开时间边界：**官方 API 未公开该历史 JSON 行的精确首次上传时间；`known_at` 使用市场收盘事件时间，不能声称是 API 的精确首次发布时间。该时间模型仍须独立审查。
- **持久化边界：**这是 `PASS_EPHEMERAL_B2`，不是 canonical durable admission。按上交所数据复用限制，实际原始行情字节和含数值的 candidate manifest 仅存在于临时 runner 工作区，没有上传或提交到 Git。私有部署 Host 必须在其受控 data root 中重新获取/保存同一官方 HTTPS 源、记录精确哈希与签名准入，再重复 B2/PIT 后才能进入正式估值与决策。

## 五、下一道门

1. 继续寻找满足 HTTPS intake 契约的官方/授权免费 2026-10-08 收盘价来源，并单独核验来源版本、字段含义、已知时间和复用条款；如找不到，价格继续 UNKNOWN。
2. 新价格通过后，运行原封不动的 B2/PIT validator。只有七组全部被有效记录覆盖，才允许进入正式估值和决策链。
3. 生产 Host 配置仍是独立 OPEN gate。尚无实际部署 Host 的真实 605016 请求、真实语义/Forecast/Valuation 准入、Decision Revision、报告与完整 Run Receipt 回放及独立红队证据。P0-LLM-001 / P0-LLM-004 继续 OPEN。
