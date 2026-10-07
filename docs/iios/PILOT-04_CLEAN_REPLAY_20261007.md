# PILOT-04 — Xinhecheng Independent Clean Replay — 2026-10-07

Status: PASS / READY FOR MERGE

## Purpose

PILOT-04 is the first independent clean replay after PILOT-03.

It asks whether the accepted PILOT-02 Xinhecheng case reproduces from canonical main in a fresh CI workspace, with fresh external evidence acquisition and the full existing Investment Core lifecycle.

## Canonical starting point

The replay branch is based directly on:

`79c5576bc4c63d3989a252401683c6691e66d998`

The workflow independently checked both the pull-request base SHA and remote `origin/main` before executing any investment code.

## Candidate contract

- Company: 浙江新和成股份有限公司
- Symbol: 002001
- Market: CN-A
- Cutoff: 2026-10-07
- Classification: NON_FINANCIAL
- Research weighting: cyclical 70% / growth 30%
- Latest admitted tradable close: 2026-09-30 at CNY 25.95

## Fresh evidence

Run #3 reacquired:

1. CNINFO 2026 H1 report;
2. Tencent historical K-line for 2026-09-30;
3. ChinaClear 2026 holiday schedule.

The static evidence bytes matched the accepted PILOT-02 values exactly:

- CNINFO report SHA-256: `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e`
- ChinaClear schedule SHA-256: `756241e1e86515b5a9bbfafdede05055344c9ac9cf7dcba38a75141ed2096fa7`

The fresh Tencent response received a new raw SHA-256:

`3716fea96259842264ee47a8c04a69c1515b127c3d4617ab803026398cb0caa5`

Its normalized 2026-09-30 historical day-row projection matched the accepted pilot exactly:

`cdbe0bfc375a5d84ed99d59a3ca925e4488607d8ad3d4df57f7b5d88962473be`

The raw Tencent bytes are therefore retained as a new source-vintage rather than incorrectly being required to match the dynamic transport payload from PILOT-02.

## Full-chain replay

Accepted remote run:

- workflow: `IIOS PILOT-04 — Xinhecheng Independent Clean Replay`
- run #3: `37632285110`
- job: `112829358751`
- overall conclusion: **SUCCESS**

All acceptance steps passed:

- canonical base assertion;
- dependency installation;
- compileall;
- fresh exact evidence acquisition;
- full Investment Core E2E;
- semantic replay equivalence;
- artifact persistence;
- git diff-check.

The replay reproduced the accepted PILOT-02 semantic fingerprint:

`acd3943850ed38ca001e4a636ba8fea6e5cf69e23b0cfb820a8ad2e398408af2`

Canonical Decision / lifecycle result:

- Trust = REVALIDATION
- Quality = CONDITIONAL
- Decision = REVIEW_REQUIRED
- Primary reason = TRUST_NOT_PASS_REQUIRES_REVIEW
- New capital = FALSE
- Human approval = TRUE
- Automatic execution = FALSE
- expected annualized return = 20.1734104046%...
- fundamental target gate = PASS
- required return gate = PASS
- risk gate = PASS
- target entry price = CNY 26.60
- Decision ID = `CN-A-002001-r001`
- Revision = 1
- Monitoring = VALID
- Validation = PASS
- Lifecycle replay = PASS
- Machine Publication QA = PASS
- Human Report QA = PASS
- deterministic report replay = TRUE

The fresh run generated new lineage hashes because its admitted Tencent raw source SHA is a new source-vintage:

- snapshot hash: `72e424ba5fa688e61e15d5b8af9ddc7451eeb733aaae8ef9d280b204e368d30b`
- revision hash: `96df16ea04b82635924c991bd514dc6d94e895451caae136268ec2287dccc0c8`
- publication hash: `7e9bc390c03e12ac3309754cdb65938aa928d9dea97a4145998e3ab9911a0ea0`
- report hash: `ca073cc344d975670e6b1b7650975a25eacd1cdc16cd8567a1cbb17dc6d3deba`
- QA hash: `d014ac3feffa7c5d8b407c6ed4c0f3dc53d8a29bd618625ff1e8a20cf429b520`

The verifier checks that these hashes are internally bound and deterministic; it does not falsely treat a fresh source-vintage as the old artifact.

## Run #2 diagnostic finding

Run #2 failed before Decision execution because the new replay receipt omitted `price_source_ref`, which the existing canonical current-price admission path requires.

That was a PILOT-04 test-harness defect, not an Investment Core semantic defect.

The same run also proved that the Tencent raw JSON transport bytes had changed while the economic observation remained the same. The verifier was redesigned to compare the normalized historical observation while retaining the fresh raw-byte SHA as provenance.

No production Investment Core semantic code was changed by these fixes.

## Acceptance

PILOT-04 is accepted because:

1. the replay started from canonical main `79c5576…`;
2. fresh primary evidence was reacquired in a clean CI runner;
3. exact static evidence and normalized market observation matched the accepted case;
4. full Investment Core E2E passed;
5. Decision/lifecycle semantic fingerprint matched the accepted PILOT-02 result;
6. Decision Revision, Monitoring, Validation, Machine Publication and Human Report remained internally bound and deterministic;
7. raw evidence receipt contains source location, raw SHA and normalized projection SHA;
8. artifact persistence and `git diff --check` passed.

PILOT-04 therefore closes as **PASS / READY FOR MERGE**.

Human usability remains a separate operator-evidence boundary and is not inferred from this technical replay.
