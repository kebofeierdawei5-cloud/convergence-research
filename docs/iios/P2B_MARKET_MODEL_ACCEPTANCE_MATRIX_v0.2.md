# P2-B Market Model Acceptance Matrix v0.2

Date: 2026-10-04
Status: FROZEN AS FOUNDATION / EXECUTION PENDING

This matrix is the canonical acceptance boundary for P2-B foundation work. It defines what the typed market-model domain must be able to represent and reject before a production identification algorithm is built.

## A. Model-semantic coverage

| ID | Model family | Required market-economic semantics | Acceptance |
|---|---|---|---|
| MM-01 | PE | forward EPS / earnings | Candidate and feasible solution MUST remain EPS/earnings based. |
| MM-02 | PS | revenue | MUST NOT be converted to implied net profit. |
| MM-03 | PB | book equity | MUST retain book-equity semantics. |
| MM-04 | EV/EBITDA | EBITDA + enterprise-value bridge | MUST preserve EBITDA and EV bridge separately. |
| MM-05 | DCF | FCF / growth / margin / reinvestment / terminal assumptions | MUST represent assumptions; MUST NOT manufacture implied net profit. |
| MM-06 | DDM | dividend / payout / growth / discount rate | MUST represent dividend-model assumptions. |
| MM-07 | SOTP | segment value + residual value | MUST retain segment/residual construction. |
| MM-08 | rNPV | pipeline value + probability + timing | MUST retain pipeline probability/timing semantics. |

## B. Identification-state coverage

| ID | Scenario | Expected state | Hard prohibition |
|---|---|---|---|
| MM-09 | One materially preferred feasible model remains | IDENTIFIABLE | Selected model must be one of feasible models. |
| MM-10 | Two or more materially different feasible models remain | AMBIGUOUS | No selected model may be forced. |
| MM-11 | No supported feasible model remains | UNIDENTIFIABLE | No selected model. |
| MM-12 | Evidence cannot distinguish a supported interpretation | INSUFFICIENT_EVIDENCE | No selected model. |
| MM-13 | Reasonable perturbation changes interpretation | UNSTABLE | Must not report stable interpretation. |
| MM-14 | Interpretation remains materially stable under admissible perturbations | STABLE | Stability must retain an explicit assessment basis. |

## C. Admission / fit coverage

| ID | Scenario | Expected behavior |
|---|---|---|
| MM-15 | Mathematical inverse exists but no supporting market evidence | Candidate is not admissible as evidence-backed. |
| MM-16 | Candidate has required observable/economic variables and evidence basis | Candidate can enter fit evaluation. |
| MM-17 | Fit is FEASIBLE | Fit must retain evidence IDs and diagnostics. |
| MM-18 | Feasible solution set is NONEMPTY | At least one model-consistent solution and evidence provenance are required. |
| MM-19 | Feasible solution set is EMPTY | Solutions MUST be absent. |
| MM-20 | Feasible solution set lacks evidence | MUST fail validation. |

## D. Cross-domain invariants

| ID | Invariant | Acceptance |
|---|---|---|
| MM-21 | Solution model mismatch | MUST fail validation. |
| MM-22 | IDENTIFIABLE without a feasible selected model | MUST fail validation. |
| MM-23 | AMBIGUOUS with fewer than two feasible models | MUST fail validation. |
| MM-24 | AMBIGUOUS / UNIDENTIFIABLE / INSUFFICIENT_EVIDENCE with a selected model | MUST fail validation. |
| MM-25 | STABLE without perturbation/regime evidence | MUST fail validation at the foundation layer. |
| MM-26 | P2-B output attempts to force BUY | MUST be rejected; decision gating is downstream of P2-B. |

## E. Explicit non-goals

P2-B foundation does NOT define:

- a universal model score;
- a numeric identifiability threshold;
- a numeric stability threshold;
- a production market-model classifier;
- market-implied expectation calculations;
- expectation-gap calculations;
- return or position sizing;
- automatic trading.

The typed objects are intentionally narrower than the eventual production engine. They make ambiguity, insufficiency, and instability representable without forcing a winner.
