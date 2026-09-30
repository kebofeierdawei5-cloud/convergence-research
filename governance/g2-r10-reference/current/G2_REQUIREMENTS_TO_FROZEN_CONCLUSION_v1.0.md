# IIOS｜需求设计 → G0/G1 → G2 → Frozen 结论性总文件

**文档类型：** CONSOLIDATED ARCHIVE / NON-NORMATIVE NAVIGATION & CONCLUSION
**快照日期：** 2026-09-30
**用途：** 本地完整留档、后续上下文恢复、审计链导航。不能替代各 exact source artifact。

---

## 1. 项目定位

IIOS（Intelligent Investment Operating System）是面向中国 A 股与港股候选单股深度分析、决策、持仓跟踪与复盘的个人投资操作系统。当前系统目标不是全市场筛选，而是在用户完成行业/公司粗筛后的 candidate universe 中，把研究、证据、预测、估值、市场隐含预期、风险、决策、仓位、监控、验证组织成可审计、可重现、fail-closed 的决策系统。

核心投资目标持续围绕：

> 好公司 + 合理价格 + 足够安全边际

核心治理原则：AI 标准化分析与决策输出；人类最终批准与执行；系统不承担自动下单权限。

---

## 2. G0 / Requirements 层应解决什么

G0 的职责是冻结系统义务、决策语义、权限边界和验收要求，而不是证明所有阈值都正确，更不是证明投资业绩。

核心设计纪律：

1. 明确区分事实、推断、假设、观点。
2. 缺失、过期、冲突或不可验证证据必须 fail-closed，而不是由 LLM 自行补数字。
3. Human Decision 与 AI Decision 必须分离、分别留存。
4. Authorization 不得超出 Human Decision 批准范围。
5. State 与 Artifact Version 分离；历史对象不可被静默覆盖。
6. 决策链必须可追溯、可重演、可独立验证。
7. “无动作”本身也是正式决策结果。

### 当前决策优先级

`Trust Gate > Portfolio Constraint > Long-term Value > Expectation Gap > Tactical Market`

### 核心决策链

`Candidate → Trust → Quality → Reality → Independent Forecast → Valuation → Market Implied Expectation → Expectation Gap → Risk → Market/Positioning → Decision → Position → Monitoring → Validation`

---

## 3. G1 State Model 核心结论

G1 State Model 采用：

> 1 个主生命周期状态 + 多个正交状态维度 + 不可变分析对象

主生命周期包含：

`INIT → RESEARCH → QUALIFICATION → ANALYSIS → DECISION_READY → AI_DECISION → HUMAN_AUTHORIZATION → EXECUTION → MONITORING ↔ REASSESSMENT → CLOSING → VALIDATION → CLOSED`

另有 `TERMINATED`。

正交状态至少覆盖：

- Trust
- Thesis
- Valuation
- Investment Attractiveness
- Position
- Monitoring
- Validation

分析对象采用：

`DRAFT → FROZEN → SUPERSEDED / INVALID`

关键原则：上游对象失效必须向下游传播；不得为了保持一个旧 Decision 看起来稳定而修改其历史输入。

Trust、Thesis、Valuation、Attractiveness 不可互相偷换，例如价格下跌不自动等于 Thesis Broken；高估值也不自动等于公司质量恶化。

---

## 4. G2 的架构定位

G2 将 G0/G1 的系统约束进一步转化为可执行、可验证的规范、数据契约、引用/版本、状态/授权、验收与证据链。

长期架构目标为 00–12：

`Qualification / China-Macro-PQ / Market / Industry / Company / Earnings-Forecast / Valuation-Expectation / Risk / Falsification / Scenario / Decision / Position-Portfolio / Tracking`

当前 G2 的关键工程对象包括：

- G2 Clause Registry：唯一 normative carrier。
- G2 Data Contract / Enum Registry / Reference Dictionary / Field Validation Matrix。
- Schema Formalization + Complete Fixture Acceptance。
- Behavioral Test Catalog。
- Mutation Catalog。
- Independent Gap Oracle / Clean-room replay。
- Governance / Authority / Authorization / Reservation / Execution semantics。
- Traceability Closure。
- Output Contract Closure。
- Freeze Approval / Freeze Commit / Post-Freeze Verification。

---

## 5. 历史 G2 v0.4 冻结基线

历史基线：

`G2-NORMATIVE-0.4-FROZEN`

SHA-256：

`5399f216ebb96709876bf9a9ddd94c6d20ab809243290503df6ace35da4d61d8`

该版本作为后续重建/修复链的历史不可变参考，不与当前 v0.9 Frozen Carrier 混淆。

G2 Clause Registry v0.4 是历史 normative baseline；后续 v0.5/v0.6/v0.8/RM7R 是对其发现、修复、治理与验证链的演进。

---

## 6. G2 v0.5 / v0.6：从“有规范”转向“可证伪、可执行”

主要引入/强化：

- Acceptance Architecture。
- Clause Traceability。
- Behavioral Test Catalog。
- Mutation Acceptance。
- Independent Oracle / Gap Oracle independence。
- AUTH006 对抗性授权/身份/权限测试。
- Semantic Decision Lock。
- RFEC v0.3 semantic repair。
- Normative Encoding。
- Governance Encoding Repair。
- External Independent Audit。

这一阶段的核心思想变化是：

> “文字上写了 MUST” 不等于 “系统已经被证明能够执行 MUST”。

因此最终验收要求逐步转为：

`Normative Clause → Executable Fixture → Runtime Evidence → Independent Verification`

---

## 7. v0.8 / RM7R 之后的关键教训

历史红队审计识别出多个关键问题，包括：

- 执行证据与声明 hash 不一致。
- Traceability 指向非当前载体。
- 父版本 / migration lineage 不一致。
- Validation Profile / Execution Scope 绑定漂移。
- 202 fixture 与策略目录依赖链不闭合。
- Executor 与 expected 的一致性不足以证明规范语义正确。
- 部分 stage/reason 字段曾被实现错误地当成语义结果传播。

因此后续治理不允许“引用上一轮 PASS”作为本轮 PASS 的依据，而要求针对当前 exact bytes 做重新验证。

---

## 8. RM3C 当前规范与治理锚点

当前候选/冻结对象：

`G2-NORMATIVE-0.9-RM7R-TR02B-F03FIX-CANDIDATE`

Revision：`F03FIX-4`

Exact SHA-256：

`899f0b1b9f3619458e17be76ac43dd6e00b5397d0c12adb7b68e2479c7f51524`

该 candidate 的 bytes 在 Freeze Commit 中没有被修改；Frozen 是外部 carrier/governance state transition。

---

## 9. 关键 G2 normative anchors

- `G2-ID-055`：FinalHumanDecisionSnapshot 是人类最终决策的权威记录。
- `G2-ID-058`：最终 Human Decision 定义/继承明确 approved scope。
- `G2-ID-060`：Authorization 不得超过 approved scope。
- `G2-ID-061`：Authorization 绑定 exact approved security/account/action scope。
- `G2-ID-062`：Authorization 绑定适用 Decision/HumanDecision revisions。
- `G2-ID-063`：Authorization 生命周期：PENDING / ACTIVE / SUSPENDED / REVOKED / EXPIRED。
- `G2-ID-064`：多个 active authorization 的累计能力不得超过 approved scope；replacement 需要明确 predecessor 链。
- `G2-ID-065`：Execution / Reservation / Adjustment 不得隐式扩展 Authorization。
- `G2-ID-163`：Typed Propagation Policy；Reason labels 不得直接决定行为。
- `G2-ID-168`：S0→S7 evaluation stage precedence；后续阶段不得绕过前置失败。
- `G2-ID-181`：G2 Clause Registry 是唯一 normative carrier。
- `G2-ID-190`：Stage Observability Boundary；stage 默认 diagnostic-only，除非绑定独立版本化 output profile。
- `G2-ID-202`：ValidationProfile identity / successor / execution-scope binding；当前 obligation bearer 为 `G2-REGISTRY-AUTHORITY`。

---

## 10. RM3C 202 执行结论

当前 authorized execution universe：202 fixtures。

Exact suite SHA：

`766e6e20164e6d2280bc1b559acefb7b4dbea6b15f499440ec70feefece72edc`

Current execution receipt：

`RM3C-S7FIX-202-001`

Receipt SHA：

`4f674556f3ea6f7f8cd65ea1f8cbd1d88ce8c2d7964d7176591cd4e618c12d32`

Independent verification：

`RM3C_S7FIX_202_INDEPENDENT_VERIFICATION-v0.1`

SHA：

`29e5b20d2ebb6c7ea84d1ca341af0043cbeb2fef59901c7c5af8d95fd2d083a6`

Independent clean-room replay：

SHA：`fdb48d35d82df416065d59ce86f50cef20d853b78d969b4c187e2068a270e839`

语义匹配：`202/202`

External side effects：`NONE`

---

## 11. 63 / 16 / 21 Divergence 最终处理

### 63

初始 @1 executor 在成功 S7 compare-match 路径无条件覆盖 producer stage/reason，造成 S7 metadata override。

修复：

`RFEC-EXECUTOR-V0.9-RM3C-CANDIDATE@2`

S7 compare-match 保留 producer stage/reason；S7 compare-mismatch 才触发 `RE_EVALUATE`。

这 63 条不再构成当前 divergence。

### 16 + 21

剩余 raw stage/reason 差异被正式纳入 Output Contract / Observability Governance，而不是删除或忽略。

Output profile：

`RFEC-STAGE-OUTPUT-1@0.3`

SHA：

`970c8a36a0aaf06abde946113401344a96996d77e2397bace99fb6b9ab968e`

Normative semantic output fields：

`result / side_effect / commit_eligible / reservation_ref_unchanged`

Raw `stage / reason_code`：diagnostic-only。

因此 divergence 被保留、可审计，但不再被错误升级为 semantic equality requirement。

---

## 12. Traceability Closure

最终状态：

`CLOSED_CURRENT_EXECUTION_UNIVERSE`

- Previous unresolved declared fixture references：38
- Recanonicalized to exact current IDs：26
- Current unresolved declared fixture count：0
- Current declared fixture refs resolved：291
- Clause coverage：45
  - 30 `CLOSED_EXACT`
  - 15 `CLOSED_GOVERNANCE_EXEMPTION`
- Non-instantiated adversarial backlog：12

这 12 条不属于当前 202 execution evidence，不得被描述为“已运行验证”。它们被明确留在 regression backlog，未来需新 execution authorization 后才能进入运行证据。

---

## 13. Authority / Identity Governance Closure

历史 authorization 曾使用：

`G2-NORMATIVE-OWNER`

当前 normative bearer：

`G2-REGISTRY-AUTHORITY`

处理方案不是建立新的 role-equivalence mapping，而是重新签发 B1/B2 authorization，直接绑定当前注册 authority。

当前 successor authorization：

`G2-RM3A-PROFILE-SUCCESSOR-004`

SHA：`355a748bf745e0af92a31b1f5d73acc5505d99b799c5d09cc32cf8e1a94b55ac`

External identity verification 被定位为 security control，而不是另造一层 normative permission gate。

---

## 14. d8e3 Scope Binding provenance exception

Receipt 曾声明：

`d8e3b4daa8094fb11b40c22ccfb994ab7ec1f92da56856f3946d0302f22b4675`

该 exact bytes 未被恢复。

正式结论：

`RECEIPT_SINGLE_FIELD_METADATA_STALE`

当前可验证的 exact v0.4 Scope Binding：

`2cfa64af3f8da3e18d03604f881e77b3a483df8cb313e69d54aad6b74deb9549`

原 Receipt 保持不变；通过 metadata-only reconciliation 关闭 provenance seam；semantic impact = `NONE`；没有声称 d8e3 bytes 已恢复。

这是一项显式、不可变的 provenance exception，而不是被抹掉的历史不一致。

---

## 15. Freeze Approval → Freeze Commit → Post-Freeze Verification

Owner Approval：

`G2-RM7R-FREEZE-APPROVAL-001`

Approval SHA：

`f8fdb121f388645532f33db8a6a3f9a23aa5664cae1b450faeffa469a2973d5f`

Approval 明确绑定 exact candidate SHA `899f0b...51524`。

Freeze Approval Preflight：

SHA：`961dc01b381a7baa4f384dccc9073b269909af7097607b29426fac23229cf6db`

Status：`PASS`

Freeze Commit：

SHA：`f7de620d1a8664ff87cfb4f4b7857818eee60f5fb4b0ce4bd112e390899a32b5`

Status：`COMMITTED`

Frozen Carrier State：

SHA：`828380414903519a7461dd67a91f4d6f6ba81a2fbb9697714f9c761eef7d8e6a`

Status：`FROZEN`

Independent Post-Freeze Verification：

SHA：`bb096fe54eaf68de84999eb0fd10fa846e737d6b3493718e45b16ab63af9d006`

Status：`PASS`

Checks：`15/15`

---

## 16. 最终系统结论

当前 G2 已完成从“规范草案/候选”到“可执行验证 + 独立复核 + 显式人工批准 + Frozen Carrier”的完整闭环。

最终可形成以下明确判断：

1. 当前 Frozen 对象有 exact candidate bytes、exact approval、exact commit、exact post-freeze verification。
2. Candidate bytes 在 Freeze Commit 中没有被修改，因此批准对象与冻结对象保持同一 exact SHA。
3. 当前 202-fixture execution semantics 为 202/202，external side effects 为 NONE，且有独立 verification / clean-room replay 支撑。
4. Traceability 当前 execution universe 已闭合；未实例化 adversarial backlog 被显式隔离，没有被伪装成 tested evidence。
5. Output stage/reason divergence 已通过规范化 Observability Contract 完成治理，而没有修改 expected semantic values。
6. Authority seam 已通过直接 reissue 到 `G2-REGISTRY-AUTHORITY` 关闭，没有建立 shadow role mapping。
7. d8e3 scope hash 的 exact bytes 未恢复这一事实被永久保留并显式 reconciliation，不能在后续上下文中被“压缩掉”。

---

## 17. 当前 Frozen 的演进规则

Frozen 不是允许“原地修改”的开发分支。

正确的后续路径只能是：

`FROZEN → Successor Candidate → Validation / Traceability / Execution as applicable → Fresh Verification → Explicit Human Approval → New Freeze Commit → Next FROZEN`

当前 Freeze 不产生任何 future execution、future successor 或 future authorization 的隐式权限。

---

## 18. 本地留档主文件

最权威的当前完整结果包：

`source/05_G2_V09_RM3C/RM3C_FINAL_FROZEN_CARRIER_v0_1.zip`

其 SHA-256：

`bd5cbaf23c9029b46fafd19992029932431059de7424a08de48624aca5d431c8`

同时提供 extracted browsing copy：

`06_FINAL_FROZEN_CARRIER_EXTRACTED/`

上下文恢复快照：

`00_CURRENT/IIOS_G2_CURRENT_STATE_SNAPSHOT_2026-09-30_v0_1.md`

`00_CURRENT/IIOS_G2_CURRENT_STATE_SNAPSHOT_2026-09-30_v0_1.json`

---

## 19. 证据优先级

后续任何争议按以下顺序解释：

`Frozen exact artifact / current manifest → current verification evidence → current authorized execution evidence → historical source artifacts → narrative summaries`

摘要、旧审计结论、旧状态报告都不能覆盖当前 exact bytes。
