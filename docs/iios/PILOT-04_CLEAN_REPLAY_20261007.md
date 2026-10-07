# PILOT-04 — Xinhecheng Independent Clean Replay — 2026-10-07

Status: DEVELOPMENT / AWAITING CI

## Purpose

PILOT-04 is the first independent clean replay after PILOT-03.

It is not a new Investment Core semantic implementation. It asks a narrower question:

> Can the accepted PILOT-02 Xinhecheng case be reproduced from the canonical main baseline, using a fresh CI workspace and fresh exact-byte evidence acquisition, with the same canonical Decision, lifecycle and publication outputs?

## Canonical starting point

PILOT-04 branch must be created directly from:

`79c5576bc4c63d3989a252401683c6691e66d998`

That SHA is the canonical main after PILOT-03 state synchronization.

The replay workflow independently asserts that:

- the pull-request base SHA is `79c5576bc4c63d3989a252401683c6691e66d998`;
- remote `origin/main` is the same SHA;
- the replay does not use a diagnostic branch as its execution base.

## Candidate contract

- Company: 浙江新和成股份有限公司
- Symbol: 002001
- Market: CN-A
- Cutoff: 2026-10-07
- Classification: NON_FINANCIAL
- Research weighting: cyclical 70% / growth 30%
- 2026-10-07 is treated according to the admitted holiday evidence; latest tradable close is 2026-09-30 at CNY 25.95.

## Fresh evidence requirement

PILOT-04 reacquires, rather than copies, the three primary evidence surfaces used in PILOT-02:

1. CNINFO 2026 H1 report;
2. Tencent historical daily close for 2026-09-30;
3. ChinaClear 2026 holiday schedule.

Each is hashed from the raw bytes inside the clean CI runner. The replay must match the previously admitted SHA-256 values exactly. A changed or missing byte sequence therefore fails closed rather than silently accepting merely equivalent extracted values.

## Full-chain replay

The replay executes the existing Investment Core E2E harness from canonical main, covering:

`Reality → Quality → Value Driver → Valuation → Forecast → Return/Risk → Decision Admission → Decision Revision → Monitoring → Validation → Lifecycle Replay → Machine Publication → Human Report → Report QA`

The replay must reproduce the accepted PILOT-02 outcome:

- Trust = REVALIDATION
- Quality = CONDITIONAL
- Decision = REVIEW_REQUIRED
- New capital = FALSE
- Human approval = TRUE
- Automatic execution = FALSE
- Expected annualized return = approximately 20.1734%
- Return / required-return / risk gates = PASS
- Decision revision = r001
- Monitoring evaluation = VALID
- Validation = PASS
- Decision lifecycle replay = PASS
- Machine publication QA = PASS
- Human report QA = PASS
- deterministic report replay = TRUE

The replay also checks the exact prior decision snapshot/revision hashes and publication/report/QA content hashes.

## Acceptance

PILOT-04 is PASS only when all of the following hold:

1. canonical base SHA check passes;
2. compileall passes;
3. fresh exact evidence acquisition passes;
4. full Investment Core E2E passes;
5. exact replay equivalence against the accepted PILOT-02 oracle passes;
6. artifact publication succeeds;
7. `git diff --check` passes.

No production Investment Core semantic code should be changed by PILOT-04.

## Failure interpretation

- If the base-SHA check fails: infrastructure / branch hygiene defect.
- If a fresh source byte hash differs: external evidence-vintage drift; fail closed.
- If the Decision/lifecycle/publication hashes differ while inputs match: deterministic replay regression requiring investigation.
- If only the network acquisition fails: external endpoint instability, not evidence of Investment Core semantic failure.

Human usability remains separate from this technical replay and cannot be inferred from CI.
