# MVP Pilot Acceptance — Human Gate Preparation — 2026-10-07

Status: **TECHNICAL GATE READY / HUMAN ACCEPTANCE REQUIRED**

## 1. Purpose

This record prepares the final MVP Pilot Acceptance boundary after PILOT-04 independent clean replay.

The acceptance decision is intentionally split:

- **Machine-verifiable technical gate**: derived from canonical PILOT-01 / PILOT-02 / PILOT-03 / PILOT-04 evidence.
- **Human usability gate**: requires the actual operator to read the generated Investment Report and attest whether it is practically usable for investment review.

The human gate must not be inferred from CI success.

## 2. Technical evidence already available

Required product-path evidence exists for:

- two materially different real-company cases: CATL / 300750 and 科伦药业 / 002422;
- one fresh user-selected candidate: 新和成 / 002001.SZ;
- Decision → Human Approval boundary;
- Execution Receipt boundary with automatic execution disabled;
- Monitoring and Validation linkage;
- independent clean replay;
- Machine Publication and Human Report QA;
- current-to-historical substitution protection;
- LLM authority isolation;
- A02 / CSI800 remaining outside the Investment Core critical path.

PILOT-04 canonical replay:

- merge commit: `f3405f66e74a091e4f60aac0ddb5c6d1e1ad4700`;
- clean replay baseline: `79c5576bc4c63d3989a252401683c6691e66d998`;
- accepted run: `37632285110`;
- acceptance steps: 11/11 PASS.

## 3. Report readability hardening

The current Human Report Contract requires investor-facing prose rather than raw internal JSON.

A PILOT-04 inspection found that the Risk / Portfolio contract was being serialized directly into the report body even though automated QA passed.

This batch corrects only that presentation-layer defect:

- risk / portfolio information is rendered as structured investor-facing bullets;
- contract audit hashes remain machine-level provenance, not main-report prose;
- no Investment Core decision semantics are changed;
- no historical report is mutated;
- a regression test prevents reintroduction of the machine-JSON dump.

## 4. Human acceptance questionnaire

The operator must review the actual generated report(s) and answer:

### A. Immediate usability

- Can the current action be identified within the first screen?
- Is it clear whether new capital is currently permitted?
- Is the current price / entry zone / position package understandable?
- Is the maximum-loss boundary visible without searching the appendix?

### B. Investment reasoning

- Is the causal chain from Thesis → Evidence → Forecast → Valuation → Return → Risk understandable?
- Are the key assumptions distinguishable from sourced facts?
- Are uncertainty / UNKNOWN / BLOCKED states understandable rather than merely technical status codes?

### C. Decision authority

- Is the separation between AI proposal and human approval unambiguous?
- Is it obvious that publication/report does not authorize trading?
- Is it obvious what would cause a new review or decision revision?

### D. Operational friction

Record any information that had to be manually reconstructed outside the report.

Record any repeated, confusing, hidden, or unnecessarily technical content.

## 5. Acceptance rule

The final MVP Pilot Acceptance may be marked **PASS** only when:

1. the technical gate remains PASS;
2. no unresolved P0 exists;
3. the operator records the human observations above;
4. the operator explicitly states whether the report is practically usable for investment review;
5. any material P1/P2 usability issue is either fixed and re-tested or explicitly accepted by the owner.

A human rejection does not invalidate the underlying Investment Core semantics. It creates a product/usability finding for a narrowly scoped follow-up batch.

## 6. Current blocker

**Only the human usability gate remains unresolved.**

No fabricated human observation, inferred approval, or CI-derived “usable” status may be used to close this gate.

## 7. Research-track separation

A02 / CSI800 historical-universe evidence remains non-blocking to this acceptance.

The absence of `000906cons.xls` historical target bytes or B-side PIT evidence cannot be used to block company-level Investment Core MVP acceptance.
