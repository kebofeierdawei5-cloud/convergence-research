# PILOT-04 — Xinhecheng Independent Clean Replay — 2026-10-07

Status: DEVELOPMENT / REPLAY IN PROGRESS

## Purpose

PILOT-04 is the first independent clean replay after PILOT-03.

It asks whether the accepted PILOT-02 Xinhecheng case reproduces from canonical main in a fresh CI workspace, with fresh external evidence acquisition and the full existing Investment Core lifecycle.

## Canonical starting point

The replay branch is based directly on:

`79c5576bc4c63d3989a252401683c6691e66d998`

The workflow independently checks both the pull-request base SHA and remote `origin/main` before executing any investment code.

## Candidate contract

- Company: 浙江新和成股份有限公司
- Symbol: 002001
- Market: CN-A
- Cutoff: 2026-10-07
- Classification: NON_FINANCIAL
- Research weighting: cyclical 70% / growth 30%
- Latest admitted tradable close: 2026-09-30 at CNY 25.95

## Fresh evidence

The clean runner reacquires:

1. CNINFO 2026 H1 report;
2. Tencent historical K-line for 2026-09-30;
3. ChinaClear 2026 holiday schedule.

Raw evidence is always SHA-256 hashed at acquisition. The static company report and holiday-page bytes must match the previously accepted exact bytes.

The Tencent endpoint contains dynamic quote metadata outside the historical day row. Therefore the replay does **not** incorrectly require the whole dynamic JSON blob to have the same raw-byte hash as PILOT-02. Instead:

- the fresh raw Tencent blob receives its own raw SHA-256 and remains part of the new evidence receipt;
- the canonical 2026-09-30 day-row projection is normalized and hashed;
- the normalized historical observation must match the previously accepted projection exactly;
- the Investment Core still admits the newly captured raw bytes with its own provenance and hash.

This preserves evidence provenance without conflating dynamic transport bytes with the economic observation being replayed.

## Full-chain replay

The existing production E2E harness is run from the clean branch, covering:

`Reality → Quality → Value Driver → Valuation → Forecast → Return/Risk → Decision Admission → Decision Revision → Monitoring → Validation → Lifecycle Replay → Machine Publication → Human Report → Report QA`

PILOT-04 compares a stable semantic fingerprint against the accepted PILOT-02 result, rather than requiring all lineage hashes to remain byte-identical when the fresh market-data artifact is a new source-vintage.

The replay must preserve:

- Trust = REVALIDATION
- Quality = CONDITIONAL
- Decision = REVIEW_REQUIRED
- New capital = FALSE
- Human approval = TRUE
- Automatic execution = FALSE
- expected annualized return = 20.1734%...
- return / required-return / risk gates = PASS
- Decision revision = r001
- Monitoring = VALID
- Validation = PASS
- lifecycle replay = PASS
- Machine Publication / Human Report QA = PASS
- deterministic human-report replay = TRUE

The fresh Decision Snapshot / Revision / Publication hashes are allowed to differ because the newly admitted market-data raw SHA is intentionally new. Their internal bindings must remain self-consistent.

## Known run #2 finding

The first execution version of PILOT-04 failed in the replay harness because the newly constructed receipt omitted `price_source_ref`, which the existing canonical current-price admission path requires.

At the same time, fresh Tencent raw bytes produced SHA:

`69e540826fd6a6cee3ee8072732502658d0e727d55434fa88b111225ff1d4388`

versus PILOT-02's previously captured raw SHA:

`637bd885980763b1eea5ce63e7b255746e4a4c6ade4ec8981dabbad75635405b`.

The historical 2026-09-30 observation itself remained CNY 25.95. The corrected verifier therefore treats the raw SHA as fresh-vintage evidence and the normalized day-row hash as the replay equivalence key.

No Investment Core production semantics were changed.

## Acceptance

PILOT-04 is PASS only when:

1. canonical base SHA check passes;
2. compileall passes;
3. fresh exact evidence acquisition passes;
4. full Investment Core E2E passes;
5. stable Decision/lifecycle semantic fingerprint matches the accepted PILOT-02 result;
6. new Decision/Revision/Publication hashes bind internally and remain deterministic;
7. raw evidence receipt is fully populated with source, raw SHA and projection SHA;
8. artifact persistence and `git diff --check` pass.

Human usability remains outside this technical gate.
