
# C1/C2 下一批操作清单（面向单人本地 IIOS，2026-10-13）

**目的**：按现有正式准入实现推进，而不是另写一套准入代码。签名、权利和独立复核均为真实授权事项；CI 通过、文件哈希、公开可访问和 AI 复核都不自动关闭它们。

## 当前卡点

| 轨道 | 已完成 | 真实阻塞 |
|---|---|---|
| C1 / 百龙创园（605016） | 私有来源年代候选与 Core/PIT 候选校验完成；签名/权利合同与只读 preflight 代码已存在 | SSE 行情的具体留存/本地计算使用权未获书面许可；可信签名者注册表为空；还没有正式签名准入 |
| C2 / 新和成（002001） | 13 个官方 PDF 定位候选在机器独立复核中通过；私有人类复核包生成器已实现 | 必须由真实独立复核人检查原 PDF 字节和事实、明确使用范围并签名；可信独立签名者及权利范围未完成 |
| 本地模拟研究 | 已完成本轮 605016 首轮/Replay 的有限范围 Mac 接受；仓位包被跳过并保持 UNKNOWN | 非正式试运行不等于正式 Evidence/PIT/Decision |

## 执行顺序

### A. C1：先解决行情使用权，再签名

1. 使用现成草稿 docs/iios/EXCHANGE_MARKET_DATA_RIGHTS_REQUESTS_20261011.md 向上交所/上证所信息网络有限公司的正式渠道提交申请。当前文件只是草稿，尚未发送；未收到书面许可前不能把行情标为 ALLOWED。也可以提交适用的合规授权供应商合同作为许可依据。
2. 由所有者在私有 Mac 上按 docs/iios/EVIDENCE_ADMISSION_SIGNING_AND_MARKET_DATA_RIGHTS_GATE_20261011.md 生成**专用** Evidence Admission 密钥对与本地 enrollment request。私钥留在权限受限的私有目录；不要发给 AI、不要提交 Git、不要复用 Provider 运行密钥。
3. 人工审核签名者身份、角色、精确 case scope 与有效期后，才把公钥注册请求应用到规范 signer registry。不能让密钥自签自信任，也不能用通配 case scope 绕过审批。
4. 收到并审核许可文件后，把原始许可字节留在本地私有目录，记录真实仪器编号/范围/有效期/精确 SHA-256，并形成 case-bound rights record。
5. 用现有命令 python -m iios_mvp.canonical_signed_evidence_admission_v01 preflight ... 只读检查。只有真正返回 READY_FOR_SIGNATURE_NOT_ADMITTED 后，才由已注册授权人签名并运行 verify。任何 BLOCKED 都保持阻塞；不允许手工改状态字段。

### B. C2：独立事实复核和使用范围签核

1. 在规范 checkout 使用现成命令生成本地私有复核包：  
   python -m iios_mvp.c2_independent_fact_review_v01  
   输出默认写入 ~/.iios-private/reviews/，文件权限为 0600；原始 PDF 与私有复核包不上传 GitHub。
2. 由**与准入签名者不同的真实复核人**重新打开对应官方 PDF 原始字节，逐条核对 13 个事实、页码定位、known_at 上界、使用/留存依据并记录拒绝或未知项。ChatGPT 自己生成的复核意见不能冒充单独的人类身份/独立签名。
3. 复核人需明确个人非商业私有用途是否有足够依据、允许哪些操作、留存/备份限制、衍生研究输出与禁止的第三方传播范围，并由单独登记的 INDEPENDENT_REVIEWER 密钥签名。若权利范围不能被文件明确支持，维持 UNKNOWN / BLOCKED。
4. 将人工复核结果映射回具体 case 的事实清单和 rights record；随后走既有签名/verify流程。不能把 PUBLIC_ACCESS_REUSE_UNKNOWN 改名为允许使用。

## 不做的事情

- 不重新下载或抓取 605016/002001 行情来绕过当前使用权问题；手工提供的价格继续属于 OPERATOR_ATTESTED_MARKET_DATA，只用于隔离的情景估值。
- 不把 C1 私有候选 Core/PIT PASS 当成正式准入；不把 C2 的机器 PDF 定位 PASS 当成独立事实签核。
- 不安装或依赖本地 LLM；C1/C2 权利与签名处理是确定性流程，不需要模型、付费 API 或市场数据 API。
- 不在公开仓库记录原始报价、私有证据字节、私钥、私人许可往来或用户组合信息。

## 完成定义

C1 只有在具体行情许可/授权依据、可信登记的授权签名、完整原始字节与 Core/PIT 复核都通过后才可正式准入。C2 只有在 13 条事实由真实独立复核者确认、用途权限范围明确、独立签名/rights record/原始文件校验全都通过后才可正式准入。此后再按当前批次计划推进 D1 真实生产 Host；D1 不能先于 C1 通过。

本清单是可执行顺序，不代表申请已发送、许可已取得、签名者已授权或正式准入已完成。
