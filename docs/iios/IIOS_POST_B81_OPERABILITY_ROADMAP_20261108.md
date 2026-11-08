# IIOS Post-B81 Operability and Real-Use Acceptance Roadmap

**Date:** 2026-11-08  
**Status:** B82 source/workflow audit complete; local Mac acceptance remains open  
**Branch:** `docs/iios-operability-roadmap-20261108`  
**Scope:** Personal-investor workflow reliability, low manual operation, low environment dependence, and real-case acceptance.

## 1. Executive decision

Pause expansion of investment-research features. Prioritize making the existing IIOS research workflow reliably usable by an individual investor without requiring routine developer skills.

The objective is not merely fewer clicks or a new launcher. It is:

> Without purchasing commercial data APIs or weakening evidence and investment controls, enable a personal investor to complete a real-company research and decision workflow with minimal technical operation, low failure probability, recoverable execution, and auditable outputs.

Two acceptance dimensions must remain separate:

1. **Operational acceptance:** Can the user complete the workflow reliably with little technical intervention?
2. **Research-value acceptance:** Do the newer research capabilities materially improve identification of the main business contradiction, earnings path, per-share value transmission, price-implied expectations, and decision quality?

Passing one does not imply passing the other.

**B82 audit outcome (2026-11-08):** the canonical-main Pilot already has the guided CLI, two-round Web handoff, patch validation, protected operator-field restoration, private persistence, hash receipts and Replay. The next engineering gap is durable cross-process stage resumption, not a second input UI. See [B82 current-main Pilot operability audit](B82_CURRENT_MAIN_PILOT_OPERABILITY_AUDIT_20261108.md). Audited main SHA: `2fd009b10bd4b13467ebdd8b2692eab62a772878`. The audit was source-level only; no local tests or user-Mac workflow were run.

## 2. Known project context and cautions

The following combines prior context with the source-level B82 audit. B82 is not a local execution or Mac acceptance:

- The original decision core has prior accepted real-company cases for CATL (300750) and Kolon Pharma (002422). These historical acceptances should not be confused with validation of later B42-B81 research additions.
- B42-B81 added or developed research capabilities, but the complete newer workflow has not yet been accepted through end-to-end real-company cases.
- PR #587 was previously reported as Draft/Open/Unmerged and based on a B73 proposal branch. Do not merge the entire proposal chain as one unit.
- B81 reportedly updated the macOS hosted runner to macOS 15 and passed 466 selected tests. Hosted CI does not replace acceptance on the user's own Mac.
- B74/B75 regression assertions were reported as drafted but not fully run.
- The new research workflow still needs real-case acceptance, including EPS_MULTIPLE and SOTP paths.
- Newhe Cheng (002001) has known source-data gaps in historical physical sales, net selling prices, and unit variable costs. Do not infer these from accounting cost data. Preserve UNKNOWN where evidence is insufficient.
- MIE remains optional explanatory context under the stated v0.3 policy; its absence alone must not veto an otherwise valid opportunity.
- ChatGPT Free Web plus local scripts remains a pilot workflow, not an accepted canonical end-user workflow.
- The current-main CLI already implements separate Round A and Round B response files, stable-save detection, phase-specific validation, a frozen Round A artifact and Replay lineage. Do not recreate these capabilities.
- The current wizard has no supported cross-process `--resume-task` mode. Its task stages are written to files, but a terminated process cannot be resumed through a durable task-state interface.
- macOS `pbcopy` is invoked as a required command for both prompts; a clipboard failure can abort an otherwise recoverable workflow. Treat clipboard as optional.
- The local template starts with an empty evidence register and relies on ChatGPT Web research; original official filing bytes are not locally acquired and archived by the basic wizard.
- README still points to the 2026-10-11 quick guide, whose handoff description predates the current two-round workflow. The current 2026-10-21 runbook documents the two-round process.
- The current-main B34 Mac acceptance remains OPEN / NOT VERIFIED. Source inspection and hosted CI do not close that gate.

**Mandatory precondition for implementation:** Before coding each batch, re-read the current canonical main state index, relevant source files, current PR metadata, and actual local-pilot implementation. Treat the bullets above as leads to verify, not as permission to assume the repository has not changed.

## 3. Non-negotiable design principles

1. **Human work is reserved for human judgment.** The user should not routinely edit JSON, manage paths, install dependencies, change permissions, assemble prompts, or diagnose stack traces.
2. **Local code handles deterministic operations.** Task creation, file management, schema validation, arithmetic, provenance, version checks, archiving, and replay belong in deterministic code.
3. **ChatGPT Web remains the research interface.** Retain a small number of explicit human Web interactions. Do not make clipboard synchronization, GUI automation, or browser robotics critical-path dependencies.
4. **Free official evidence first.** Prefer exchange/company disclosures and official source files. Do not buy commercial APIs or build a broad market-data platform for this scope.
5. **Unknown remains unknown.** Missing evidence, ambiguous definitions, and incomplete assumptions must not silently become zero or fabricated facts.
6. **Recover by stage.** Interrupted work resumes from the last valid stage. Preserve raw inputs and prior valid outputs; never silently overwrite evidence.
7. **Reuse before rebuilding.** Audit existing Pilot, B73-B81 artifacts, schemas, scripts, and workflow contracts before adding modules.
8. **Separate operational success from investment success.** More automation, more fields, longer reports, and more passing unit tests do not prove better investment decisions.

## 4. Target user workflow

1. Create a research task using a small, guided input surface: security, as-of date, and price/time only when not reliably available. Load investment policy defaults from versioned configuration.
2. Automatically prepare a source/evidence pack from supported official disclosures; show explicit manual fallback when retrieval fails.
3. Generate Round A materials and prompt locally. User runs the prompt in ChatGPT Web and imports the result once.
4. Validate, preserve, and archive the raw Round A response. Generate Round B materials locally.
5. User runs Round B in ChatGPT Web and imports the result once.
6. Locally validate schemas, provenance, period alignment, arithmetic, EPS/SOTP transmission, policy constraints, and missing evidence.
7. Generate reviewable report, structured output, exception list, evidence manifest, and replay record.
8. On failure, resume from the failed stage without repeating completed work.

The Web interactions are intentionally retained. A dependable two-import workflow is preferable to fragile full browser automation.

## 5. Batch roadmap

### B82 — Existing workflow audit and minimal architecture decision

<badge>COMPLETE — SOURCE AUDIT</badge>

**Audited baseline:** canonical `main@2fd009b10bd4b13467ebdd8b2692eab62a772878` (2026-11-08 GitHub inspection).  
**Audit artifact:** [B82 current-main Pilot operability audit](B82_CURRENT_MAIN_PILOT_OPERABILITY_AUDIT_20261108.md).

Completed:
- Reconstructed the real CLI → Round A → frozen company artifact → Round B → local validation → report/receipt → Replay workflow from current-main source and user documentation.
- Inventoried human inputs and mechanical operations.
- Reviewed current-main Pilot entry/response/persistence code, targeted test coverage and local Pilot GitHub workflow.
- Re-checked current PR #587 metadata, changed-file inventory, proposal branch and its large ancestry relative to `main`.
- Produced failure register F82-01 through F82-09 and a capability reuse/build matrix.
- Revised the minimal architecture and B83-B89 plan based on verified current-main behavior.

Key decisions:
- Reuse the existing guided wizard, prompt builders, patch validator, response parser, operator-field protection, private storage, run receipt and Replay.
- Do not build another input UI or duplicate research pipeline.
- Prioritize durable task state/resume; make clipboard optional; then add bounded official-source intake and update stale instructions.
- Keep B34 current-main real Mac acceptance OPEN / NOT VERIFIED.

Limitations: source inspection only. Local pytest, actual Mac GUI/browser/clipboard execution and B34 acceptance were NOT RUN. No runtime code changed.

**B82 is complete as an audit batch only; it does not claim operational acceptance.**

### B83 — Durable task workspace, stage manifest and resume

**Purpose:** Let the user recover the same research task after Terminal closure, process failure or Mac restart without repeating completed Web research or re-entering protected operator inputs.

Reuse the existing wizard/template and `~/.iios-private/local-pilot/{inputs,runs}` conventions. Do not create a second input interface or a parallel research engine.

Deliver:
- stable task ID and one private workspace per research task;
- versioned task manifest containing input snapshot hash, source SHA, schema/prompt versions and current stage;
- append-only stage-transition journal with timestamp, state, artifact path, byte size and SHA-256;
- immutable/versioned Round A prompt, raw response, validated patch and frozen company artifact;
- immutable/versioned Round B prompt, raw response and validated merged input;
- an explicit `--resume-task <task_id>` or equivalently simple resume entry that validates the manifest and resumes the first incomplete stage;
- safe handling of duplicate, incomplete, tampered, mismatched or missing artifacts;
- no-clobber behavior for prior valid inputs and responses.

Minimum states: `TASK_INPUT_READY`, `ROUND_A_PROMPT_READY`, `ROUND_A_RESPONSE_CAPTURED`, `ROUND_A_VALIDATED`, `ROUND_A_FROZEN`, `ROUND_B_PROMPT_READY`, `ROUND_B_RESPONSE_CAPTURED`, `ROUND_B_VALIDATED`, `RUN_WRITTEN`, `REPLAY_VERIFIED`.

Do not let LLM output write or advance task state. Deterministic local code alone advances the manifest after validation succeeds.

Exit criteria:
- Simulated process interruption at every stage resumes the same task from the last valid stage;
- previously completed Round A is not repeated when Round B is pending;
- protected price, cutoff, position and policy inputs are not re-entered or rewritten during resume;
- tampered/missing/hash-mismatched artifacts stop safely with an actionable error;
- prior valid artifacts remain byte-identical.

### B84 — One supported launch path and local runtime preflight

**Purpose:** Remove avoidable source-version, Python and environment ambiguity without replacing the existing Pilot.

Deliver:
- decide and document one normal daily launch/update path, separately from the packaged full-acceptance launcher;
- preflight displays source SHA/version, supported Python version, dependency readiness, required paths, private workspace permissions and available disk space before asking for case inputs;
- detect stale source or unsupported runtime before the user starts a research task;
- keep concise actionable logs and a safe recovery path;
- remove routine manual Git commands, chmod, venv activation, shell-profile edits and dependency repair where the existing distribution path can handle them safely.

Do not introduce a new desktop framework, complex installer, signing/notarization work or pinned environment machinery unless B82 evidence shows the current Python entry path cannot meet the requirement. Do not make the daily workflow dependent on GitHub availability after a verified source copy has been installed.

Exit criteria:
- one documented daily launch path and one clearly labeled acceptance path;
- stale source and unsupported runtime are detected before user input;
- clean supported Mac setup and routine startup have concrete, low-operations steps;
- no unnecessary rewrite of the Python application entry point.

### B85 — Round A/B handoff resilience and documentation alignment

**Purpose:** Make the existing two-round Web handoff tolerant of local clipboard/GUI failures and easy to follow without adding browser automation.

Deliver:
- keep the existing phase-specific prompt builders, patch allowlists, frozen Round A artifact and response parser;
- make `pbcopy` best-effort; the prompt file is always authoritative and must be shown/openable with clear manual copy instructions;
- browser and TextEdit opening are best-effort with explicit visible fallback instructions;
- preserve separate Round A/Round B response files, stable-save detection, file chooser and concise repair prompts;
- bind each response attempt to B83 task ID/stage and never overwrite the last valid response;
- reconcile README and quick guide with the current two-round main workflow and 2026-10-21 acceptance runbook.

Important rules:
- retain ChatGPT Web as the research interface;
- no clipboard, GUI or browser-automation dependency in the correctness-critical path;
- preserve raw failed responses for diagnosis but do not accept them as validated stage artifacts;
- never auto-fill missing investment facts or weaken phase/UNKNOWN controls.

Exit criteria:
- clipboard failure does not terminate the task;
- user can manually open/copy the exact prompt and save/import the response;
- no more than one deliberate response import per round;
- failed imports preserve the raw response and last valid state;
- instructions match the exact current implementation.

### B86 — Official evidence preparation automation

**Purpose:** Reduce manual searching, downloading, deduplication, and filing without creating a broad data platform.

Prioritize:
- CNINFO for A-share disclosures;
- SSE/SZSE official disclosure sources;
- HKEXnews for Hong Kong listings;
- company investor-relations sites where appropriate.

Initial scope:
- annual, interim, and quarterly reports;
- earnings forecasts and earnings releases;
- material operating announcements;
- selected company-specific operating metrics needed by the research question.

Each source artifact should preserve:
- original file;
- source URL and source institution;
- publication date and reporting period;
- retrieval timestamp;
- file hash;
- extraction status and parser version;
- extracted field definitions and source location where possible;
- manual verification state.

Use automatic retrieval first and an explicit manual-download fallback second. Do not treat successful PDF extraction as proof of data correctness.

Exit criteria:
- supported official documents can be found and archived reproducibly;
- failed retrieval provides a clear official source and manual fallback;
- duplicates do not pollute the evidence pack;
- extraction failures remain visible;
- missing evidence remains UNKNOWN.

### B87 — End-to-end real-company acceptance

**Purpose:** Validate both workflow reliability and the value of new research capabilities.

Use distinct valuation paths:
- EPS_MULTIPLE: Newhe Cheng (002001) if sufficient verified inputs exist; otherwise select a data-sufficient replacement and keep Newhe Cheng's unavailable operating inputs UNKNOWN.
- SOTP: Kolon Pharma (002422), with the current source pack and model path independently rechecked.

Compare old and new research workflow using the same:
- research as-of date;
- evidence pack;
- price and price timestamp;
- investment hurdle and horizon;
- policy configuration.

Review:
1. main contradiction and key value drivers;
2. evidence quality and provenance;
3. future events and operating variables;
4. Bear/Base/Bull normalized earnings bridge;
5. EPS or SOTP per-share transmission;
6. current-price-implied earnings/value requirements;
7. return/risk and policy checks;
8. uncertainty, UNKNOWN handling, and decision rationale.

Exit criteria:
- At least one complete, auditable case for each valuation path;
- relevant B74/B75 regression checks addressed;
- numerical and provenance checks pass;
- any research-quality improvement is evidenced, not inferred from report length or field count;
- all unresolved gaps are explicitly listed.

### B88 — Controlled integration and release

**Purpose:** Move only accepted, necessary changes into the canonical product.

Rules:
- do not merge the entire PR #587 proposal chain;
- inspect dependency and commit ancestry before extracting changes;
- use canonical main as the release baseline;
- integrate in small, reviewable units;
- keep code, schemas, docs, state index, and acceptance records synchronized;
- document rollback and compatibility;
- do not label unaccepted capabilities canonical.

Exit criteria:
- release can be reproduced from canonical main;
- no hidden dependency on unmerged proposal code remains;
- accepted and pilot-only capabilities are clearly distinguished.

### B89 — User's actual Mac acceptance

**Purpose:** Prove the workflow works in the real operating environment, not only in hosted CI.

Test:
1. clean installation;
2. first-run preflight;
3. task creation;
4. evidence preparation;
5. Round A Web handoff and import;
6. Round B Web handoff and import;
7. local calculations and decision checks;
8. deliberate interruption and stage recovery;
9. replay with identical inputs and versions;
10. evidence, report, and manifest audit.

Exit criteria:
- user does not need to debug Python, shell permissions, or JSON;
- interrupted work recovers without data loss;
- replay is deterministic for identical inputs and versions;
- all investment evidence and decision constraints remain enforced;
- operational time and error rate are measured.

## 6. Dependency and execution order

Recommended sequence:

`B82 (complete) -> B83 -> B84 -> B85 -> B86 -> B87 -> B88 -> B89`

B83 establishes the durable task/workspace contract first. B84 and B85 then build around that same task ID and stage manifest; do not implement competing state or handoff models.

The existing current-main B34 acceptance is a separate prerequisite for deciding whether the unchanged B33 workflow is operationally accepted. Do not confuse B34 with B89: B34 validates the already-merged current-main workflow, while B89 validates the modified B83-B88 product.

B86 may be developed after the task/workspace contract exists. Use a verified manually assembled official evidence pack to validate handoff/recovery before depending on automated retrieval.

Do not start a broad rewrite. Every code change must map to a verified B82 failure or a real-case acceptance finding.

## 7. Unified task workspace and provenance contract

Proposed logical layout (adapt to existing private Pilot paths and do not duplicate an existing equivalent):

```text
~/.iios-private/local-pilot/
├── tasks/<task_id>/
│   ├── task_manifest.json
│   ├── transitions.jsonl
│   ├── input/                 # immutable operator task snapshot / revisions
│   ├── round_a/               # prompt, raw response, validated patch, frozen artifact
│   ├── round_b/               # prompt, raw response, validated patch
│   ├── output/                # analysis, report, receipt, replay
│   └── evidence/              # optional original-source pack
├── runs/                      # existing run bundles retained for compatibility
└── logs/
```

The layout is a target logical contract, not a claim that these directories already exist. Preserve compatibility with existing `inputs/` and `runs/` until a migration decision is supported by the code audit.

Suggested source-of-truth responsibilities:
- JSON: machine-readable task inputs, stage state and structured outputs;
- PDF/XBRL/HTML original disclosures: immutable source evidence;
- Markdown: exact prompt text, readable reports and exception explanations;
- manifest/journal: task identity, source SHA, schema/prompt versions, hashes, transitions and resume point.

Keep original raw responses immutable. New attempts create versioned candidate artifacts; only a successfully validated response becomes the current accepted stage artifact. Do not maintain duplicate competing sources of truth.

## 8. Validation strategy

Avoid running the full test suite after every small edit, but never defer critical safety checks.

Three levels:
1. **Per-batch minimum:** syntax, interface contracts, and narrowly targeted tests for changed behavior.
2. **Integration checkpoints:** Round A/B handoff and evidence pipeline integration after B85/B86.
3. **Unified acceptance:** required regression suites, end-to-end real cases, replay, and actual Mac workflow in B87-B89.

Must validate immediately when changed:
- financial arithmetic, EPS/share count, and valuation transmission;
- Trust and evidence admission;
- UNKNOWN/null semantics;
- period and price-time alignment;
- file overwrite/data-loss behavior;
- decision hard constraints.

A test not run must be marked NOT_RUN. Hosted macOS CI must not be described as user's local Mac acceptance.

## 9. Operational metrics

Measure a baseline during B82 before setting improvement claims.

Track:
- hands-on user minutes per company;
- number of manual technical operations;
- number of deliberate Web imports;
- repeated/manual file operations;
- task completion rate;
- failure rate by stage;
- mean recovery time;
- percentage of evidence fields with source provenance;
- number of silent coercions or overwritten valid artifacts (target: zero);
- replay reproducibility;
- research-quality differences between old and new workflow.

Initial product targets:
- routine manual JSON editing: zero;
- routine chmod/shell-profile/venv operations: zero;
- routine manual dependency installation: zero;
- clipboard/GUI as critical dependencies: zero;
- at most one deliberate result import per Web round;
- invalid inputs blocked before execution;
- recoverable stage interruption;
- no silent evidence overwrite or unknown-to-zero coercion.

Do not set an arbitrary user-time target until the B82 baseline is measured.

## 10. Explicit non-goals

Do not build in this roadmap:
- a full-market free-data warehouse;
- a large-scale quote or fundamentals database;
- reverse-engineered unstable free APIs as critical dependencies;
- complex browser robots or clipboard-driven orchestration;
- a new desktop application framework without demonstrated need;
- a broad rewrite of the IIOS investment core;
- automatic trading;
- automatic completion of missing evidence or assumptions.

## 11. Batch completion and reporting discipline

For every batch report:
- objective and scope;
- files/modules changed;
- existing components reused;
- tests run and exact results;
- tests not run;
- known limitations;
- branch and commit SHA;
- state-index/documentation updates;
- exit criteria met/not met;
- next batch authorization.

Always distinguish:
- code implemented;
- targeted tests passed;
- integration tests passed;
- hosted CI passed;
- real-company case accepted;
- user's local Mac accepted.

No claim of completion without the corresponding evidence.

## 12. Immediate next action

Start B83 only: implement the durable task workspace, stage manifest, immutable artifacts and `--resume-task` entry described above. Reuse the existing wizard and Round A/B pipeline; do not build a second input UI.

Before coding, re-check the exact main HEAD, Pilot source and tests, then define the manifest schema and stage-transition contract. Add narrow interruption/resume and tamper-rejection tests. Do not modify investment formulas, Trust/forecast admission, formal Decision authority or execution permissions.

**Current status:** B82 source/workflow audit is persisted on this dedicated documentation branch. No runtime code was changed, no local tests or user-Mac workflow were run, and the roadmap has not been merged to `main`.
