# IIOS Post-B81 Operability and Real-Use Acceptance Roadmap

**Date:** 2026-11-08  
**Status:** Planning baseline; B82 audit not yet executed  
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

## 2. Known project context and cautions

The following is the project context available when this plan was written. It is not a fresh code audit:

- The original decision core has prior accepted real-company cases for CATL (300750) and Kolon Pharma (002422). These historical acceptances should not be confused with validation of later B42-B81 research additions.
- B42-B81 added or developed research capabilities, but the complete newer workflow has not yet been accepted through end-to-end real-company cases.
- PR #587 was previously reported as Draft/Open/Unmerged and based on a B73 proposal branch. Do not merge the entire proposal chain as one unit.
- B81 reportedly updated the macOS hosted runner to macOS 15 and passed 466 selected tests. Hosted CI does not replace acceptance on the user's own Mac.
- B74/B75 regression assertions were reported as drafted but not fully run.
- The new research workflow still needs real-case acceptance, including EPS_MULTIPLE and SOTP paths.
- Newhe Cheng (002001) has known source-data gaps in historical physical sales, net selling prices, and unit variable costs. Do not infer these from accounting cost data. Preserve UNKNOWN where evidence is insufficient.
- MIE remains optional explanatory context under the stated v0.3 policy; its absence alone must not veto an otherwise valid opportunity.
- ChatGPT Free Web plus local scripts remains a pilot workflow, not an accepted canonical end-user workflow.

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

**Priority:** Immediate; first execution batch  
**Purpose:** Establish what already exists, what fails, what users actually do, and what should be reused.

Audit:
- Pilot entry points, shell scripts, Python launch path, installation path, and dependency handling;
- task input templates, system configuration, schemas, and default-value behavior;
- Round A/B prompt generation and evidence packaging;
- Round A/B response import, parsing, schema validation, and error reporting;
- task state, manifest, file layout, logs, resume/retry, and replay;
- clipboard, GUI, browser, network, and filesystem dependencies;
- relevant B73-B81 code, documents, tests, and unresolved regressions;
- current main, PR #587 base/head/state, branch ancestry, and merge risks.

Deliverables:
1. End-to-end current-state workflow diagram;
2. step-by-step human-operation inventory;
3. failure register with trigger, root cause, impact, and recovery;
4. capability reuse/delete/modify/build matrix;
5. minimal target architecture and batch implementation plan;
6. baseline measurement plan for user time and failure frequency.

Exit criteria:
- Every human step has a documented reason;
- every known failure has a proposed containment or fix;
- every proposed feature maps to a verified user problem;
- existing components and contracts are identified for reuse;
- no broad rewrite is proposed without evidence.

**B82 is an audit batch, not a feature-building batch.**

### B83 — Unified task entry and input contract

**Purpose:** Eliminate routine manual JSON editing and task-file assembly.

Deliver:
- one task-creation interface or the smallest viable guided entry point;
- canonical task object and versioned JSON Schema;
- automatic JSON generation and validation;
- versioned defaults for required annualized return, max-loss policy, horizon, valuation mode, and research rules;
- task ID and isolated workspace creation;
- explicit distinction between user-supplied values, system defaults, operator-attested values, and unknown values;
- immutable or versioned task-input snapshots.

Exit criteria:
- User can create a valid task without editing JSON;
- invalid input is rejected before research begins;
- null/unknown values are not silently coerced to zero;
- changes create traceable revisions rather than overwriting prior task history.

### B84 — Local runtime and environment reliability

**Purpose:** Remove recurring Python, shell, permission, and dependency friction.

Preferred minimal design:
- retain the current Python application entry point where viable;
- one-time installer/bootstrapper creates an isolated environment and installs pinned dependencies;
- fixed supported Python version and dependency lock;
- daily launcher performs preflight checks and starts the workflow;
- terminal command remains a fallback, not the normal user path;
- logs are retained, but user-facing errors are concise and actionable;
- no daily chmod, manual venv activation, shell-profile editing, dependency installation, or interpreter selection;
- clipboard and GUI integrations remain optional.

Preflight checks should cover supported OS/Python, required dependencies, configuration/schema compatibility, workspace permissions, disk space, and required paths.

Exit criteria:
- Clean supported macOS environment can be installed from documented steps;
- routine runs do not require developer-level environment operations;
- startup failures are diagnosed before task execution;
- failure messages identify a concrete next action;
- the workflow does not depend on clipboard or GUI synchronization.

Do not rewrite the desktop application or add signing/notarization complexity unless the audit demonstrates it is necessary.

### B85 — Round A/B handoff and recovery

**Purpose:** Preserve ChatGPT Web while removing manual prompt assembly, file juggling, and format repair.

Deliver:
- deterministic Round A/B input-pack generation;
- prompt generation tied to task, schema, and prompt versions;
- a documented response contract;
- robust import for the supported output formats;
- task ID, schema version, period, and required-field validation;
- preservation of raw Web responses;
- no overwrite of last valid result on failed import;
- actionable validation errors with field/path context;
- automatic next-stage package generation;
- stage state machine and resumable execution.

Important rule:
- Do not rely on ChatGPT always emitting perfect JSON.
- Parse only supported formats; validate before accepting.
- Never silently discard unknown or required fields.
- Never auto-fill missing investment facts to make a schema pass.

Exit criteria:
- A real task completes both Web rounds with no manual JSON editing;
- no more than one deliberate import action per round;
- failed imports preserve the raw response and prior valid artifacts;
- interrupted tasks resume from the last valid stage.

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

`B82 -> (B83 + B84) -> B85 -> B86 -> B87 -> B88 -> B89`

B83 and B84 may be designed or implemented in parallel after B82, but must share one task contract, configuration model, and workspace protocol.

B86 is not a prerequisite for first proving B85. Use an existing verified evidence pack to validate the Round A/B handoff, then improve automated source preparation.

Do not start B83-B86 implementation until B82 identifies the actual reusable components and the smallest safe change set.

## 7. Unified task workspace and provenance contract

Proposed logical layout (adapt to existing repository conventions; do not duplicate an existing equivalent):

```text
IIOS/
├── app/
├── config/
│   ├── system_config.json
│   └── schemas/
├── workspace/
│   └── <ticker>/<asof>/
│       ├── input/
│       ├── evidence/
│       ├── round_a/
│       ├── round_b/
│       ├── output/
│       └── manifest.json
├── logs/
└── launcher/
```

Suggested source-of-truth responsibilities:
- JSON: machine-readable task inputs, states, and structured outputs;
- PDF/XBRL and original disclosure files: immutable source evidence;
- Markdown: prompts, readable reports, exception explanations;
- manifest: task identity, versions, hashes, stage states, timestamps, and recovery point.

Do not maintain duplicate Excel/Markdown/JSON copies as competing sources of truth.

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

Start B82 only.

First inspect the current canonical main state index, current PR #587 metadata and diff, and actual Pilot entry/input/handoff/import/runtime files. Produce the audit artifacts and a minimal implementation map. Do not modify runtime code until the audit is complete.

**Current status of this roadmap:** persisted as a planning document on a dedicated documentation branch. It is not merged into main, and no B82 code audit or implementation is claimed by this document.
