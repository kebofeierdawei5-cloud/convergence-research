# Batch 0 — Local Pilot Baseline Audit

- Date: 2026-10-13
- Classification: implementation baseline / evidence-limited audit
- Authority: `docs/PROJECT_STATE_INDEX.md`
- Canonical baseline: `main@f29b1906170a75f628c6d1917f591660660ed20d`
- Result: **ARCHIVED INPUT REVIEW COMPLETE / ACTUAL MAC RUN BUNDLE NOT REVIEWED**
- Purpose: establish what can actually be confirmed before changing the core research flow. This is not a new company analysis or a formal IIOS acceptance.

## 1. Scope and material inspected

Inspected the current canonical implementation and guidance:
- `iios_mvp/local_investment_pilot_v01.py`
- `docs/iios/LOCAL_INVESTMENT_PILOT_V01_GUIDE_20261011.md`
- `docs/iios/LOCAL_SINGLE_USER_EXECUTION_FIRST_PIVOT_20261011.md`
- `docs/iios/IIOS_BATCH_EXECUTION_PLAN_20261010.md`
- `docs/PROJECT_STATE_INDEX.md`
- `README.md`

Inspected archived operator/Library material available in the review context:
- `IIOS_Pilot_Response_山东赫达_002810_20261012.json` — archived structured AI research response, 13,285 bytes / 219 lines.
- `IIOS_山东赫达_002810_试运行研究摘要_20261012.md` — separate research summary, 6,168 bytes.

Those two artifacts were available through the user's file Library; they were **not** present in the public Git repository. The response JSON is research input/return content; the Markdown summary is a separate narrative artifact. Neither one, alone or together, proves that the current launcher wrote a local run directory or generated a bound `analysis.json`, `report.md`, and `pilot_receipt.json`.

The current private macOS run directory under `~/.iios-private/local-pilot/runs/` was not available to this review. Accordingly, this audit does not claim that the latest local application run, its receipt, file permissions or output replay have passed independent inspection.

## 2. What is already implemented

The current local pilot already provides:
- one-click macOS entry and guided case/price/cutoff/position input;
- an operator-attested price class that remains distinct from source-verified market data;
- a ChatGPT browser prompt and a dedicated JSON response-file handoff;
- current-version input/response validation, including source-reference, cutoff/known-at, conflicting-price, scenario-ordering, Bear failure-path and independent thesis-break stress checks;
- reuse of IIOS deterministic return/entry-price calculations;
- Chinese report, machine-readable analysis, an input copy and a private local pilot record;
- explicit non-canonical status, human-approval requirement and no-trading declarations.

This is a substantial provisional workflow foundation. It must not be rebuilt as a second engine or report pipeline.

## 3. Baseline findings and defects

### B0-01 — The archived response predates the current response contract

The archived 2026-10-12 response includes the candidate, operator-attested price metadata, an evidence register, structured assessments and Bear/Base/Bull scenario inputs. It does **not** contain `forecast_valuation.thesis_break_stress`.

The current `_validate_guided_research_response()` contract requires the independent thesis-break stress case and validates its trigger, operating impact, valuation method, rationale and quantified terminal value. Therefore, the archived response must not be treated as a current-version accepted response. Re-open the existing repair-prompt flow or regenerate the response using the current prompt; do not weaken the validator to accept a stale response.

### B0-02 — The available report-like artifact is not a runner-bound output

The archived Markdown research summary is not linked here to a local pilot ID, a runner-generated `analysis.json`, or a `pilot_receipt.json`. Its existence does not establish that the current application completed the workflow. It remains useful for checking the economic narrative and assumptions, but not for product-run acceptance.

### B0-03 — Evidence quality is explicitly provisional

The archived response keeps Trust at UNKNOWN, Reality/Quality conditional, Thesis at WATCH, MIE as NOT_IDENTIFIABLE, expectation gap as UNKNOWN, and risk as UNKNOWN. Its scenario assumptions are explicitly uncalibrated. Those states are directionally conservative: the response does not establish a formal positive expectation gap or formal evidence admission, and it must not be used to justify a canonical BUY/ADD.

The source register is a set of references and summaries, not proof that the exact original bytes were captured and admitted, the facts independently rechecked, or applicable source-use rights resolved. The operator-attested price is not upgraded by being repeated in the response.

### B0-04 — Run record/replay semantics still need a later functional correction

In the current implementation, the local pilot record stores run identity, file names, time and optional `replay_of`, but it does not bind the output files with per-file hashes. The current replay-labelled path creates a new run from an input; it does not load a prior receipt and compare the prior run's output with recomputed output. A `PILOT_REPLAY_RECOMPUTED` label therefore must not be read as proof that equality was independently verified.

This is a concrete later-batch defect. Correcting it belongs in the reliability/reproducibility batch, not by expanding speculative adversarial permutations in Batch 0.

### B0-05 — A real private run bundle remains unverified

This review did not inspect the actual macOS output directory. Existence, privacy permissions, operator input binding, report/JSON agreement and replay behavior of that actual bundle remain **NOT VERIFIED**. Keep this status open until the real private bundle is available for review; it does not block continuing code work on the provisional pilot.

## 4. Boundary decisions

- Preserve the archived operator response and summary as diagnostic material; do not copy their private payloads or quote value into the public repository.
- Do not re-run web research or redo the 山东赫达 company analysis as part of this baseline batch.
- Do not alter economic semantics, formal Evidence/PIT contracts, signer registry, rights records or canonical Decision state here.
- Keep the day-to-day local path labelled `PILOT_NON_CANONICAL` while free/manual ChatGPT output and operator-attested price remain non-admitted.
- Do not let formal C1/C2 gates, the non-blocking CI zero-job diagnostic, or residual tamper permutations block the next core-integration batch.

## 5. Handoff to the next batch

**Batch 0 outcome: sufficient baseline established to continue; actual local bundle inspection remains open.**

Next priority is Batch 1: integrate the existing IIOS decision capabilities into one working, candidate-driven provisional research chain. Use a response that passes the *current* contract, retain explicit UNKNOWN states, and reuse the existing calculation/report code. Once the minimal core chain is connected, run a real company immediately and iterate from observed defects. The run/replay implementation should subsequently be corrected so a replay means a verified comparison, not merely creation of a second run record.

## 6. Acceptance status

| Check | Result | Evidence basis |
|---|---|---|
| Current pilot entry/schema capability inspected | PASS | Canonical source inspection |
| Archived 002810 response inspected | PASS, limited to archived input | Library artifact; not a runner receipt |
| Archived response conforms to current stress-case contract | FAIL / STALE INPUT | Required `forecast_valuation.thesis_break_stress` absent |
| Narrative report proven to be generated by current runner | NOT VERIFIED | No linked local analysis/receipt bundle was available |
| Real Mac private bundle inspected | NOT VERIFIED | Operator environment not directly available |
| Formal Evidence/PIT or canonical Decision admitted | NO | Explicitly outside this provisional baseline batch |
