# P0 Batch B3 — Persisted Upstream Admission and Formal Write Authorization

Date: 2026-10-10

## Decision

**MERGED / EXACT-HEAD CONTROL-PLANE REGRESSION PASS / PRODUCTION P0 REMAINS OPEN**

PR #276: https://github.com/kebofeierdawei5-cloud/convergence-research/pull/276

- Merge commit: `d3582621918b285f29b4573c2618c1072247885c`
- Validated pre-merge exact head: `f31f029b8027b19f4a8ff74fede7fdae8977f516`
- Scope: formal write authorization, not company-evidence admission or a production deployment.

## Changes accepted

1. The persisted canonical pipeline stores the exact Semantic Artifact, Semantic Producer Receipt and Admission, Forecast Admission record, Valuation Admission record/output, and a content-addressed upstream-admission bundle before recording `DECISION_ADMITTED`.
2. Formal Decision Revision, Machine Publication and Investor Review Report authorization re-open these persisted objects and validate canonical bytes, content hashes, schemas, case/cutoff identity, semantic producer/admission bindings, forecast/valuation bindings and stage-receipt references.
3. A persisted canonical run cannot downgrade to authorization based only on a Valuation reference ID: the resolver must return the exact admitted Valuation record.
4. The earlier fixture based on placeholder stage IDs/hash strings was replaced with complete synthetic TEST_ONLY lifecycle records that exercise the real authorization validators.
5. Negative compliance regression `test_p0_ce_07_formal_writers_block_when_upstream_admission_bytes_are_missing` deletes the exact semantic, valuation-output or forecast-admission bytes at each relevant writer gate. Each path expects `BLOCKED` and asserts the persisted Run Envelope remains byte-identical; formal output/report/complete Run Receipt side effects are absent on the tested blocked paths.

## Exact-head validation

All following workflows completed with conclusion `success` on exact PR head `f31f029b8027b19f4a8ff74fede7fdae8977f516`:

- IIOS P0 Canonical Entry Incident Reproduction
- IIOS B2-E Natural Language Semantic Decision E2E
- IIOS Investment Core CI
- IIOS P0 Trusted Runtime Factory
- IIOS Investor Review Report v0.2
- IIOS B04 Forecast-Valuation-Return Lineage
- IIOS B04-B Mandatory Forecast-Valuation-Return Lineage
- IIOS B00-B Authority Threat Reproduction
- IIOS B2 Semantic Producer Admission
- IIOS B2-F Fresh Independent Red-team (FR1–FR5)
- IIOS Post-B04 Independent Red-team
- IIOS MVP Pilot — Investment Core
- IIOS PILOT-02 — Xinhecheng Fresh Candidate
- IIOS C8 Auth Remediation

P0 workflow run: https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38027705399

## Acceptance boundary and non-claims

The passing lifecycle fixtures are synthetic and explicitly TEST_ONLY. This acceptance establishes that the tested formal-write gates revalidate persisted upstream admission payloads and fail closed under the tested missing-byte attacks. It does **not** prove:

- source-origin, first-public-time, licence/reuse or point-in-time admission of any 605016 evidence;
- all seven required 605016 evidence groups are admitted;
- a deployed/production-accepted first-party HTTP host or host-origin run;
- genuine production natural-language → semantic reasoning → independent Forecast → admitted Valuation → Decision conformance;
- a live full report/publication/Run Receipt replay under the deployed runtime; or
- economic validity or capital authorization.

Therefore **P0-LLM-001 and P0-LLM-004 remain OPEN**. No formal investment action or capital execution is authorized merely by this engineering acceptance.

## Next canonical gate

Continue source-by-source issuer-origin, first-public-time/PIT and reuse adjudication for `RC-CN-A-605016-20261009`, then run the unchanged B2 Evidence/PIT admission. In parallel, complete the trusted runtime/deployment provisioning and prove one genuine host-origin canonical run through upstream admission, Decision Revision, Publication, investor report and full Run Receipt replay; require independent review of that evidence before changing the production P0 status. Route A remains free-first and does not require a paid search API or LLM provider API key.
