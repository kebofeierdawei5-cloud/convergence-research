# B82 — Current-main Pilot Operability Audit

**Date:** 2026-11-08  
**Status:** SOURCE / WORKFLOW AUDIT COMPLETE; LOCAL MAC ACCEPTANCE NOT RUN  
**Audited canonical baseline:** main @ 2fd009b10bd4b13467ebdd8b2692eab62a772878  
**Main state index snapshot:** 2026-10-25  
**Audit branch:** docs/iios-operability-roadmap-20261108  
**Scope:** Existing personal local Pilot entry, input, two-round ChatGPT handoff, import, validation, persistence, recovery, Replay and environment dependencies.

## 1. Executive conclusion

The current canonical-main Pilot is more complete than a superficial workflow review would suggest. It already has a guided command-line entry, a price-blind Round A and price-aware Round B, compact response-patch parsing, operator-field protection, stable-file detection, repair prompts, private local storage, SHA-256-bound run receipts and Replay comparison.

Therefore, the next work should **not** rebuild the guided input surface, create a new desktop application, or automate the ChatGPT browser. The actual deficiencies are narrower and more consequential:

1. **No durable stage-resume entry point.** A/B work files are preserved, but the CLI has no resume-task mode. If the Python process exits or the machine restarts while waiting for a response, the operator has no supported command to reopen the same task at the last valid stage. The user can be forced to re-enter the company, price and cutoff, and may have to repeat an already completed Web round.
2. **Clipboard remains a critical path dependency.** The macOS wizard calls pbcopy with check=true and a five-second timeout for both prompts. A clipboard command failure aborts the flow instead of degrading to a visible prompt file/manual copy. Browser and TextEdit open calls are best-effort, but the workflow does not expose a consistent fallback state.
3. **Official evidence preparation is not automated in the current Pilot.** The template initializes evidence_register as an empty list and asks ChatGPT Web to search public material. The local wizard does not retrieve and archive the underlying official filings as source bytes. URL presence, a source-class label or a valid response shape is not equivalent to original-source verification or formal Evidence/PIT admission.
4. **User guidance is inconsistent.** README still points the ordinary user to the 2026-10-11 short guide, whose instructions describe the earlier single-response handoff. The actual main workflow and the 2026-10-21 acceptance runbook use separate Round A and Round B responses.
5. **The canonical current-main real-Mac acceptance is still open.** The main state index records B34 as the next user-Mac two-round full-run plus independent Replay gate. CI and code inspection do not close it.

The product architecture should remain a local deterministic runner plus a small number of deliberate ChatGPT Web interactions. Remove fragile mechanics around those interactions; do not replace them with browser robotics.

## 2. Repository and authority snapshot

### Canonical main

- Current main SHA resolved in this audit: 2fd009b10bd4b13467ebdd8b2692eab62a772878.
- docs/PROJECT_STATE_INDEX.md identifies itself as the sole canonical current-state index and records B33 / PR #585 as merged.
- The index reports B33's exact tested head passed 350 Local Investment Pilot + Replay/acceptance tests and 6/6 triggered workflows. It also explicitly leaves current-main real macOS two-round full-run and independent Replay OPEN / NOT VERIFIED.
- The same index identifies B34 — real Mac current-main two-round full-run + independent Replay — as the next acceptance gate.
- README and the current local Pilot source identify the user workflow as PILOT_NON_CANONICAL. Its output is not formal Evidence/PIT, Forecast, Valuation or canonical Decision admission and creates no execution authority.

### B73–B81 proposal chain / PR #587

- PR #587 was re-fetched during B82: **Open / Draft / Unmerged**, base `feat/b73-evidence-driven-remediation-20261031` at `faeee544238dd4b6154e2b0a7a4a53c8a88a6815`, head `feat/b76-core-integrated-20261101` at `d092355aba29476624925c15d82a42d9b1f30354`; GitHub reports `merged=false`. Its own body says validation-only and explicitly says do not merge the proposal chain as a whole.
- Comparing the proposal head with current `main@2fd009b10bd4b13467ebdd8b2692eab62a772878` reports 515 commits ahead, 0 behind. The 515 is branch ancestry/delta, not 515 commits uniquely authored by PR #587. The compare lists a broad cross-cutting change set, not a safe single-batch integration unit.
- Its changed-file list includes B42–B81 research documents and modules, the Pilot source, authority/runtime code, schemas and tests. It is materially broader than an operability-only patch.
- B74 and B75 documents on that branch explicitly state their regression assertions were added but not executed, and no Replay, CI or real Mac acceptance is claimed for those batches.
- The B79 document says the production signer registry remains empty and the Xinhecheng case still lacks Q4 assumptions, annual weighted-average diluted shares and operator-attested current price.
- The B81 document reports hosted-runner remediation and selected Pilot tests. It also explicitly says headless GitHub macOS CI does not prove the user's Finder, browser, TextEdit, clipboard or actual two-round Replay behavior.
- No B42–B81 research capability should be described as canonical-main user functionality until selectively reviewed, integrated and accepted.

References:
- Canonical state index: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/docs/PROJECT_STATE_INDEX.md
- Main README: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/README.md
- PR #587: https://github.com/kebofeierdawei5-cloud/convergence-research/pull/587
- Proposal-branch B74: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/feat/b76-core-integrated-20261101/docs/iios/B74_CORE_CONTRADICTION_RESEARCH_20261101.md
- Proposal-branch B75: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/feat/b76-core-integrated-20261101/docs/iios/B75_EVENT_DRIVEN_EARNINGS_BRIDGE_20261101.md
- Proposal-branch B79: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/feat/b76-core-integrated-20261101/docs/iios/B79_SOURCE_TRUST_AND_FORECAST_ADMISSION_20261106.md
- Proposal-branch B81: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/feat/b76-core-integrated-20261101/docs/iios/B81_MACOS_RUNNER_IMAGE_RETIREMENT_FIX_20261107.md

## 3. Actual canonical-main user workflow

The following is a source-level reconstruction from main's README, launcher, Pilot Python module and macOS acceptance runbook. It is not a claim that this audit executed the workflow on a Mac.

### A. Launch and environment

1. The daily entry is the repository-root shell launcher 启动IIOS投资分析.command.
2. It checks that python3 exists and is version 3.10 or later, sets PYTHONPATH to the repository root, then runs the module in --wizard mode.
3. It does not bootstrap Python, pin the exact interpreter version, install dependencies, or update the local repository. README therefore tells the operator to update the repository to current main before launch.
4. There is a separate packaged acceptance launcher, IIOS_一键启用并验收.command. The macOS runbook recommends a successful GitHub Actions artifact, double extraction, and this launcher to obtain a verified private source copy and run first-run + Replay acceptance. This is an acceptance distribution path, not the same as the ordinary repository-root daily launcher.

Sources:
- Launcher: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/%E5%90%AF%E5%8A%A8IIOS%E6%8A%95%E8%B5%84%E5%88%86%E6%9E%90.command
- Pilot entry: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/iios_mvp/local_investment_pilot_v01.py
- Current-main Mac runbook: https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/docs/iios/MACOS_REAL_E2E_ACCEPTANCE_RUNBOOK_20261021.md

### B. Guided human inputs

The current wizard requests:
- company name and security code;
- A-share or Hong Kong market;
- analysis cutoff date and cutoff semantics;
- current position percentage;
- operator-checked price;
- price observation date and price-known time;
- confirmation of the combined case/price/cutoff/position values.

The common cutoff path uses defaults; the user still owns the price, its observation time and the accuracy of the entered company/case details. The input is not an exchange-verified live quote. The wizard labels the price OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED.

After the two research rounds, the operator also enters optional portfolio/risk context and independently chooses the primary valuation model. These are legitimate human-authority fields and must not be auto-authored by the LLM.

### C. Round A — price-blind company-side research

1. The local template is generated and stored beneath ~/.iios-private/local-pilot/inputs.
2. The Round A allowlist includes company identity, cutoff, evidence register and company-side research fields. The prompt excludes structured current price, current position, operator valuation context, MIE and expectation gap.
3. The wizard writes a dedicated Round A prompt and response file, copies the prompt to the macOS clipboard, opens ChatGPT and opens the response file in TextEdit.
4. The user sends the prompt in ChatGPT Web, copies one compact response object and saves it to the Round A response file.
5. The local process waits for a non-empty file whose size/mtime/SHA-256 signature remains stable, then validates the phase envelope and allowed fields.
6. On success, the company-side Round A artifact is frozen and hashed. The prompt/response lineage and frozen-artifact summary are retained in the local task/input provenance.

### D. Round B — price-aware valuation and expectation gap

1. Only after Round A validates does the wizard generate the Round B prompt using the protected price-bearing template and the frozen Round A artifact.
2. It copies the Round B prompt to the clipboard and opens a separate Round B response file.
3. The user sends the second request in ChatGPT Web and saves one compact response object.
4. Local code checks the Round B field allowlist and protects the frozen Round A fields. It restores operator-controlled fields from the trusted template, performs full input/research validation, then asks for portfolio and model-selection context.
5. The local runner produces the analysis, Chinese report and receipt. Run files and responses are stored under the private ~/.iios-private tree with restrictive POSIX modes. The receipt binds the exact input, analysis and report bytes; the Round B raw response is also captured and hash-bound. Round A prompt/response provenance is embedded in the private input lineage.
6. The daily wizard ends with its analysis/report. Separate CLI and acceptance-wrapper paths perform bundle verification and true Replay. The packaged acceptance runbook includes first-run verification, Replay, Replay verification and private audit packaging.

### E. Recovery already present

Reuse these existing controls rather than rebuilding them:
- dedicated Round A and Round B response files;
- stable-file detection based on size, modification time and SHA-256;
- Enter-triggered file selection when the response was saved elsewhere;
- strict response parsing and phase-specific patch allowlists;
- compact repair prompt generation on validation errors;
- restoration of operator-owned case, price, valuation-context and policy fields from the local template;
- frozen Round A artifact and phase provenance;
- private run bundles, receipts, SHA-256 manifests and Replay field comparison.

## 4. Capability reuse / gap matrix

| Capability | Current-main finding | Decision |
|---|---|---|
| Guided entry | Exists as CLI wizard; already asks for case, cutoff, position and price | Reuse; no parallel UI |
| Input template | Generated locally with typed defaults and explicit UNKNOWN values | Reuse; add task identity/version binding only where necessary |
| Price-blind Round A | Exists with input allowlist and separate response file | Reuse |
| Price-aware Round B | Exists after Round A freeze, with phase allowlist | Reuse |
| Response parser | Handles one JSON response object, supported legacy shape, bounded repairs and trailing-content rejection | Reuse |
| File import | Stable-save detection and alternate file picker exist | Reuse; harden only evidenced defects |
| Operator authority | Trusted local template restores operator-owned fields | Preserve; no LLM control |
| Private storage | ~/.iios-private, restrictive directory/file permissions | Reuse |
| Provenance and replay | Run receipt/hash manifest and true Replay comparison exist | Reuse |
| Process-stage resume | No --resume-task mode or durable cross-process stage transition contract found | Build |
| Clipboard fallback | pbcopy is called with check=true and timeout=5 for Round A/B prompts | Fix; clipboard must be optional |
| GUI open failure | Browser/TextEdit opening is best-effort, but not represented as an explicit fallback state | Improve only as part of simple handoff reliability |
| Official filing retrieval | Prompt asks ChatGPT Web to search; the local template begins with an empty evidence register | Build narrow official-source intake later |
| Formal source admission | Current Pilot is PILOT_NON_CANONICAL; URL/source labels are not formal source admission | Preserve boundary; do not claim formal admission |
| User Mac acceptance | B34 remains OPEN / NOT VERIFIED in canonical state | Must perform on user's Mac |
| User instructions | 2026-10-11 short guide describes the earlier single-response path; 2026-10-21 runbook contains the two-round flow | Consolidate and clearly mark superseded guide |

## 5. Manual-operation inventory

The current workflow retains deliberate human judgment and external Web interaction. The following should not be counted as defects by themselves:
- entering the company/cutoff/price facts that only the operator can attest;
- sending Round A and Round B in ChatGPT Web;
- reviewing the required portfolio and valuation-model context;
- deciding how to interpret incomplete evidence and whether to proceed.

The following are mechanical steps and should be reduced:
- manually maintaining/updating the local source checkout before using the simple root launcher;
- relying on clipboard success for prompt handoff;
- saving two large responses into two separate files and manually keeping the files/rounds straight;
- re-entering an entire task after process interruption;
- manually finding official filings and keeping source artifacts organised when the same company is researched repeatedly;
- reconciling old short-guide instructions with the current runbook.

No hands-on minutes, completion-rate or actual Mac failure-rate baseline was measured in this source audit. Do not invent those metrics. They must be measured during the next operator-run baseline.

## 6. Failure register and root-cause hypotheses

| ID | Priority | Trigger / symptom | Verified current condition | Containment or fix |
|---|---|---|---|---|
| F82-01 | P1 | Process/window closes during Round A/B wait; operator must restart | CLI has wizard/template/input/replay/check modes but no resume-task mode. Stage files exist, but no supported state loader resumes the same task | B83: durable task manifest, immutable stage files, hash-verified resume |
| F82-02 | P1 | Clipboard tool unavailable, permission denied or times out | Round A/B use pbcopy with check=true and five-second timeout; failure propagates | B85: clipboard best-effort only; prompt file + clear manual-copy fallback |
| F82-03 | P1 | No original public filing bytes in the research record | Local template starts evidence_register=[] and delegates public-source search to ChatGPT Web | B86: bounded official disclosure retrieval, original-byte archive, URL/date/hash/parser metadata and manual fallback |
| F82-04 | P1 | Cannot prove user-facing operation is reliable on actual Mac | Canonical B34 gate remains OPEN / NOT VERIFIED | Close baseline acceptance on user's Mac; retain private first-run and Replay bundle |
| F82-05 | P2 | User follows old single-round guide and selects wrong file / expects wrong handoff | README links the 2026-10-11 guide; main code/runbook now use two rounds | Update README and short guide to point to one current procedure; clearly label old guide superseded |
| F82-06 | P2 | User does not know if browser or TextEdit failed to open | open calls are best-effort and flow continues; clipboard call may be fatal | Provide explicit visible state and manual open/copy steps without blocking the rest of the task |
| F82-07 | P2 | User launches stale local code | Root launcher executes the checkout in place; README requires updating to current main first | B84: a single clear supported daily launch/update path and preflight version display |
| F82-08 | P2 | Waiting appears hung | Response watcher intentionally waits indefinitely; Ctrl-C exits and Enter can trigger selection/recheck | Add heartbeat/status and resume instructions; do not add a short timeout that interrupts long research |
| F82-09 | P2 | Operator confuses daily run with acceptance Replay | Root wizard and packaged full acceptance are separate entry paths | Label daily research versus full acceptance explicitly; keep Replay available and required at acceptance gates |

### Root-cause assessment

The current Pilot is a guided serial process, not a durable task orchestrator. Local files preserve useful artifacts, but no task-level stage machine owns them across process restarts. The clipboard is treated as a required transport even though the prompt already exists as a durable file. Research source acquisition is still entrusted to the external Web session rather than a local source-evidence preparation stage. Documentation did not stay synchronised with B33.

These are bounded workflow design gaps. They do not justify a broad rewrite of the valuation engine, a new LLM layer, a desktop GUI framework or browser automation.

## 7. Minimal target architecture

Reuse the current wizard, template, response parser, protected-field restoration, runner, receipt, private storage and Replay. Add only a small durable task/workspace controller.

### Workspace

One task directory per analysis beneath the existing private local-pilot root. It should contain:
- immutable task-input snapshot and versioned task manifest;
- Round A prompt, raw response and validated/frozen company artifact;
- Round B prompt, raw response and validated merged input;
- generated analysis, report and run receipt;
- stage-transition log and SHA-256 manifest.

Directory permissions remain owner-only (0700); private files remain owner-only (0600) where supported. Previous valid files must never be silently overwritten. New response attempts should create versioned candidates or explicit revisions.

### Stage state

Use a small deterministic state machine, not a new orchestration framework. Minimum states:
- TASK_INPUT_READY
- ROUND_A_PROMPT_READY
- ROUND_A_RESPONSE_CAPTURED
- ROUND_A_VALIDATED
- ROUND_A_FROZEN
- ROUND_B_PROMPT_READY
- ROUND_B_RESPONSE_CAPTURED
- ROUND_B_VALIDATED
- RUN_WRITTEN
- REPLAY_VERIFIED

Every transition records timestamp, task ID, stage, exact artifact path, schema/prompt version and SHA-256. Only deterministic local code advances state. LLM output may be data for validation; it must not write task state.

### Resume semantics

A resume command must:
1. load the existing task manifest;
2. validate its schema and all recorded hashes;
3. identify the last complete valid stage;
4. continue from the next incomplete stage without regenerating or overwriting completed work;
5. ask the user for another Web response only when the current stage genuinely lacks a valid response;
6. fail closed on tampering, a mismatched cutoff/schema/prompt or corrupted artifact.

Do not attempt automatic browser session recovery. The user still chooses when and how to send each prompt in ChatGPT Web.

## 8. Revised B83–B89 execution plan

### B83 — Durable task workspace, stage manifest and resume

Build the smallest possible task-state layer on top of the existing local Pilot. Do not create another input interface or duplicate the research pipeline.

Deliver: stable task ID, isolated private workspace, immutable prompt/response/frozen artifacts, stage manifest, append-only transition record, hash verification and a resume-task command.

Exit: simulated interruption after each stage resumes the same task without repeating completed Web work or re-entering protected operator inputs; tampered/missing artifacts block safely; prior valid data remains unchanged.

### B84 — One supported launch path and runtime preflight

Retain the existing Python Pilot. Decide and document one normal daily launch/update path, separately from the full acceptance launcher. Preflight should show the source SHA, Python version, required paths, workspace permissions and dependency readiness before asking the user for case inputs. Do not introduce package installation or a new desktop framework unless inspection proves it necessary.

Exit: a clean supported Mac can start using one documented path; stale source or unsupported runtime is caught before research begins; routine use does not require Git commands, chmod, venv activation or manual dependency installation.

### B85 — Round A/B handoff resilience

Reuse the two-round prompt builders and patch validator. Make clipboard copy best-effort; always preserve and reveal the exact prompt file. Make browser/TextEdit opening best-effort with visible fallback instructions. Retain the dedicated response files, stable-save detection, file chooser and concise repair prompt. Wire the handoff to B83 resume states. Update README and the short guide to agree with the current two-round runbook.

Exit: clipboard failure does not terminate a task; user can manually open/copy/save; one valid import per round; failed import preserves raw bytes and prior valid state; restart resumes the same round.

### B86 — Narrow official evidence preparation

Start with official company/exchange/regulator disclosure sources and only the document classes needed by a selected company task. Preserve original bytes, source URL/institution, publication date, reporting period, retrieval time, SHA-256, extraction/parser version and manual-review state. A failed fetch must yield an explicit manual-download path and UNKNOWN where content is unavailable.

No full-market warehouse, paid APIs, reverse-engineered fragile quote APIs or automatic trust promotion.

Exit: a selected company's required official documents can be retrieved or manually supplied into one versioned evidence pack; every extracted claim points to the original artifact and source location where possible; no successful PDF parse is treated as truth.

### B87 — New-research real-company acceptance

Test the new B73–B81 research path independently from the already accepted historical decision core. Use a data-sufficient EPS_MULTIPLE company and a separate SOTP company; Xinhecheng can remain an UNKNOWN/blocked case when its source gaps persist. Compare old/current-main and candidate-new outputs on the same cutoff, evidence pack and price input. Review primary contradiction, future event chain, operating assumptions, attributable earnings, diluted EPS, valuation transmission, price-implied requirements and decision changes.

Exit: every material difference is traceable to source evidence or a disclosed analyst assumption; unknowns remain unknown; no arithmetic or source-admission contradiction; independent red-team accepts the comparison. A positive investment decision is not a required outcome.

### B88 — Selective integration and release

Integrate only the modules/contracts that passed B87, using a fresh branch from current main and small reviewable PRs. Do not merge PR #587 as a whole or fast-forward the B73 proposal ancestry into main. Preserve formal authority, no-auto-execution and all fail-closed semantics.

Exit: every merged change has narrow regression tests, exact-head CI, state-index update and rollback/recovery instructions; rejected or still-unverified proposal modules remain outside main.

### B89 — Actual operator-Mac acceptance

Run the supported installer/launcher and full two-round workflow on the user's Mac. Complete first run, original-response capture, private bundle verification, true Replay and Replay-bundle verification. Review the actual files and report, not only the success banner.

Exit: two-round workflow completes without routine technical intervention; all stage hashes/receipts bind; Replay is MATCH; report and JSON are consistent; failures are recoverable; no formal authority or execution permissions are accidentally created.

### Existing B34 gate — do not skip

B34 on canonical main remains the baseline acceptance of the already-merged B33 two-round workflow. It is not closed by this B82 source audit, by B81 hosted macOS CI, or by a future B89 run of modified code. Keep its status OPEN / NOT VERIFIED until a genuine current-main user-Mac run and Replay bundle are reviewed.

## 9. Baseline metrics and verification discipline

This audit measured implementation facts, not user time. During the first operator-run baseline, record:
- elapsed time and hands-on minutes;
- manual field entries and deliberate Web sends/saves;
- failures by stage and exact error;
- whether the operator had to repeat any completed stage;
- time to recover from a failed save/import or process interruption;
- source-pack completion and unresolved source items;
- first-run and Replay result.

Do not claim improvements without before/after observations from comparable cases.

Verification status for this B82 audit:
- GitHub source and document inspection: DONE.
- Current-main workflow reconstruction: DONE at source level.
- Current PR #587 changed-file inventory and proposal-branch docs reviewed: DONE.
- Local Python tests executed in this audit: NOT RUN.
- User's own macOS GUI/browser/clipboard workflow executed: NOT RUN.
- Current-main B34 acceptance: OPEN / NOT VERIFIED.
- Any runtime code changed by B82: NO.

## 10. B82 decision

B82 is complete as a source-level audit and architecture decision. Reuse the current guided wizard and two-round pipeline. Build stage-persistent task resumption before cosmetic UI simplification; make clipboard optional; add narrow official evidence packaging; keep research-value acceptance separate from operational acceptance.

No runtime code was changed in B82. The next implementation batch is B83: durable task workspace, stage manifest and resume.