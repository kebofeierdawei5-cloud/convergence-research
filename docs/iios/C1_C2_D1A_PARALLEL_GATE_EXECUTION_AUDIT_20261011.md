# C1 / C2 / D1-A 并行推进审计与执行记录

- 日期：2026-10-11
- 记录类型：并行执行 checkpoint / 证据与阻塞审计
- 检查基线：canonical `main@18854586bd6cd71059d6da7d3beef4f1f61a8e64`
- 状态：本记录为检查与执行准备记录；不创建新的正式 Evidence/PIT Admission，不声明生产 Host 已接受
- 私有数据规则：不在 Git 中写入私有行情数值、原始行情字节、用户本机路径、模型提示/原始回复、密钥或 bearer token

## 1. 本轮结论

三条工作流均已推进，但**尚不能把三条工作流全部标记完成**：

| 工作流 | 本轮已完成 | 仍然阻塞 / 本记录的结论 |
|---|---|---|
| C1 — 605016 | 复核了已存在的 source-vintage successor 和 Core/PIT 校验记录；确认原始候选已持久化、不得重复摄取 | 正式 Evidence/PIT Admission 仍为 false。当前本地 ingester 明确写出 `formal_signed_admission_created=false`；已检查的 Candidate/Validator 流程没有给出可被本项目认可的正式签署授权与签署流程。另需独立解决 SSE 历史收盘行情使用权限问题。 |
| C2 — 002001 | 复核既存 Run #8 归档记录、13 项官方 PDF 事实定位/时间边界检查结果，并重新查看官方 PDF 页面与公告 | 本轮独立方法复核支持所检查事实与官方文件/公告相符；但不冒充第三方法律意见。C2 现行 machine record 的来源复用状态仍为 `PUBLIC_ACCESS_REUSE_UNKNOWN`，外部/人类复核签结与正式签名准入仍未完成。操作者价格仍是 `OPERATOR_ATTESTED_MARKET_DATA`，绝不升级为独立来源验证行情。 |
| D1-A — 本机 Host 准备 | 核对了 canonical Host、Local Ollama 配置工具、回环探针和验收 Runbook；已有可执行准备步骤 | 本会话无法访问操作者 Mac 的本地服务、私有目录或密钥。本轮没有运行用户本机配置、模型版本、受保护环境文件或 health/readiness 探针；状态仍是待操作者实际执行。 |

本轮未重新运行 C1 ingest、未请求新的 C1 行情，也未对已提供的 C2 行情做第二轮行情网页搜索。

## 2. C1 — 605016：保留现有候选，不重复摄取

Canonical 记录已确认：
- Case：`RC-CN-A-605016-20261009`，cutoff 仍为日期型 `2026-10-09`，即上海时间该日开始；
- 现存 successor 有 11 条 Evidence、11 项 raw-artifact declarations、8 个唯一原始文件，Investment Core-owned Core/PIT validator PASS；
- 价格 observation date 是 `2026-10-08`；
- source-vintage 采用官方规则推导的保守可用时间上界 `2026-10-08T15:30:00+08:00`；
- `exact_first_public_timestamp_verified=false` 保持不变；SSE 规则页面的原始字节在先前本地 adjudication 中没有被 materialize/hash；
- 先前本地 persistence receipt 已明确：`formal_signed_admission_created=false`、`production_host_accepted=false`。本轮不得将这些值改写为 true。

### C1 的正式准入门槛

1. **来源时点和 Core/PIT**：已有 bounded source-vintage successor，但它不能证明端点的精确首次公开时间。
2. **行情使用权限**：现行《上海证券交易所交易规则（2026年修订）》第 5.1.3 条说明交易信息归上交所所有，未经许可不得使用和传播。该规则页面可作为公开政策依据，但本轮没有取得 SSE 对该具体行情存储/使用范围的专门许可。因此，“来源来自官方 HTTPS”与“允许按当前系统用途正式准入”必须分开判定。
3. **正式 Admission writer / signer**：`tools/iios_private_605016_b2_ingest_v01.py` 的输出合同是私有候选及完整性校验；`iios_mvp.canonical_evidence_admission_v01.validate_company_evidence_manifest` 是校验器。当前 C1 记录没有一份经授权的正式签署凭据，也不能把候选 receipt 的普通 SHA-256 自称为数字签名。不得借用 Provider 的 Ed25519 key 作为未经授权的 Evidence Admission signer。
4. **授权边界**：只有在项目定义了受信任的准入签署者/签署合同、并证明行情来源的允许用途之后，才能创建正式 admission 记录并通过独立验证。仅重新运行校验器不会关闭这个缺口。

### C1 下一步

- 不重复 ingest、不重新下载 Attempt 10、不重新调用官方行情端点；
- 为 formal Evidence/PIT admission 建立明确的版本化授权/签署合同与独立验证流程，不能通过手改字段或重新散列候选来假造批准；
- 明确该 SSE 行情在个人非商业研究中的许可依据。若没有适用许可或授权证据，则 C1 的 `market_price` 正式准入继续 BLOCKED；可另行提供一个允许个人内部研究及私有字节留存的原始历史行情凭据作为替代来源候选，但不得自动升级其来源保证等级。

## 3. C2 — 新和成：第二方法事实复核与使用边界

### 本轮事实复核

复核对象保持为原有 Run #8 的不可变归档及已归档的脱敏报告，没有改变原始 ZIP、manifest、receipt、PDF 字节或历史 preflight。

已有 CI/本地记录报告 13/13 fact locator term sets、13/13 cutoff-safe date bounds、13/13 official SZSE domain bindings 通过。另行打开并截图检查了这些官方文档的相关页面：
- 2026 年半年度报告全文：issuer/security identity、财务数据、管理层业务叙述、分产品收入及资产负债项目；官方 URL: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/83165436-1015-4d77-919c-97c8cce0c67d.PDF
- 2026 年半年度报告摘要，公告编号 2026-035；官方 URL: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/6d1ad0be-5e22-482b-a163-2ebb0b6d1d95.PDF
- 董事会决议公告 2026-034，说明半年度报告及摘要于同日披露；官方 URL: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/a0f47443-c60c-4e88-b444-bf3e0da5372e.PDF
- 回购方案公告 2026-027；官方 URL: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-06-24/53248225-c2cf-45cf-a0fd-a6c9fee4f267.PDF
- 回购方案董事会决议公告 2026-026；官方 URL: https://disc.static.szse.cn/disc/disk03/finalpage/2026-06-24/0f51c1d5-2f3d-4f07-9f7c-c02bfd2c63a4.PDF

上述直接复核与归档的逐条 locator 检查互相支持，但不代表本轮在本机重新哈希了 Run #8 原始 PDF，也不构成第三方法律意见。原归档的原始字节与哈希结论继续引用 C2 原有记录。

### C2 使用权限结论

深圳证券交易所公开《法律声明》说明：机构或个人可以基于非商业目的浏览、下载网站内容；未经书面许可，不得以向他人出售牟利为目的使用网站内容。官方页面：https://www.szse.cn/application/laws/

据此，本轮对**公司披露文件**提出以下窄范围处理意见：个人非商业研究、私有目录内存储、仅事实级抽取、不向 GitHub 上传原始 PDF/完整表格、不再分发原文件或行情数据。此为运行工作流的保守内部处理建议，不是法律意见，也不扩张为商业复用、再分发或行情服务许可。

该条款有助于缩小公司披露文件的 use-rights 问题，但当前 canonical C2 machine record 仍将相关 13 项事实记录为 `PUBLIC_ACCESS_REUSE_UNKNOWN`、`retention_permission_declared=false`，并要求独立 reviewer sign-off。不能在未按现行合同记录独立签结前，擅自将这些状态批量改为 `ADMITTED`。

特别是：交易所的公司披露文件与交易行情数据不是同一类对象。SZSE Data Services 将收盘价等描述为市场数据服务；该页面不能解释为对历史行情原始数据无条件授权。操作者提供的价格仍保持 `OPERATOR_ATTESTED_MARKET_DATA`，其哈希只证明声明字节完整，不证明供应商原始行情字节或来源时间。

### C2 下一步

1. 将本次第二方法结果提交为独立审查记录，供授权的独立 reviewer 复核并签结 13 项事实、保守 `known_at`、私有事实级用途边界；
2. 原始 Run #8、历史 cutoff、原始数据和 numeric quote 均保持不变；
3. 在 reviewer 记录明确准入范围、证据类及允许用途之前，C2 正式 signed Evidence/PIT admission 仍 BLOCKED；
4. 不重新检索行情网页，不把 operator-attested 价格升级为 source-vintage-verified。

## 4. D1-A — 本机 Host / 模型准备

Canonical Runbook 已提供如下步骤；本轮仅完成路径/合同核对，**没有在操作者主机执行这些命令**。

在安装且已启动 Ollama、目标模型已下载的操作者 Mac 上，先运行：

```bash
python tools/prepare_iios_local_ollama_runtime.py \
  --workspace "$HOME/.iios-private" \
  --model "qwen3:8b"
```

准备工具要求本机 Ollama API 可达、版本不低于 0.13.3、模型 tag 已安装；它创建权限受限的私有环境文件，其中包含运行时密钥和 Host bearer token。**不要把 env 文件内容、私钥或 token 复制到聊天或 GitHub。**

然后在同一本机、关闭 shell tracing 的终端里检查配置：

```bash
set +x
source "$HOME/.iios-private/secrets/host.env"
python -m iios_mvp.canonical_host_v01 --check-config
```

再启动实际 Host，并另开终端执行回环健康探测：

```bash
python -m iios_mvp.canonical_host_v01 \
  > "$IIOS_HOST_OUTPUT_ROOT/host.log" 2>&1 &
python tools/iios_d1a_host_liveness_probe_v01.py \
  --host 127.0.0.1 \
  --port "${IIOS_HOST_PORT:-8765}" \
  --out "$IIOS_HOST_OUTPUT_ROOT/d1a-liveness-probe.json"
```

这里最后两条应在**两个终端**内运行：Host 进程先在一个终端启动，探测在另一个终端执行。命令必须从 canonical main 检出版本执行，并确认 repo 根目录正确。探测器只 GET `/healthz` 与 `/readyz`，成功状态是 `HOST_LIVENESS_PROBED_NOT_PRODUCTION_ACCEPTED`；它不能证明 Provider 被调用，更不能关闭 D1-A。不得在 C1 正式准入前发送 605016 canonical Host 请求。

### 本机输出回传约定

只回传脱敏状态和版本信息：配置检查的 status、Host version、两个端点的 HTTP/body status、探针输出中的响应 SHA-256、是否本地模型版本/模型检查通过。不要回传 env 文件、私钥、bearer token、host.log 原文、prompt/response、原始行情或私有 manifest。

## 5. 当前唯一可接受的状态变化

本记录不允许从 `CANDIDATE` 直接手工改为 `ADMITTED`，也不允许由 CI 的成功结论推断生产准入。状态只能在受信任的准入合同与签署权限明确、适用来源用途合法依据已核验、真实证据字节通过原有 validator，并由独立 reviewer 对最终记录复核后，按 canonical 流程晋级。

当前状态继续为：
- C1：`LOCAL_PRIVATE_CANDIDATE_CORE_PIT_PASS / FORMAL_ADMISSION_BLOCKED`；
- C2：`CORE_PIT_PASS_OPERATOR_ATTESTED / INDEPENDENT_SIGNOFF_AND_FORMAL_ADMISSION_OPEN`；
- D1-A：`RUNBOOK_READY / OPERATOR_HOST_PREPARATION_NOT_RUN`。

P0-LLM-001 / P0-LLM-004、正式 Decision、完整 Run Receipt、MVP acceptance 及 execution authorization 均保持 OPEN/false。
