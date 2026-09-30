# IIOS G2 Current State Snapshot

**Snapshot date:** 2026-09-30  
**Purpose:** compact context-restore record. Use this snapshot before reading historical conversation. The full audit/package remains the evidence source; this file is a navigation/state summary, not a replacement for exact artifacts.

## 1. Current phase / canonical state

G2 normative governance/execution validation has completed Freeze Approval and Freeze Commit.

**Current carrier status: `FROZEN`**

Frozen object:
- Registry ID: `G2-NORMATIVE-0.9-RM7R-TR02B-F03FIX-CANDIDATE`
- Revision: `F03FIX-4`
- Approved candidate SHA-256: `899f0b1b9f3619458e17be76ac43dd6e00b5397d0c12adb7b68e2479c7f51524`
- Frozen artifact SHA-256: same as candidate (`899f0b...51524`)
- Candidate bytes were **not modified** during freeze.
- Freeze is an external governance/carrier state transition over exact candidate bytes.

## 2. Freeze chain completed

`CANDIDATE_NOT_FROZEN`
→ explicit owner approval
→ Freeze Approval Preflight PASS
→ Freeze Commit COMMITTED
→ Independent Post-Freeze Verification PASS
→ `FROZEN`

Freeze Approval:
- ID: `G2-RM7R-FREEZE-APPROVAL-001`
- SHA-256: `f8fdb121f388645532f33db8a6a3f9a23aa5664cae1b450faeffa469a2973d5f`
- Action: `FREEZE_EXACT_CANDIDATE`
- Source: explicit current-user directive in controlled session

Freeze Preflight v0.2:
- SHA-256: `961dc01b381a7baa4f384dccc9073b269909af7097607b29426fac23229cf6db`
- Status: `PASS`

Freeze Commit:
- SHA-256: `f7de620d1a8664ff87cfb4f4b7857818eee60f5fb4b0ce4bd112e390899a32b5`
- Status: `COMMITTED`

Frozen Carrier State v0.3:
- SHA-256: `828380414903519a7461dd67a91f4d6f6ba81a2fbb9697714f9c761eef7d8e6a`
- Status: `FROZEN`

Independent Post-Freeze Verification:
- SHA-256: `bb096fe54eaf68de84999eb0fd10fa846e737d6b3493718e45b16ab63af9d006`
- Status: `PASS`
- Checks: `15/15`

## 3. Evidence chain that is current

Current 202 execution receipt:
- ID: `RM3C-S7FIX-202-001`
- SHA-256: `4f674556f3ea6f7f8cd65ea1f8cbd1d88ce8c2d7964d7176591cd4e618c12d32`

Independent verification:
- ID: `RM3C_S7FIX_202_INDEPENDENT_VERIFICATION-v0.1`
- SHA-256: `29e5b20d2ebb6c7ea84d1ca341af0043cbeb2fef59901c7c5af8d95fd2d083a6`

Independent clean-room replay:
- SHA-256: `fdb48d35d82df416065d59ce86f50cef20d853b78d969b4c187e2068a270e839`
- Semantic match: `202/202`

Current execution scope binding:
- Artifact: `PROFILE_EXECUTION_SCOPE_BINDING_v0_4.json`
- Current exact SHA: `2cfa64af3f8da3e18d03604f881e77b3a483df8cb313e69d54aad6b74deb9549`

Current exact execution suite:
- `RFEC_G2_v0_8_Canonical_Fixtures_v0_3_Repaired.json`
- SHA-256: `766e6e20164e6d2280bc1b559acefb7b4dbea6b15f499440ec70feefece72edc`
- Fixture count: `202`

## 4. Important provenance exception: d8e3...

Historical/current execution receipt contains a scope field declaring:
`d8e3b4daa8094fb11b40c22ccfb994ab7ec1f92da56856f3946d0302f22b4675`

Exact bytes for `d8e3...` were **not recovered** from active runtime or available historical archives.

Do NOT claim the `d8e3...` bytes were recovered.

Formal handling:
- Recovery result: `NOT_RECOVERED`
- Current exact v0.4 scope binding: `2cfa64af...deb9549`
- Reconciliation classification: `RECEIPT_SINGLE_FIELD_METADATA_STALE`
- Original receipt preserved unchanged.
- Current v0.4 scope, contemporaneous rerun manifest, and approved candidate lineage all agree on `2cfa...`.
- Reconciliation status: `CLOSED_METADATA_PROVENANCE_RECONCILIATION`
- Semantic impact: `NONE`
- Execution replay required: `false`

This exception is explicit and immutable in the frozen evidence chain.

## 5. 202 execution / divergence closure

Initial executor `@1` run had semantic equality 202/202 but raw stage/reason divergences.

Critical 63-row defect:
- Successful S7 compare-match path overwrote producer stage/reason metadata.
- Fixed in executor `RFEC-EXECUTOR-V0.9-RM3C-CANDIDATE@2`.
- S7 metadata override rows eliminated.

Remaining raw stage/reason differences are governed as **diagnostic-only observability differences**, not semantic differences, under:
- `G2-ID-163`: reason labels MUST NOT directly determine behavior.
- `G2-ID-168`: semantic stage precedence.
- `G2-ID-190`: stage labels diagnostic unless a separately versioned stage-output profile is normatively bound.

Output Contract Closure:
- Profile: `RFEC-STAGE-OUTPUT-1@0.3`
- SHA-256: `970c8a36a0aaf06abde946113401344a96996d77e2397bace99fb6b9ab968e`
- Normatively bound candidate observability contract.
- Exact semantic output fields: `result`, `side_effect`, `commit_eligible`, `reservation_ref_unchanged`.
- Raw `stage` / `reason_code` are diagnostic-only.
- No expected-value rewrite; no semantic rule change.

## 6. Traceability closure

Traceability status: `CLOSED_CURRENT_EXECUTION_UNIVERSE`

- Previous unresolved declared fixture refs: `38`
- Recanonicalized to exact current IDs: `26`
- Remaining non-instantiated adversarial backlog: `12`
- Current unresolved declared fixture count: `0`
- Clause coverage: `45` clauses total
  - `30 CLOSED_EXACT`
  - `15 CLOSED_GOVERNANCE_EXEMPTION`
- Backlog remains explicitly outside current freeze evidence; it is NOT runtime evidence.

Backlog families (not currently authorized/tested):
- G2-ID-197: `PS-AUTHORITY-AMBIGUOUS`, `PS-BOTH-ONE-MISSING`
- G2-ID-198: `HPOL-UNAVAILABLE`, `HPOL-LATEST-FALLBACK`
- G2-ID-199: `CONC-SAME-MEMBERS-DIFF-REVISION`
- G2-ID-200: `HIST-MISSING-EXACT`, `HIST-MISSING-POLICY`, `HIST-MISSING-CUT`
- G2-ID-201: `REEVAL-MISSING-CURRENT`, `REEVAL-VALID-ALLOW`, `REEVAL-VALID-BLOCK`, `REEVAL-DIAGNOSTIC-POLLUTION`

## 7. Governance seams already resolved — do not reopen without new evidence

### Authority / role seam
Old authorizations used `G2-NORMATIVE-OWNER`; current normative bearer is `G2-REGISTRY-AUTHORITY` (per G2-ID-202). New B1/B2 authorizations were reissued using `G2-REGISTRY-AUTHORITY`.

Current successor authorization:
- ID: `G2-RM3A-PROFILE-SUCCESSOR-004`
- SHA-256: `355a748bf745e0af92a31b1f5d73acc5505d99b799c5d09cc32cf8e1a94b55ac`

Current execution authorization used for the fresh execution:
- Current artifact in freeze package: `G2_RM3C_PROFILE_EXECUTION_AUTHORIZATION_v0_3.json`
- Freeze-chain evidence continues to bind the authorized execution to the current scope/profile lineage.

External identity verification remains a **security control**, not a shadow normative permission gate.

### Historical evidence
Old RM2B execution and older RM4/RM6 evidence are historical only. Do not rebind them as current execution evidence.

## 8. Core normative anchors to remember

- `G2-ID-055`: `FinalHumanDecisionSnapshot` authoritative human decision record.
- `G2-ID-058`: final human decision defines/inherits explicit approved scope.
- `G2-ID-060`: Authorization MUST NOT exceed FinalHumanDecision approved scope.
- `G2-ID-061`: Authorization binds exact approved security/account/action scope.
- `G2-ID-062`: Authorization references applicable Decision/HumanDecision revisions.
- `G2-ID-063`: authorization lifecycle `PENDING/ACTIVE/SUSPENDED/REVOKED/EXPIRED`.
- `G2-ID-064`: cumulative active authorizations cannot exceed approved scope; replacement semantics explicit.
- `G2-ID-065`: execution/reservation/adjustment cannot implicitly expand Authorization.
- `G2-ID-163`: typed propagation; reason labels cannot directly determine behavior.
- `G2-ID-168`: evaluation stage precedence S0→S7; later stage cannot bypass earlier failure.
- `G2-ID-181`: G2 Clause Registry is the sole normative carrier.
- `G2-ID-190`: stage observability boundary.
- `G2-ID-202`: ValidationProfile identity/successor/execution-scope binding; obligation bearer `G2-REGISTRY-AUTHORITY`.

## 9. Freeze invariant / future change rule

Current Frozen artifact is immutable.

Future normative changes MUST NOT edit frozen bytes in place. Correct evolution path:

`FROZEN`
→ `Successor Candidate`
→ validation / traceability / execution as applicable
→ fresh verification
→ explicit human approval
→ new freeze commit
→ next `FROZEN` revision.

No implicit future-successor authority is created by current Freeze Approval.
No future 212 execution is authorized by this freeze.

## 10. Package / artifact locations

Primary final package:
`/mnt/data/RM3C_FINAL_FROZEN_CARRIER_v0_1.zip`

ZIP SHA-256:
`bd5cbaf23c9029b46fafd19992029932431059de7424a08de48624aca5d431c8`

Inside the package, the most important paths are:
- `03_CANDIDATE/G2_NORMATIVE_0_9_RM7R_TR02B_F03FIX_CANDIDATE_v4.json`
- `08_FINAL_FREEZE/01_RECOVERY/G2_SCOPE_BINDING_EXACT_RECOVERY_v0_1.json`
- `08_FINAL_FREEZE/02_RECONCILIATION/G2_EXECUTION_SCOPE_AND_SUITE_RECONCILIATION_v0_1.json`
- `08_FINAL_FREEZE/03_PREFLIGHT/G2_FREEZE_APPROVAL_PREFLIGHT_v0_2.json`
- `08_FINAL_FREEZE/04_COMMIT/G2_FREEZE_COMMIT_v0_1.json`
- `08_FINAL_FREEZE/04_COMMIT/G2_FROZEN_CARRIER_STATE_v0_3.json`
- `08_FINAL_FREEZE/05_POST_VERIFICATION/G2_INDEPENDENT_POST_FREEZE_VERIFICATION_v0_1.json`
- `08_FINAL_FREEZE/06_SNAPSHOT/G2_NORMATIVE_0_9_RM7R_TR02B_F03FIX_FROZEN_ARTIFACT.json`
- `08_FINAL_FREEZE/06_SNAPSHOT/G2_FINAL_FROZEN_CARRIER_MANIFEST_v0_3.json`

## 11. How to resume work efficiently

Start from THIS SNAPSHOT.

Default assumption: the frozen G2 state above is authoritative for context restoration.
Read the full package only when the next task needs exact field-level evidence, executable bytes, or an audit artifact.

Do not re-run/redo:
- identity reconciliation already closed,
- authority-role mapping seam already resolved,
- 63 S7 metadata bug root-cause analysis already closed,
- output-contract closure already completed,
- current 202 execution semantic closure,
- current traceability closure,
- Freeze Approval itself.

Instead, branch from the Frozen state for the next authorized phase.
