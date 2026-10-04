# IIOS B0 — Authority / Audit Freeze

Date: 2026-10-04
Status: EXECUTION BASELINE FROZEN
Scope: Investment Decision Core repair program
Repository: kebofeierdawei5-cloud/convergence-research
Baseline branch: main
Baseline HEAD: d209b33b7f922866f2fdc1190785c27edb8a28e4
Repair branch: repair/b0-authority-audit-freeze-20261004

## 1. Purpose

B0 establishes the authoritative starting point for the post-red-team Investment Core repair program.

B0 freezes:
- the exact Git starting point for repair;
- the distinction between historical/frozen governance evidence and the new repair target;
- the authority precedence used for interpretation;
- the known semantic conflicts that must be resolved before semantic implementation changes;
- the allowed and prohibited work during B0/B1;
- the non-claims that prevent engineering PASS from being mistaken for investment-validity PASS.

B0 does not amend the Investment Core Contract v0.2, decision semantics, return formulas, or production code semantics. Those changes belong to B1 and require explicit semantic approval and versioning.

## 2. Exact Baseline

At B0 start, the public GitHub repository was independently read at its default branch.

- Repository: kebofeierdawei5-cloud/convergence-research
- Default branch: main
- Baseline HEAD: d209b33b7f922866f2fdc1190785c27edb8a28e4
- Baseline commit message: Docs: record P4-F acceptance and advance to P5 (#17)
- Baseline commit is a merge commit with parents 9732f33d3b0163832d317661b8171046d93c6455 and 6d60900c02bba3713738eeed28156fcf12c2f0ff.

The baseline is immutable for audit comparison. Future repair work proceeds on successor commits/branches and does not rewrite this commit.

## 3. Authority Model

B0 distinguishes historical interpretation authority from repair-target authority.

### 3.1 Historical interpretation authority

When determining what the existing system currently says or does, use this order:

1. Exact frozen governance artifacts and accepted evidence chains.
2. Current canonical Git repository state at the B0 baseline.
3. Independent CI / execution evidence tied to the relevant exact commit.
4. Historical audit records as point-in-time evidence.
5. Chat/context summaries.

A lower layer cannot silently overwrite a higher layer's historical record.

### 3.2 Repair-target authority

When determining what the repaired IIOS is intended to mean, use this chain:

1. Explicit owner decision / adjudication in the current conversation.
2. A versioned semantic ADR produced in B1 and explicitly accepted by the owner.
3. The successor Investment Core Contract produced from that ADR.
4. Versioned implementation and schemas derived from the accepted contract.
5. Tests / mutation / replay evidence demonstrating the implementation follows the contract.

Therefore, audit reconstruction is not automatically equivalent to the original Requirements v1.1. Where the exact historical requirement artifact is unavailable, it remains an audit reconstruction or historical interpretation until explicitly re-adjudicated.

## 4. Immutable / Reference-Only Boundaries

The following remain historical/reference evidence and are not silently rewritten during repair:

- G2 frozen carrier / governance evidence under governance/g2-r10-reference/;
- historical acceptance records P2/P3/P4;
- the exact B0 baseline commit d209b33...;
- prior audit records and their original conclusions;
- FM-00 historical/exploratory research evidence;
- blocked or rejected historical implementation paths.

The P4-A through P4-F implementation remains in the repository, but for the repair program it is treated as conditional explanatory infrastructure, not evidence that the complete investment decision semantics are production-valid.

The blocked historical Batch 2 v0.1 PR must not be revived or merged as the repair path.

## 5. Current Engineering State at B0

### Accepted engineering artifacts already present

- PIT / Trust / fail-closed foundations;
- snapshot hash / replay foundations;
- Decision Series / Revision / Human Approval skeleton;
- Company Value Core structured scan;
- Human-authoritative company Primary Model selection;
- deterministic valuation calculators for supported models;
- P2-A through P4-F acceptance artifacts and tests.

### Not yet production-capable for investment decisions

- complete company-side Reality → Quality → Value Core economic chain;
- independent forecast contract suitable for the repaired decision path;
- corrected Return Engine semantics;
- complete deterministic Decision Kernel;
- complete position / entry package semantics;
- complete monitoring / validation lifecycle;
- real-company end-to-end acceptance;
- independent semantic / mutation validation of the repaired chain.

## 6. Known Semantic Conflicts

These are open conflicts, not B0-resolved semantics.

| ID | Conflict | Incumbent baseline | Repair target / required action | Gate |
|---|---|---|---|---|
| B0-S01 | Two different meanings of 15% are conflated | Current v0.2 contract/code use 15% as the Expected Return hurdle | Owner clarification: 15% BUY-entry threshold / safety-margin requirement is distinct from 1–3Y fundamental-investing target annualized return >=15%; freeze exact definitions separately | B1-Critical |
| B0-S02 | Horizon semantics are absent/ambiguous in current return gate | Current baseline has no fixed 1–3Y core horizon | Repair must represent 1–3Y as the intended fundamental-investment holding horizon without collapsing it into the BUY threshold | B1-Critical |
| B0-S03 | Expected Return vs Required Return | Current baseline does not provide a complete independent RR semantics | Define ER, RR and their relationship without double-counting risk | B1-Critical |
| B0-S04 | Margin of Safety vs BUY threshold | Current wording can make threshold, valuation discount and risk compensation overlap | Define MoS and entry threshold as separate objects/policies and specify whether/where each participates in BUY | B1-Critical |
| B0-S05 | Quality is not first-class enough | Existing Value Core is substantially a structured classifier/scan | Upgrade Quality to an explicit economic object with evidence, metrics and decision role | B1/B3 |
| B0-S06 | Trust vs Investability | Trust currently carries part of the gating burden | Define Trust and Investability as distinct dimensions | B1 |
| B0-S07 | MIE role | Existing chain makes MIE central and prior gates can require identifiability/stability | Keep P4 MIE as conditional explanation infrastructure; do not make it a universal BUY gate before evidence demonstrates necessity | B1/B8 |
| B0-S08 | Unknown semantics | Current state space includes UNKNOWN, but default-action semantics are incomplete | UNKNOWN must not silently become HOLD; define action policy | B1 |
| B0-S09 | HOLD / EXIT economics | Existing skeleton can be asymmetric to new BUY | Existing holdings must be assessed from current opportunity, not historical cost basis; define formal lifecycle semantics | B1/B6 |
| B0-S10 | Quality / Value Core / Forecast ordering | Existing modules are not yet a fully connected company-economic chain | Freeze Value Sources → Drivers → Ranking → History → Forecast Variables → Valuation Variables | B3/B4 |
| B0-S11 | Evidence time semantics | PIT has known_at, but repair must distinguish knowability from retrieval time | Evidence contract must preserve known_at, retrieved_at, publication/observation semantics | B2 |
| B0-S12 | Semantic changes lack one explicit authority gate | Existing documents may say FROZEN while repair needs to change semantics | Every critical semantic change requires Owner-approved ADR + contract version bump + implementation/schema/test update | B0/B1 onward |

## 7. Owner Adjudication Recorded at B0

The following statement is a repair-target requirement from the owner, not an assertion about the existing v0.2 implementation:

15% annualized return as the expected long-term result of a fundamental investment held for roughly 1–3 years, and 15% as the threshold / desired safety margin used to trigger an investment entry, are two different concepts and must be modeled separately even though the numeric value is currently the same.

B0 therefore forbids any new implementation from representing both concepts with a single semantic field merely because both currently equal 15%.

The exact mathematical mapping of the BUY-entry threshold, Expected Return, Required Return, Margin of Safety and the 1–3Y annualized target remains B1 work.

## 8. Work-Preservation Rules

The following work is preserved but quarantined from production decision authority:

- P4-A through P4-F MIE modules;
- historical reverse-valuation / market-model identification primitives;
- old return-gate code and v0.2 schemas;
- prior acceptance tests that validate the incumbent contract.

They may be used as migration/reference material, but passing those tests does not establish the truth of the repaired semantics.

## 9. Prohibited Changes Before B1 Approval

Do not:
- change the meaning of 15%, Expected Return, Required Return, Horizon or Margin of Safety in implementation;
- reconnect P5/P6 logic to production decision authority;
- introduce a second ambiguous alias such as hurdle_pct for one of the two 15% concepts;
- infer historical Requirements v1.1 from reconstructed audit language and label it as exact recovered requirements;
- merge the blocked Batch 2 v0.1 path;
- add automatic trading/execution capability;
- use current market price as an input to independent company forecasting;
- treat P4/P5/P6 test counts as proof of economic correctness.

## 10. Allowed Changes in B0

B0/B1 preparation may add:
- authority / audit-freeze documentation;
- semantic conflict registers;
- ADR templates and requirement-authority registers;
- migration notes and non-decision-grade test scaffolding;
- status/index synchronization that does not alter investment semantics.

Semantic implementation changes begin only after the B1 approval gate.

## 11. Release / Qualification Boundary

At B0 completion the repository is classified as:

L0 — Experimental / Repair Baseline

B0 PASS means:
- exact repair baseline is identified;
- authority chain is explicit;
- semantic conflicts are enumerated;
- historical and target semantics are not conflated;
- repair boundaries are explicit.

B0 PASS does not mean:
- investment decision capability is production-ready;
- the 15% return semantics are finalized;
- MIE is decision-grade;
- Forecast Research is validated;
- any real company is currently decision-approved by the repaired system.

## 12. B0 Acceptance Criteria

B0 is PASS when:
1. Current main HEAD is independently recorded exactly.
2. Repair branch starts from that exact HEAD.
3. Historical authority and repair-target authority are separated.
4. Known semantic conflicts are recorded without silently resolving them.
5. The owner-approved dual-15% clarification is recorded as a target requirement for B1.
6. P4/P5 historical work is quarantined from claims of production investment capability.
7. No production semantic code is changed as part of B0.
8. The next mandatory gate is B1 Investment Semantics, not further P4/P5 feature expansion.

## 13. B0 Result

B0 STATUS: PASS — READY FOR B1 INVESTMENT SEMANTICS v0.3

Baseline SHA: d209b33b7f922866f2fdc1190785c27edb8a28e4

Next gate:
B1 Investment Semantics v0.3 → Owner semantic adjudication → Contract draft → Independent red-team → Approval → Implementation
